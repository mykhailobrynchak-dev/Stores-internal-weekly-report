# 3P Stores Ukraine — Weekly Performance Report

Live report: **https://mykhailobrynchak-dev.github.io/Stores-internal-weekly-report/**

## Overview

A comprehensive financial and operational performance dashboard for Ukraine's 3P stores segment, covering:

- **Financial Overview**: GMV, Orders, AOV, Eater Fees, CP Margins, Bolt Plus share
- **Operational Overview**: Acceptance Rate, Availability, Ratings, Honey/Bad Order Rates, Delivery Times
- **Campaign Analytics**: Bolt vs Partner investment breakdown by campaign type

## Partners Tracked

LOKO, VARUS, KOPIYKA, CAFE RYNOK, HOP HEY, BEER MARKET, TAISTRA, RUKAVYCHKA, PYVNA BORODA, + dynamically determined 10th largest

## Data Source

All data is sourced from Databricks (tables: `fact_order_delivery`, `etl_delivery_order_monetary_metrics`, `dim_provider_v2`, `etl_incentives_provider_targeting_features`).

## Automation

The report auto-updates every Monday at 06:00 UTC via GitHub Actions. Manual trigger is also available via the Actions tab.

## Setup (GitHub Secrets)

Add the following secrets to the repository:

| Secret | Description |
|--------|-------------|
| `DATABRICKS_HOST` | Databricks workspace hostname (e.g. `adb-xxx.azuredatabricks.net`) |
| `DATABRICKS_TOKEN` | Personal access token for Databricks |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path (e.g. `/sql/1.0/warehouses/xxx`) |

## Local Development

```bash
export DATABRICKS_HOST="your-host"
export DATABRICKS_TOKEN="your-token"
export DATABRICKS_HTTP_PATH="your-http-path"
pip install -r requirements.txt
python generate_report.py
```
