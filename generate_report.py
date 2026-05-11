#!/usr/bin/env python3
"""Generate 3P Stores Ukraine Weekly Performance Report (index.html) from Databricks."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from databricks import sql as dbsql

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]
DATABRICKS_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]

NAMED_PARTNERS = [
    "LOKO", "VARUS", "KOPIYKA", "CAFE RYNOK", "HOP HEY",
    "BEER MARKET", "TAISTRA", "RUKAVYCHKA", "PYVNA BORODA",
]
DATA_START = "2026-02-01"

TEMPLATE_PATH = Path(__file__).parent / "template.html"
OUTPUT_PATH = Path(__file__).parent / "index.html"


def get_connection():
    return dbsql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )


def run_query(cursor, query):
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def to_serializable(rows):
    out = []
    for row in rows:
        d = {}
        for k, v in row.items():
            if isinstance(v, (datetime,)):
                d[k] = v.isoformat()
            elif hasattr(v, "as_py"):
                d[k] = v.as_py()
            else:
                d[k] = v
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def _partner_filter(alias="f"):
    return f"""
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON {alias}.provider_id = p.provider_id
        WHERE {alias}.city_country_code = 'ua'
          AND {alias}.order_state = 'delivered'
          AND p.delivery_vertical LIKE 'store_3p%'
          AND {alias}.order_created_date >= '{DATA_START}'
    """


def _group_name_expr():
    cases = " ".join(
        f"WHEN UPPER(p.group_name) LIKE '%{n}%' THEN '{n}'" for n in NAMED_PARTNERS
    )
    return f"CASE {cases} ELSE UPPER(p.group_name) END"


FINANCIAL_MONTHLY = """
SELECT
    DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
    COUNT(*) AS orders,
    SUM(f.gmv_eur) AS gmv_eur,
    SUM(f.gmv_eur) / NULLIF(COUNT(*), 0) AS aov_with_delivery,
    SUM(f.gmv_eur - f.delivery_price_before_discount_eur) / NULLIF(COUNT(*), 0) AS aov_items_only,
    SUM(f.delivery_price_before_discount_eur + f.small_order_fee_eur + f.service_fee_eur) / NULLIF(COUNT(*), 0) AS eater_fees_per_order,
    SUM(f.delivery_price_before_discount_eur) AS delivery_fee_total,
    SUM(f.delivery_price_before_discount_eur) / NULLIF(COUNT(*), 0) AS delivery_fee_per_order,
    SUM(f.small_order_fee_eur) AS small_order_fee_total,
    SUM(f.small_order_fee_eur) / NULLIF(COUNT(*), 0) AS small_order_fee_per_order,
    SUM(f.service_fee_eur) AS service_fee_total,
    SUM(f.service_fee_eur) / NULLIF(COUNT(*), 0) AS service_fee_per_order,
    SUM(CASE WHEN f.is_bolt_plus THEN f.gmv_eur ELSE 0 END) / NULLIF(SUM(f.gmv_eur), 0) * 100 AS bolt_plus_gmv_share,
    COUNT(DISTINCT CASE WHEN f.is_first_delivery_order THEN f.user_id END) AS users_activated,
    COUNT(DISTINCT f.user_id) AS active_users,
    SUM(f.refund_eur) / NULLIF(SUM(f.gmv_eur), 0) * 100 AS refund_rate_pct
FROM bolt_food_analytics_db.gold.fact_order f
{partner_join}
GROUP BY 1
ORDER BY 1
""".format(partner_join=_partner_filter())

FINANCIAL_WEEKLY = FINANCIAL_MONTHLY.replace(
    "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
)

CP_MARGINS_MONTHLY = """
SELECT
    DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period,
    SUM(m.net_income_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100 AS cp_margin_pct,
    SUM(m.net_income_l2_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100 AS cp_l2_margin_pct
FROM bolt_food_analytics_db.gold.fact_monetary_metrics m
    INNER JOIN bolt_food_analytics_db.gold.dim_provider p
        ON m.provider_id = p.provider_id
WHERE m.city_country_code = 'ua'
  AND m.order_state = 'delivered'
  AND p.delivery_vertical LIKE 'store_3p%'
  AND m.order_created_date >= '{start}'
GROUP BY 1
ORDER BY 1
""".format(start=DATA_START)

CP_MARGINS_WEEKLY = CP_MARGINS_MONTHLY.replace(
    "DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', m.order_created_date), 'yyyy-MM-dd') AS period",
)

OPERATIONAL_MONTHLY = """
SELECT
    DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
    COUNT(*) AS delivered_orders,
    COUNT(DISTINCT f.provider_id) AS active_stores,
    SUM(CASE WHEN f.is_honey_order THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS honey_order_rate,
    SUM(CASE WHEN f.is_bad_order THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS bad_order_rate,
    SUM(CASE WHEN f.delivery_late_minutes >= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS late_delivery_rate,
    SUM(CASE WHEN f.pickup_late_minutes >= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS late_pickup_rate,
    AVG(f.delivery_duration_minutes) AS avg_delivery_minutes,
    AVG(f.courier_wait_at_provider_minutes) AS avg_courier_wait_at_provider_min,
    SUM(CASE WHEN f.has_replacement THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS replacement_rate,
    SUM(CASE WHEN f.has_adjustment THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS adjustment_rate
FROM bolt_food_analytics_db.gold.fact_order f
{partner_join}
GROUP BY 1
ORDER BY 1
""".format(partner_join=_partner_filter())

OPERATIONAL_WEEKLY = OPERATIONAL_MONTHLY.replace(
    "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
)

FAILED_ORDERS_MONTHLY = """
SELECT
    DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
    COUNT(*) AS total_placed,
    SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) AS delivered,
    SUM(CASE WHEN f.order_state != 'delivered' AND f.failed_party = 'merchant' THEN 1 ELSE 0 END) AS failed_merchant,
    SUM(CASE WHEN f.order_state != 'delivered' AND f.failed_party IN ('bolt','courier') THEN 1 ELSE 0 END) AS failed_bolt_courier,
    SUM(CASE WHEN f.order_state != 'delivered' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS failed_rate_total
FROM bolt_food_analytics_db.gold.fact_order f
    INNER JOIN bolt_food_analytics_db.gold.dim_provider p
        ON f.provider_id = p.provider_id
WHERE f.city_country_code = 'ua'
  AND p.delivery_vertical LIKE 'store_3p%'
  AND f.order_created_date >= '{start}'
GROUP BY 1
ORDER BY 1
""".format(start=DATA_START)

FAILED_ORDERS_WEEKLY = FAILED_ORDERS_MONTHLY.replace(
    "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
)

CAMPAIGNS_MONTHLY = """
SELECT
    DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period,
    SUM(m.delivery_discount_eur + m.menu_discount_eur) AS campaigns_discount_eur,
    SUM(m.bolt_delivery_campaign_cost_eur + m.bolt_menu_campaign_cost_eur) AS bolt_spend_eur,
    SUM(m.provider_delivery_campaign_cost_eur + m.provider_menu_campaign_cost_eur) AS merchant_spend_eur,
    SUM(m.gmv_eur) AS gmv_eur
FROM bolt_food_analytics_db.gold.fact_monetary_metrics m
    INNER JOIN bolt_food_analytics_db.gold.dim_provider p
        ON m.provider_id = p.provider_id
WHERE m.city_country_code = 'ua'
  AND m.order_state = 'delivered'
  AND p.delivery_vertical LIKE 'store_3p%'
  AND m.order_created_date >= '{start}'
GROUP BY 1
ORDER BY 1
""".format(start=DATA_START)

CAMPAIGNS_WEEKLY = CAMPAIGNS_MONTHLY.replace(
    "DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', m.order_created_date), 'yyyy-MM-dd') AS period",
)

GMV_BY_PARTNER_MONTHLY = """
SELECT
    DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
    {group_name} AS group_name,
    SUM(f.gmv_eur) AS gmv_eur,
    COUNT(*) AS orders
FROM bolt_food_analytics_db.gold.fact_order f
{partner_join}
GROUP BY 1, 2
ORDER BY 1, 3 DESC
""".format(group_name=_group_name_expr(), partner_join=_partner_filter())

GMV_BY_PARTNER_WEEKLY = GMV_BY_PARTNER_MONTHLY.replace(
    "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
    "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
)

TOP_PARTNERS_GMV = """
SELECT
    {group_name} AS group_name,
    SUM(f.gmv_eur) AS gmv_eur
FROM bolt_food_analytics_db.gold.fact_order f
{partner_join}
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15
""".format(group_name=_group_name_expr(), partner_join=_partner_filter())

ACCEPTANCE_AVAILABILITY_OVERVIEW = """
SELECT
    AVG(ps.acceptance_rate_30d) AS acceptance_rate_30d,
    AVG(ps.availability_rate_30d) AS availability_rate_30d,
    AVG(ps.avg_rating_30d) AS avg_rating_30d
FROM bolt_food_analytics_db.gold.dim_provider_stats ps
    INNER JOIN bolt_food_analytics_db.gold.dim_provider p
        ON ps.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND p.delivery_vertical LIKE 'store_3p%'
LIMIT 1
"""


def _acceptance_by_partner(partner_name):
    return f"""
    SELECT
        AVG(ps.acceptance_rate_30d) AS acceptance_rate_30d,
        AVG(ps.availability_rate_30d) AS availability_rate_30d,
        AVG(ps.avg_rating_30d) AS avg_rating_30d
    FROM bolt_food_analytics_db.gold.dim_provider_stats ps
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON ps.provider_id = p.provider_id
    WHERE p.country_code = 'ua'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    LIMIT 1
    """


# Per-partner financial queries
def _partner_financial_monthly(partner_name):
    return f"""
    SELECT
        DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
        COUNT(*) AS orders,
        SUM(f.gmv_eur) AS gmv_eur,
        SUM(f.gmv_eur) / NULLIF(COUNT(*), 0) AS aov_with_delivery,
        SUM(f.gmv_eur - f.delivery_price_before_discount_eur) / NULLIF(COUNT(*), 0) AS aov_items_only,
        SUM(f.delivery_price_before_discount_eur + f.small_order_fee_eur + f.service_fee_eur) / NULLIF(COUNT(*), 0) AS eater_fees_per_order,
        SUM(f.delivery_price_before_discount_eur) AS delivery_fee_total,
        SUM(f.delivery_price_before_discount_eur) / NULLIF(COUNT(*), 0) AS delivery_fee_per_order,
        SUM(f.small_order_fee_eur) AS small_order_fee_total,
        SUM(f.small_order_fee_eur) / NULLIF(COUNT(*), 0) AS small_order_fee_per_order,
        SUM(f.service_fee_eur) AS service_fee_total,
        SUM(f.service_fee_eur) / NULLIF(COUNT(*), 0) AS service_fee_per_order,
        SUM(CASE WHEN f.is_bolt_plus THEN f.gmv_eur ELSE 0 END) / NULLIF(SUM(f.gmv_eur), 0) * 100 AS bolt_plus_gmv_share,
        COUNT(DISTINCT CASE WHEN f.is_first_delivery_order THEN f.user_id END) AS users_activated,
        COUNT(DISTINCT f.user_id) AS active_users,
        SUM(f.refund_eur) / NULLIF(SUM(f.gmv_eur), 0) * 100 AS refund_rate_pct
    FROM bolt_food_analytics_db.gold.fact_order f
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND f.order_created_date >= '{DATA_START}'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    GROUP BY 1
    ORDER BY 1
    """


def _partner_financial_weekly(partner_name):
    return _partner_financial_monthly(partner_name).replace(
        "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
        "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
    )


def _partner_cp_monthly(partner_name):
    return f"""
    SELECT
        DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period,
        SUM(m.net_income_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100 AS cp_margin_pct,
        SUM(m.net_income_l2_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100 AS cp_l2_margin_pct
    FROM bolt_food_analytics_db.gold.fact_monetary_metrics m
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON m.provider_id = p.provider_id
    WHERE m.city_country_code = 'ua'
      AND m.order_state = 'delivered'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND m.order_created_date >= '{DATA_START}'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    GROUP BY 1
    ORDER BY 1
    """


def _partner_cp_weekly(partner_name):
    return _partner_cp_monthly(partner_name).replace(
        "DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period",
        "DATE_FORMAT(DATE_TRUNC('week', m.order_created_date), 'yyyy-MM-dd') AS period",
    )


def _partner_operational_monthly(partner_name):
    return f"""
    SELECT
        DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
        COUNT(*) AS delivered_orders,
        COUNT(DISTINCT f.provider_id) AS active_stores,
        SUM(CASE WHEN f.is_honey_order THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS honey_order_rate,
        SUM(CASE WHEN f.is_bad_order THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS bad_order_rate,
        SUM(CASE WHEN f.delivery_late_minutes >= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS late_delivery_rate,
        SUM(CASE WHEN f.pickup_late_minutes >= 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS late_pickup_rate,
        AVG(f.delivery_duration_minutes) AS avg_delivery_minutes,
        AVG(f.courier_wait_at_provider_minutes) AS avg_courier_wait_at_provider_min,
        SUM(CASE WHEN f.has_replacement THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS replacement_rate,
        SUM(CASE WHEN f.has_adjustment THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS adjustment_rate
    FROM bolt_food_analytics_db.gold.fact_order f
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND f.order_created_date >= '{DATA_START}'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    GROUP BY 1
    ORDER BY 1
    """


def _partner_operational_weekly(partner_name):
    return _partner_operational_monthly(partner_name).replace(
        "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
        "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
    )


def _partner_failed_monthly(partner_name):
    return f"""
    SELECT
        DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period,
        COUNT(*) AS total_placed,
        SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) AS delivered,
        SUM(CASE WHEN f.order_state != 'delivered' AND f.failed_party = 'merchant' THEN 1 ELSE 0 END) AS failed_merchant,
        SUM(CASE WHEN f.order_state != 'delivered' AND f.failed_party IN ('bolt','courier') THEN 1 ELSE 0 END) AS failed_bolt_courier,
        SUM(CASE WHEN f.order_state != 'delivered' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) * 100 AS failed_rate_total
    FROM bolt_food_analytics_db.gold.fact_order f
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND f.order_created_date >= '{DATA_START}'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    GROUP BY 1
    ORDER BY 1
    """


def _partner_failed_weekly(partner_name):
    return _partner_failed_monthly(partner_name).replace(
        "DATE_FORMAT(f.order_created_date, 'yyyy-MM') AS period",
        "DATE_FORMAT(DATE_TRUNC('week', f.order_created_date), 'yyyy-MM-dd') AS period",
    )


def _partner_campaigns_monthly(partner_name):
    return f"""
    SELECT
        DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period,
        SUM(m.delivery_discount_eur + m.menu_discount_eur) AS campaigns_discount_eur,
        SUM(m.bolt_delivery_campaign_cost_eur + m.bolt_menu_campaign_cost_eur) AS bolt_spend_eur,
        SUM(m.provider_delivery_campaign_cost_eur + m.provider_menu_campaign_cost_eur) AS merchant_spend_eur,
        SUM(m.gmv_eur) AS gmv_eur
    FROM bolt_food_analytics_db.gold.fact_monetary_metrics m
        INNER JOIN bolt_food_analytics_db.gold.dim_provider p
            ON m.provider_id = p.provider_id
    WHERE m.city_country_code = 'ua'
      AND m.order_state = 'delivered'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND m.order_created_date >= '{DATA_START}'
      AND UPPER(p.group_name) LIKE '%{partner_name}%'
    GROUP BY 1
    ORDER BY 1
    """


def _partner_campaigns_weekly(partner_name):
    return _partner_campaigns_monthly(partner_name).replace(
        "DATE_FORMAT(m.order_created_date, 'yyyy-MM') AS period",
        "DATE_FORMAT(DATE_TRUNC('week', m.order_created_date), 'yyyy-MM-dd') AS period",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def determine_partners_list(top_partners):
    """Build final partners list: named partners + 10th largest dynamic."""
    existing = set(NAMED_PARTNERS)
    for row in top_partners:
        if row["group_name"] not in existing:
            return NAMED_PARTNERS + [row["group_name"]]
    return NAMED_PARTNERS


def main():
    print("Connecting to Databricks...")
    conn = get_connection()
    cursor = conn.cursor()

    print("Querying overview data...")
    fin_m = to_serializable(run_query(cursor, FINANCIAL_MONTHLY))
    fin_w = to_serializable(run_query(cursor, FINANCIAL_WEEKLY))
    cp_m = to_serializable(run_query(cursor, CP_MARGINS_MONTHLY))
    cp_w = to_serializable(run_query(cursor, CP_MARGINS_WEEKLY))
    ops_m = to_serializable(run_query(cursor, OPERATIONAL_MONTHLY))
    ops_w = to_serializable(run_query(cursor, OPERATIONAL_WEEKLY))
    fail_m = to_serializable(run_query(cursor, FAILED_ORDERS_MONTHLY))
    fail_w = to_serializable(run_query(cursor, FAILED_ORDERS_WEEKLY))
    camp_m = to_serializable(run_query(cursor, CAMPAIGNS_MONTHLY))
    camp_w = to_serializable(run_query(cursor, CAMPAIGNS_WEEKLY))
    gmv_part_m = to_serializable(run_query(cursor, GMV_BY_PARTNER_MONTHLY))
    gmv_part_w = to_serializable(run_query(cursor, GMV_BY_PARTNER_WEEKLY))
    top_partners = to_serializable(run_query(cursor, TOP_PARTNERS_GMV))

    partners_list = determine_partners_list(top_partners)

    print("Querying acceptance/availability overview...")
    aa_overview = to_serializable(run_query(cursor, ACCEPTANCE_AVAILABILITY_OVERVIEW))

    acceptance_availability = {"overview": aa_overview}
    partners_data = {}

    for pname in partners_list:
        print(f"  Querying partner: {pname}...")
        acceptance_availability[pname] = to_serializable(
            run_query(cursor, _acceptance_by_partner(pname))
        )
        partners_data[pname] = {
            "monthly": {
                "financial": to_serializable(run_query(cursor, _partner_financial_monthly(pname))),
                "cp_margins": to_serializable(run_query(cursor, _partner_cp_monthly(pname))),
                "operational": to_serializable(run_query(cursor, _partner_operational_monthly(pname))),
                "failed_orders": to_serializable(run_query(cursor, _partner_failed_monthly(pname))),
                "campaigns": to_serializable(run_query(cursor, _partner_campaigns_monthly(pname))),
            },
            "weekly": {
                "financial": to_serializable(run_query(cursor, _partner_financial_weekly(pname))),
                "cp_margins": to_serializable(run_query(cursor, _partner_cp_weekly(pname))),
                "operational": to_serializable(run_query(cursor, _partner_operational_weekly(pname))),
                "failed_orders": to_serializable(run_query(cursor, _partner_failed_weekly(pname))),
                "campaigns": to_serializable(run_query(cursor, _partner_campaigns_weekly(pname))),
            },
        }

    cursor.close()
    conn.close()

    report_data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "data_start": DATA_START,
        "partners_list": partners_list,
        "top_partners_gmv": top_partners,
        "overview": {
            "monthly": {
                "financial": fin_m,
                "cp_margins": cp_m,
                "operational": ops_m,
                "failed_orders": fail_m,
                "campaigns": camp_m,
                "gmv_by_partner": gmv_part_m,
            },
            "weekly": {
                "financial": fin_w,
                "cp_margins": cp_w,
                "operational": ops_w,
                "failed_orders": fail_w,
                "campaigns": camp_w,
                "gmv_by_partner": gmv_part_w,
            },
        },
        "acceptance_availability": acceptance_availability,
        "partners": partners_data,
    }

    print("Generating index.html...")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    js_data = f"const REPORT_DATA = {json.dumps(report_data, ensure_ascii=False, default=str)};"
    html = template.replace("/*__REPORT_DATA__*/", js_data)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Done! Report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
