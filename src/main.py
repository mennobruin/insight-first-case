""" entrypoint: fetch last N days of rates → convert to EUR base → upload to BigQuery if new data is available. """
from datetime import date, datetime, timedelta, timezone
import logging
import os
import sys

from bigquery_writer import BigQueryWriter
from config import DAYS_TO_FETCH, Config
from conversion import MissingCurrencyError, to_eur_rates
from models import RateRow
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
    """Execute the job. Returns a process exit code (0 = success)."""
    client = OxrClient(config)
    writer = BigQueryWriter(config)
    fetched_at = datetime.now(tz=timezone.utc)
    today = fetched_at.date()

    rows: list[RateRow] = []
    fetch_failures = 0
    data_failures = 0
    
    for rate_date in last_n_days(n=DAYS_TO_FETCH, today=today):
        try:
            snapshot = client.fetch_historical(rate_date)
            rows.extend(
                to_eur_rates(snapshot.rates, rate_date, snapshot.timestamp, fetched_at)
            )
        except OxrError:
            # Transient/per-day fetch problem: skip this date, keep the rest.
            fetch_failures += 1
            logger.warning(f"Skipping {rate_date} due to fetch error", exc_info=True)
        except MissingCurrencyError:
            # This date's payload is unusable; skip it rather than the whole run.
            data_failures += 1
            logger.warning(f"Skipping {rate_date} due to data error", exc_info=True)

    if not rows:
        logger.error(
            f"No rates collected across {DAYS_TO_FETCH} day(s) "
            f"({fetch_failures} fetch / {data_failures} data failures); "
            "nothing to write"
        )
        return 1

    written = writer.upsert(rows)
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
        sys.exit(run(Config()))
    except Exception:
        logger.exception("Unhandled error; job failed", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
