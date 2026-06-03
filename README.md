# Exchange Rates → BigQuery

A daily job that fetches the last 30 days of exchange rates from
[Open Exchange Rates](https://openexchangerates.org/), converts them to a **EUR
base**, and upserts one clean analytical table in BigQuery. Designed to run as a
**Cloud Run Job** triggered daily by Cloud Scheduler.

## What it does

1. For each of the last 30 days, call `GET /historical/{date}.json` (USD base) and filter on `EUR,USD,GBP,JPY,CHF`.
2. Convert each currency to **EUR per 1 unit of currency**:
   `rate = rates["EUR"] / rates[currency]`. If `EUR` (or a target
   currency) is missing/zero, that day is skipped.
3. Upsert into BigQuery via a single idempotent `MERGE` on `(date, currency)`.

### Conversion direction

`rate` = **EUR per 1 unit of the currency**, so:

```
revenue_eur = revenue_local * rate
```

## Table: `exchange_rates`

We work under the assumption that an `exchange_rates` table already exists in BigQuery.

| column | type | meaning |
|---|---|---|
| `date` | `DATE` | The date the rate applies to. |
| `currency` | `STRING` | `USD`, `GBP`, `JPY`, `CHF`. |
| `rate` | `BIGNUMERIC` | EUR per 1 unit of `currency`. |
| `rate_timestamp` | `TIMESTAMP` | When the **source** published the rate (OXR `timestamp`). |
| `fetched_at` | `TIMESTAMP` | When **we** fetched/wrote the row. |

### Idempotency (no duplicates, updates on correction)

The rows for the window are passed inline to a single parameterized `MERGE`:

```sql
MERGE `<project>.<dataset>.exchange_rates` T
USING (SELECT * FROM UNNEST(@rows)) S
ON T.date = S.date AND T.currency = S.currency
WHEN MATCHED AND T.rate != S.rate THEN UPDATE SET
  rate = S.rate, rate_timestamp = S.rate_timestamp, fetched_at = S.fetched_at
WHEN NOT MATCHED THEN INSERT (date, currency, rate, rate_timestamp, fetched_at)
VALUES (S.date, S.currency, S.rate, S.rate_timestamp, S.fetched_at);
```

- **No duplicates on re-run** — the key match means a re-run updates in place.
- **Updates on source correction** — `WHEN MATCHED AND T.rate != S.rate` rewrites
  the row (and its `fetched_at`) only when the value actually changed, so
  `fetched_at` reflects when a rate was first seen or last corrected.

## Configuration (environment variables)

| var | required | default | notes |
|---|---|---|---|
| `OXR_APP_ID` | ✅ | — | Open Exchange Rates app id (sent as the `app_id` query parameter). |
| `GCP_PROJECT` | ✅ | — | Target GCP project. |
| `BQ_DATASET` | | `finance` | |
| `BQ_TABLE` | | `exchange_rates` | |
