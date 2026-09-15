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
  demand refunds and CP L1.

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
  incentives, demand refunds, commission %, CP L1 €, CP L1 %, WoW deltas,
  MTD GMV and projected full-month GMV.
- Each weekly tab also expands the top 20 partners into a DI breakdown by
  campaign objective (Bolt spend vs provider spend) and an accounting bridge.
  BRSM is pinned as an example.
- Commission % and CP L1 / CP L2: `fact_provider_weekly`, same naming as
  `fetch_weekly_data.py`.
  - **CP L1** = `total_contribution_profit_eur` = reporting revenue − variable
    costs. Variable costs do **not** include demand incentives.
  - **CP L2** = `total_contribution_profit_without_demand_incentives_eur` = CP L1
    minus demand incentives (and a small residual for menu-DI accounting on a
    handful of partners).
- **Total reporting revenue** is itemised into invoiced provider commission,
  eater fee revenue, Bolt+ agency fee, other invoiced revenue and an invoicing
  reconciliation residual. The residual closes the block exactly for all 146
  partners; it is needed because the four named components leave a gap of about
  1.7% in absolute terms (83 of 146 partners are within €1, worst case €119).
  Eater fee revenue is kept whole: splitting it into service fee, small order
  fee and delivery price does not reconcile (off by ~8%), so those sit in a
  clearly labelled memo instead of the bridge.
- The partner bridge shows: total reporting revenue → itemised **CP L1 costs** +
  **Total costs in CP L1** → **CP L1** → **CP L2 costs** (demand incentives) +
  **Total costs in CP L2** → **CP L2**. Revenue line items sit in a collapsed
  “How reporting revenue is built” block so DI never appears inside the CP L1
  cost list.
- `Other variable costs` in the bridge is a residual (total variable costs minus
  courier costs, refunds and fraud) and carries supply incentives with it. Supply
  incentives are not broken out separately because at partner level they are not
  a clean subset of total variable costs — subtracting them as their own line
  makes the residual negative for about half the partners. As defined, the
  residual is non-negative for all 146 partners and is roughly 20% of the cost
  base.
- Refund causes: latest non-deleted reason from `delivery_order_user_refund` joined to `delivery_order_user_refund_reason`.
- Programs: named campaigns, objective, campaign type, attributed orders and
  Bolt spend from `dim_order_campaign_delivery` and `dim_campaign_delivery_v2`.
- Campaign objectives come from `dim_campaign_delivery_v2.campaign_spend_objective`.
  All 24 values seen in UA 3P stores are mapped to a readable label, a
  “funded by” hint and a description, shown as a tooltip in the partner DI table
  and in full under “DI objective glossary” on each weekly tab. The glossary
  lives in `OBJECTIVES` in `cumulative-report.js`. The table carries no column
  comments for these values, so the descriptions were derived from campaign names
  and the Bolt/provider spend split — funding is authoritative only in the spend
  columns. Note the `provider_campaign_*` prefix means the campaign was created
  in the partner-campaign framework, not that the partner funded it: the split is
  set by the “% On Provider” share in the campaign name.
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

The report refreshes itself every Monday at 10:00 Kyiv time through the
`Update Stores Cumulative Weekly Report` GitHub Actions workflow, which rebuilds
`data.json`, verifies it and commits the result. Because cron only accepts UTC,
the workflow registers both 07:00 and 08:00 UTC and a guard step lets through
only the one matching Kyiv's current offset, so the time holds across the
daylight-saving switch. GitHub may start a scheduled job a few minutes later.

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
