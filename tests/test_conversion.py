"""The core correctness: USD-base → EUR-per-unit, and the EUR-missing guard."""
import datetime as dt
from decimal import Decimal

import pytest

from conversion import MissingCurrencyError, to_eur_rates

DATE = dt.date(2026, 6, 2)
# OXR free, USD base: value of 1 USD in each currency (+ an extra we should ignore).
USD_BASE = {
    "EUR": Decimal("0.873117"),
    "USD": Decimal("1.0"),
    "GBP": Decimal("0.737614"),
    "JPY": Decimal("142.42825"),
    "CHF": Decimal("0.815974"),
}


def test_converts_each_target_to_eur_per_unit(rate_timestamp, fetched_at):
    rows = {r.currency: r for r in to_eur_rates(USD_BASE, DATE, rate_timestamp, fetched_at)}
    # EUR per 1 unit X = rates[EUR] / rates[X], computed exactly in Decimal.
    assert rows.keys() == {"USD", "GBP", "JPY", "CHF"}
    assert rows["USD"].rate == Decimal("0.873117") / Decimal("1.0")
    assert rows["GBP"].rate == Decimal("0.873117") / Decimal("0.737614")
    assert rows["JPY"].rate == Decimal("0.873117") / Decimal("142.42825")
    assert rows["CHF"].rate == Decimal("0.873117") / Decimal("0.815974")
    assert rows["USD"].rate_timestamp == rate_timestamp


def test_raises_when_eur_missing(rate_timestamp, fetched_at):
    broken = {k: v for k, v in USD_BASE.items() if k != "EUR"}
    with pytest.raises(MissingCurrencyError, match="EUR"):
        to_eur_rates(broken, DATE, rate_timestamp, fetched_at)


def test_raises_when_target_currency_missing(rate_timestamp, fetched_at):
    broken = {k: v for k, v in USD_BASE.items() if k != "CHF"}
    with pytest.raises(MissingCurrencyError, match="CHF"):
        to_eur_rates(broken, DATE, rate_timestamp, fetched_at)
