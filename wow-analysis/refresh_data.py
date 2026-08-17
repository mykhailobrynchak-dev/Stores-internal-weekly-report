"""Refresh the last-week and month-to-date slices of data.json from Databricks.

Run: python3 wow-analysis/refresh_data.py
Requires DATABRICKS_HOST, DATABRICKS_TOKEN and DATABRICKS_WAREHOUSE_ID.
"""
import json
import os
from pathlib import Path

import databricks.sql

DATA = Path(__file__).with_name("data.json")

SCOPE = """
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

WEEK_SQL = f"""
WITH base AS (
  SELECT {PARTNER} AS partner,
         f.order_state, f.order_gmv_eur, f.demand_incentives_eur,
         f.demand_refunds_eur, f.total_refunds_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p ON f.provider_id = p.provider_id
  WHERE {SCOPE}
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


def query(cursor, sql):
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def main():
    host = os.environ["DATABRICKS_HOST"].replace("https://", "").rstrip("/")
    with databricks.sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        access_token=os.environ["DATABRICKS_TOKEN"],
    ) as conn, conn.cursor() as cur:
        periods = {
            "last_week": ("2026-08-10", "2026-08-16"),
            "prior_week": ("2026-08-03", "2026-08-09"),
            "mtd_current": ("2026-08-01", "2026-08-16"),
            "mtd_prior": ("2026-07-01", "2026-07-16"),
        }
        result = {
            name: query(cur, WEEK_SQL.format(start=start, end=end))
            for name, (start, end) in periods.items()
        }

    data = json.loads(DATA.read_text())
    econ_last = {r["partner"]: r for r in data["partner_economics_last_week"]}
    econ_prior = {r["partner"]: r for r in data["partner_economics_prior_week"]}

    def with_economics(rows, econ):
        merged = []
        for row in rows:
            e = econ.get(row["partner"], {})
            merged.append({
                **{k: float(v) if isinstance(v, (int, float)) else v for k, v in row.items()},
                "commission_gmv_pct": e.get("commission_gmv_pct"),
                "cm_l1_eur": e.get("cm_l1_eur"),
                "cm_l1_pct": e.get("cm_l1_pct"),
            })
        return merged

    data["partner_last_week"] = with_economics(result["last_week"], econ_last)
    data["partner_prior_week"] = with_economics(result["prior_week"], econ_prior)
    data["partner_mtd_current"] = result["mtd_current"]
    data["partner_mtd_prior"] = result["mtd_prior"]

    # The weekly trend must show the complete week 10-16 Aug, not the partial WTD window.
    data["weekly_partner"] = [r for r in data["weekly_partner"] if r["week_start"] != "2026-08-10"]
    data["weekly_partner"] += [{"week_start": "2026-08-10", **r} for r in result["last_week"]]
    data["weekly_partner"].sort(key=lambda r: (r["week_start"], -r["gmv_eur"]))

    data["metadata"].update({
        "data_through": "2026-08-16",
        "current_week": "2026-08-10",
        "current_week_label": "10–16 Aug",
        "prior_week_label": "3–9 Aug",
        "mtd_label": "1–16 Aug",
        "mtd_prior_label": "1–16 Jul",
    })

    DATA.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    for name, rows in result.items():
        print(f"{name}: {len(rows)} partners, "
              f"orders={sum(r['orders'] for r in rows):,}, "
              f"gmv={sum(r['gmv_eur'] for r in rows):,.0f}, "
              f"di={sum(r['demand_incentives_eur'] for r in rows):,.0f}, "
              f"dr={sum(r['demand_refunds_eur'] for r in rows):,.2f}")


if __name__ == "__main__":
    main()
