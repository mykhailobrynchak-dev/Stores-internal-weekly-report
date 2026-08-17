# Stores WoW analysis

Interactive snapshot covering 13 full/partial weeks from 11 May through 13 August 2026.

## Scope and definitions

- Ukraine 3P Stores: `delivery_vertical LIKE 'store_3p%'`, plus ANRI-PHARM, BRSM, VAPORS and PIVASOV to match the internal weekly report.
- GMV and orders: delivered orders only.
- Active partners: partner groups with at least one delivered order in the period.
- Demand incentives: `demand_incentives_eur` on delivered orders.
- Demand refunds: `demand_refunds_eur` across all order states. The observed current-week refunds were all on delivered orders.
- Current-week WoW: Monday–Thursday 10–13 August against Monday–Thursday 3–6 August.
- Refund causes: latest non-deleted reason from `delivery_order_user_refund` joined to `delivery_order_user_refund_reason`.
- Campaign drivers: named campaigns from `dim_order_campaign_delivery` and `dim_campaign_delivery_v2`; fact-level objective totals remain the financial source of truth.
- Refund liability is not the same as operational fault: all 30 current refunds are Bolt-liable, while actor-at-fault is unknown for 29.
- All partners table: every metric is the last full week (10–16 August), with WoW comparing against the prior full week (3–9 August). Orders, GMV, demand incentives and refunds come from `fact_order_delivery`; commission and CM L1 from `fact_provider_weekly`. Last-week delivered orders total 12,381.
- Commission % / € and CM L1: `fact_provider_weekly`. Last week is the full week 10–16 August; prior week is the full week 3–9 August. Commission € is the GMV-weighted commission amount; Commission % is Commission of GMV. CM L1 is `total_contribution_profit_eur` (same as CP Margin in the weekly report), shown in € and as a % of `total_gmv_before_discounts_eur`.
- Monetary values: EUR.

## Files

- `index.html` — interactive report.
- `data.json` — Databricks snapshot generated on 14 August 2026.
- `query.sql` — core weekly partner query.
