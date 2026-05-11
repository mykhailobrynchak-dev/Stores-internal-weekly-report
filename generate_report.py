"""
3P Stores Ukraine — Weekly Performance Report Generator
Queries Databricks, aggregates data at weekly + monthly levels,
and generates a self-contained HTML report.
"""

import os
import json
import sys
from datetime import datetime, timedelta
from databricks import sql as databricks_sql

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
DATABRICKS_HTTP_PATH = os.environ.get("DATABRICKS_HTTP_PATH")

DATA_START_DATE = "2026-02-01"

NAMED_PARTNERS = [
    "LOKO", "VARUS", "KOPIYKA", "CAFE RYNOK", "HOP HEY",
    "BEER MARKET", "TAISTRA", "RUKAVYCHKA", "PYVNA BORODA"
]


def get_connection():
    return databricks_sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )


def execute_query(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    return [dict(zip(columns, row)) for row in rows]


def get_financial_overview(conn, granularity="month", group_filter=None):
    """Financial metrics aggregated by week or month."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', f.order_created_date)"
    else:
        time_col = "DATE_TRUNC('month', f.order_created_date)"

    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        COUNT(*) as orders,
        SUM(f.order_gmv_eur) as gmv_eur,
        SUM(f.total_price_before_discount_eur) / COUNT(*) as aov_with_delivery,
        SUM(f.provider_price_before_discount_eur) / COUNT(*) as aov_items_only,
        (SUM(f.delivery_price_eur) + SUM(f.small_order_fee_eur) + SUM(f.order_service_fee_eur)) / COUNT(*) as eater_fees_per_order,
        SUM(f.delivery_price_eur) as delivery_fee_total,
        SUM(f.delivery_price_eur) / COUNT(*) as delivery_fee_per_order,
        SUM(f.small_order_fee_eur) as small_order_fee_total,
        SUM(f.small_order_fee_eur) / COUNT(*) as small_order_fee_per_order,
        SUM(f.order_service_fee_eur) as service_fee_total,
        SUM(f.order_service_fee_eur) / COUNT(*) as service_fee_per_order,
        SUM(CASE WHEN f.is_bolt_plus_order THEN f.order_gmv_eur ELSE 0 END) / SUM(f.order_gmv_eur) * 100 as bolt_plus_gmv_share,
        SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) as new_user_orders,
        SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as new_user_share,
        SUM(f.total_refunds_eur) as total_refunds_eur,
        SUM(f.total_refunds_eur) / SUM(f.order_gmv_eur) * 100 as refund_rate_pct
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}
    ORDER BY period
    """
    return execute_query(conn, query)


def get_cp_margins(conn, granularity="month", group_filter=None):
    """CP and CP L2 margins from monetary metrics table."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', CAST(m.order_created_date AS DATE))"
    else:
        time_col = "SUBSTR(m.order_created_date, 1, 7)"

    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        SUM(m.gmv_eur) as gmv_eur,
        SUM(m.net_income_eur) as net_income_eur,
        SUM(m.net_income_eur) / NULLIF(SUM(m.gmv_eur), 0) * 100 as cp_margin_pct,
        (SUM(m.net_income_eur) - SUM(m.bolt_delivery_campaign_cost_eur) - SUM(m.bolt_menu_campaign_cost_eur)) / NULLIF(SUM(m.gmv_eur), 0) * 100 as cp_l2_margin_pct,
        SUM(m.bolt_delivery_campaign_cost_eur) as bolt_delivery_campaign_eur,
        SUM(m.bolt_menu_campaign_cost_eur) as bolt_menu_campaign_eur,
        SUM(m.provider_delivery_campaign_cost_eur) as provider_delivery_campaign_eur,
        SUM(m.provider_menu_campaign_cost_eur) as provider_menu_campaign_eur,
        SUM(m.delivery_discount_eur) as delivery_discount_eur,
        SUM(m.menu_discount_eur) as menu_discount_eur
    FROM ng_public_spark.etl_delivery_order_monetary_metrics m
    JOIN ng_delivery_spark.dim_provider_v2 p ON m.provider_id = p.provider_id
    WHERE m.country = 'ua'
      AND m.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}
    ORDER BY period
    """
    return execute_query(conn, query)


def get_operational_overview(conn, granularity="month", group_filter=None):
    """Operational metrics: honey, bad, late, failed rates."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', f.order_created_date)"
    else:
        time_col = "DATE_TRUNC('month', f.order_created_date)"

    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        COUNT(*) as delivered_orders,
        COUNT(DISTINCT f.provider_id) as active_stores,
        SUM(CASE WHEN f.is_honey_order THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as honey_order_rate,
        SUM(CASE WHEN f.is_bad_order THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as bad_order_rate,
        SUM(CASE WHEN f.is_order_late_to_eater_5_min THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as late_delivery_rate,
        SUM(CASE WHEN f.is_order_late_to_partner_5_min THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as late_pickup_rate,
        AVG(CASE WHEN f.order_delivery_minutes > 0 AND f.order_delivery_minutes < 180 THEN f.order_delivery_minutes END) as avg_delivery_minutes,
        AVG(CASE WHEN f.courier_waiting_to_pickup_seconds > 0 THEN f.courier_waiting_to_pickup_seconds / 60.0 END) as avg_courier_wait_at_provider_min,
        SUM(CASE WHEN f.order_has_discrepancies THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as item_discrepancy_rate
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}
    ORDER BY period
    """
    return execute_query(conn, query)


def get_failed_orders(conn, granularity="month", group_filter=None):
    """Failed order breakdown (includes non-delivered orders)."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', f.order_created_date)"
    else:
        time_col = "DATE_TRUNC('month', f.order_created_date)"

    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        COUNT(*) as total_placed,
        SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) as delivered,
        SUM(CASE WHEN f.order_state != 'delivered' AND (f.is_rejected_by_provider = true OR f.is_not_responded_by_provider = true) THEN 1 ELSE 0 END) as failed_merchant,
        SUM(CASE WHEN f.order_state != 'delivered' AND f.is_rejected_by_provider = false AND (f.is_not_responded_by_provider = false OR f.is_not_responded_by_provider IS NULL) THEN 1 ELSE 0 END) as failed_bolt_courier,
        SUM(CASE WHEN f.order_state != 'delivered' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as failed_rate_total
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}
    ORDER BY period
    """
    return execute_query(conn, query)


def get_campaign_analytics(conn, granularity="month", group_filter=None):
    """Campaign investment breakdown: Bolt vs Partner."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', f.order_created_date)"
    else:
        time_col = "DATE_TRUNC('month', f.order_created_date)"

    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        SUM(f.order_gmv_eur) as gmv_eur,
        SUM(f.demand_incentives_eur) as bolt_demand_incentives_eur,
        SUM(f.supply_incentives_eur) as bolt_supply_incentives_eur,
        SUM(f.demand_incentives_eur) + SUM(f.supply_incentives_eur) as bolt_total_investment_eur,
        (SUM(f.demand_incentives_eur) + SUM(f.supply_incentives_eur)) / NULLIF(SUM(f.order_gmv_eur), 0) * 100 as bolt_investment_pct_gmv,
        SUM(f.order_provider_spend_provider_campaign_eur) as partner_investment_eur,
        SUM(f.order_provider_spend_provider_campaign_eur) / NULLIF(SUM(f.order_gmv_eur), 0) * 100 as partner_investment_pct_gmv,
        SUM(f.bolt_spend_user_lifecycle_activation_campaign) as bolt_activation_eur,
        SUM(f.bolt_spend_user_lifecycle_reactivation_campaign) as bolt_reactivation_eur,
        SUM(f.bolt_spend_user_lifecycle_engagement_campaign) as bolt_engagement_eur,
        SUM(f.bolt_spend_liquidity_campaign) as bolt_liquidity_eur,
        SUM(f.bolt_spend_marketing_campaign) as bolt_marketing_eur
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
      {group_clause}
    GROUP BY {time_col}
    ORDER BY period
    """
    return execute_query(conn, query)


def get_gmv_by_partner(conn, granularity="month"):
    """GMV breakdown by partner group for pie chart."""
    if granularity == "week":
        time_col = "DATE_TRUNC('week', f.order_created_date)"
    else:
        time_col = "DATE_TRUNC('month', f.order_created_date)"

    query = f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        p.group_name,
        SUM(f.order_gmv_eur) as gmv_eur,
        COUNT(*) as orders
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
    GROUP BY {time_col}, p.group_name
    ORDER BY period, gmv_eur DESC
    """
    return execute_query(conn, query)


def get_acceptance_availability(conn, group_filter=None):
    """Latest acceptance rate and availability from provider targeting features."""
    group_clause = ""
    if group_filter:
        group_clause = f"AND p.group_name = '{group_filter}'"

    query = f"""
    SELECT
        AVG(t.acceptance_rate_last_7d) as acceptance_rate_7d,
        AVG(t.acceptance_rate_last_30d) as acceptance_rate_30d,
        AVG(t.availability_rate_last_7d) as availability_rate_7d,
        AVG(t.availability_rate_last_30d) as availability_rate_30d,
        AVG(t.avg_rating_last_7d) as avg_rating_7d,
        AVG(t.avg_rating_last_30d) as avg_rating_30d
    FROM ng_public_spark.etl_incentives_provider_targeting_features t
    JOIN ng_delivery_spark.dim_provider_v2 p ON t.provider_id = p.provider_id
    WHERE t.provider_country_code = 'ua'
      AND p.delivery_vertical LIKE 'store_3p%'
      AND t.date = (SELECT MAX(date) FROM ng_public_spark.etl_incentives_provider_targeting_features WHERE provider_country_code = 'ua')
      {group_clause}
    """
    return execute_query(conn, query)


def get_top_partners(conn):
    """Get top 10 partners by GMV to identify the 10th largest."""
    query = f"""
    SELECT
        p.group_name,
        SUM(f.order_gmv_eur) as gmv_eur,
        COUNT(*) as orders
    FROM ng_delivery_spark.fact_order_delivery f
    JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START_DATE}'
      AND p.delivery_vertical LIKE 'store_3p%'
    GROUP BY p.group_name
    ORDER BY gmv_eur DESC
    LIMIT 15
    """
    return execute_query(conn, query)


def serialize_for_json(obj):
    """Handle non-serializable types."""
    if obj is None:
        return None
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    try:
        return float(obj)
    except (TypeError, ValueError):
        return str(obj)


def collect_all_data(conn):
    """Collect all data for the report."""
    print("Fetching top partners...")
    top_partners = get_top_partners(conn)

    tenth_partner = None
    for partner in top_partners:
        if partner["group_name"] not in NAMED_PARTNERS:
            tenth_partner = partner["group_name"]
            break
    all_partners = NAMED_PARTNERS + ([tenth_partner] if tenth_partner else [])

    print("Fetching overview data (monthly)...")
    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "data_start": DATA_START_DATE,
        "partners_list": all_partners,
        "tenth_partner": tenth_partner,
        "top_partners_gmv": top_partners,
        "overview": {
            "monthly": {
                "financial": get_financial_overview(conn, "month"),
                "cp_margins": get_cp_margins(conn, "month"),
                "operational": get_operational_overview(conn, "month"),
                "failed_orders": get_failed_orders(conn, "month"),
                "campaigns": get_campaign_analytics(conn, "month"),
                "gmv_by_partner": get_gmv_by_partner(conn, "month"),
            },
            "weekly": {
                "financial": get_financial_overview(conn, "week"),
                "cp_margins": get_cp_margins(conn, "week"),
                "operational": get_operational_overview(conn, "week"),
                "failed_orders": get_failed_orders(conn, "week"),
                "campaigns": get_campaign_analytics(conn, "week"),
                "gmv_by_partner": get_gmv_by_partner(conn, "week"),
            },
        },
        "acceptance_availability": {
            "overview": get_acceptance_availability(conn),
        },
    }

    print("Fetching overview data (weekly)...")
    # Already fetched above

    print("Fetching partner-level data...")
    data["partners"] = {}
    for partner in all_partners:
        print(f"  → {partner}...")
        data["partners"][partner] = {
            "monthly": {
                "financial": get_financial_overview(conn, "month", partner),
                "cp_margins": get_cp_margins(conn, "month", partner),
                "operational": get_operational_overview(conn, "month", partner),
                "failed_orders": get_failed_orders(conn, "month", partner),
                "campaigns": get_campaign_analytics(conn, "month", partner),
            },
            "weekly": {
                "financial": get_financial_overview(conn, "week", partner),
                "cp_margins": get_cp_margins(conn, "week", partner),
                "operational": get_operational_overview(conn, "week", partner),
                "failed_orders": get_failed_orders(conn, "week", partner),
                "campaigns": get_campaign_analytics(conn, "week", partner),
            },
        }
        data["acceptance_availability"][partner] = get_acceptance_availability(conn, partner)

    return data


def generate_html(data):
    """Generate the complete HTML report with embedded data."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "template.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, default=serialize_for_json)
    html = template.replace("/*__REPORT_DATA__*/", f"const REPORT_DATA = {data_json};")

    output_path = os.path.join(script_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Report generated: {output_path}")
    return output_path


def main():
    if not all([DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH]):
        print("Error: Missing environment variables.")
        print("Required: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH")
        sys.exit(1)

    print("Connecting to Databricks...")
    conn = get_connection()

    try:
        data = collect_all_data(conn)
        generate_html(data)
        print("Done!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
