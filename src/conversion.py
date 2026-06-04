"""Convert OXR USD-base rates into EUR-base rows (EUR per 1 unit of currency)."""
from datetime import date, datetime
from decimal import Decimal

from config import TARGET_CURRENCIES
from models import ExchangeRate


class MissingCurrencyError(ValueError):
    """Raised when a required currency is absent or unusable in the OXR payload."""


def to_eur_rates(
    usd_base_rates: dict[str, Decimal],
    rate_date: date,
    rate_timestamp: datetime,
    fetched_at: datetime,
    targets: tuple[str, ...] = TARGET_CURRENCIES,
) -> list[ExchangeRate]:
    """Convert USD-base quotes to EUR-base rows.

    OXR returns ``rates[X]`` = units of X per 1 USD. 
    The value of 1 unit of currency X in EUR is therefore ``rates["EUR"] / rates[X]``.
    """
    eur_per_usd = usd_base_rates.get("EUR")
    if not eur_per_usd:  # missing or zero -> cannot establish EUR base
        raise MissingCurrencyError(
            "EUR rate missing or zero in OXR response; cannot convert to EUR base"
        )

    rates: list[ExchangeRate] = []
    for currency in targets:
        currency_per_usd = usd_base_rates.get(currency)
        if not currency_per_usd:
            raise MissingCurrencyError(f"{currency} rate missing or zero in OXR response")
        rates.append(
            ExchangeRate(
                date=rate_date,
                currency=currency,
                rate=eur_per_usd / currency_per_usd,
                rate_timestamp=rate_timestamp,
                fetched_at=fetched_at,
            )
        )
    return rates
