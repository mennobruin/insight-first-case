"""The idempotency contract (MERGE) and the create→merge write path."""
from datetime import date, datetime, timezone
from decimal import Decimal

from bigquery_writer import BigQueryWriter
from models import ExchangeRate

TS = datetime(2026, 6, 2, 23, 59, 59, tzinfo=timezone.utc)
NOW = datetime(2026, 6, 3, tzinfo=timezone.utc)
RATES = [
    ExchangeRate(date=date(2026, 6, 2), currency="USD", rate=Decimal("0.873"), published_at=TS, fetched_at=NOW),
    ExchangeRate(date=date(2026, 6, 2), currency="GBP", rate=Decimal("1.183"), published_at=TS, fetched_at=NOW),
]


def test_merge_matches_on_key_and_updates_only_on_change(config, mocker):
    """No duplicate rows on re-run; existing values updated only when the rate changes."""
    sql = BigQueryWriter(config, client=mocker.Mock()).merge_sql()
    
    assert "MERGE `proj.ds.exchange_rates`" in sql
    assert "ON T.date = S.date AND T.currency = S.currency" in sql
    assert "WHEN MATCHED AND T.rate != S.rate THEN UPDATE SET" in sql
    assert "rate = S.rate" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_upsert_merges_rates_inline(config, mocker):
    client = mocker.Mock()
    writer = BigQueryWriter(config, client=client)

    assert writer.upsert(RATES) == 2

    sqls = [c.args[0] for c in client.query.call_args_list]
    assert any(s.startswith("MERGE") for s in sqls)

    merge_call = next(c for c in client.query.call_args_list if c.args[0].startswith("MERGE"))
    params = merge_call.kwargs["job_config"].query_parameters
    assert len(params) == 1 and params[0].name == "rates"
    assert len(params[0].values) == 2  # one struct per row, passed safely as a param


def test_upsert_empty(config, mocker):
    client = mocker.Mock()
    
    assert BigQueryWriter(config, client=client).upsert([]) == 0
    client.query.assert_not_called()
