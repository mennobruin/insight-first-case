"""Orchestration: collect all days then upsert once; tolerate a single bad date."""
from datetime import date, datetime, timezone

import pytest

import main as m
from oxr_client import OxrError, OxrSnapshot

RATES = {"EUR": 0.873117, "USD": 1.0, "GBP": 0.737614, "JPY": 142.42825, "CHF": 0.815974}


def _snap(rate_date):
    return OxrSnapshot(date=rate_date, rates=RATES, timestamp=datetime(2026, 6, 2, tzinfo=timezone.utc))


@pytest.fixture
def patched(mocker, config):
    client = mocker.Mock()
    writer = mocker.Mock()
    writer.upsert.return_value = 8
    # Pin the fetch window to two dates so the orchestration assertions are exact.
    mocker.patch.object(m, "last_n_days", return_value=[date(2026, 6, 1), date(2026, 6, 2)])
    mocker.patch.object(m, "OxrClient", return_value=client)
    mocker.patch.object(m, "BigQueryWriter", return_value=writer)
    return client, writer


def test_collects_all_days_then_upserts_once(patched, config):
    client, writer = patched
    client.fetch_historical.side_effect = _snap
    assert m.run(config) == 0
    writer.upsert.assert_called_once()
    assert len(writer.upsert.call_args.args[0]) == 2 * 4  # 2 days × 4 currencies


def test_skips_a_failed_date_but_still_writes_the_rest(patched, config):
    client, writer = patched
    client.fetch_historical.side_effect = [OxrError("boom"), _snap(date(2026, 6, 2))]
    assert m.run(config) == 0
    assert len(writer.upsert.call_args.args[0]) == 4  # only the good day


def test_skips_a_data_error_date_but_still_writes_the_rest(patched, config):
    client, writer = patched
    # First day's payload is missing EUR → unusable; second day is fine.
    bad = OxrSnapshot(
        date=date(2026, 6, 1),
        rates={"USD": 1.0, "GBP": 0.737614},
        timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    client.fetch_historical.side_effect = [bad, _snap(date(2026, 6, 2))]
    assert m.run(config) == 0
    assert len(writer.upsert.call_args.args[0]) == 4  # only the good day


def test_returns_nonzero_when_nothing_collected(patched, config):
    client, writer = patched
    client.fetch_historical.side_effect = OxrError("boom")
    assert m.run(config) == 1
    writer.upsert.assert_not_called()
