from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RateRow(BaseModel):

    model_config = ConfigDict(frozen=True)

    date: date
    currency: str
    rate: Decimal  # EUR per 1 unit of `currency` (BigQuery BIGNUMERIC)
    rate_timestamp: datetime  # when the OXR source published the rate
    fetched_at: datetime  # when we fetched/wrote the row
