# Case: Exchange Rates in BigQuery

## Situation

We use exchange rates daily to convert revenue from various countries to euros. Until now we've been doing this manually; we want to automate it.

We want a process to run every day that fetches exchange rates via the Open Exchange Rates API and stores them in BigQuery. This allows us to analyse historical data and always use the correct rate per date.

## Assignment

Create a Python function that:

- can run within Google Cloud Run (you don't need to deploy it)
- fetches the last 30 days of exchange rates (USD, GBP, JPY, CHF) — the base currency in the free version is USD
- converts everything to EUR as the base currency
- saves or updates the results in BigQuery
- includes proper logging and error handling
- includes a few simple tests that verify the update logic is correct and prevent errors (e.g. what if EUR is missing)

## Important

- If the script runs multiple times, no duplicate rows should be created.
- If a rate for a given day changes (for example because the source corrects its data), the existing value must be updated.
- The data must be usable for analysis — so one clear table with date, currency, and rate.
- We also want to be able to see when the data was fetched.

## Requirements

You can sign up for the free plan at Open Exchange Rates: https://openexchangerates.org/signup/free in order to call the API.

## What you deliver

A Git repo that you share with us. We will walk through it together in the interview and ask you to explain your choices.

## Guideline

You don't need to build a perfect architecture; we mainly want to see how you approach this and what choices you make.
