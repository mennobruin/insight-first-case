"""Convert OXR USD-base rates into EUR-base rows (EUR per 1 unit of currency)."""
import datetime as dt
from decimal import Decimal

from config import TARGET_CURRENCIES
from models import RateRow


class MissingCurrencyError(ValueError):
    """Raised when a required currency is absent or unusable in the OXR payload."""


def to_eur_rates(
    usd_base_rates: dict[str, Decimal],
    date: dt.date,
    rate_timestamp: dt.datetime,
    fetched_at: dt.datetime,
    targets: tuple[str, ...] = TARGET_CURRENCIES,
) -> list[RateRow]:
    """Convert USD-base quotes to EUR-base rows.

    OXR free returns ``rates[X]`` = units of X per 1 USD. The value of 1 unit of
    currency X in EUR is therefore ``rates["EUR"] / rates[X]`` (USD cancels).
    """
    eur_per_usd = usd_base_rates.get("EUR")
    if not eur_per_usd:  # missing or zero → cannot establish EUR base
        raise MissingCurrencyError(
            "EUR rate missing or zero in OXR response; cannot convert to EUR base"
        )

    rows: list[RateRow] = []
    for ccy in targets:
        ccy_per_usd = usd_base_rates.get(ccy)
        if not ccy_per_usd:
            raise MissingCurrencyError(f"{ccy} rate missing or zero in OXR response")
        rows.append(
            RateRow(
                date=date,
                currency=ccy,
                rate=eur_per_usd / ccy_per_usd,
                rate_timestamp=rate_timestamp,
                fetched_at=fetched_at,
            )
        )
    return rows
