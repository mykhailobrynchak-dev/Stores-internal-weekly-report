# Stores WoW analysis

Interactive snapshot covering 13 full/partial weeks from 11 May through 13 August 2026.

## Scope and definitions

- Ukraine 3P Stores: `delivery_vertical LIKE 'store_3p%'`, plus ANRI-PHARM, BRSM, VAPORS and PIVASOV to match the internal weekly report.
- GMV and orders: delivered orders only.
- Active partners: partner groups with at least one delivered order in the period.
- Demand incentives: `demand_incentives_eur` on delivered orders.
- Demand refunds: `demand_refunds_eur` across all order states. The observed current-week refunds were all on delivered orders.
- Current-week WoW: Monday–Thursday 10–13 August against Monday–Thursday 3–6 August.
- Monetary values: EUR.

## Files

- `index.html` — interactive report.
- `data.json` — Databricks snapshot generated on 14 August 2026.
- `query.sql` — core weekly partner query.
