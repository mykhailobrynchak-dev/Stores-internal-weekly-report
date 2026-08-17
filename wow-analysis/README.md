# Stores WoW analysis

Interactive snapshot covering 14 complete weeks from 11 May through 16 August 2026.

## Periods

Every comparison in the report uses complete weeks, so no partial week-to-date
window is ever compared against a full one.

- Last full week: 10–16 August (12,381 delivered orders).
- Prior full week: 3–9 August, used for every WoW change.
- Month to date: 1–16 August against 1–16 July, the same number of days.

## Scope and definitions

- Ukraine 3P Stores: `delivery_vertical LIKE 'store_3p%'`, plus ANRI-PHARM, BRSM, VAPORS and PIVASOV to match the internal weekly report.
- GMV and orders: delivered orders only.
- Active partners: partner groups with at least one delivered order in the period.
- Demand incentives: `demand_incentives_eur` on delivered orders.
- Demand refunds: `demand_refunds_eur` across all order states, divided by delivered GMV for rates.
- All partners table: weekly columns are the last full week with WoW against the prior full week; `GMV MTD` and `MTD vs prior month` cover 1–16 August against 1–16 July. Orders, GMV, demand incentives and refunds come from `fact_order_delivery`; commission and CM L1 from `fact_provider_weekly`.
- Commission % and CM L1: `fact_provider_weekly`. Commission % is commission as a share of GMV. CM L1 is `total_contribution_profit_eur` (the same figure as CP Margin in the weekly report), shown in € and as a % of `total_gmv_before_discounts_eur`.
- Incentive objectives: an order counts as AM Spend when any of its campaign rows carries a non-zero `am_campaign_spend_bolt_eur`. Remaining objectives are grouped into families (New City, Activation, Bolt Market, Bolt Plus, Engagement, Reactivation) so each order lands in exactly one bucket. Orders with no campaign row are `Unclassified`.
- Refund causes: latest non-deleted reason from `delivery_order_user_refund` joined to `delivery_order_user_refund_reason`.
- Campaign drivers: named campaigns from `dim_order_campaign_delivery` and `dim_campaign_delivery_v2`; fact-level objective totals remain the financial source of truth.
- Refund liability is not the same as operational fault: the demand refunds in scope are Bolt-liable, while actor-at-fault is recorded as unknown on almost all of them.
- Monetary values: EUR.

## Files

- `index.html` — interactive report.
- `data.json` — Databricks snapshot.
- `query.sql` — reference SQL for the main slices.
- `refresh_data.py` — regenerates every slice in `data.json` from Databricks.

## Refreshing

Set `DATABRICKS_HOST`, `DATABRICKS_TOKEN` and `DATABRICKS_WAREHOUSE_ID`, adjust the
week constants at the top of `refresh_data.py`, then run:

```bash
python3 wow-analysis/refresh_data.py
```
