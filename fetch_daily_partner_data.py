#!/usr/bin/env python3
"""Fetch the daily ENT/SMB Stores partner performance dataset from Databricks."""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from databricks import sql as dbsql


ROOT = Path(__file__).parent
KYIV = ZoneInfo("Europe/Kyiv")
LOOKBACK_DAYS = 95

QUERY = f"""
WITH providers AS (
    SELECT
        provider_id,
        CASE
            WHEN business_segment_v2 = 'Enterprise (AM Segment)' THEN 'ENT'
            WHEN business_segment_v2 = 'SMB (AM Segment)' THEN 'SMB'
        END AS segment,
        COALESCE(group_name, brand_name, provider_name) AS partner
    FROM main.ng_delivery.dim_provider_v2
    WHERE country_code = 'ua'
      AND provider_status = 'active'
      AND delivery_vertical IN ('store_3p_ent', 'store_3p_mm_smb')
      AND business_segment_v2 IN ('Enterprise (AM Segment)', 'SMB (AM Segment)')
),
orders AS (
    SELECT
        f.order_created_date AS date,
        p.segment,
        p.partner,
        SUM(CASE WHEN f.order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
        SUM(CASE WHEN f.order_state = 'delivered' THEN f.order_gmv_eur ELSE 0 END) AS gmv_eur,
        SUM(CASE WHEN f.order_state = 'delivered' AND f.is_bad_order THEN 1 ELSE 0 END) AS bad_orders,
        SUM(CASE WHEN f.order_state IN ('failed', 'rejected') THEN 1 ELSE 0 END) AS failed_orders
    FROM main.ng_delivery.fact_order_delivery f
    JOIN providers p ON p.provider_id = f.provider_id
    WHERE f.order_created_date >= DATE_ADD(CURRENT_DATE(), -{LOOKBACK_DAYS})
      AND f.order_created_date < CURRENT_DATE()
    GROUP BY 1, 2, 3
),
availability AS (
    SELECT
        d.observation_date AS date,
        p.segment,
        p.partner,
        SUM(d.provider_active_time_minutes) AS active_minutes,
        SUM(d.provider_working_time_minutes) AS working_minutes,
        COUNT(DISTINCT d.provider_id) AS stores_observed
    FROM main.ng_delivery.fact_provider_daily d
    JOIN providers p ON p.provider_id = d.provider_id
    WHERE d.observation_date >= DATE_ADD(CURRENT_DATE(), -{LOOKBACK_DAYS})
      AND d.observation_date < CURRENT_DATE()
    GROUP BY 1, 2, 3
)
SELECT
    COALESCE(o.date, a.date) AS date,
    COALESCE(o.segment, a.segment) AS segment,
    COALESCE(o.partner, a.partner) AS partner,
    COALESCE(o.orders, 0) AS orders,
    COALESCE(o.gmv_eur, 0) AS gmv_eur,
    COALESCE(o.bad_orders, 0) AS bad_orders,
    COALESCE(o.failed_orders, 0) AS failed_orders,
    a.active_minutes,
    a.working_minutes,
    COALESCE(a.stores_observed, 0) AS stores_observed
FROM orders o
FULL OUTER JOIN availability a
  ON o.date = a.date AND o.segment = a.segment AND o.partner = a.partner
ORDER BY 1, 2, 3
"""


def _load_dotenv():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _value(value):
    if isinstance(value, (Decimal,)):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def main():
    _load_dotenv()
    host = os.environ["DATABRICKS_HOST"]
    token = os.environ["DATABRICKS_TOKEN"]
    http_path = os.getenv("DATABRICKS_HTTP_PATH") or (
        f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}"
    )
    with dbsql.connect(
        server_hostname=host, http_path=http_path, access_token=token
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(QUERY)
            columns = [column[0] for column in cursor.description]
            rows = [
                {name: _value(value) for name, value in zip(columns, row)}
                for row in cursor.fetchall()
            ]

    if not rows:
        raise RuntimeError("Daily Stores query returned no rows; existing report was preserved.")

    payload = {
        "generated_at": datetime.now(KYIV).isoformat(),
        "through": max(row["date"] for row in rows),
        "lookback_days": LOOKBACK_DAYS,
        "scope": (
            "UA Stores partners in Enterprise (AM Segment) and SMB (AM Segment); "
            "Mid-market is intentionally excluded."
        ),
        "rows": rows,
    }
    (ROOT / "daily_partner_data.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Published {len(rows)} partner-day rows through {payload['through']}.")


if __name__ == "__main__":
    main()
