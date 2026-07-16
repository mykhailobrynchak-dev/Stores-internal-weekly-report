"""Fetch ALL data from Databricks for the 3P Stores Weekly Report."""
import os, json, sys
from collections import defaultdict
from pathlib import Path
from databricks import sql as dbsql


def _load_dotenv():
    """Load local .env (NOT committed to git) so the script runs locally too."""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _require_env(name):
    value = os.environ.get(name)
    if not value:
        print(f"Missing {name}. Create .env from .env.example or export the variable.", file=sys.stderr)
        sys.exit(1)
    return value


def _connect_kwargs():
    """DATABRICKS_TLS_NO_VERIFY=1 — local-only workaround for corporate proxy SSL errors."""
    kwargs = {}
    if os.environ.get("DATABRICKS_TLS_NO_VERIFY", "").strip().lower() in ("1", "true", "yes"):
        kwargs["_tls_no_verify"] = True
    return kwargs


_load_dotenv()

HOST = _require_env("DATABRICKS_HOST")
TOKEN = _require_env("DATABRICKS_TOKEN")
WAREHOUSE_ID = _require_env("DATABRICKS_WAREHOUSE_ID")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_START = "2026-01-01"

NAMED_PARTNERS = [
    "LOKO", "VARUS", "KOPIYKA", "CAFE RYNOK", "HOP HEY",
    "BEER MARKET", "TAISTRA", "RUKAVYCHKA", "PYVNA BORODA"
]

ALL_TRACKED_PARTNERS = [
    "LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK",
    "VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "TAISTRA", "BEERLAND K",
    "PYVNA BORODA", "WINETIME", "LEPRUKON", "TOCHKA", "SPRAGA",
    "DIMPYVA", "MAXBEER", "FLOWER SHOP",
    "RODYNNA KOVBASKA", "NO TABOO", "SPAR", "ANRI-PHARM",
    "BRSM", "VAPORS", "PIVASOV", "OKKO MARKET", "VAPERY | VAPE SHOP"
]

EXTRA_PARTNERS = ["ANRI-PHARM", "BRSM", "VAPORS", "PIVASOV"]

# Brands tracked as standalone partners even though they live inside a larger group_name
# (e.g. OKKO MARKET is a brand within group OKKO CAFE GROUP). GROUP_KEY splits them out.
BRAND_PARTNERS = ["OKKO MARKET"]
_BRAND_LIST_SQL = ",".join(f"'{b}'" for b in BRAND_PARTNERS)
GROUP_KEY = f"CASE WHEN p.brand_name IN ({_BRAND_LIST_SQL}) THEN p.brand_name ELSE p.group_name END"

VERTICAL_FILTER = "(p.delivery_vertical LIKE 'store_3p%' OR p.group_name IN ({extra}))"
VERTICAL_FILTER_SQL = VERTICAL_FILTER.format(extra=",".join(f"'{p}'" for p in EXTRA_PARTNERS))
VERTICAL_LIST_OPS = "('store_3p_ent', 'store_3p_mm_smb')"


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
    group_col = f", {GROUP_KEY}" if group_filter == "ALL_BY_GROUP" else ""
    group_select = f"{GROUP_KEY} as group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND {GROUP_KEY} = '{group_filter}'"
    week_filter = "AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE()) AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)" if granularity == "week" else ""

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        COUNT(*) as orders,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur,
        ROUND(SUM(f.total_price_before_discount_eur) / COUNT(*), 2) as aov_with_delivery,
        ROUND(SUM(f.provider_price_before_discount_eur) / COUNT(*), 2) as aov_items_only,
        ROUND(SUM(f.delivery_price_eur) / COUNT(*), 2) as eater_fees_per_order,
        ROUND(SUM(f.delivery_price_eur - f.small_order_fee_eur - f.order_service_fee_eur), 2) as delivery_fee_total,
        ROUND(SUM(f.delivery_price_eur - f.small_order_fee_eur - f.order_service_fee_eur) / COUNT(*), 2) as delivery_fee_per_order,
        ROUND(SUM(f.small_order_fee_eur), 2) as small_order_fee_total,
        ROUND(SUM(f.small_order_fee_eur) / COUNT(*), 2) as small_order_fee_per_order,
        ROUND(SUM(f.order_service_fee_eur), 2) as service_fee_total,
        ROUND(SUM(f.order_service_fee_eur) / COUNT(*), 2) as service_fee_per_order,
        ROUND(SUM(CASE WHEN f.is_bolt_plus_order THEN f.order_gmv_eur ELSE 0 END) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 2) as bolt_plus_gmv_share,
        SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) as users_activated,
        ROUND(SUM(CASE WHEN f.is_first_delivery_order THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as new_user_share,
        COUNT(DISTINCT f.user_id) as active_users,
        ROUND(SUM(f.total_refunds_eur), 2) as total_refunds_eur,
        ROUND(SUM(f.total_refunds_eur) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 2) as refund_rate_pct,
        ROUND(SUM(f.supply_refunds_eur) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 3) as supply_refund_gmv_pct,
        ROUND(SUM(f.demand_refunds_eur) / NULLIF(SUM(f.order_gmv_eur), 0) * 100, 3) as demand_refund_gmv_pct
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      {week_filter}
      AND {VERTICAL_FILTER_SQL}
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def refund_query(granularity, group_filter=None):
    """Refunds from ALL orders (not just delivered) to capture supply refunds."""
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    group_col = f", {GROUP_KEY}" if group_filter == "ALL_BY_GROUP" else ""
    group_select = f"{GROUP_KEY} as group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND {GROUP_KEY} = '{group_filter}'"
    week_filter = "AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE()) AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)" if granularity == "week" else ""

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        ROUND(SUM(f.supply_refunds_eur) / NULLIF(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur END), 0) * 100, 3) as supply_refund_gmv_pct,
        ROUND(SUM(f.demand_refunds_eur) / NULLIF(SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur END), 0) * 100, 3) as demand_refund_gmv_pct
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_created_date >= '{DATA_START}'
      {week_filter}
      AND {VERTICAL_FILTER_SQL}
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def campaign_query(granularity, group_filter=None):
    time_col = "DATE_TRUNC('week', CAST(m.order_created_date AS DATE))" if granularity == "week" else "DATE_TRUNC('month', CAST(m.order_created_date AS DATE))"
    group_col = f", {GROUP_KEY}" if group_filter == "ALL_BY_GROUP" else ""
    group_select = f"{GROUP_KEY} as group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND {GROUP_KEY} = '{group_filter}'"
    week_filter = "AND CAST(m.order_created_date AS DATE) < DATE_TRUNC('week', CURRENT_DATE()) AND CAST(m.order_created_date AS DATE) >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)" if granularity == "week" else ""

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        ROUND(SUM(m.gmv_eur), 2) as gmv_eur,
        ROUND(SUM(m.delivery_discount_eur) + SUM(m.menu_discount_eur), 2) as campaigns_discount_eur,
        ROUND(SUM(m.bolt_delivery_campaign_cost_eur) + SUM(m.bolt_menu_campaign_cost_eur), 2) as bolt_spend_eur,
        ROUND(SUM(m.provider_delivery_campaign_cost_eur) + SUM(m.provider_menu_campaign_cost_eur), 2) as merchant_spend_eur
    FROM hive_metastore.ng_public_spark.etl_delivery_order_monetary_metrics m
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON m.provider_id = p.provider_id
    WHERE m.country = 'ua'
      AND m.order_created_date >= '{DATA_START}'
      {week_filter}
      AND {VERTICAL_FILTER_SQL}
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def failed_orders_query(granularity, group_filter=None):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    group_col = f", {GROUP_KEY}" if group_filter == "ALL_BY_GROUP" else ""
    group_select = f"{GROUP_KEY} as group_name, " if group_filter == "ALL_BY_GROUP" else ""
    group_clause = ""
    if group_filter and group_filter != "ALL_BY_GROUP":
        group_clause = f"AND {GROUP_KEY} = '{group_filter}'"
    week_filter = "AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE()) AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)" if granularity == "week" else ""

    return f"""
    SELECT
        {group_select}CAST({time_col} AS STRING) as period,
        COUNT(*) as total_placed,
        SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) as delivered,
        SUM(CASE WHEN f.order_state != 'delivered' AND (f.is_rejected_by_provider = true OR f.is_not_responded_by_provider = true) THEN 1 ELSE 0 END) as failed_merchant,
        SUM(CASE WHEN f.order_state != 'delivered' AND f.is_rejected_by_provider = false AND (f.is_not_responded_by_provider = false OR f.is_not_responded_by_provider IS NULL) THEN 1 ELSE 0 END) as failed_bolt_courier,
        ROUND(SUM(CASE WHEN f.order_state != 'delivered' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as failed_rate_total
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_created_date >= '{DATA_START}'
      {week_filter}
      AND {VERTICAL_FILTER_SQL}
      {group_clause}
    GROUP BY {time_col}{group_col}
    ORDER BY period
    """


def gmv_by_partner_query(granularity):
    time_col = "DATE_TRUNC('week', f.order_created_date)" if granularity == "week" else "DATE_TRUNC('month', f.order_created_date)"
    week_filter = "AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE()) AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)" if granularity == "week" else ""
    return f"""
    SELECT
        CAST({time_col} AS STRING) as period,
        {GROUP_KEY} as group_name,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur,
        COUNT(*) as orders
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      {week_filter}
      AND {VERTICAL_FILTER_SQL}
    GROUP BY {time_col}, {GROUP_KEY}
    ORDER BY period, gmv_eur DESC
    """


def item_defect_query():
    # Defect rates = eater-impacting adjustments over ALL dish states (numerator)
    # divided by ACTIVE dish items (denominator). Matches Looker (e.g. VARUS Jun 2026:
    # quantity 12.1%, replacement 18.8%, weighted 1.1%, price 0%).
    return f"""
    SELECT
        CAST(DATE_TRUNC('week', b.order_created_date) AS STRING) as period,
        {GROUP_KEY} as group_name,
        SUM(CASE WHEN b.has_item_quantity_adjustment_with_eater_impact THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN b.basket_item_state = 'active' THEN 1 ELSE 0 END), 0) as quantity_defect_rate,
        SUM(CASE WHEN b.is_item_replacement THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN b.basket_item_state = 'active' THEN 1 ELSE 0 END), 0) as item_replacement_rate,
        SUM(CASE WHEN b.has_item_weighted_adjustment_with_eater_impact THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN b.basket_item_state = 'active' THEN 1 ELSE 0 END), 0) as weighted_defect_rate,
        SUM(CASE WHEN b.has_item_price_adjustment_with_price_increase THEN 1 ELSE 0 END) * 100.0 / NULLIF(SUM(CASE WHEN b.basket_item_state = 'active' THEN 1 ELSE 0 END), 0) as price_defect_rate
    FROM hive_metastore.ng_delivery_spark.dim_basket_item_delivery b
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON b.provider_id = p.provider_id
    WHERE p.country_code = 'ua'
      AND b.order_state = 'delivered'
      AND b.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)
      AND b.order_created_date < DATE_TRUNC('week', CURRENT_DATE())
      AND b.basket_item_is_dish = true
      AND {VERTICAL_FILTER_SQL}
    GROUP BY DATE_TRUNC('week', b.order_created_date), {GROUP_KEY}
    ORDER BY period, group_name
    """


def city_breakdown_query():
    return f"""
    SELECT
        CAST(DATE_TRUNC('week', f.order_created_date) AS STRING) as period,
        f.city_name,
        COUNT(*) as orders,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE())
      AND {VERTICAL_FILTER_SQL}
    GROUP BY DATE_TRUNC('week', f.order_created_date), f.city_name
    ORDER BY period, gmv_eur DESC
    """


def city_eater_fees_query():
    return f"""
    SELECT
        CAST(DATE_TRUNC('week', f.order_created_date) AS STRING) as period,
        f.city_name,
        ROUND(SUM(f.delivery_price_eur) / COUNT(*), 2) as eater_fees_per_order,
        ROUND(SUM(f.delivery_price_eur - f.small_order_fee_eur - f.order_service_fee_eur) / COUNT(*), 2) as delivery_fee_per_order,
        ROUND(SUM(f.small_order_fee_eur) / COUNT(*), 2) as small_order_fee_per_order,
        ROUND(SUM(f.order_service_fee_eur) / COUNT(*), 2) as service_fee_per_order
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= '{DATA_START}'
      AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE())
      AND {VERTICAL_FILTER_SQL}
    GROUP BY DATE_TRUNC('week', f.order_created_date), f.city_name
    ORDER BY period, f.city_name
    """


def _ops_window(granularity):
    """Returns (period_expr, date_filter). Weekly = last 10 completed weeks; monthly = from DATA_START."""
    if granularity == "month":
        period_expr = "DATE_FORMAT(DATE_TRUNC('month', f.metric_timestamp_local), 'yyyy-MM-dd')"
        date_filter = f"AND f.metric_timestamp_local >= '{DATA_START}' AND f.metric_timestamp_local < DATE_TRUNC('week', CURRENT_DATE())"
    else:
        period_expr = "DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd')"
        date_filter = "AND f.metric_timestamp_local >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70) AND f.metric_timestamp_local < DATE_TRUNC('week', CURRENT_DATE())"
    return period_expr, date_filter


def operational_overview_query(granularity="week"):
    period_expr, date_filter = _ops_window(granularity)
    extra_partners_sql = ",".join(f"'{p}'" for p in EXTRA_PARTNERS)
    return f"""
SELECT {period_expr} as period,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight) / NULLIF(SUM(f.provider_commission_gmv_share_weight), 0) * 100, 1) as commission_gmv_pct,
  ROUND(SUM(f.provider_commission_aov_share_value * f.provider_commission_aov_share_weight) / NULLIF(SUM(f.provider_commission_aov_share_weight), 0) * 100, 1) as commission_aov_pct,
  ROUND(SUM(total_contribution_profit_eur) / NULLIF(SUM(total_gmv_before_discounts_eur), 0) * 100, 2) as cp_margin_pct,
  ROUND(SUM(total_contribution_profit_without_demand_incentives_eur) / NULLIF(SUM(total_gmv_before_discounts_eur), 0) * 100, 2) as cp_l2_margin_pct,
  ROUND(SUM(f.provider_acceptance_rate_value * f.provider_acceptance_rate_weight) / NULLIF(SUM(f.provider_acceptance_rate_weight), 0) * 100, 1) as acceptance_rate,
  ROUND(SUM(f.provider_active_rate_value * f.provider_active_rate_weight) / NULLIF(SUM(f.provider_active_rate_weight), 0) * 100, 1) as availability_rate,
  ROUND(SUM(f.provider_rating_per_order_value * f.provider_rating_per_order_weight) / NULLIF(SUM(f.provider_rating_per_order_weight), 0), 2) as avg_rating,
  ROUND(SUM(f.honey_order_rate_value * f.honey_order_rate_weight) / NULLIF(SUM(f.honey_order_rate_weight), 0) * 100, 1) as honey_rate,
  ROUND(SUM(f.bad_order_rate_value * f.bad_order_rate_weight) / NULLIF(SUM(f.bad_order_rate_weight), 0) * 100, 2) as bad_rate,
  ROUND(SUM(f.late_delivery_order_rate_value * f.late_delivery_order_rate_weight) / NULLIF(SUM(f.late_delivery_order_rate_weight), 0) * 100, 1) as late_delivery_rate,
  ROUND(SUM(f.late_pickup_order_rate_value * f.late_pickup_order_rate_weight) / NULLIF(SUM(f.late_pickup_order_rate_weight), 0) * 100, 1) as late_pickup_rate,
  ROUND(SUM(f.order_total_minutes_per_order_value * f.order_total_minutes_per_order_weight) / NULLIF(SUM(f.order_total_minutes_per_order_weight), 0), 1) as avg_delivery_min,
  ROUND(SUM(f.courier_minutes_per_order_value * f.courier_minutes_per_order_weight) / NULLIF(SUM(f.courier_minutes_per_order_weight), 0), 1) as courier_min_per_order,
  ROUND((SUM(f.total_contribution_profit_eur) - SUM(f.total_contribution_profit_without_demand_incentives_eur)) / NULLIF(SUM(f.total_gmv_before_discounts_eur), 0) * 100, 2) as demand_incentives_gmv_share,
  ROUND(SUM(f.batched_order_rate_value * f.batched_order_rate_weight) / NULLIF(SUM(f.batched_order_rate_weight), 0) * 100, 1) as batching_rate,
  ROUND(SUM(f.courier_acceptance_rate_value * f.courier_acceptance_rate_weight) / NULLIF(SUM(f.courier_acceptance_rate_weight), 0) * 100, 1) as courier_acceptance_rate,
  ROUND(SUM(f.total_invoiced_courier_costs_eur) / NULLIF(SUM(f.delivered_orders_count), 0), 2) as cpo_eur,
  ROUND(SUM(f.provider_sku_session_availability_rate_value) / NULLIF(SUM(f.provider_sku_session_availability_rate_weight), 0) * 100, 1) as sku_availability_pct,
  SUM(f.delivered_orders_count) as orders,
  COUNT(DISTINCT f.provider_id) as total_stores,
  COUNT(DISTINCT CASE WHEN f.delivered_orders_count > 0 THEN f.provider_id END) as stores_with_orders
FROM hive_metastore.ng_delivery_spark.fact_provider_weekly f
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND (p.delivery_vertical IN {VERTICAL_LIST_OPS} OR p.group_name IN ({extra_partners_sql}))
  {date_filter}
GROUP BY {period_expr}
ORDER BY period
"""


def operational_partner_query(granularity="week"):
    period_expr, date_filter = _ops_window(granularity)
    extra_partners_sql = ",".join(f"'{p}'" for p in EXTRA_PARTNERS)
    return f"""
SELECT {GROUP_KEY} as group_name, {period_expr} as period,
  ROUND(SUM(f.provider_commission_gmv_share_value * f.provider_commission_gmv_share_weight) / NULLIF(SUM(f.provider_commission_gmv_share_weight), 0) * 100, 1) as commission_gmv_pct,
  ROUND(SUM(f.provider_commission_aov_share_value * f.provider_commission_aov_share_weight) / NULLIF(SUM(f.provider_commission_aov_share_weight), 0) * 100, 1) as commission_aov_pct,
  ROUND(SUM(total_contribution_profit_eur) / NULLIF(SUM(total_gmv_before_discounts_eur), 0) * 100, 2) as cp_margin_pct,
  ROUND(SUM(total_contribution_profit_without_demand_incentives_eur) / NULLIF(SUM(total_gmv_before_discounts_eur), 0) * 100, 2) as cp_l2_margin_pct,
  ROUND(SUM(f.provider_acceptance_rate_value * f.provider_acceptance_rate_weight) / NULLIF(SUM(f.provider_acceptance_rate_weight), 0) * 100, 1) as acceptance_rate,
  ROUND(SUM(f.provider_active_rate_value * f.provider_active_rate_weight) / NULLIF(SUM(f.provider_active_rate_weight), 0) * 100, 1) as availability_rate,
  ROUND(SUM(f.provider_rating_per_order_value * f.provider_rating_per_order_weight) / NULLIF(SUM(f.provider_rating_per_order_weight), 0), 2) as avg_rating,
  ROUND(SUM(f.honey_order_rate_value * f.honey_order_rate_weight) / NULLIF(SUM(f.honey_order_rate_weight), 0) * 100, 1) as honey_order_rate,
  ROUND(SUM(f.bad_order_rate_value * f.bad_order_rate_weight) / NULLIF(SUM(f.bad_order_rate_weight), 0) * 100, 2) as bad_order_rate,
  ROUND(SUM(f.late_delivery_order_rate_value * f.late_delivery_order_rate_weight) / NULLIF(SUM(f.late_delivery_order_rate_weight), 0) * 100, 1) as late_delivery_rate,
  ROUND(SUM(f.late_pickup_order_rate_value * f.late_pickup_order_rate_weight) / NULLIF(SUM(f.late_pickup_order_rate_weight), 0) * 100, 1) as late_pickup_rate,
  ROUND(SUM(f.order_total_minutes_per_order_value * f.order_total_minutes_per_order_weight) / NULLIF(SUM(f.order_total_minutes_per_order_weight), 0), 1) as avg_delivery_minutes,
  ROUND(SUM(f.courier_minutes_per_order_value * f.courier_minutes_per_order_weight) / NULLIF(SUM(f.courier_minutes_per_order_weight), 0), 1) as courier_minutes_per_order,
  ROUND((SUM(f.total_contribution_profit_eur) - SUM(f.total_contribution_profit_without_demand_incentives_eur)) / NULLIF(SUM(f.total_gmv_before_discounts_eur), 0) * 100, 2) as demand_incentives_gmv_share,
  ROUND(SUM(f.batched_order_rate_value * f.batched_order_rate_weight) / NULLIF(SUM(f.batched_order_rate_weight), 0) * 100, 1) as batching_rate,
  ROUND(SUM(f.courier_acceptance_rate_value * f.courier_acceptance_rate_weight) / NULLIF(SUM(f.courier_acceptance_rate_weight), 0) * 100, 1) as courier_acceptance_rate,
  ROUND(SUM(f.order_item_replacement_rate_value * f.order_item_replacement_rate_weight) / NULLIF(SUM(f.order_item_replacement_rate_weight), 0) * 100, 2) as replacement_rate,
  ROUND(SUM(f.order_item_adjustment_rate_value * f.order_item_adjustment_rate_weight) / NULLIF(SUM(f.order_item_adjustment_rate_weight), 0) * 100, 2) as adjustment_rate,
  ROUND(SUM(f.provider_campaign_discount_gmv_share_value * f.provider_campaign_discount_gmv_share_weight) / NULLIF(SUM(f.provider_campaign_discount_gmv_share_weight), 0) * 100, 2) as item_discount_promo_share,
  ROUND(SUM(f.total_invoiced_courier_costs_eur) / NULLIF(SUM(f.delivered_orders_count), 0), 2) as cpo_eur,
  ROUND(SUM(f.provider_sku_session_availability_rate_value) / NULLIF(SUM(f.provider_sku_session_availability_rate_weight), 0) * 100, 1) as sku_availability_pct,
  SUM(f.delivered_orders_count) as orders,
  COUNT(DISTINCT f.provider_id) as total_stores,
  COUNT(DISTINCT CASE WHEN f.delivered_orders_count > 0 THEN f.provider_id END) as stores_with_orders
FROM hive_metastore.ng_delivery_spark.fact_provider_weekly f
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND (p.delivery_vertical IN {VERTICAL_LIST_OPS} OR p.group_name IN ({extra_partners_sql}))
  {date_filter}
GROUP BY {GROUP_KEY}, {period_expr}
HAVING SUM(f.delivered_orders_count) > 0
ORDER BY group_name, period
"""

def sku_median_query(granularity="week"):
    """Median (across a brand's providers) of provider_catalog_size = available SKU count.
    Source: etl_delivery_market_provider_sku_ml_features — covers ALL SKUs (incl. non-food,
    e.g. pharmacy), unlike the dish-only menu metrics. Per provider, take the latest snapshot in each bucket."""
    trunc = "month" if granularity == "month" else "week"
    if granularity == "month":
        win = f"as_on_date >= '{DATA_START}' AND as_on_date < DATE_TRUNC('week', CURRENT_DATE())"
    else:
        win = "as_on_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70) AND as_on_date < DATE_TRUNC('week', CURRENT_DATE())"
    return f"""
    WITH daily AS (
        SELECT DISTINCT provider_id, as_on_date,
               DATE_TRUNC('{trunc}', as_on_date) AS period_bucket,
               provider_catalog_size AS sku
        FROM hive_metastore.ng_delivery_spark.etl_delivery_market_provider_sku_ml_features
        WHERE {win} AND provider_catalog_size IS NOT NULL
    ),
    snap AS (
        SELECT provider_id, period_bucket, sku,
               ROW_NUMBER() OVER (PARTITION BY provider_id, period_bucket ORDER BY as_on_date DESC) AS rn
        FROM daily
    )
    SELECT CAST(s.period_bucket AS STRING) as period,
           {GROUP_KEY} as group_name,
           ROUND(percentile(s.sku, 0.5), 0) as median_available_sku
    FROM snap s
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON s.provider_id = p.provider_id
    WHERE s.rn = 1
      AND p.country_code = 'ua'
      AND {VERTICAL_FILTER_SQL}
    GROUP BY s.period_bucket, {GROUP_KEY}
    HAVING percentile(s.sku, 0.5) > 0
    ORDER BY period, group_name
    """


TOP_PARTNERS_QUERY = f"""
SELECT {GROUP_KEY} as group_name, ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur, COUNT(*) as orders
FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE f.city_country_code = 'ua'
  AND f.order_state = 'delivered'
  AND f.order_created_date >= '{DATA_START}'
  AND {VERTICAL_FILTER_SQL}
GROUP BY {GROUP_KEY}
ORDER BY gmv_eur DESC
LIMIT 20
"""

ACCEPTANCE_AVAILABILITY_QUERY = f"""
SELECT {GROUP_KEY} as group_name,
  ROUND(AVG(t.acceptance_rate_last_30d), 3) as acceptance_rate_30d,
  ROUND(AVG(t.availability_rate_last_30d), 3) as availability_rate_30d,
  ROUND(AVG(t.avg_rating_last_30d), 2) as avg_rating_30d
FROM hive_metastore.ng_public_spark.etl_incentives_provider_targeting_features t
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON t.provider_id = p.provider_id
WHERE t.provider_country_code = 'ua'
  AND {VERTICAL_FILTER_SQL}
  AND t.date = (SELECT MAX(date) FROM hive_metastore.ng_public_spark.etl_incentives_provider_targeting_features WHERE provider_country_code = 'ua')
GROUP BY {GROUP_KEY}
"""

ACCEPTANCE_OVERVIEW_QUERY = f"""
SELECT
  ROUND(AVG(t.acceptance_rate_last_30d), 3) as acceptance_rate_30d,
  ROUND(AVG(t.availability_rate_last_30d), 3) as availability_rate_30d,
  ROUND(AVG(t.avg_rating_last_30d), 2) as avg_rating_30d
FROM hive_metastore.ng_public_spark.etl_incentives_provider_targeting_features t
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON t.provider_id = p.provider_id
WHERE t.provider_country_code = 'ua'
  AND {VERTICAL_FILTER_SQL}
  AND t.date = (SELECT MAX(date) FROM hive_metastore.ng_public_spark.etl_incentives_provider_targeting_features WHERE provider_country_code = 'ua')
"""


def partner_city_breakdown_query():
    return f"""
    SELECT
        CAST(DATE_TRUNC('week', f.order_created_date) AS STRING) as period,
        {GROUP_KEY} as group_name,
        f.city_name,
        COUNT(*) as orders,
        ROUND(SUM(f.order_gmv_eur), 2) as gmv_eur
    FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
    JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
    WHERE f.city_country_code = 'ua'
      AND f.order_state = 'delivered'
      AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -70)
      AND f.order_created_date < DATE_TRUNC('week', CURRENT_DATE())
      AND {VERTICAL_FILTER_SQL}
    GROUP BY DATE_TRUNC('week', f.order_created_date), {GROUP_KEY}, f.city_name
    ORDER BY period, group_name, gmv_eur DESC
    """


def clean_row(row):
    return {k: to_float(v) if k != "period" and k != "group_name" and k != "city_name" else v for k, v in row.items()}


def clean_ops_overview_row(r):
    return {
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
        "courier_min_per_order": to_float(r["courier_min_per_order"]),
        "demand_incentives_gmv_share": to_float(r["demand_incentives_gmv_share"]),
        "batching_rate": to_float(r["batching_rate"]),
        "courier_acceptance_rate": to_float(r["courier_acceptance_rate"]),
        "cpo_eur": to_float(r["cpo_eur"]),
        "sku_availability_pct": to_float(r["sku_availability_pct"]),
        "orders": to_int(r["orders"]),
        "total_stores": to_int(r["total_stores"]),
        "stores_with_orders": to_int(r["stores_with_orders"]),
    }


def clean_ops_partner_row(r):
    return {
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
        "courier_minutes_per_order": to_float(r["courier_minutes_per_order"]),
        "demand_incentives_gmv_share": to_float(r["demand_incentives_gmv_share"]),
        "batching_rate": to_float(r["batching_rate"]),
        "courier_acceptance_rate": to_float(r["courier_acceptance_rate"]),
        "replacement_rate": to_float(r["replacement_rate"]),
        "adjustment_rate": to_float(r["adjustment_rate"]),
        "item_discount_promo_share": to_float(r["item_discount_promo_share"]),
        "cpo_eur": to_float(r["cpo_eur"]),
        "sku_availability_pct": to_float(r["sku_availability_pct"]),
        "orders": to_int(r["orders"]),
        "total_stores": to_int(r["total_stores"]),
        "stores_with_orders": to_int(r["stores_with_orders"]),
    }


def main():
    connection = dbsql.connect(
        server_hostname=HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=TOKEN,
        **_connect_kwargs()
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
    all_partners = list(dict.fromkeys(NAMED_PARTNERS + ([tenth_partner] if tenth_partner else []) + ALL_TRACKED_PARTNERS))
    print(f"  Partners ({len(all_partners)}): {all_partners[:10]}...")

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

    # 4. Failed orders (weekly + monthly, overview + partner)
    print("4. Fetching failed orders...")
    failed_weekly = [clean_row(r) for r in run_query(cursor, failed_orders_query("week"))]
    failed_monthly = [clean_row(r) for r in run_query(cursor, failed_orders_query("month"))]
    save_json("data_failed_orders_weekly.json", failed_weekly)
    save_json("data_failed_orders_monthly.json", failed_monthly)

    partner_failed_weekly = [clean_row(r) for r in run_query(cursor, failed_orders_query("week", "ALL_BY_GROUP"))]
    partner_failed_monthly = [clean_row(r) for r in run_query(cursor, failed_orders_query("month", "ALL_BY_GROUP"))]
    save_json("data_partner_failed_weekly.json", partner_failed_weekly)
    save_json("data_partner_failed_monthly.json", partner_failed_monthly)

    # 5. GMV by partner (monthly + weekly)
    print("5. Fetching GMV by partner...")
    gmv_monthly = [clean_row(r) for r in run_query(cursor, gmv_by_partner_query("month"))]
    gmv_weekly = [clean_row(r) for r in run_query(cursor, gmv_by_partner_query("week"))]
    save_json("data_gmv_by_partner_monthly.json", gmv_monthly)
    save_json("data_gmv_by_partner_weekly.json", gmv_weekly)

    # 6. Operational metrics from fact_provider_weekly (overview + partners)
    #    Weekly = last 10 completed weeks; Monthly = accumulated from DATA_START (Jan 2026).
    print("6. Fetching operational overview (fact_provider_weekly)...")
    ops_overview_clean = [clean_ops_overview_row(r) for r in run_query(cursor, operational_overview_query("week"))]
    save_json("data_ops_overview_weekly.json", ops_overview_clean)
    ops_overview_m_clean = [clean_ops_overview_row(r) for r in run_query(cursor, operational_overview_query("month"))]
    save_json("data_ops_overview_monthly.json", ops_overview_m_clean)

    print("   Fetching operational partners (fact_provider_weekly)...")
    ops_partners_clean = [clean_ops_partner_row(r) for r in run_query(cursor, operational_partner_query("week"))]
    save_json("data_ops_partners_weekly.json", ops_partners_clean)
    ops_partners_m_clean = [clean_ops_partner_row(r) for r in run_query(cursor, operational_partner_query("month"))]
    save_json("data_ops_partners_monthly.json", ops_partners_m_clean)

    print("   Fetching median available SKU (etl_delivery_menu_active_menu_metrics_by_day)...")
    sku_median_weekly = [clean_row(r) for r in run_query(cursor, sku_median_query("week"))]
    save_json("data_sku_median_weekly.json", sku_median_weekly)
    sku_median_monthly = [clean_row(r) for r in run_query(cursor, sku_median_query("month"))]
    save_json("data_sku_median_monthly.json", sku_median_monthly)

    # 7. Partner financial (monthly + weekly)
    print("7. Fetching partner financial...")
    partner_fin_rows = run_query(cursor, financial_query("month", "ALL_BY_GROUP"))
    partner_fin_clean = [clean_row(r) for r in partner_fin_rows]
    save_json("data_partner_fin_monthly.json", partner_fin_clean)

    partner_fin_w_rows = run_query(cursor, financial_query("week", "ALL_BY_GROUP"))
    partner_fin_w_clean = [clean_row(r) for r in partner_fin_w_rows]
    save_json("data_partner_fin_weekly.json", partner_fin_w_clean)

    # 8. Partner campaigns (monthly + weekly)
    print("8. Fetching partner campaigns...")
    partner_camp_rows = run_query(cursor, campaign_query("month", "ALL_BY_GROUP"))
    partner_camp_clean = [clean_row(r) for r in partner_camp_rows]
    save_json("data_partner_camp_monthly.json", partner_camp_clean)

    partner_camp_w_rows = run_query(cursor, campaign_query("week", "ALL_BY_GROUP"))
    partner_camp_w_clean = [clean_row(r) for r in partner_camp_w_rows]
    save_json("data_partner_camp_weekly.json", partner_camp_w_clean)

    # 9. Acceptance/availability
    print("9. Fetching acceptance/availability...")
    acc_overview = run_query(cursor, ACCEPTANCE_OVERVIEW_QUERY)
    acc_partners = run_query(cursor, ACCEPTANCE_AVAILABILITY_QUERY)
    acc_data = {"overview": [clean_row(r) for r in acc_overview]}
    for r in acc_partners:
        acc_data[r["group_name"]] = [{"acceptance_rate_30d": to_float(r["acceptance_rate_30d"]), "availability_rate_30d": to_float(r["availability_rate_30d"]), "avg_rating_30d": to_float(r["avg_rating_30d"])}]
    save_json("data_acceptance.json", acc_data)

    # 10. Item defect metrics
    print("10. Fetching item defect metrics...")
    item_defects = [clean_row(r) for r in run_query(cursor, item_defect_query())]
    save_json("data_item_defects_weekly.json", item_defects)

    # 11. City breakdown (weekly)
    print("11. Fetching city breakdown...")
    city_breakdown = [clean_row(r) for r in run_query(cursor, city_breakdown_query())]
    save_json("data_city_breakdown_weekly.json", city_breakdown)

    # 12. City eater fees (weekly)
    print("12. Fetching city eater fees...")
    city_fees = [clean_row(r) for r in run_query(cursor, city_eater_fees_query())]
    save_json("data_city_eater_fees_weekly.json", city_fees)

    # 13. Partner city breakdown
    print("13. Fetching partner city breakdown...")
    partner_city = [clean_row(r) for r in run_query(cursor, partner_city_breakdown_query())]
    save_json("data_partner_city_weekly.json", partner_city)

    # 14. Refunds from all orders (supply refunds only on non-delivered)
    print("14. Fetching refund metrics (all orders)...")
    refund_weekly = [clean_row(r) for r in run_query(cursor, refund_query("week"))]
    refund_monthly = [clean_row(r) for r in run_query(cursor, refund_query("month"))]
    save_json("data_refund_weekly.json", refund_weekly)
    save_json("data_refund_monthly.json", refund_monthly)
    refund_partner_weekly = [clean_row(r) for r in run_query(cursor, refund_query("week", "ALL_BY_GROUP"))]
    refund_partner_monthly = [clean_row(r) for r in run_query(cursor, refund_query("month", "ALL_BY_GROUP"))]
    save_json("data_refund_partner_weekly.json", refund_partner_weekly)
    save_json("data_refund_partner_monthly.json", refund_partner_monthly)

    # 15. Active Stores count (providers with status='active')
    print("15. Fetching active stores count...")
    active_stores_query = f"""
    SELECT {GROUP_KEY} as group_name, COUNT(DISTINCT p.provider_id) as active_stores
    FROM hive_metastore.ng_delivery_spark.dim_provider_v2 p
    WHERE p.country_code = 'ua'
      AND p.provider_status = 'active'
      AND {VERTICAL_FILTER_SQL}
    GROUP BY {GROUP_KEY}
    """
    active_stores_rows = run_query(cursor, active_stores_query)
    active_stores_data = {"total": sum(to_int(r["active_stores"]) for r in active_stores_rows)}
    for r in active_stores_rows:
        active_stores_data[r["group_name"]] = to_int(r["active_stores"])
    save_json("data_active_stores.json", active_stores_data)

    # 16. Metadata
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
