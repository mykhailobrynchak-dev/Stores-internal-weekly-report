# Stores cumulative weekly report

An accumulating report covering every complete week from 11 May 2026 onward.
Running the build script adds the newest completed week and its tab automatically.

## Report structure

- **Overview** — cumulative KPIs, weekly trends, top 15 cumulative partners,
  latest-week demand-cost contributors, and top 15 programs across the period.
- **One tab per complete week** — weekly KPIs and WoW, month-to-date actuals,
  straight-line full-month projection, top 20 partners across all metrics,
  top programs and refund reasons.
- Partner ranking can be switched between GMV, orders, demand incentives,
  demand refunds and CM L1.

Every comparison uses complete weeks. MTD compares the same number of calendar
days with the prior month. Projection is `MTD / elapsed calendar days × days in
month`; it is a run-rate estimate, not a seasonality-adjusted forecast.

## Scope and definitions

- Ukraine 3P Stores: `delivery_vertical LIKE 'store_3p%'`, plus ANRI-PHARM, BRSM, VAPORS and PIVASOV to match the internal weekly report.
- GMV and orders: delivered orders only.
- Active partners: partner groups with at least one delivered order in the period.
- Demand incentives: `demand_incentives_eur` on delivered orders.
- Demand refunds: `demand_refunds_eur` across all order states, divided by delivered GMV for rates.
- Weekly partner tables: top 20 partners with orders, GMV, AOV, demand
  incentives, demand refunds, commission %, CM L1 €, CM L1 %, WoW deltas,
  MTD GMV and projected full-month GMV.
- Commission % and CM L1: `fact_provider_weekly`. Commission % is commission as a share of GMV. CM L1 is `total_contribution_profit_eur` (the same figure as CP Margin in the weekly report), shown in € and as a % of `total_gmv_before_discounts_eur`.
- Refund causes: latest non-deleted reason from `delivery_order_user_refund` joined to `delivery_order_user_refund_reason`.
- Programs: named campaigns, objective, campaign type, attributed orders and
  Bolt spend from `dim_order_campaign_delivery` and `dim_campaign_delivery_v2`.
- Refund liability is not the same as operational fault: the demand refunds in scope are Bolt-liable, while actor-at-fault is recorded as unknown on almost all of them.
- Monetary values: EUR.

## Files

- `index.html` — interactive report.
- `cumulative-report.js` — overview and dynamically generated weekly tabs.
- `data.json` — Databricks snapshot.
- `query.sql` — reference SQL for the main slices.
- `build_report.py` — regenerates all cumulative report datasets.
- `verify_report.py` — fails the refresh if a dataset is empty, a week is missing
  or the latest week is not the one that just closed.

## Refreshing

The report refreshes itself every Monday at 10:30 Kyiv time through the
`Update Stores Cumulative Weekly Report` GitHub Actions workflow, which rebuilds
`data.json`, verifies it and commits the result. Because cron only accepts UTC,
the workflow registers both 07:30 and 08:30 UTC and a guard step lets through
only the one matching Kyiv's current offset, so the time holds across the
daylight-saving switch.

To refresh manually, either run the workflow from the Actions tab or set
`DATABRICKS_HOST`, `DATABRICKS_TOKEN` and `DATABRICKS_WAREHOUSE_ID` locally:

```bash
python3 wow-analysis/build_report.py && python3 wow-analysis/verify_report.py
```

The script derives the latest completed Sunday from the current date. No dates
need to be changed manually.

## Restatements

Source figures for a closed week can change after the fact. Orders, GMV and
refunds typically drift up by a few percent as late data arrives, but incentives
have been restated more heavily: the week of 10–16 Aug 2026 first reported
€27,674 of demand incentives and later settled at €13,562. Compare against the
current report rather than an earlier screenshot.
