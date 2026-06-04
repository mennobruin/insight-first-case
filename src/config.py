from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://openexchangerates.org/api"
TARGET_CURRENCIES = ("USD", "GBP", "JPY", "CHF")
DAYS_TO_FETCH = 30


class Config(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    app_id: str = Field(alias="OXR_APP_ID")
    base_url: str = Field(default=DEFAULT_BASE_URL, alias="OXR_BASE_URL")

    gcp_project: str = Field(alias="GCP_PROJECT")
    bq_dataset: str = Field(default="finance", alias="BQ_DATASET")
    bq_table: str = Field(default="exchange_rates", alias="BQ_TABLE")

    @property
    def table_path(self) -> str:  # for this example we assume a table exists named <gcp_project>.finance.exchange_rates
        return f"{self.gcp_project}.{self.bq_dataset}.{self.bq_table}"
