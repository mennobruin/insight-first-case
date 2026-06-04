"""The core correctness: USD-base → EUR-per-unit, and the EUR-missing guard."""
from datetime import date
from decimal import Decimal

import pytest

from conversion import MissingCurrencyError, to_eur_rates

DATE = date(2026, 6, 2)
# OXR free, USD base: value of 1 USD in each currency (+ an extra we should ignore).
USD_BASE = {
    "EUR": Decimal("0.873117"),
    "USD": Decimal("1.0"),
    "GBP": Decimal("0.737614"),
    "JPY": Decimal("142.42825"),
    "CHF": Decimal("0.815974"),
}


def test_converts_each_target_to_eur_per_unit(published_at, fetched_at):
    rates = {r.currency: r for r in to_eur_rates(USD_BASE, DATE, published_at, fetched_at)}
    
    assert rates.keys() == {"USD", "GBP", "JPY", "CHF"}
    assert rates["USD"].rate == USD_BASE["EUR"] / USD_BASE["USD"]
    assert rates["GBP"].rate == USD_BASE["EUR"] / USD_BASE["GBP"]
    assert rates["JPY"].rate == USD_BASE["EUR"] / USD_BASE["JPY"]
    assert rates["CHF"].rate == USD_BASE["EUR"] / USD_BASE["CHF"]
    assert rates["USD"].published_at == published_at
    assert rates["USD"].fetched_at == fetched_at


def test_raises_when_eur_missing(published_at, fetched_at):
    broken = {k: v for k, v in USD_BASE.items() if k != "EUR"}
    with pytest.raises(MissingCurrencyError, match="EUR"):
        to_eur_rates(broken, DATE, published_at, fetched_at)


def test_raises_when_target_currency_missing(published_at, fetched_at):
    broken = {k: v for k, v in USD_BASE.items() if k != "CHF"}
    with pytest.raises(MissingCurrencyError, match="CHF"):
        to_eur_rates(broken, DATE, published_at, fetched_at)
