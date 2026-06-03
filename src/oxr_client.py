import datetime as dt
from decimal import Decimal

import requests
from pydantic import BaseModel, ConfigDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config, TARGET_CURRENCIES


class OxrError(RuntimeError):
    """Raised when an OXR request fails or returns an unexpected payload."""


class OxrSnapshot(BaseModel):
    """A single date's USD-base rates plus the source's published timestamp."""

    model_config = ConfigDict(frozen=True)

    date: dt.date
    rates: dict[str, Decimal]
    timestamp: dt.datetime  # OXR `timestamp` (epoch seconds) → UTC


class OxrClient:

    def __init__(self, config: Config, timeout: float = 30.0):
        self.config = config
        self.timeout = timeout
        self.session = requests.Session()

        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._symbols = ",".join(dict.fromkeys(("EUR", *TARGET_CURRENCIES)))

    def fetch_historical(self, date: dt.date) -> OxrSnapshot:
        """Return the USD-base rates and source timestamp for a single date."""
        url = f"{self.config.base_url}/historical/{date.isoformat()}.json"
        try:
            resp = self.session.get(
                url,
                params={"app_id": self.config.app_id, "symbols": self._symbols},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise OxrError(f"OXR request failed for {date}: {exc}") from exc

        body = resp.json(parse_float=Decimal)
        rates = body.get("rates")
        if not isinstance(rates, dict) or not rates:
            raise OxrError(f"OXR response for {date} missing 'rates': {body!r}")
        epoch = body.get("timestamp")
        if not isinstance(epoch, (int, float)):
            raise OxrError(f"OXR response for {date} missing 'timestamp': {body!r}")
        timestamp = dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)
        return OxrSnapshot(date=date, rates=rates, timestamp=timestamp)

