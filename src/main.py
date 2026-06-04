""" entrypoint: fetch last N days of rates → convert to EUR base → upload to BigQuery if new data is available. """
from datetime import date, datetime, timedelta, timezone
import logging
import os
import sys

from bigquery_writer import BigQueryWriter
from config import DAYS_TO_FETCH, Config
from conversion import MissingCurrencyError, to_eur_rates
from models import ExchangeRate
from oxr_client import OxrClient, OxrError


logger = logging.getLogger("exchange_rates")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


def last_n_days(n: int, today: date):
    """Yield the n dates ending at `today`, oldest first."""
    for offset in range(n - 1, -1, -1):
        yield today - timedelta(days=offset)


def run(config: Config) -> int:
    """ 
    Execute a data pulling job, fetching the last 30 days of exchange rate data from the OpenExchangeRates (OXR) API.
    The data returned from OXR is in a USD base, which is then converted to EUR before being uploaded to BigQuery.
     
    Returns: a process exit code
       - 0 = success
       - 1 = failure, no rates were collected for the last 30 days
    """
    client = OxrClient(config)
    writer = BigQueryWriter(config)
    fetched_at = datetime.now(tz=timezone.utc)
    today = fetched_at.date()

    rates: list[ExchangeRate] = []
    fetch_failures = 0
    data_failures = 0

    # since the historical OXR API requires a date specified, we loop through the last DAYS_TO_FETCH days and pull data for each.
    for day_to_fetch in last_n_days(n=DAYS_TO_FETCH, today=today):
        try:
            historical_rates = client.fetch_historical(day_to_fetch)
            rates.extend(
                to_eur_rates(
                    historical_rates.rates, 
                    day_to_fetch, 
                    historical_rates.timestamp, 
                    fetched_at
                )
            )
        except OxrError:
            # Transient/per-day fetch problem: skip this date, keep the rest.
            fetch_failures += 1
            logger.warning(f"Skipping {day_to_fetch} due to fetch error", exc_info=True)
        except MissingCurrencyError:
            # This date's payload is unusable; skip it rather than the whole run.
            data_failures += 1
            logger.warning(f"Skipping {day_to_fetch} due to data error", exc_info=True)

    if not rates:
        logger.error(
            f"No rates collected across {DAYS_TO_FETCH} day(s) "
            f"({fetch_failures} fetch / {data_failures} data failures); "
            "nothing to write"
        )
        return 1

    written = writer.upsert(rates)
    logger.info(
        f"Run complete: {written} rows upserted; "
        f"{fetch_failures} fetch / {data_failures} data day(s) failed"
    )
    return 0


def check_env() -> None:
    """Fail fast with a clear message if required env vars are missing."""
    missing = [var for var in ("OXR_APP_ID", "GCP_PROJECT") if not os.environ.get(var)]
    if missing:
        raise SystemExit(f"Missing required environment variable(s): {', '.join(missing)}")


def main() -> None:
    check_env()
    try:
        config = Config()
        sys.exit(run(config))
    except Exception:
        logger.exception("Unhandled error; job failed", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
