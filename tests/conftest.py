from datetime import datetime, timezone

import pytest

from config import Config


@pytest.fixture
def config():
    return Config(
        app_id="test-key",
        gcp_project="proj",
        bq_dataset="ds",
        bq_table="exchange_rates",
    )


@pytest.fixture
def rate_timestamp():
    return datetime(2026, 6, 2, 23, 59, 59, tzinfo=timezone.utc)


@pytest.fixture
def fetched_at():
    return datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
