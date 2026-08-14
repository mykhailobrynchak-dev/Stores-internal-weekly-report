-- Core 13-week partner dataset used by the report.
-- Current week excludes CURRENT_DATE so each reported day is complete.
WITH base AS (
  SELECT
    DATE_TRUNC('week', f.order_created_date) AS week_start,
    CASE
      WHEN p.brand_name = 'OKKO MARKET' THEN p.brand_name
      ELSE COALESCE(p.group_name, p.brand_name, f.provider_name)
    END AS partner,
    f.order_state,
    f.order_gmv_eur,
    f.demand_incentives_eur,
    f.demand_refunds_eur,
    f.total_refunds_eur
  FROM main.ng_delivery.fact_order_delivery f
  JOIN main.ng_delivery.dim_provider_v2 p
    ON f.provider_id = p.provider_id
  WHERE f.city_country_code = 'ua'
    AND (
      p.delivery_vertical LIKE 'store_3p%'
      OR p.group_name IN ('ANRI-PHARM', 'BRSM', 'VAPORS', 'PIVASOV')
    )
    AND f.order_created_date >= DATE_ADD(DATE_TRUNC('week', CURRENT_DATE()), -91)
    AND f.order_created_date < CURRENT_DATE()
)
SELECT
  CAST(week_start AS DATE) AS week_start,
  partner,
  SUM(CASE WHEN order_state = 'delivered' THEN 1 ELSE 0 END) AS orders,
  ROUND(SUM(CASE WHEN order_state = 'delivered' THEN order_gmv_eur ELSE 0 END), 2) AS gmv_eur,
  ROUND(SUM(CASE WHEN order_state = 'delivered' THEN COALESCE(demand_incentives_eur, 0) ELSE 0 END), 2) AS demand_incentives_eur,
  ROUND(SUM(COALESCE(demand_refunds_eur, 0)), 2) AS demand_refunds_eur,
  ROUND(SUM(COALESCE(total_refunds_eur, 0)), 2) AS total_refunds_eur,
  SUM(CASE WHEN order_state = 'delivered' AND COALESCE(demand_incentives_eur, 0) != 0 THEN 1 ELSE 0 END) AS incentive_orders,
  SUM(CASE WHEN COALESCE(demand_refunds_eur, 0) != 0 THEN 1 ELSE 0 END) AS demand_refund_orders
FROM base
GROUP BY week_start, partner
HAVING orders > 0 OR demand_refunds_eur != 0
ORDER BY week_start, gmv_eur DESC;
