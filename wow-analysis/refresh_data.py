"""Rebuild data.json from Databricks for a chosen pair of full weeks.

Run: python3 wow-analysis/refresh_data.py
Requires DATABRICKS_HOST, DATABRICKS_TOKEN and DATABRICKS_WAREHOUSE_ID.

Every slice is anchored on complete weeks so the report never mixes a
partial week-to-date window with full-week comparisons.
"""
import json
import os
from pathlib import Path

import databricks.sql

DATA = Path(__file__).with_name("data.json")

CURRENT_WEEK = ("2026-08-10", "2026-08-16")
PRIOR_WEEK = ("2026-08-03", "2026-08-09")
MTD_CURRENT = ("2026-08-01", "2026-08-16")
MTD_PRIOR = ("2026-07-01", "2026-07-16")

CUR_START, CUR_END = CURRENT_WEEK
PRI_START, PRI_END = PRIOR_WEEK

STORE_SCOPE = """
  f.city_country_code = 'ua'
  AND (
    p.delivery_vertical LIKE 'store_3p%'
    OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV')
  )
"""

PARTNER = """
  CASE
    WHEN p.brand_name = 'OKKO MARKET' THEN p.brand_name
    ELSE COALESCE(p.group_name, p.brand_name, f.provider_name)
  END
"""

# Both weeks in one pass; every deep-dive slice reuses this window.
WEEK_BUCKET = f"""
  CASE
    WHEN f.order_created_date BETWEEN DATE '{CUR_START}' AND DATE '{CUR_END}' THEN 'current'
    WHEN f.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{PRI_END}' THEN 'prior'
  END
"""

DELIVERED = "CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END"

PERIOD_SQL = f"""
WITH base AS (
  SELECT {PARTNER} AS partner,
         f.order_state, f.order_gmv_eur, f.demand_incentives_eur,
         f.demand_refunds_eur, f.total_refunds_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {STORE_SCOPE}
    AND f.order_created_date BETWEEN DATE '{{start}}' AND DATE '{{end}}'
)
SELECT
  partner,
  SUM(CASE WHEN order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
  ROUND(SUM(CASE WHEN order_state = 'delivered' THEN order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN order_state = 'delivered' THEN COALESCE(demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  ROUND(SUM(COALESCE(demand_refunds_eur, 0)), 2) AS demand_refunds_eur,
  ROUND(SUM(COALESCE(total_refunds_eur, 0)), 2) AS total_refunds_eur,
  SUM(CASE WHEN order_state = 'delivered' AND COALESCE(demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  SUM(CASE WHEN COALESCE(demand_refunds_eur, 0) != 0 THEN 1 ELSE 0 END) AS demand_refund_orders
FROM base
GROUP BY partner
HAVING orders > 0 OR demand_refunds_eur != 0
ORDER BY gmv_eur DESC
"""

DAILY_SQL = f"""
SELECT
  CAST(f.order_created_date AS STRING) AS date,
  SUM({DELIVERED}) AS orders,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN COALESCE(f.demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  SUM(CASE WHEN f.order_state = 'delivered' AND COALESCE(f.demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  ROUND(SUM(COALESCE(f.demand_refunds_eur, 0)), 2) AS demand_refunds_eur,
  SUM(CASE WHEN COALESCE(f.demand_refunds_eur, 0) != 0 THEN 1 ELSE 0 END) AS demand_refund_orders
FROM main.ng_delivery.fact_order_delivery f
JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE {STORE_SCOPE}
  AND f.order_created_date BETWEEN DATE '{CUR_START}' AND DATE '{CUR_END}'
GROUP BY 1
ORDER BY 1
"""

CITY_SQL = f"""
SELECT
  {WEEK_BUCKET} AS period,
  f.city_name AS city,
  SUM({DELIVERED}) AS orders,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN f.order_state = 'delivered' THEN COALESCE(f.demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  SUM(CASE WHEN f.order_state = 'delivered' AND COALESCE(f.demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  ROUND(SUM(COALESCE(f.demand_refunds_eur, 0)), 2) AS demand_refunds_eur,
  SUM(CASE WHEN COALESCE(f.demand_refunds_eur, 0) != 0 THEN 1 ELSE 0 END) AS demand_refund_orders
FROM main.ng_delivery.fact_order_delivery f
JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE {STORE_SCOPE}
  AND f.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{CUR_END}'
GROUP BY 1, 2
HAVING period IS NOT NULL
ORDER BY demand_incentives_eur DESC
"""

REFUND_BUCKET_SQL = f"""
WITH refunded AS (
  SELECT f.order_id, SUM(COALESCE(f.demand_refunds_eur, 0)) AS refund_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {STORE_SCOPE}
    AND f.order_created_date BETWEEN DATE '{CUR_START}' AND DATE '{CUR_END}'
    AND COALESCE(f.demand_refunds_eur, 0) != 0
  GROUP BY f.order_id
)
SELECT
  CASE
    WHEN refund_eur < 5 THEN '<€5'
    WHEN refund_eur < 10 THEN '€5–10'
    WHEN refund_eur < 20 THEN '€10–20'
    WHEN refund_eur < 50 THEN '€20–50'
    ELSE '€50+'
  END AS bucket,
  COUNT(*) AS refund_orders,
  ROUND(SUM(refund_eur), 2) AS demand_refunds_eur,
  ROUND(AVG(refund_eur), 2) AS avg_refund_eur
FROM refunded
GROUP BY 1
"""

# AM Spend is identified by a non-zero am_campaign_spend_bolt_eur on the order's
# campaign rows; remaining objectives are folded into families so a single order
# lands in exactly one bucket.
OBJECTIVE_SQL = f"""
WITH scope AS (
  SELECT f.order_id, {WEEK_BUCKET} AS period, f.order_state,
         f.order_gmv_eur, f.demand_incentives_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {STORE_SCOPE}
    AND f.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{CUR_END}'
),
campaigns AS (
  SELECT
    oc.order_id,
    MAX(CASE WHEN COALESCE(oc.am_campaign_spend_bolt_eur, 0) != 0 THEN 1 ELSE 0 END) AS has_am,
    COLLECT_SET(
      CASE WHEN COALESCE(oc.am_campaign_spend_bolt_eur, 0) = 0 THEN
        CASE
          WHEN cd.campaign_spend_objective = 'new_city_launch' THEN 'New City'
          WHEN cd.campaign_spend_objective IN ('activation', 'sp_activation') THEN 'Activation'
          WHEN cd.campaign_spend_objective = 'bolt_market_supplier' THEN 'Bolt Market'
          WHEN cd.campaign_spend_objective = 'bolt_plus_campaign' THEN 'Bolt Plus'
          WHEN cd.campaign_spend_objective IN ('engagement', 'sp_engagement') THEN 'Engagement'
          WHEN cd.campaign_spend_objective IN ('reactivation', 'sp_reactivation') THEN 'Reactivation'
          ELSE 'Other'
        END
      END
    ) AS families
  FROM main.ng_delivery.dim_order_campaign_delivery oc
  JOIN main.ng_delivery.dim_campaign_delivery_v2 cd ON oc.campaign_id = cd.campaign_id
  WHERE oc.country_code = 'ua'
    AND oc.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{CUR_END}'
  GROUP BY oc.order_id
)
SELECT
  s.period,
  CASE
    WHEN c.has_am = 1 AND SIZE(COALESCE(c.families, ARRAY())) = 0 THEN 'AM Spend only'
    WHEN c.has_am = 1 THEN 'AM Spend + other'
    WHEN SIZE(COALESCE(c.families, ARRAY())) = 0 THEN 'Unclassified'
    WHEN SIZE(c.families) = 1 THEN CONCAT(c.families[0], ' (no AM Spend)')
    ELSE 'Other classified'
  END AS objective,
  SUM(CASE WHEN s.order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
  SUM(CASE WHEN s.order_state = 'delivered' AND COALESCE(s.demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  ROUND(SUM(CASE WHEN s.order_state = 'delivered' THEN COALESCE(s.demand_incentives_eur, 0) ELSE 0 END), 2) AS spend,
  ROUND(SUM(CASE WHEN s.order_state = 'delivered' THEN s.order_gmv_eur ELSE 0 END), 2) AS gmv
FROM scope s
LEFT JOIN campaigns c ON c.order_id = s.order_id
WHERE s.period IS NOT NULL
GROUP BY 1, 2
ORDER BY spend DESC
"""

CAMPAIGN_SQL = f"""
SELECT
  cd.campaign_name AS campaign,
  ROUND(SUM(CASE WHEN oc.order_created_date BETWEEN DATE '{CUR_START}' AND DATE '{CUR_END}'
                 THEN COALESCE(oc.campaign_spend_bolt_eur, 0) ELSE 0 END), 2) AS current,
  ROUND(SUM(CASE WHEN oc.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{PRI_END}'
                 THEN COALESCE(oc.campaign_spend_bolt_eur, 0) ELSE 0 END), 2) AS prior
FROM main.ng_delivery.dim_order_campaign_delivery oc
JOIN main.ng_delivery.dim_campaign_delivery_v2 cd ON oc.campaign_id = cd.campaign_id
JOIN main.ng_delivery.dim_provider_v2 p ON oc.provider_id = p.provider_id
WHERE oc.country_code = 'ua'
  AND (
    p.delivery_vertical LIKE 'store_3p%'
    OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV')
  )
  AND oc.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{CUR_END}'
GROUP BY 1
HAVING current != 0 OR prior != 0
ORDER BY current - prior DESC
"""

REFUND_REASON_SQL = f"""
WITH refunded AS (
  SELECT f.order_id, {WEEK_BUCKET} AS period, {PARTNER} AS partner,
         SUM(COALESCE(f.demand_refunds_eur, 0)) AS refund_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {STORE_SCOPE}
    AND f.order_created_date BETWEEN DATE '{PRI_START}' AND DATE '{CUR_END}'
    AND COALESCE(f.demand_refunds_eur, 0) != 0
  GROUP BY 1, 2, 3
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
SELECT r.period, r.partner, COALESCE(lr.reason, 'unclassified') AS reason,
       COUNT(*) AS orders, ROUND(SUM(r.refund_eur), 2) AS refund_eur
FROM refunded r
LEFT JOIN latest_reason lr ON lr.order_id = r.order_id
WHERE r.period IS NOT NULL
GROUP BY 1, 2, 3
"""


def query(cursor, sql):
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def reason_label(raw):
    if not raw or raw == "unclassified":
        return "Unclassified"
    text = raw[:-6] if raw.endswith("_eater") else raw
    text = text.replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def campaign_reason(current, prior):
    if prior == 0:
        return "New campaign this week"
    if current == 0:
        return "Ended after the prior week"
    return "Scaled up vs prior week" if current > prior else "Scaled down vs prior week"


def main():
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    with databricks.sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        access_token=os.environ["DATABRICKS_TOKEN"],
    ) as conn, conn.cursor() as cur:
        periods = {
            "last_week": CURRENT_WEEK,
            "prior_week": PRIOR_WEEK,
            "mtd_current": MTD_CURRENT,
            "mtd_prior": MTD_PRIOR,
        }
        res = {
            name: query(cur, PERIOD_SQL.format(start=start, end=end))
            for name, (start, end) in periods.items()
        }
        daily = query(cur, DAILY_SQL)
        cities = query(cur, CITY_SQL)
        buckets = query(cur, REFUND_BUCKET_SQL)
        objectives = query(cur, OBJECTIVE_SQL)
        campaigns = query(cur, CAMPAIGN_SQL)
        reasons = query(cur, REFUND_REASON_SQL)

    data = json.loads(DATA.read_text())
    econ_last = {r["partner"]: r for r in data["partner_economics_last_week"]}
    econ_prior = {r["partner"]: r for r in data["partner_economics_prior_week"]}

    def with_economics(rows, econ):
        out = []
        for row in rows:
            e = econ.get(row["partner"], {})
            out.append({
                **row,
                "commission_gmv_pct": e.get("commission_gmv_pct"),
                "cm_l1_eur": e.get("cm_l1_eur"),
                "cm_l1_pct": e.get("cm_l1_pct"),
            })
        return out

    data["partner_last_week"] = with_economics(res["last_week"], econ_last)
    data["partner_prior_week"] = with_economics(res["prior_week"], econ_prior)
    data["partner_mtd_current"] = res["mtd_current"]
    data["partner_mtd_prior"] = res["mtd_prior"]

    data["weekly_partner"] = [r for r in data["weekly_partner"] if r["week_start"] != CUR_START]
    data["weekly_partner"] += [{"week_start": CUR_START, **r} for r in res["last_week"]]
    data["weekly_partner"].sort(key=lambda r: (r["week_start"], -r["gmv_eur"]))

    data["current_week_daily"] = daily

    cur_cities = [r for r in cities if r["period"] == "current"]
    prior_cities = {r["city"]: r for r in cities if r["period"] == "prior"}
    data["current_week_cities"] = [
        {k: v for k, v in r.items() if k != "period"} for r in cur_cities
    ]
    city_rows = []
    for r in cur_cities:
        p = prior_cities.get(r["city"], {})
        di_p = p.get("demand_incentives_eur", 0) or 0
        dr_p = p.get("demand_refunds_eur", 0) or 0
        city_rows.append([
            r["city"], r["demand_incentives_eur"], di_p,
            round(r["demand_incentives_eur"] - di_p, 2),
            r["demand_refunds_eur"], dr_p,
            round(r["demand_refunds_eur"] - dr_p, 2),
        ])
    city_rows.sort(key=lambda x: -x[3])
    data["city_growth_drivers"] = city_rows[:15]

    order = ["<€5", "€5–10", "€10–20", "€20–50", "€50+"]
    data["refund_buckets"] = sorted(buckets, key=lambda r: order.index(r["bucket"]))

    data["incentive_objective_comparison"] = [
        {"period": r["period"], "objective": r["objective"], "orders": r["incentive_orders"],
         "spend": r["spend"], "gmv": r["gmv"]}
        for r in objectives
    ]
    data["incentive_objectives"] = sorted(
        ({"objective": r["objective"], "orders": r["orders"],
          "incentive_orders": r["incentive_orders"],
          "demand_incentives_eur": r["spend"], "gmv_eur": r["gmv"]}
         for r in objectives if r["period"] == "current"),
        key=lambda r: -r["demand_incentives_eur"],
    )

    data["campaign_growth_drivers"] = [
        {"campaign": r["campaign"], "current": r["current"], "prior": r["prior"],
         "delta": round(r["current"] - r["prior"], 2),
         "why": campaign_reason(r["current"], r["prior"])}
        for r in campaigns[:10]
    ]

    reason_totals = {}
    for r in reasons:
        label = reason_label(r["reason"])
        slot = reason_totals.setdefault(label, {"cur_o": 0, "pri_o": 0, "cur_e": 0.0, "pri_e": 0.0})
        if r["period"] == "current":
            slot["cur_o"] += r["orders"]
            slot["cur_e"] += r["refund_eur"]
        else:
            slot["pri_o"] += r["orders"]
            slot["pri_e"] += r["refund_eur"]
    data["refund_reason_comparison"] = sorted(
        ([label, v["cur_o"], v["pri_o"], round(v["cur_e"], 2), round(v["pri_e"], 2),
          round(v["cur_e"] - v["pri_e"], 2)] for label, v in reason_totals.items()),
        key=lambda x: -x[5],
    )
    data["refund_partner_reasons"] = sorted(
        ([r["partner"], reason_label(r["reason"]), r["orders"], round(r["refund_eur"], 2)]
         for r in reasons if r["period"] == "current"),
        key=lambda x: -x[3],
    )[:20]

    data.pop("wtd_partner_comparison", None)
    data["metadata"].update({
        "data_through": CUR_END,
        "current_week": CUR_START,
        "current_week_label": "10–16 Aug",
        "prior_week_label": "3–9 Aug",
        "mtd_label": "1–16 Aug",
        "mtd_prior_label": "1–16 Jul",
        "analysis_note": (
            "All comparisons use complete weeks: 10–16 Aug against 3–9 Aug 2026, "
            "with month to date covering 1–16 Aug against 1–16 Jul. Refund reasons come "
            "from delivery_order_user_refund_reason; all demand refunds in scope are "
            "liable to Bolt, while operational fault is mostly recorded as unknown."
        ),
    })

    DATA.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    for name, rows in res.items():
        print(f"{name}: {len(rows)} partners, orders={sum(r['orders'] for r in rows):,}, "
              f"gmv={sum(r['gmv_eur'] for r in rows):,.0f}, "
              f"di={sum(r['demand_incentives_eur'] for r in rows):,.0f}, "
              f"dr={sum(r['demand_refunds_eur'] for r in rows):,.2f}")
    print(f"daily days={len(daily)} cities={len(data['current_week_cities'])} "
          f"buckets={len(data['refund_buckets'])} objectives={len(data['incentive_objectives'])} "
          f"campaigns={len(data['campaign_growth_drivers'])} "
          f"reasons={len(data['refund_reason_comparison'])}")


if __name__ == "__main__":
    main()
