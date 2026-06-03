"""OXR payload parsing: rates + source timestamp, and error handling."""
import datetime as dt
from decimal import Decimal

import pytest
import requests

from oxr_client import OxrClient, OxrError

# The client parses JSON floats as Decimal (parse_float=Decimal); the mock returns
# this dict verbatim, so use Decimal here to mirror the real parsed payload.
BODY = {
    "timestamp": 1748908799,  # 2025-06-02 23:59:59 UTC
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
    snap = OxrClient(config).fetch_historical(dt.date(2026, 6, 2))
    assert snap.rates["EUR"] == Decimal("0.873117")
    assert snap.timestamp == dt.datetime(2025, 6, 2, 23, 59, 59, tzinfo=dt.timezone.utc)


def test_authenticates_via_header_not_query(config, mocker):
    """app_id travels in the Authorization header, never in the URL/query (no log leak)."""
    get = mocker.patch("requests.Session.get", return_value=_resp(mocker, json_body=BODY))
    client = OxrClient(config)
    client.fetch_historical(dt.date(2026, 6, 2))
    assert client.session.headers["Authorization"] == "Token test-key"
    assert "app_id" not in get.call_args.kwargs["params"]


def test_raises_oxr_error_on_http_failure(config, mocker):
    mocker.patch("requests.Session.get", return_value=_resp(mocker, status=429))
    with pytest.raises(OxrError):
        OxrClient(config).fetch_historical(dt.date(2026, 6, 2))
