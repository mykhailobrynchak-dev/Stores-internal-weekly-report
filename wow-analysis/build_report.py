"""Build the cumulative Stores weekly report from Databricks.

The report always ends on the latest completed Sunday. Adding a new week only
requires running this script; index.html creates the week tab dynamically.
"""
from __future__ import annotations

import calendar
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import databricks.sql


DATA = Path(__file__).with_name("data.json")
PERIOD_START = date(2026, 5, 11)


def iso(day: date) -> str:
    return day.isoformat()


def previous_month(day: date) -> date:
    return date(day.year - (day.month == 1), 12 if day.month == 1 else day.month - 1, 1)


today = date.today()
CURRENT_WEEK_START = today - timedelta(days=today.weekday() + 7)
CURRENT_WEEK_END = CURRENT_WEEK_START + timedelta(days=6)
PRIOR_WEEK_START = CURRENT_WEEK_START - timedelta(days=7)
DAILY_START = previous_month(PERIOD_START.replace(day=1))

PARTNER = """
CASE
  WHEN p.brand_name = 'OKKO MARKET' THEN p.brand_name
  ELSE COALESCE(p.group_name, p.brand_name, f.provider_name)
END
"""

SCOPE = """
f.city_country_code = 'ua'
AND (
  p.delivery_vertical LIKE 'store_3p%'
  OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV')
)
"""

WEEKLY_SQL = f"""
SELECT
  CAST(CAST(DATE_TRUNC('week', f.order_created_date) AS DATE) AS STRING) AS week_start,
  {PARTNER} AS partner,
  SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN COALESCE(f.demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  ROUND(SUM(COALESCE(f.demand_refunds_eur, 0)), 2) AS demand_refunds_eur,
  ROUND(SUM(COALESCE(f.total_refunds_eur, 0)), 2) AS total_refunds_eur,
  SUM(CASE WHEN f.order_state = 'delivered' AND COALESCE(f.demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  SUM(CASE WHEN COALESCE(f.demand_refunds_eur, 0) != 0 THEN 1 ELSE 0 END) AS demand_refund_orders
FROM main.ng_delivery.fact_order_delivery f
JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE {SCOPE}
  AND f.order_created_date BETWEEN DATE '{iso(PERIOD_START)}' AND DATE '{iso(CURRENT_WEEK_END)}'
GROUP BY 1, 2
HAVING orders > 0 OR demand_refunds_eur != 0
ORDER BY 1, gmv_eur DESC
"""

ECONOMICS_SQL = f"""
SELECT
  CAST(f.metric_timestamp_local AS STRING) AS week_start,
  CASE WHEN p.brand_name = 'OKKO MARKET' THEN p.brand_name
       ELSE COALESCE(p.group_name, p.brand_name) END AS partner,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight), 2) AS commission_eur,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight)
    / NULLIF(SUM(f.provider_commission_gmv_share_weight), 0) * 100, 2) AS commission_gmv_pct,
  ROUND(SUM(f.total_contribution_profit_eur), 2) AS cm_l1_eur,
  ROUND(SUM(f.total_contribution_profit_eur)
    / NULLIF(SUM(f.total_gmv_before_discounts_eur), 0) * 100, 2) AS cm_l1_pct,
  ROUND(SUM(f.total_gmv_before_discounts_eur), 2) AS economics_gmv_eur
FROM main.ng_delivery.fact_provider_weekly f
JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND (p.delivery_vertical LIKE 'store_3p%'
       OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV'))
  AND f.metric_timestamp_local BETWEEN DATE '{iso(PERIOD_START)}' AND DATE '{iso(CURRENT_WEEK_START)}'
GROUP BY 1, 2
HAVING SUM(f.delivered_orders_count) > 0
ORDER BY 1, economics_gmv_eur DESC
"""

CAMPAIGNS_SQL = f"""
SELECT
  CAST(CAST(DATE_TRUNC('week', oc.order_created_date) AS DATE) AS STRING) AS week_start,
  COALESCE(cd.campaign_name, 'Unnamed campaign') AS campaign,
  COALESCE(cd.campaign_spend_objective, 'unclassified') AS objective,
  COALESCE(cd.campaign_type, oc.campaign_type, 'unclassified') AS campaign_type,
  COUNT(DISTINCT oc.order_id) AS orders,
  ROUND(SUM(COALESCE(oc.campaign_spend_bolt_eur, 0)), 2) AS bolt_spend_eur
FROM main.ng_delivery.dim_order_campaign_delivery oc
JOIN main.ng_delivery.dim_campaign_delivery_v2 cd ON oc.campaign_id = cd.campaign_id
JOIN main.ng_delivery.dim_provider_v2 p ON oc.provider_id = p.provider_id
WHERE oc.country_code = 'ua'
  AND (p.delivery_vertical LIKE 'store_3p%'
       OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV'))
  AND oc.order_created_date BETWEEN DATE '{iso(PERIOD_START)}' AND DATE '{iso(CURRENT_WEEK_END)}'
GROUP BY 1, 2, 3, 4
HAVING bolt_spend_eur != 0
ORDER BY 1, bolt_spend_eur DESC
"""

REFUND_REASONS_SQL = f"""
WITH refunded AS (
  SELECT
    f.order_id,
    CAST(CAST(DATE_TRUNC('week', f.order_created_date) AS DATE) AS STRING) AS week_start,
    SUM(COALESCE(f.demand_refunds_eur, 0)) AS refund_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {SCOPE}
    AND f.order_created_date BETWEEN DATE '{iso(PERIOD_START)}' AND DATE '{iso(CURRENT_WEEK_END)}'
    AND COALESCE(f.demand_refunds_eur, 0) != 0
  GROUP BY 1, 2
),
latest_reason AS (
  SELECT order_id, reason FROM (
    SELECT ur.order_id, urr.reason,
      ROW_NUMBER() OVER (PARTITION BY ur.order_id ORDER BY ur.created DESC, urr.id DESC) AS rn
    FROM main.ng_delivery.delivery_order_user_refund ur
    JOIN main.ng_delivery.delivery_order_user_refund_reason urr ON urr.user_refund_id = ur.id
    WHERE NOT COALESCE(ur._deleted_from_source, false)
  ) WHERE rn = 1
)
SELECT r.week_start, COALESCE(l.reason, 'unclassified') AS reason,
       COUNT(*) AS orders, ROUND(SUM(r.refund_eur), 2) AS demand_refunds_eur
FROM refunded r
LEFT JOIN latest_reason l ON l.order_id = r.order_id
GROUP BY 1, 2
ORDER BY 1, demand_refunds_eur DESC
"""

DAILY_PARTNER_SQL = f"""
SELECT
  CAST(f.order_created_date AS STRING) AS date,
  {PARTNER} AS partner,
  SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN COALESCE(f.demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  ROUND(SUM(COALESCE(f.demand_refunds_eur, 0)), 2) AS demand_refunds_eur
FROM main.ng_delivery.fact_order_delivery f
JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE {SCOPE}
  AND f.order_created_date BETWEEN DATE '{iso(DAILY_START)}' AND DATE '{iso(CURRENT_WEEK_END)}'
GROUP BY 1, 2
HAVING orders > 0 OR demand_refunds_eur != 0
ORDER BY 1, gmv_eur DESC
"""


def query(cursor, sql: str) -> list[dict]:
    cursor.execute(sql)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def reason_label(raw: str) -> str:
    if not raw or raw == "unclassified":
        return "Unclassified"
    value = raw[:-6] if raw.endswith("_eater") else raw
    return value.replace("_", " ").strip().capitalize()


def sum_rows(rows: list[dict]) -> dict:
    keys = ("orders", "gmv_eur", "demand_incentives_eur", "demand_refunds_eur")
    return {key: round(sum(float(row.get(key) or 0) for row in rows), 2) for key in keys}


def build_mtd_snapshots(weeks: list[str], daily_rows: list[dict]) -> list[dict]:
    by_partner_date = defaultdict(lambda: defaultdict(dict))
    partners = set()
    for row in daily_rows:
        partners.add(row["partner"])
        by_partner_date[row["partner"]][date.fromisoformat(row["date"])] = row

    output = []
    metric_keys = ("orders", "gmv_eur", "demand_incentives_eur", "demand_refunds_eur")
    for week_value in weeks:
        week_start = date.fromisoformat(week_value)
        as_of = min(week_start + timedelta(days=6), CURRENT_WEEK_END)
        month_start = as_of.replace(day=1)
        prior_start = previous_month(month_start)
        prior_days = min(as_of.day, calendar.monthrange(prior_start.year, prior_start.month)[1])
        prior_end = prior_start + timedelta(days=prior_days - 1)
        days_in_month = calendar.monthrange(as_of.year, as_of.month)[1]

        for partner in partners:
            current_rows = [
                row for day, row in by_partner_date[partner].items()
                if month_start <= day <= as_of
            ]
            prior_rows = [
                row for day, row in by_partner_date[partner].items()
                if prior_start <= day <= prior_end
            ]
            current = sum_rows(current_rows)
            prior = sum_rows(prior_rows)
            if not any(current.values()) and not any(prior.values()):
                continue
            item = {
                "week_start": week_value,
                "partner": partner,
                "as_of": iso(as_of),
                "days_elapsed": as_of.day,
                "days_in_month": days_in_month,
            }
            for key in metric_keys:
                item[f"mtd_{key}"] = current[key]
                item[f"prior_mtd_{key}"] = prior[key]
                item[f"projected_{key}"] = round(current[key] / as_of.day * days_in_month, 2)
            output.append(item)
    return output


def main() -> None:
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    with databricks.sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        access_token=os.environ["DATABRICKS_TOKEN"],
    ) as connection, connection.cursor() as cursor:
        weekly = query(cursor, WEEKLY_SQL)
        economics = query(cursor, ECONOMICS_SQL)
        campaigns = query(cursor, CAMPAIGNS_SQL)
        reasons = query(cursor, REFUND_REASONS_SQL)
        daily = query(cursor, DAILY_PARTNER_SQL)

    weeks = sorted({row["week_start"] for row in weekly})
    mtd = build_mtd_snapshots(weeks, daily)
    for row in reasons:
        row["reason"] = reason_label(row["reason"])

    payload = {
        "metadata": {
            "generated_at": date.today().isoformat(),
            "data_through": iso(CURRENT_WEEK_END),
            "period_start": iso(PERIOD_START),
            "latest_week": iso(CURRENT_WEEK_START),
            "currency": "EUR",
            "scope": "Ukraine 3P Stores",
            "projection_method": "Straight-line projection: MTD actual / elapsed calendar days × days in month.",
        },
        "weekly_partner": weekly,
        "weekly_economics": economics,
        "weekly_campaigns": campaigns,
        "weekly_refund_reasons": reasons,
        "weekly_mtd_partner": mtd,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    latest = [row for row in weekly if row["week_start"] == iso(CURRENT_WEEK_START)]
    totals = sum_rows(latest)
    print(
        f"{len(weeks)} complete weeks through {iso(CURRENT_WEEK_END)}; "
        f"latest orders={totals['orders']:,.0f}, GMV={totals['gmv_eur']:,.0f}, "
        f"DI={totals['demand_incentives_eur']:,.0f}, DR={totals['demand_refunds_eur']:,.2f}"
    )
    print(
        f"rows: weekly={len(weekly):,}, economics={len(economics):,}, "
        f"campaigns={len(campaigns):,}, reasons={len(reasons):,}, mtd={len(mtd):,}"
    )


if __name__ == "__main__":
    main()
