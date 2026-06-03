"""Config validation: required env vars and a sane day window."""
import pytest
from pydantic import ValidationError

from config import Config


def test_requires_app_id(monkeypatch):
    monkeypatch.delenv("OXR_APP_ID", raising=False)
    monkeypatch.setenv("GCP_PROJECT", "proj")
    with pytest.raises(ValidationError, match="OXR_APP_ID"):
        Config()


def test_requires_gcp_project(monkeypatch):
    monkeypatch.setenv("OXR_APP_ID", "k")
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    with pytest.raises(ValidationError, match="GCP_PROJECT"):
        Config()


def test_parses_env_into_config(monkeypatch):
    monkeypatch.setenv("OXR_APP_ID", "k")
    monkeypatch.setenv("GCP_PROJECT", "proj")
    for var in ("BQ_DATASET", "BQ_TABLE"):
        monkeypatch.delenv(var, raising=False)
    cfg = Config()
    assert (cfg.app_id, cfg.gcp_project) == ("k", "proj")
    assert cfg.table_path == "proj.finance.exchange_rates"
