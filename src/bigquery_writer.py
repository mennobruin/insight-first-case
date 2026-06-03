import logging

from google.cloud import bigquery

from config import Config
from models import ExchangeRate

logger = logging.getLogger(__name__)

# (column name, BigQuery type) in MERGE order.
_COLUMNS = (
    ("date", "DATE"),
    ("currency", "STRING"),
    ("rate", "BIGNUMERIC"),
    ("rate_timestamp", "TIMESTAMP"),
    ("fetched_at", "TIMESTAMP"),
)


class BigQueryWriter:
    def __init__(self, config: Config, client: bigquery.Client | None = None):
        self.config = config
        self.client = client or bigquery.Client(project=config.gcp_project)

    def merge_sql(self) -> str:
        cols = ", ".join(name for name, _ in _COLUMNS)
        insert_vals = ", ".join(f"S.{name}" for name, _ in _COLUMNS)
        return (
            f"MERGE `{self.config.table_path}` T\n"
            "USING (SELECT * FROM UNNEST(@rates)) S\n"
            "ON T.date = S.date AND T.currency = S.currency\n"
            "WHEN MATCHED AND T.rate != S.rate THEN UPDATE SET\n"
            "  rate = S.rate, rate_timestamp = S.rate_timestamp, fetched_at = S.fetched_at\n"
            f"WHEN NOT MATCHED THEN INSERT ({cols})\n"
            f"VALUES ({insert_vals});"
        )

    def upsert(self, rates: list[ExchangeRate]) -> int:
        if not rates:
            logger.info("No rows to upsert; skipping.")
            return 0

        rates_param = bigquery.ArrayQueryParameter(
            "rates", "STRUCT", [self._convert_to_query_param(rate) for rate in rates]
        )
        job_config = bigquery.QueryJobConfig(query_parameters=[rates_param])
        self.client.query(self.merge_sql(), job_config=job_config).result()

        logger.info(f"Upserted {len(rates)} rows into `{self.config.table_path}`")
        return len(rates)

    @staticmethod
    def _convert_to_query_param(rate: ExchangeRate) -> bigquery.StructQueryParameter:
        values = {
            "date": rate.date,
            "currency": rate.currency,
            "rate": rate.rate,
            "rate_timestamp": rate.rate_timestamp,
            "fetched_at": rate.fetched_at,
        }
        return bigquery.StructQueryParameter(
            None,
            *(
                bigquery.ScalarQueryParameter(name, bq_type, values[name])
                for name, bq_type in _COLUMNS
            ),
        )
