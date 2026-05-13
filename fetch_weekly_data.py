"""Fetch latest data from Databricks and update JSON files for report generation."""
import os, json
from databricks import sql as dbsql

HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ALL_PARTNERS = [
    "LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK",
    "VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "TAISTRA", "BEERLAND K",
    "PYVNA BORODA", "WINETIME", "LEPRUKON", "TOCHKA", "SPRAGA",
    "DIMPYVA", "MAXBEER", "CHILL TIME", "FLOWER SHOP", "MAXBEER GROUP",
    "RODYNNA KOVBASKA", "NO TABOO", "BEERLAND", "SPAR"
]

PARTNERS_SQL = ",".join(f"'{p}'" for p in ALL_PARTNERS)

OVERVIEW_QUERY = f"""
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
  AND f.metric_timestamp_local >= '2026-01-26'
GROUP BY DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd')
ORDER BY period
"""

PARTNER_QUERY = f"""
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
  SUM(f.delivered_orders_count) as orders,
  COUNT(DISTINCT CASE WHEN f.delivered_orders_count > 0 THEN f.provider_id END) as active_stores
FROM ng_delivery_spark.fact_provider_weekly f
JOIN ng_delivery_spark.dim_provider_v2 p ON f.provider_id = p.provider_id
WHERE p.country_code = 'ua'
  AND p.group_name IN ({PARTNERS_SQL})
  AND f.metric_timestamp_local >= '2026-01-26'
GROUP BY p.group_name, DATE_FORMAT(f.metric_timestamp_local, 'yyyy-MM-dd')
HAVING SUM(f.delivered_orders_count) > 0
ORDER BY p.group_name, period
"""


def run_query(cursor, query):
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def main():
    connection = dbsql.connect(
        server_hostname=HOST,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        access_token=TOKEN
    )
    cursor = connection.cursor()

    # Fetch overview data
    print("Fetching overview weekly data...")
    overview_rows = run_query(cursor, OVERVIEW_QUERY)
    overview_data = []
    for r in overview_rows:
        overview_data.append({
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
            "orders": int(r["orders"]) if r["orders"] else 0,
            "active_stores": int(r["active_stores"]) if r["active_stores"] else 0
        })

    with open(os.path.join(SCRIPT_DIR, "overview_corrected_weekly.json"), "w") as f:
        json.dump(overview_data, f)
    print(f"  Saved {len(overview_data)} overview rows")

    # Fetch partner data
    print("Fetching partner weekly data...")
    partner_rows = run_query(cursor, PARTNER_QUERY)
    partner_data = []
    for r in partner_rows:
        partner_data.append({
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
            "orders": int(r["orders"]) if r["orders"] else 0,
            "active_stores": int(r["active_stores"]) if r["active_stores"] else 0
        })

    # Split into batch1 (first 12 partners alphabetically in our list) and batch2
    batch1_partners = set(ALL_PARTNERS[:12])
    batch1 = [r for r in partner_data if r["group_name"] in batch1_partners]
    batch2 = [r for r in partner_data if r["group_name"] not in batch1_partners]

    with open(os.path.join(SCRIPT_DIR, "partners_corrected_batch1.json"), "w") as f:
        json.dump(batch1, f)
    with open(os.path.join(SCRIPT_DIR, "partners_corrected_batch2.json"), "w") as f:
        json.dump(batch2, f)
    print(f"  Saved {len(batch1)} batch1 + {len(batch2)} batch2 partner rows")

    cursor.close()
    connection.close()
    print("Done!")


if __name__ == "__main__":
    main()
