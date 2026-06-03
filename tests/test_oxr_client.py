"""OXR payload parsing: rates + source timestamp, and error handling."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import requests

from oxr_client import OxrClient, OxrError

BODY = {
    "timestamp": 1780444799,  # 2026-06-02 23:59:59 UTC
    "base": "USD",
    "rates": {
        "CHF": Decimal("0.815974"),
        "EUR": Decimal("0.873117"),
        "GBP": Decimal("0.737614"),
        "JPY": Decimal("142.42825"),
    },
}


def _resp(mocker, *, status=200, json_body=None):
    r = mocker.Mock(spec=requests.Response)
    r.json.return_value = json_body or {}
    r.raise_for_status.side_effect = (
        requests.HTTPError(str(status)) if status >= 400 else None
    )
    return r


def test_parses_rates_and_source_timestamp(config, mocker):
    mocker.patch("requests.Session.get", return_value=_resp(mocker, json_body=BODY))
    snap = OxrClient(config).fetch_historical(date(2026, 6, 2))
    assert snap.rates["EUR"] == Decimal("0.873117")
    assert snap.timestamp == datetime(2026, 6, 2, 23, 59, 59, tzinfo=timezone.utc)


def test_sends_app_id_and_symbols_as_query_params(config, mocker):
    get = mocker.patch("requests.Session.get", return_value=_resp(mocker, json_body=BODY))
    client = OxrClient(config)
    client.fetch_historical(date(2026, 6, 2))
    params = get.call_args.kwargs["params"]
    assert params["app_id"] == "test-key"
    assert params["symbols"] == "EUR,USD,GBP,JPY,CHF"


def test_raises_oxr_error_on_http_failure(config, mocker):
    mocker.patch("requests.Session.get", return_value=_resp(mocker, status=429))
    with pytest.raises(OxrError):
        OxrClient(config).fetch_historical(date(2026, 6, 2))
