"""Fetch ALL data from Databricks for the 3P Stores Weekly Report."""
import os, json
from collections import defaultdict
from databricks import sql as dbsql

HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_START = "2026-01-01"

NAMED_PARTNERS = [
    "LOKO", "VARUS", "KOPIYKA", "CAFE RYNOK", "HOP HEY",
    "BEER MARKET", "TAISTRA", "RUKAVYCHKA", "PYVNA BORODA"
]


def run_query(cursor, query):
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def to_int(v):
    if v is None:
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def save_json(filename, data):
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f)
    print(f"  Saved {filename} ({len(data) if isinstance(data, list) else 'dict'})")


def financial_query(granularity, group_filter=None):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    group_col = ", p.group_name" if group_filter == "ALL_BY_GROUP" else ""
    group_select = "p.group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND p.group_name = '{group_filter}'"

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        COUNT(*) as orders,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur,
        ROUND(SUM(f.total_price_before_discount_eur) / COUNT(*), 2) as aov_with_delivery,
        ROUND(SUM(f.provider_price_before_discount_eur) / COUNT(*), 2) as aov_items_only,
        ROUND((SUM(f.delivery_price_eur) + SUM(f.small_order_fee_eur) + SUM(f.order_service_fee_eur)) / COUNT(*), 2) as eater_fees_per_order,
        ROUND(SUM(f.delivery_price_eur), 2) as delivery_fee_total,
        ROUND(SUM(f.delivery_price_eur) / COUNT(*), 2) as delivery_fee_per_order,
        ROUND(SUM(f.small_order_fee_eur), 2) as small_order_fee_total,
        ROUND(SUM(f.small_order_fee_eur) / COUNT(*), 2) as small_order_fee_per_order,
        ROUND(SUM(f.order_service_fee_eur), 2) as service_fee_total,
        ROUND(SUM(f.order_service_fee_eur) / COUNT(*), 2) as service_fee_per_order,
        ROUND(SUM(CASE WHEN f.is_bolt_plus_order THEN f.order_gmv_eur ELSE 0 END) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 2) as bolt_plus_gmv_share,
        SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) as users_activated,
        ROUND(SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as new_user_share,
        COUNT(DISTINCT f.user_id) as active_users,
        ROUND(SUM(f.total_refunds_eur), 2) as total_refunds_eur,
        ROUND(SUM(f.total_refunds_eur) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 2) as refund_rate_pct
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def campaign_query(granularity, group_filter=None):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    group_col = ", p.group_name" if group_filter == "ALL_BY_GROUP" else ""
    group_select = "p.group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND p.group_name = '{group_filter}'"

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur,
        ROUND(SUM(f.demand_incentives_eur) + SUM(f.supply_incentives_eur) + COALESCE(SUM(f.order_provider_spend_provider_campaign_eur), 0), 2) as campaigns_discount_eur,
        ROUND(SUM(f.demand_incentives_eur) + SUM(f.supply_incentives_eur), 2) as bolt_spend_eur,
        ROUND(COALESCE(SUM(f.order_provider_spend_provider_campaign_eur), 0), 2) as merchant_spend_eur
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def failed_orders_query(granularity):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    return f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        COUNT(*) as total_placed,
        SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) as delivered,
        SUM(CASE WHEN f.order_state != 'delivered' AND (f.is_rejected_by_provider = true OR f.is_not_responded_by_provider = true) THEN 1 ELSE 0 END) as failed_merchant,
        SUM(CASE WHEN f.order_state != 'delivered' AND f.is_rejected_by_provider = false AND (f.is_not_responded_by_provider = false OR f.is_not_responded_by_provider IS NULL) THEN 1 ELSE 0 END) as failed_bolt_courier,
        ROUND(SUM(CASE WHEN f.order_state != 'delivered' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as failed_rate_total
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_created_date >= '{DATA_START}'
      AND p.delivery_vertical LIKE 'store_3p%'
    GROUP BY {time_col}
    ORDER BY period
    """


def gmv_by_partner_query(granularity):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    return f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        p.group_name,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur,
        COUNT(*) as orders
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      AND p.delivery_vertical LIKE 'store_3p%'
    GROUP BY {time_col}, p.group_name
    ORDER BY period, gmv_eur DESC
    """


def cp_margins_query(granularity, group_filter=None):
    time_col = "DATE_TRUNC('week', CAST(m.order_created_date AS DATE))" if granularity == "week" else "DATE_TRUNC('month', CAST(m.order_created_date AS DATE))"
    group_col = ", p.group_name" if group_filter == "ALL_BY_GROUP" else ""
    group_select = "p.group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND p.group_name = '{group_filter}'"

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        ROUND(SUM(m.gmv_eur), 2) as gmv_eur,
        ROUND(SUM(m.net_income_eur), 2) as net_income_eur,
        ROUND(SUM(m.net_income_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100, 2) as cp_margin_pct,
        ROUND((SUM(m.net_income_eur) - SUM(m.bolt_delivery_campaign_cost_eur) - SUM(m.bolt_menu_campaign_cost_eur)) / NULLIF(SUM(m.gmv_eur), 0) * 100, 2) as cp_l2_margin_pct,
        ROUND(SUM(m.bolt_delivery_campaign_cost_eur), 2) as bolt_delivery_campaign_eur,
        ROUND(SUM(m.bolt_menu_campaign_cost_eur), 2) as bolt_menu_campaign_eur,
        ROUND(SUM(m.provider_delivery_campaign_cost_eur), 2) as provider_delivery_campaign_eur,
        ROUND(SUM(m.provider_menu_campaign_cost_eur), 2) as provider_menu_campaign_eur
    FROM ng_public_spark.etl_delivery_order_monetary_metrics m
    JOIN ng_delivery_spark.dim_provider_v2 p ON m.provider_id = p.provider_id
    WHERE m.country = 'ua'
      AND m.order_created_date >= '{DATA_START}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


OPERATIONAL_OVERVIEW_QUERY = f"""
SELECT DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd') as period,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight) / NULLIF(SUM(f.provider_commission_gmv_share_weight), 0) * 100, 1) as commission_gmv_pct,
  ROUND(SUM(f.provider_commission_aov_share_value * f.provider_commission_aov_share_weight) / NULLIF(SUM(f.provider_commission_aov_share_weight), 0) * 100, 1) as commission_aov_pct,
  ROUND(SUM(f.contribution_profit_rate_value * f.contribution_profit_rate_weight) / NULLIF(SUM(f.contribution_profit_rate_weight), 0) * 100, 2) as cp_margin_pct,
  ROUND(SUM(f.contribution_profit_without_demand_incentives_rate_value * f.contribution_profit_without_demand_incentives_rate_weight) / NULLIF(SUM(f.contribution_profit_without_demand_incentives_rate_weight), 0) * 100, 2) as cp_l2_margin_pct,
  ROUND(SUM(f.provider_acceptance_rate_value * f.provider_acceptance_rate_weight) / NULLIF(SUM(f.provider_acceptance_rate_weight), 0) * 100, 1) as acceptance_rate,
  ROUND(SUM(f.provider_active_rate_value * f.provider_active_rate_weight) / NULLIF(SUM(f.provider_active_rate_weight), 0) * 100, 1) as availability_rate,
  ROUND(SUM(f.provider_rating_per_order_value * f.provider_rating_per_order_weight) / NULLIF(SUM(f.provider_rating_per_order_weight), 0), 2) as avg_rating,
  ROUND(SUM(f.honey_order_rate_value * f.honey_order_rate_weight) / NULLIF(SUM(f.honey_order_rate_weight), 0) * 100, 1) as honey_rate,
  ROUND(SUM(f.bad_order_rate_value * f.bad_order_rate_weight) / NULLIF(SUM(f.bad_order_rate_weight), 0) * 100, 2) as bad_rate,
  ROUND(SUM(f.late_delivery_order_rate_value * f.late_delivery_order_rate_weight) / NULLIF(SUM(f.late_delivery_order_rate_weight), 0) * 100, 1) as late_delivery_rate,
  ROUND(SUM(f.late_pickup_order_rate_value * f.late_pickup_order_rate_weight) / NULLIF(SUM(f.late_pickup_order_rate_weight), 0) * 100, 1) as late_pickup_rate,
  ROUND(SUM(f.order_total_minutes_per_order_value * f.order_total_minutes_per_order_weight) / NULLIF(SUM(f.order_total_minutes_per_order_weight), 0), 1) as avg_delivery_min,
  SUM(f.delivered_orders_count) as orders,
  COUNT(DISTINCT CASE WHEN f.delivered_orders_count > 0 THEN f.provider_id END) as active_stores
FROM ng_delivery_spark.fact_provider_weekly f
JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND p.delivery_vertical IN ('store_3p_ent', 'store_3p_mm_smb')
  AND f.metric_timestamp_local >= '2026-01-01'
GROUP BY DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd')
ORDER BY period
"""

OPERATIONAL_PARTNER_QUERY = f"""
SELECT p.group_name, DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd') as period,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight) / NULLIF(SUM(f.provider_commission_gmv_share_weight), 0) * 100, 1) as commission_gmv_pct,
  ROUND(SUM(f.provider_commission_aov_share_value * f.provider_commission_aov_share_weight) / NULLIF(SUM(f.provider_commission_aov_share_weight), 0) * 100, 1) as commission_aov_pct,
  ROUND(SUM(f.contribution_profit_rate_value * f.contribution_profit_rate_weight) / NULLIF(SUM(f.contribution_profit_rate_weight), 0) * 100, 2) as cp_margin_pct,
  ROUND(SUM(f.contribution_profit_without_demand_incentives_rate_value * f.contribution_profit_without_demand_incentives_rate_weight) / NULLIF(SUM(f.contribution_profit_without_demand_incentives_rate_weight), 0) * 100, 2) as cp_l2_margin_pct,
  ROUND(SUM(f.provider_acceptance_rate_value * f.provider_acceptance_rate_weight) / NULLIF(SUM(f.provider_acceptance_rate_weight), 0) * 100, 1) as acceptance_rate,
  ROUND(SUM(f.provider_active_rate_value * f.provider_active_rate_weight) / NULLIF(SUM(f.provider_active_rate_weight), 0) * 100, 1) as availability_rate,
  ROUND(SUM(f.provider_rating_per_order_value * f.provider_rating_per_order_weight) / NULLIF(SUM(f.provider_rating_per_order_weight), 0), 2) as avg_rating,
  ROUND(SUM(f.honey_order_rate_value * f.honey_order_rate_weight) / NULLIF(SUM(f.honey_order_rate_weight), 0) * 100, 1) as honey_order_rate,
  ROUND(SUM(f.bad_order_rate_value * f.bad_order_rate_weight) / NULLIF(SUM(f.bad_order_rate_weight), 0) * 100, 2) as bad_order_rate,
  ROUND(SUM(f.late_delivery_order_rate_value * f.late_delivery_order_rate_weight) / NULLIF(SUM(f.late_delivery_order_rate_weight), 0) * 100, 1) as late_delivery_rate,
  ROUND(SUM(f.late_pickup_order_rate_value * f.late_pickup_order_rate_weight) / NULLIF(SUM(f.late_pickup_order_rate_weight), 0) * 100, 1) as late_pickup_rate,
  ROUND(SUM(f.order_total_minutes_per_order_value * f.order_total_minutes_per_order_weight) / NULLIF(SUM(f.order_total_minutes_per_order_weight), 0), 1) as avg_delivery_minutes,
  ROUND(SUM(f.order_item_replacement_rate_value * f.order_item_replacement_rate_weight) / NULLIF(SUM(f.order_item_replacement_rate_weight), 0) * 100, 2) as replacement_rate,
  ROUND(SUM(f.order_item_adjustment_rate_value * f.order_item_adjustment_rate_weight) / NULLIF(SUM(f.order_item_adjustment_rate_weight), 0) * 100, 2) as adjustment_rate,
  ROUND(SUM(f.provider_campaign_discount_gmv_share_value * f.provider_campaign_discount_gmv_share_weight) / NULLIF(SUM(f.provider_campaign_discount_gmv_share_weight), 0) * 100, 2) as item_discount_promo_share,
  SUM(f.delivered_orders_count) as orders,
  COUNT(DISTINCT CASE WHEN f.delivered_orders_count > 0 THEN f.provider_id END) as active_stores
FROM ng_delivery_spark.fact_provider_weekly f
JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND p.delivery_vertical IN ('store_3p_ent', 'store_3p_mm_smb')
  AND f.metric_timestamp_local >= '2026-01-01'
GROUP BY p.group_name, DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd')
HAVING SUM(f.delivered_orders_count) > 0
ORDER BY p.group_name, period
"""

TOP_PARTNERS_QUERY = f"""
SELECT p.group_name, ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur, COUNT(*) as orders
FROM ng_delivery_spark.fact_order_delivery f
JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE f.city_country_code = 'ua'
  AND f.order_state = 'delivered'
  AND f.order_created_date >= '{DATA_START}'
  AND p.delivery_vertical LIKE 'store_3p%'
GROUP BY p.group_name
ORDER BY gmv_eur DESC
LIMIT 20
"""

ACCEPTANCE_AVAILABILITY_QUERY = """
SELECT p.group_name,
  ROUND(AVG(t.acceptance_rate_last_30d), 3) as acceptance_rate_30d,
  ROUND(AVG(t.availability_rate_last_30d), 3) as availability_rate_30d,
  ROUND(AVG(t.avg_rating_last_30d), 2) as avg_rating_30d
FROM ng_public_spark.etl_incentives_provider_targeting_features t
JOIN ng_delivery_spark.dim_provider_v2 p ON t.provider_id = p.provider_id
WHERE t.provider_country_code = 'ua'
  AND p.delivery_vertical LIKE 'store_3p%'
  AND t.date = (SELECT MAX(date) FROM ng_public_spark.etl_incentives_provider_targeting_features WHERE provider_country_code = 'ua')
GROUP BY p.group_name
"""

ACCEPTANCE_OVERVIEW_QUERY = """
SELECT
  ROUND(AVG(t.acceptance_rate_last_30d), 3) as acceptance_rate_30d,
  ROUND(AVG(t.availability_rate_last_30d), 3) as availability_rate_30d,
  ROUND(AVG(t.avg_rating_last_30d), 2) as avg_rating_30d
FROM ng_public_spark.etl_incentives_provider_targeting_features t
JOIN ng_delivery_spark.dim_provider_v2 p ON t.provider_id = p.provider_id
WHERE t.provider_country_code = 'ua'
  AND p.delivery_vertical LIKE 'store_3p%'
  AND t.date = (SELECT MAX(date) FROM ng_public_spark.etl_incentives_provider_targeting_features WHERE provider_country_code = 'ua')
"""


def clean_row(row):
    return {k: to_float(v) if k != "period" and k != "group_name" else v for k, v in row.items()}


def main():
    connection = dbsql.connect(
        server_hostname=HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=TOKEN
    )
    cursor = connection.cursor()

    # 1. Top partners (determines the 10th partner)
    print("1. Fetching top partners...")
    top_partners = run_query(cursor, TOP_PARTNERS_QUERY)
    top_partners_clean = [{"group_name": r["group_name"], "gmv_eur": to_float(r["gmv_eur"]), "orders": to_int(r["orders"])} for r in top_partners]
    save_json("data_top_partners.json", top_partners_clean)

    tenth_partner = None
    for p in top_partners_clean:
        if p["group_name"] not in NAMED_PARTNERS:
            tenth_partner = p["group_name"]
            break
    all_partners = NAMED_PARTNERS + ([tenth_partner] if tenth_partner else [])
    print(f"  Partners: {all_partners}")

    # 2. Overview financial (weekly + monthly)
    print("2. Fetching overview financial...")
    overview_fin_weekly = [clean_row(r) for r in run_query(cursor, financial_query("week"))]
    overview_fin_monthly = [clean_row(r) for r in run_query(cursor, financial_query("month"))]
    save_json("data_overview_fin_weekly.json", overview_fin_weekly)
    save_json("data_overview_fin_monthly.json", overview_fin_monthly)

    # 3. Overview campaigns (weekly + monthly)
    print("3. Fetching overview campaigns...")
    overview_camp_weekly = [clean_row(r) for r in run_query(cursor, campaign_query("week"))]
    overview_camp_monthly = [clean_row(r) for r in run_query(cursor, campaign_query("month"))]
    save_json("data_overview_camp_weekly.json", overview_camp_weekly)
    save_json("data_overview_camp_monthly.json", overview_camp_monthly)

    # 4. Overview CP margins (monthly from monetary metrics)
    print("4. Fetching overview CP margins...")
    overview_cp_monthly = [clean_row(r) for r in run_query(cursor, cp_margins_query("month"))]
    save_json("data_overview_cp_monthly.json", overview_cp_monthly)

    # 5. Overview failed orders (monthly)
    print("5. Fetching failed orders...")
    failed_monthly = [clean_row(r) for r in run_query(cursor, failed_orders_query("month"))]
    save_json("data_failed_orders_monthly.json", failed_monthly)

    # 6. GMV by partner (monthly + weekly)
    print("6. Fetching GMV by partner...")
    gmv_monthly = [clean_row(r) for r in run_query(cursor, gmv_by_partner_query("month"))]
    gmv_weekly = [clean_row(r) for r in run_query(cursor, gmv_by_partner_query("week"))]
    save_json("data_gmv_by_partner_monthly.json", gmv_monthly)
    save_json("data_gmv_by_partner_weekly.json", gmv_weekly)

    # 7. Operational metrics from fact_provider_weekly (overview + partners)
    print("7. Fetching operational overview (fact_provider_weekly)...")
    ops_overview = run_query(cursor, OPERATIONAL_OVERVIEW_QUERY)
    ops_overview_clean = []
    for r in ops_overview:
        ops_overview_clean.append({
            "period": r["period"],
            "commission_gmv_pct": to_float(r["commission_gmv_pct"]),
            "commission_aov_pct": to_float(r["commission_aov_pct"]),
            "cp_margin_pct": to_float(r["cp_margin_pct"]),
            "cp_l2_margin_pct": to_float(r["cp_l2_margin_pct"]),
            "acceptance_rate": to_float(r["acceptance_rate"]),
            "availability_rate": to_float(r["availability_rate"]),
            "avg_rating": to_float(r["avg_rating"]),
            "honey_rate": to_float(r["honey_rate"]),
            "bad_rate": to_float(r["bad_rate"]),
            "late_delivery_rate": to_float(r["late_delivery_rate"]),
            "late_pickup_rate": to_float(r["late_pickup_rate"]),
            "avg_delivery_min": to_float(r["avg_delivery_min"]),
            "orders": to_int(r["orders"]),
            "active_stores": to_int(r["active_stores"])
        })
    save_json("data_ops_overview_weekly.json", ops_overview_clean)

    print("   Fetching operational partners (fact_provider_weekly)...")
    ops_partners = run_query(cursor, OPERATIONAL_PARTNER_QUERY)
    ops_partners_clean = []
    for r in ops_partners:
        ops_partners_clean.append({
            "group_name": r["group_name"],
            "period": r["period"],
            "commission_gmv_pct": to_float(r["commission_gmv_pct"]),
            "commission_aov_pct": to_float(r["commission_aov_pct"]),
            "cp_margin_pct": to_float(r["cp_margin_pct"]),
            "cp_l2_margin_pct": to_float(r["cp_l2_margin_pct"]),
            "acceptance_rate": to_float(r["acceptance_rate"]),
            "availability_rate": to_float(r["availability_rate"]),
            "avg_rating": to_float(r["avg_rating"]),
            "honey_order_rate": to_float(r["honey_order_rate"]),
            "bad_order_rate": to_float(r["bad_order_rate"]),
            "late_delivery_rate": to_float(r["late_delivery_rate"]),
            "late_pickup_rate": to_float(r["late_pickup_rate"]),
            "avg_delivery_minutes": to_float(r["avg_delivery_minutes"]),
            "replacement_rate": to_float(r["replacement_rate"]),
            "adjustment_rate": to_float(r["adjustment_rate"]),
            "item_discount_promo_share": to_float(r["item_discount_promo_share"]),
            "orders": to_int(r["orders"]),
            "active_stores": to_int(r["active_stores"])
        })
    save_json("data_ops_partners_weekly.json", ops_partners_clean)

    # 8. Partner financial (monthly)
    print("8. Fetching partner financial (monthly)...")
    partner_fin_rows = run_query(cursor, financial_query("month", "ALL_BY_GROUP"))
    partner_fin_clean = [clean_row(r) for r in partner_fin_rows]
    save_json("data_partner_fin_monthly.json", partner_fin_clean)

    # 9. Partner financial (weekly)
    print("   Fetching partner financial (weekly)...")
    partner_fin_w_rows = run_query(cursor, financial_query("week", "ALL_BY_GROUP"))
    partner_fin_w_clean = [clean_row(r) for r in partner_fin_w_rows]
    save_json("data_partner_fin_weekly.json", partner_fin_w_clean)

    # 10. Partner campaigns (monthly)
    print("9. Fetching partner campaigns (monthly)...")
    partner_camp_rows = run_query(cursor, campaign_query("month", "ALL_BY_GROUP"))
    partner_camp_clean = [clean_row(r) for r in partner_camp_rows]
    save_json("data_partner_camp_monthly.json", partner_camp_clean)

    # 11. Partner campaigns (weekly)
    print("   Fetching partner campaigns (weekly)...")
    partner_camp_w_rows = run_query(cursor, campaign_query("week", "ALL_BY_GROUP"))
    partner_camp_w_clean = [clean_row(r) for r in partner_camp_w_rows]
    save_json("data_partner_camp_weekly.json", partner_camp_w_clean)

    # 12. Acceptance/availability
    print("10. Fetching acceptance/availability...")
    acc_overview = run_query(cursor, ACCEPTANCE_OVERVIEW_QUERY)
    acc_partners = run_query(cursor, ACCEPTANCE_AVAILABILITY_QUERY)
    acc_data = {"overview": [clean_row(r) for r in acc_overview]}
    for r in acc_partners:
        acc_data[r["group_name"]] = [{"acceptance_rate_30d": to_float(r["acceptance_rate_30d"]), "availability_rate_30d": to_float(r["availability_rate_30d"]), "avg_rating_30d": to_float(r["avg_rating_30d"])}]
    save_json("data_acceptance.json", acc_data)

    # 13. Metadata
    from datetime import datetime, timezone
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_start": DATA_START,
        "partners_list": all_partners,
        "tenth_partner": tenth_partner
    }
    save_json("data_metadata.json", metadata)

    cursor.close()
    connection.close()
    print("\nAll data fetched successfully!")


if __name__ == "__main__":
    main()
