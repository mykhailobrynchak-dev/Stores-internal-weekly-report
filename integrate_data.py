"""Assemble all fetched Databricks data into the final HTML report."""
import calendar, json, os, math
from collections import defaultdict
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

NAMED_PARTNERS = [
    "LOKO", "VARUS", "KOPIYKA", "CAFE RYNOK", "HOP HEY",
    "BEER MARKET", "TAISTRA", "RUKAVYCHKA", "PYVNA BORODA"
]

ALL_TRACKED_PARTNERS = [
    "LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK",
    "VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "TAISTRA", "BEERLAND K",
    "PYVNA BORODA", "WINETIME", "LEPRUKON", "TOCHKA", "SPRAGA",
    "DIMPYVA", "MAXBEER", "FLOWER SHOP", "ALTBIER",
    "RODYNNA KOVBASKA", "NO TABOO", "SPAR", "ANRI-PHARM",
    "BRSM", "VAPORS", "PIVASOV", "OKKO MARKET", "VAPERY | VAPE SHOP",
    # Future / onboarding key accounts (not yet live on Bolt UA stores; render empty with a banner)
    "AUCHAN", "ATB", "FLOWERS UA", "THRASH", "E-ZOO", "MASTER ZOO",
    "РОСТ", "BYLE TA SYKHE", "FORA", "ANC", "BLYZENKO", "LIKI 24"
]


def load_json(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        print(f"  WARNING: {filename} not found")
        return [] if filename != "data_acceptance.json" and filename != "data_metadata.json" else {}
    with open(path) as f:
        return json.load(f)


def fmt_period(raw):
    """Normalize period string to 'YYYY-MM-DD 00:00:00' format."""
    s = str(raw).replace("T00:00:00.000Z", "").replace("T", " ").rstrip("Z").strip()
    if len(s) == 10:
        return s + " 00:00:00"
    return s


def quarter_key(period_str):
    parts = period_str.replace(" 00:00:00", "").split("-")
    q = math.ceil(int(parts[1]) / 3)
    return f"{parts[0]}-{q*3-2:02d}-01 00:00:00"


def avg_vals(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def median_vals(rows, key):
    vals = sorted(r[key] for r in rows if r.get(key) is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return round(vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2, 0)


def weighted_avg(rows, val_key, weight_key):
    total_w = sum(r.get(weight_key, 0) or 0 for r in rows)
    if total_w == 0:
        return avg_vals(rows, val_key)
    return round(sum((r.get(val_key, 0) or 0) * (r.get(weight_key, 0) or 0) for r in rows) / total_w, 2)


def aggregate_financial(rows):
    """Aggregate financial rows (weekly->monthly or monthly->quarterly)."""
    total_orders = sum(r.get("orders", 0) or 0 for r in rows)
    total_gmv = sum(r.get("gmv_eur", 0) or 0 for r in rows)
    if total_orders == 0:
        return None
    return {
        "orders": total_orders,
        "gmv_eur": round(total_gmv, 2),
        "aov_with_delivery": round(sum((r.get("aov_with_delivery", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "aov_items_only": round(total_gmv / total_orders, 2),
        "eater_fees_per_order": round(sum((r.get("eater_fees_per_order", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "delivery_fee_total": round(sum(r.get("delivery_fee_total", 0) or 0 for r in rows), 2),
        "delivery_fee_per_order": round(sum((r.get("delivery_fee_per_order", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "small_order_fee_total": round(sum(r.get("small_order_fee_total", 0) or 0 for r in rows), 2),
        "small_order_fee_per_order": round(sum((r.get("small_order_fee_per_order", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "service_fee_total": round(sum(r.get("service_fee_total", 0) or 0 for r in rows), 2),
        "service_fee_per_order": round(sum((r.get("service_fee_per_order", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "bolt_plus_gmv_share": round(sum((r.get("bolt_plus_gmv_share", 0) or 0) * (r.get("orders", 0) or 0) for r in rows) / total_orders, 2),
        "users_activated": sum(r.get("users_activated", 0) or 0 for r in rows),
        "new_user_share": round(sum(r.get("users_activated", 0) or 0 for r in rows) * 100.0 / total_orders, 2),
        "active_users": sum(r.get("active_users", 0) or 0 for r in rows),
        "total_refunds_eur": round(sum(r.get("total_refunds_eur", 0) or 0 for r in rows), 2),
        "refund_rate_pct": round(sum(r.get("total_refunds_eur", 0) or 0 for r in rows) / total_gmv * 100, 2) if total_gmv > 0 else 0,
        "supply_refund_gmv_pct": round(sum((r.get("supply_refund_gmv_pct", 0) or 0) * (r.get("gmv_eur", 0) or 0) for r in rows) / total_gmv, 2) if total_gmv > 0 else 0,
        "demand_refund_gmv_pct": round(sum((r.get("demand_refund_gmv_pct", 0) or 0) * (r.get("gmv_eur", 0) or 0) for r in rows) / total_gmv, 2) if total_gmv > 0 else 0,
    }


def aggregate_campaigns(rows):
    total_gmv = sum(r.get("gmv_eur", 0) or 0 for r in rows)
    total_discount = sum(r.get("campaigns_discount_eur", 0) or 0 for r in rows)
    total_bolt = sum(r.get("bolt_spend_eur", 0) or 0 for r in rows)
    total_merch = sum(r.get("merchant_spend_eur", 0) or 0 for r in rows)
    total_orders = sum(r.get("orders", 0) or 0 for r in rows)
    campaign_orders = sum(r.get("campaign_orders", 0) or 0 for r in rows)
    bolt_campaign_orders = sum(r.get("bolt_campaign_orders", 0) or 0 for r in rows)
    return {
        "gmv_eur": round(total_gmv, 2),
        "campaigns_discount_eur": round(total_discount, 2),
        "bolt_spend_eur": round(total_bolt, 2),
        "merchant_spend_eur": round(total_merch, 2),
        "orders": total_orders,
        "campaign_orders": campaign_orders,
        "bolt_campaign_orders": bolt_campaign_orders,
    }


def aggregate_failed(rows):
    """Aggregate failed-order rows (monthly->quarterly)."""
    total_placed = sum(r.get("total_placed", 0) or 0 for r in rows)
    delivered = sum(r.get("delivered", 0) or 0 for r in rows)
    failed_merchant = sum(r.get("failed_merchant", 0) or 0 for r in rows)
    failed_bolt_courier = sum(r.get("failed_bolt_courier", 0) or 0 for r in rows)
    return {
        "total_placed": total_placed,
        "delivered": delivered,
        "failed_merchant": failed_merchant,
        "failed_bolt_courier": failed_bolt_courier,
        "failed_rate_total": round((failed_merchant + failed_bolt_courier) / max(1, total_placed) * 100, 2),
    }


def group_by_quarter(items, period_key="period"):
    groups = defaultdict(list)
    for r in items:
        groups[quarter_key(r[period_key])].append(r)
    return groups


# ======== LOAD ALL DATA ========
print("Loading data files...")
metadata = load_json("data_metadata.json")
top_partners = load_json("data_top_partners.json")
overview_fin_weekly = load_json("data_overview_fin_weekly.json")
overview_fin_monthly = load_json("data_overview_fin_monthly.json")
overview_camp_weekly = load_json("data_overview_camp_weekly.json")
overview_camp_monthly = load_json("data_overview_camp_monthly.json")
failed_monthly = load_json("data_failed_orders_monthly.json")
gmv_monthly = load_json("data_gmv_by_partner_monthly.json")
gmv_weekly = load_json("data_gmv_by_partner_weekly.json")
ops_overview = load_json("data_ops_overview_weekly.json")
ops_partners = load_json("data_ops_partners_weekly.json")
ops_overview_monthly = load_json("data_ops_overview_monthly.json")
ops_partners_monthly = load_json("data_ops_partners_monthly.json")
sku_median_weekly = load_json("data_sku_median_weekly.json")
sku_median_monthly = load_json("data_sku_median_monthly.json")
partner_fin_monthly = load_json("data_partner_fin_monthly.json")
partner_fin_weekly = load_json("data_partner_fin_weekly.json")
partner_camp_monthly = load_json("data_partner_camp_monthly.json")
partner_camp_weekly = load_json("data_partner_camp_weekly.json")
acceptance = load_json("data_acceptance.json")
item_defects_raw = load_json("data_item_defects_weekly.json")
city_breakdown_weekly = load_json("data_city_breakdown_weekly.json")
city_eater_fees_weekly = load_json("data_city_eater_fees_weekly.json")
failed_overview_weekly = load_json("data_failed_orders_weekly.json")
partner_failed_weekly = load_json("data_partner_failed_weekly.json")
partner_failed_monthly = load_json("data_partner_failed_monthly.json")
refund_weekly = load_json("data_refund_weekly.json")
refund_monthly = load_json("data_refund_monthly.json")
refund_partner_weekly = load_json("data_refund_partner_weekly.json")
refund_partner_monthly = load_json("data_refund_partner_monthly.json")
active_stores_data = load_json("data_active_stores.json")
partner_city_weekly = load_json("data_partner_city_weekly.json")

partners_list = metadata.get("partners_list", ALL_TRACKED_PARTNERS)
tenth_partner = metadata.get("tenth_partner")

# Normalize all periods
for lst in [overview_fin_weekly, overview_fin_monthly, overview_camp_weekly, overview_camp_monthly,
            failed_monthly, gmv_monthly, gmv_weekly,
            partner_fin_monthly, partner_fin_weekly, partner_camp_monthly, partner_camp_weekly,
            failed_overview_weekly, partner_failed_weekly, partner_failed_monthly,
            item_defects_raw,
            refund_weekly, refund_monthly, refund_partner_weekly, refund_partner_monthly,
            partner_city_weekly]:
    for r in lst:
        r["period"] = fmt_period(r["period"])

# Merge refund data (from all orders) into financial data (delivered only)
refund_w_by_period = {r["period"]: r for r in refund_weekly}
for r in overview_fin_weekly:
    ref = refund_w_by_period.get(r["period"], {})
    r["supply_refund_gmv_pct"] = ref.get("supply_refund_gmv_pct", 0)
    r["demand_refund_gmv_pct"] = ref.get("demand_refund_gmv_pct", 0)
refund_m_by_period = {r["period"]: r for r in refund_monthly}
for r in overview_fin_monthly:
    ref = refund_m_by_period.get(r["period"], {})
    r["supply_refund_gmv_pct"] = ref.get("supply_refund_gmv_pct", 0)
    r["demand_refund_gmv_pct"] = ref.get("demand_refund_gmv_pct", 0)

refund_pw_by_key = {}
for r in refund_partner_weekly:
    refund_pw_by_key[(r.get("group_name"), r["period"])] = r
refund_pm_by_key = {}
for r in refund_partner_monthly:
    refund_pm_by_key[(r.get("group_name"), r["period"])] = r
for r in partner_fin_weekly:
    ref = refund_pw_by_key.get((r.get("group_name"), r["period"]), {})
    r["supply_refund_gmv_pct"] = ref.get("supply_refund_gmv_pct", 0)
    r["demand_refund_gmv_pct"] = ref.get("demand_refund_gmv_pct", 0)
for r in partner_fin_monthly:
    ref = refund_pm_by_key.get((r.get("group_name"), r["period"]), {})
    r["supply_refund_gmv_pct"] = ref.get("supply_refund_gmv_pct", 0)
    r["demand_refund_gmv_pct"] = ref.get("demand_refund_gmv_pct", 0)

# Sanitize campaign data: clamp negative values to 0 (data quality issues in source)
for lst in [overview_camp_weekly, overview_camp_monthly, partner_camp_monthly, partner_camp_weekly]:
    for r in lst:
        for key in ["campaigns_discount_eur", "bolt_spend_eur", "merchant_spend_eur"]:
            if r.get(key) is not None and r[key] < 0:
                r[key] = 0.0

# ======== BUILD OVERVIEW CP (from ops data) & OPS (from fact_provider_weekly) ========
ops_by_period = {fmt_period(r["period"]): r for r in ops_overview}

overview_cp_weekly = []
for r in ops_overview:
    period = fmt_period(r["period"])
    overview_cp_weekly.append({
        "period": period,
        "cp_margin_pct": r.get("cp_margin_pct"),
        "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
        "demand_incentives_gmv_share": r.get("demand_incentives_gmv_share"),
        "commission_gmv_pct": r.get("commission_gmv_pct"),
        "commission_aov_pct": r.get("commission_aov_pct"),
    })

overview_ops_weekly = []
for r in ops_overview:
    period = fmt_period(r["period"])
    overview_ops_weekly.append({
        "period": period,
        "delivered_orders": r["orders"],
        "total_stores": r.get("total_stores"),
        "stores_with_orders": r.get("stores_with_orders"),
        "acceptance_rate": r["acceptance_rate"],
        "availability_rate": r["availability_rate"],
        "avg_rating": r["avg_rating"],
        "honey_order_rate": r["honey_rate"],
        "bad_order_rate": r["bad_rate"],
        "late_delivery_rate": r["late_delivery_rate"],
        "late_pickup_rate": r["late_pickup_rate"],
        "avg_delivery_minutes": r["avg_delivery_min"],
        "courier_minutes_per_order": r.get("courier_min_per_order"),
        "batching_rate": r.get("batching_rate"),
        "courier_acceptance_rate": r.get("courier_acceptance_rate"),
        "cpo_eur": r.get("cpo_eur"),
        "sku_availability_pct": r.get("sku_availability_pct"),
        "replacement_rate": 0,
        "adjustment_rate": 0,
    })

# Monthly CP/OPS from the dedicated monthly ops query (accumulated from DATA_START = Jan 2026)
overview_cp_monthly_computed = []
for r in sorted(ops_overview_monthly, key=lambda x: x["period"]):
    period = fmt_period(r["period"])
    overview_cp_monthly_computed.append({
        "period": period,
        "cp_margin_pct": r.get("cp_margin_pct"),
        "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
        "demand_incentives_gmv_share": r.get("demand_incentives_gmv_share"),
        "commission_gmv_pct": r.get("commission_gmv_pct"),
        "commission_aov_pct": r.get("commission_aov_pct"),
    })

overview_ops_monthly_computed = []
for r in sorted(ops_overview_monthly, key=lambda x: x["period"]):
    period = fmt_period(r["period"])
    overview_ops_monthly_computed.append({
        "period": period,
        "delivered_orders": r.get("orders"),
        "total_stores": r.get("total_stores"),
        "stores_with_orders": r.get("stores_with_orders"),
        "acceptance_rate": r.get("acceptance_rate"),
        "availability_rate": r.get("availability_rate"),
        "avg_rating": r.get("avg_rating"),
        "honey_order_rate": r.get("honey_rate"),
        "bad_order_rate": r.get("bad_rate"),
        "late_delivery_rate": r.get("late_delivery_rate"),
        "late_pickup_rate": r.get("late_pickup_rate"),
        "avg_delivery_minutes": r.get("avg_delivery_min"),
        "courier_minutes_per_order": r.get("courier_min_per_order"),
        "batching_rate": r.get("batching_rate"),
        "courier_acceptance_rate": r.get("courier_acceptance_rate"),
        "cpo_eur": r.get("cpo_eur"),
        "sku_availability_pct": r.get("sku_availability_pct"),
        "replacement_rate": 0,
        "adjustment_rate": 0,
    })

# ======== QUARTERLY AGGREGATION ========
# Financial
q_fin_groups = defaultdict(list)
for r in overview_fin_monthly:
    q_fin_groups[quarter_key(r["period"])].append(r)
overview_fin_quarterly = []
for period in sorted(q_fin_groups.keys()):
    agg = aggregate_financial(q_fin_groups[period])
    if agg:
        agg["period"] = period
        overview_fin_quarterly.append(agg)

# CP/OPS (quarterly from monthly ops, accumulated from DATA_START)
q_ops_groups = group_by_quarter([{"period": fmt_period(r["period"]), **r} for r in ops_overview_monthly])
overview_cp_quarterly = []
overview_ops_quarterly = []
for period in sorted(q_ops_groups.keys()):
    rows = q_ops_groups[period]
    overview_cp_quarterly.append({
        "period": period,
        "cp_margin_pct": avg_vals(rows, "cp_margin_pct"),
        "cp_l2_margin_pct": avg_vals(rows, "cp_l2_margin_pct"),
        "demand_incentives_gmv_share": avg_vals(rows, "demand_incentives_gmv_share"),
        "commission_gmv_pct": avg_vals(rows, "commission_gmv_pct"),
        "commission_aov_pct": avg_vals(rows, "commission_aov_pct"),
    })
    overview_ops_quarterly.append({
        "period": period,
        "delivered_orders": sum(r["orders"] for r in rows),
        "total_stores": max((r.get("total_stores") or 0) for r in rows),
        "stores_with_orders": max((r.get("stores_with_orders") or 0) for r in rows),
        "acceptance_rate": avg_vals(rows, "acceptance_rate"),
        "availability_rate": avg_vals(rows, "availability_rate"),
        "avg_rating": avg_vals(rows, "avg_rating"),
        "honey_order_rate": avg_vals(rows, "honey_rate"),
        "bad_order_rate": avg_vals(rows, "bad_rate"),
        "late_delivery_rate": avg_vals(rows, "late_delivery_rate"),
        "late_pickup_rate": avg_vals(rows, "late_pickup_rate"),
        "avg_delivery_minutes": avg_vals(rows, "avg_delivery_min"),
        "courier_minutes_per_order": avg_vals(rows, "courier_min_per_order"),
        "batching_rate": avg_vals(rows, "batching_rate"),
        "courier_acceptance_rate": avg_vals(rows, "courier_acceptance_rate"),
        "cpo_eur": avg_vals(rows, "cpo_eur"),
        "sku_availability_pct": avg_vals(rows, "sku_availability_pct"),
        "replacement_rate": 0,
        "adjustment_rate": 0,
    })

# Campaigns quarterly
q_camp_groups = defaultdict(list)
for r in overview_camp_monthly:
    q_camp_groups[quarter_key(r["period"])].append(r)
overview_camp_quarterly = []
for period in sorted(q_camp_groups.keys()):
    agg = aggregate_campaigns(q_camp_groups[period])
    agg["period"] = period
    overview_camp_quarterly.append(agg)

# Failed orders quarterly (overview)
q_fail_groups = defaultdict(list)
for r in failed_monthly:
    q_fail_groups[quarter_key(r["period"])].append(r)
failed_quarterly = []
for period in sorted(q_fail_groups.keys()):
    agg = aggregate_failed(q_fail_groups[period])
    agg["period"] = period
    failed_quarterly.append(agg)

# ======== ITEM DEFECTS ========
print("Processing item defects...")
defects_by_partner = defaultdict(list)
for r in item_defects_raw:
    pname = r.get("group_name") or r.get("partner_name")
    if pname:
        defects_by_partner[pname].append(r)

DEFECT_RAW_FIELDS = ["quantity_defect_rate", "item_replacement_rate", "weighted_defect_rate", "price_defect_rate"]
DEFECT_OUT_FIELDS = ["item_quantity_defect_rate", "item_replacement_rate", "item_weight_defect_rate", "item_price_defect_rate"]
DEFECT_MAP = dict(zip(DEFECT_RAW_FIELDS, DEFECT_OUT_FIELDS))
item_defects = {"weekly": {}, "monthly": {}, "quarterly": {}}
for pname, rows in defects_by_partner.items():
    weekly_d = sorted([
        {"period": r["period"], **{DEFECT_MAP[f]: r.get(f) for f in DEFECT_RAW_FIELDS}}
        for r in rows
    ], key=lambda x: x["period"])
    item_defects["weekly"][pname] = weekly_d

    monthly_groups = defaultdict(list)
    for r in weekly_d:
        monthly_groups[r["period"][:7] + "-01 00:00:00"].append(r)
    item_defects["monthly"][pname] = sorted([
        {"period": p, **{f: avg_vals(g, f) for f in DEFECT_OUT_FIELDS}}
        for p, g in monthly_groups.items()
    ], key=lambda x: x["period"])

    quarterly_groups_d = defaultdict(list)
    for r in weekly_d:
        quarterly_groups_d[quarter_key(r["period"])].append(r)
    item_defects["quarterly"][pname] = sorted([
        {"period": p, **{f: avg_vals(g, f) for f in DEFECT_OUT_FIELDS}}
        for p, g in quarterly_groups_d.items()
    ], key=lambda x: x["period"])

# ======== FAILED ORDERS BY PARTNER ========
pfailed_weekly_by_partner = defaultdict(list)
for r in partner_failed_weekly:
    pfailed_weekly_by_partner[r["group_name"]].append(r)

pfailed_monthly_by_partner = defaultdict(list)
for r in partner_failed_monthly:
    pfailed_monthly_by_partner[r["group_name"]].append(r)

# ======== BUILD PARTNER DATA ========
print("Building partner data...")
ops_by_partner = defaultdict(list)
for r in ops_partners:
    ops_by_partner[r["group_name"]].append(r)

ops_monthly_by_partner = defaultdict(list)
for r in ops_partners_monthly:
    ops_monthly_by_partner[r["group_name"]].append(r)

# Median Available SKU per brand -> sorted (period, value) series. Source snapshots are sparse
# (some brands have only one month of data), so we forward/back-fill at attach time since menu size is stable.
sku_median_w_by_brand = defaultdict(list)
for r in sku_median_weekly:
    v = r.get("median_available_sku")
    if v is not None:
        sku_median_w_by_brand[r.get("group_name")].append((fmt_period(r["period"]), v))
sku_median_m_by_brand = defaultdict(list)
for r in sku_median_monthly:
    v = r.get("median_available_sku")
    if v is not None:
        sku_median_m_by_brand[r.get("group_name")].append((fmt_period(r["period"]), v))
for _s in list(sku_median_w_by_brand.values()) + list(sku_median_m_by_brand.values()):
    _s.sort()


def sku_median_ff(series, period):
    """Latest median at or before `period`; if none exists, the earliest known (back-fill)."""
    if not series:
        return None
    prior = None
    for p, v in series:
        if p <= period:
            prior = v
        else:
            break
    return prior if prior is not None else series[0][1]

pfin_monthly_by_partner = defaultdict(list)
for r in partner_fin_monthly:
    pfin_monthly_by_partner[r["group_name"]].append(r)

pfin_weekly_by_partner = defaultdict(list)
for r in partner_fin_weekly:
    pfin_weekly_by_partner[r["group_name"]].append(r)

pcamp_monthly_by_partner = defaultdict(list)
for r in partner_camp_monthly:
    pcamp_monthly_by_partner[r["group_name"]].append(r)

pcamp_weekly_by_partner = defaultdict(list)
for r in partner_camp_weekly:
    pcamp_weekly_by_partner[r["group_name"]].append(r)

partners_data = {}
for pname in partners_list:
    ops_rows = sorted(ops_by_partner.get(pname, []), key=lambda x: x["period"])
    ops_by_p_period = {fmt_period(r["period"]): r for r in ops_rows}

    # Weekly CP from ops data (cp_margin_pct, cp_l2_margin_pct, commission fields)
    weekly_cp = []
    for r in ops_rows:
        period = fmt_period(r["period"])
        weekly_cp.append({
            "period": period,
            "cp_margin_pct": r.get("cp_margin_pct"),
            "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
            "demand_incentives_gmv_share": r.get("demand_incentives_gmv_share"),
            "commission_gmv_pct": r.get("commission_gmv_pct"),
            "commission_aov_pct": r.get("commission_aov_pct"),
        })

    # Weekly OPS from fact_provider_weekly
    weekly_ops = []
    for r in ops_rows:
        period = fmt_period(r["period"])
        weekly_ops.append({
            "period": period,
            "delivered_orders": r["orders"],
            "total_stores": r.get("total_stores"),
            "stores_with_orders": r.get("stores_with_orders"),
            "acceptance_rate": r["acceptance_rate"],
            "availability_rate": r["availability_rate"],
            "avg_rating": r["avg_rating"],
            "honey_order_rate": r["honey_order_rate"],
            "bad_order_rate": r["bad_order_rate"],
            "late_delivery_rate": r["late_delivery_rate"],
            "late_pickup_rate": r["late_pickup_rate"],
            "avg_delivery_minutes": r["avg_delivery_minutes"],
            "courier_minutes_per_order": r.get("courier_minutes_per_order"),
            "batching_rate": r.get("batching_rate"),
            "courier_acceptance_rate": r.get("courier_acceptance_rate"),
            "cpo_eur": r.get("cpo_eur"),
            "sku_availability_pct": r.get("sku_availability_pct"),
            "replacement_rate": r.get("replacement_rate", 0),
            "adjustment_rate": r.get("adjustment_rate", 0),
        })

    # Monthly CP/OPS from the dedicated monthly partner ops query (from DATA_START = Jan 2026)
    ops_m_rows = sorted(ops_monthly_by_partner.get(pname, []), key=lambda x: x["period"])
    monthly_cp = []
    for r in ops_m_rows:
        monthly_cp.append({
            "period": fmt_period(r["period"]),
            "cp_margin_pct": r.get("cp_margin_pct"),
            "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
            "demand_incentives_gmv_share": r.get("demand_incentives_gmv_share"),
            "commission_gmv_pct": r.get("commission_gmv_pct"),
            "commission_aov_pct": r.get("commission_aov_pct"),
        })

    monthly_ops = []
    for r in ops_m_rows:
        monthly_ops.append({
            "period": fmt_period(r["period"]),
            "delivered_orders": r.get("orders"),
            "total_stores": r.get("total_stores"),
            "stores_with_orders": r.get("stores_with_orders"),
            "acceptance_rate": r.get("acceptance_rate"),
            "availability_rate": r.get("availability_rate"),
            "avg_rating": r.get("avg_rating"),
            "honey_order_rate": r.get("honey_order_rate"),
            "bad_order_rate": r.get("bad_order_rate"),
            "late_delivery_rate": r.get("late_delivery_rate"),
            "late_pickup_rate": r.get("late_pickup_rate"),
            "avg_delivery_minutes": r.get("avg_delivery_minutes"),
            "courier_minutes_per_order": r.get("courier_minutes_per_order"),
            "batching_rate": r.get("batching_rate"),
            "courier_acceptance_rate": r.get("courier_acceptance_rate"),
            "cpo_eur": r.get("cpo_eur"),
            "sku_availability_pct": r.get("sku_availability_pct"),
            "replacement_rate": r.get("replacement_rate", 0),
            "adjustment_rate": r.get("adjustment_rate", 0),
        })

    # Attach Median Available SKU (forward/back-filled from sparse snapshots; menu size is stable)
    _sku_w = sku_median_w_by_brand.get(pname, [])
    _sku_m = sku_median_m_by_brand.get(pname, [])
    for row in weekly_ops:
        row["median_available_sku"] = sku_median_ff(_sku_w, row["period"])
    for row in monthly_ops:
        row["median_available_sku"] = sku_median_ff(_sku_m, row["period"])

    # Weekly/Monthly financial from fact_order_delivery
    p_fin_w = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pfin_weekly_by_partner.get(pname, [])]
    p_fin_m = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pfin_monthly_by_partner.get(pname, [])]

    # Weekly/Monthly campaigns from fact_order_delivery
    p_camp_w = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pcamp_weekly_by_partner.get(pname, [])]
    p_camp_m = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pcamp_monthly_by_partner.get(pname, [])]

    # Failed orders per partner
    p_failed_w = sorted([
        {"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}}
        for r in pfailed_weekly_by_partner.get(pname, [])
    ], key=lambda x: x["period"])
    p_failed_m = sorted([
        {"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}}
        for r in pfailed_monthly_by_partner.get(pname, [])
    ], key=lambda x: x["period"])

    # Quarterly aggregation (CP/OPS from monthly ops, accumulated from DATA_START)
    q_cp_groups_p = group_by_quarter(monthly_cp)
    q_ops_groups_p = group_by_quarter(monthly_ops)
    q_fin_groups_p = group_by_quarter(p_fin_m) if p_fin_m else {}
    q_camp_groups_p = group_by_quarter(p_camp_m) if p_camp_m else {}
    q_failed_groups_p = group_by_quarter(p_failed_m) if p_failed_m else {}

    quarterly_cp = []
    for qp in sorted(q_cp_groups_p.keys()):
        quarterly_cp.append({
            "period": qp,
            "cp_margin_pct": avg_vals(q_cp_groups_p[qp], "cp_margin_pct"),
            "cp_l2_margin_pct": avg_vals(q_cp_groups_p[qp], "cp_l2_margin_pct"),
            "demand_incentives_gmv_share": avg_vals(q_cp_groups_p[qp], "demand_incentives_gmv_share"),
            "commission_gmv_pct": avg_vals(q_cp_groups_p[qp], "commission_gmv_pct"),
            "commission_aov_pct": avg_vals(q_cp_groups_p[qp], "commission_aov_pct"),
        })

    quarterly_ops = []
    for qp in sorted(q_ops_groups_p.keys()):
        g = q_ops_groups_p[qp]
        quarterly_ops.append({
            "period": qp,
            "delivered_orders": sum(r["delivered_orders"] for r in g),
            "total_stores": max((r.get("total_stores") or 0) for r in g),
            "stores_with_orders": max((r.get("stores_with_orders") or 0) for r in g),
            "acceptance_rate": avg_vals(g, "acceptance_rate"),
            "availability_rate": avg_vals(g, "availability_rate"),
            "avg_rating": avg_vals(g, "avg_rating"),
            "honey_order_rate": avg_vals(g, "honey_order_rate"),
            "bad_order_rate": avg_vals(g, "bad_order_rate"),
            "late_delivery_rate": avg_vals(g, "late_delivery_rate"),
            "late_pickup_rate": avg_vals(g, "late_pickup_rate"),
            "avg_delivery_minutes": avg_vals(g, "avg_delivery_minutes"),
            "courier_minutes_per_order": avg_vals(g, "courier_minutes_per_order"),
            "batching_rate": avg_vals(g, "batching_rate"),
            "courier_acceptance_rate": avg_vals(g, "courier_acceptance_rate"),
            "cpo_eur": avg_vals(g, "cpo_eur"),
            "sku_availability_pct": avg_vals(g, "sku_availability_pct"),
            "median_available_sku": median_vals(g, "median_available_sku"),
            "replacement_rate": avg_vals(g, "replacement_rate"),
            "adjustment_rate": avg_vals(g, "adjustment_rate"),
        })

    quarterly_fin = []
    for qp in sorted(q_fin_groups_p.keys()):
        agg = aggregate_financial(q_fin_groups_p[qp])
        if agg:
            agg["period"] = qp
            quarterly_fin.append(agg)

    quarterly_camp = []
    for qp in sorted(q_camp_groups_p.keys()):
        agg = aggregate_campaigns(q_camp_groups_p[qp])
        agg["period"] = qp
        quarterly_camp.append(agg)

    quarterly_failed = []
    for qp in sorted(q_failed_groups_p.keys()):
        agg = aggregate_failed(q_failed_groups_p[qp])
        agg["period"] = qp
        quarterly_failed.append(agg)

    partners_data[pname] = {
        "weekly": {"financial": p_fin_w, "cp_margins": weekly_cp, "operational": weekly_ops, "failed_orders": p_failed_w, "campaigns": p_camp_w},
        "monthly": {"financial": p_fin_m, "cp_margins": monthly_cp, "operational": monthly_ops, "failed_orders": p_failed_m, "campaigns": p_camp_m},
        "quarterly": {"financial": quarterly_fin, "cp_margins": quarterly_cp, "operational": quarterly_ops, "failed_orders": quarterly_failed, "campaigns": quarterly_camp},
    }

# ======== ITEM DISCOUNT PROMO SHARE ========
item_discount_promo = {"weekly": {}, "monthly": {}, "quarterly": {}}
for pname in partners_list:
    rows = ops_by_partner.get(pname, [])
    if not rows:
        continue
    weekly_entries = []
    monthly_groups = defaultdict(list)
    quarterly_groups_promo = defaultdict(list)
    for r in sorted(rows, key=lambda x: x["period"]):
        val = r.get("item_discount_promo_share")
        if val is None:
            val = 0
        period = fmt_period(r["period"])
        weekly_entries.append({"period": period, "value": val})
        monthly_groups[period[:7] + "-01 00:00:00"].append(val)
        quarterly_groups_promo[quarter_key(period)].append(val)

    item_discount_promo["weekly"][pname] = weekly_entries
    item_discount_promo["monthly"][pname] = [{"period": p, "value": round(sum(v) / len(v), 2)} for p, v in sorted(monthly_groups.items())]
    item_discount_promo["quarterly"][pname] = [{"period": p, "value": round(sum(v) / len(v), 2)} for p, v in sorted(quarterly_groups_promo.items())]

# ======== CITY OVERVIEW ========
print("Building city overview...")

def _load_city(name):
    lst = load_json(name)
    for r in lst:
        r["period"] = fmt_period(r["period"])
    return lst

_city_fin = {"weekly": _load_city("data_city_fin_weekly.json"), "monthly": _load_city("data_city_fin_monthly.json")}
_city_finp = {"weekly": _load_city("data_city_fin_partner_weekly.json"), "monthly": _load_city("data_city_fin_partner_monthly.json")}
_city_ref = {"weekly": _load_city("data_city_refund_weekly.json"), "monthly": _load_city("data_city_refund_monthly.json")}
_city_fail = {"weekly": _load_city("data_city_failed_weekly.json"), "monthly": _load_city("data_city_failed_monthly.json")}
_city_failp = {"weekly": _load_city("data_city_failed_partner_weekly.json"), "monthly": _load_city("data_city_failed_partner_monthly.json")}
_city_ops = {"weekly": _load_city("data_city_ops_weekly.json"), "monthly": _load_city("data_city_ops_monthly.json")}
_city_opsp = {"weekly": _load_city("data_city_ops_partner_weekly.json"), "monthly": _load_city("data_city_ops_partner_monthly.json")}
_city_camp = {"weekly": _load_city("data_city_camp_weekly.json"), "monthly": _load_city("data_city_camp_monthly.json")}
_city_campp = {"weekly": _load_city("data_city_camp_partner_weekly.json"), "monthly": _load_city("data_city_camp_partner_monthly.json")}

# Sanitize campaign negatives (data quality) + override financial refunds with all-orders values
for g in ("weekly", "monthly"):
    for lst in (_city_camp[g], _city_campp[g]):
        for r in lst:
            for k in ("campaigns_discount_eur", "bolt_spend_eur", "merchant_spend_eur"):
                if r.get(k) is not None and r[k] < 0:
                    r[k] = 0.0
    refidx = {(r.get("city_name"), r["period"]): r for r in _city_ref[g]}
    for r in _city_fin[g]:
        ref = refidx.get((r.get("city_name"), r["period"]))
        if ref:
            r["supply_refund_gmv_pct"] = ref.get("supply_refund_gmv_pct", 0)
            r["demand_refund_gmv_pct"] = ref.get("demand_refund_gmv_pct", 0)

def _grp_city(rows):
    d = defaultdict(list)
    for r in rows:
        d[r.get("city_name")].append(r)
    return d

def _grp_city_partner(rows):
    d = defaultdict(lambda: defaultdict(list))
    for r in rows:
        d[r.get("city_name")][r.get("group_name")].append(r)
    return d

OPS_RATE_FIELDS = ["commission_gmv_pct", "commission_aov_pct", "cp_margin_pct", "cp_l2_margin_pct",
                   "acceptance_rate", "availability_rate", "avg_rating", "honey_rate", "bad_rate",
                   "late_delivery_rate", "late_pickup_rate", "avg_delivery_min", "courier_min_per_order",
                   "demand_incentives_gmv_share", "batching_rate", "courier_acceptance_rate", "cpo_eur",
                   "sku_availability_pct"]

def _ops_cp(r):
    return {"period": r["period"], "cp_margin_pct": r.get("cp_margin_pct"), "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
            "demand_incentives_gmv_share": r.get("demand_incentives_gmv_share"),
            "commission_gmv_pct": r.get("commission_gmv_pct"), "commission_aov_pct": r.get("commission_aov_pct")}

def _ops_op(r):
    return {"period": r["period"], "delivered_orders": r.get("orders"), "total_stores": r.get("total_stores"),
            "stores_with_orders": r.get("stores_with_orders"), "acceptance_rate": r.get("acceptance_rate"),
            "availability_rate": r.get("availability_rate"), "avg_rating": r.get("avg_rating"),
            "honey_order_rate": r.get("honey_rate"), "bad_order_rate": r.get("bad_rate"),
            "late_delivery_rate": r.get("late_delivery_rate"), "late_pickup_rate": r.get("late_pickup_rate"),
            "avg_delivery_minutes": r.get("avg_delivery_min"), "courier_minutes_per_order": r.get("courier_min_per_order"),
            "batching_rate": r.get("batching_rate"), "courier_acceptance_rate": r.get("courier_acceptance_rate"),
            "cpo_eur": r.get("cpo_eur"), "sku_availability_pct": r.get("sku_availability_pct"),
            "replacement_rate": 0, "adjustment_rate": 0}

def _agg_ops_raw(rows, period):
    out = {"period": period, "orders": sum(r.get("orders", 0) or 0 for r in rows),
           "total_stores": max((r.get("total_stores") or 0) for r in rows),
           "stores_with_orders": max((r.get("stores_with_orders") or 0) for r in rows)}
    for f in OPS_RATE_FIELDS:
        out[f] = avg_vals(rows, f)
    return out

def _failed_pcts(r):
    tp = r.get("total_placed") or 0
    return {"failed_rate_total": r.get("failed_rate_total"),
            "failed_merchant_pct": round((r.get("failed_merchant", 0) or 0) / tp * 100, 2) if tp else None,
            "failed_bolt_courier_pct": round((r.get("failed_bolt_courier", 0) or 0) / tp * 100, 2) if tp else None}

def _sorted_periods(rows):
    return sorted({r["period"] for r in rows})

# Rank cities by total GMV (monthly)
_city_gmv = defaultdict(float)
for r in _city_fin["monthly"]:
    _city_gmv[r.get("city_name")] += (r.get("gmv_eur", 0) or 0)
city_list = [c for c, _ in sorted(_city_gmv.items(), key=lambda kv: -kv[1]) if c]

# Pre-group everything by city (+partner)
_fin_by = {g: _grp_city(_city_fin[g]) for g in ("weekly", "monthly")}
_finp_by = {g: _grp_city_partner(_city_finp[g]) for g in ("weekly", "monthly")}
_fail_by = {g: _grp_city(_city_fail[g]) for g in ("weekly", "monthly")}
_failp_by = {g: _grp_city_partner(_city_failp[g]) for g in ("weekly", "monthly")}
_ops_by = {g: _grp_city(_city_ops[g]) for g in ("weekly", "monthly")}
_opsp_by = {g: _grp_city_partner(_city_opsp[g]) for g in ("weekly", "monthly")}
_camp_by = {g: _grp_city(_city_camp[g]) for g in ("weekly", "monthly")}
_campp_by = {g: _grp_city_partner(_city_campp[g]) for g in ("weekly", "monthly")}

cities_data = {}
for city in city_list:
    fin_w = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _fin_by["weekly"].get(city, [])], key=lambda x: x["period"])
    fin_m = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _fin_by["monthly"].get(city, [])], key=lambda x: x["period"])
    fail_w = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _fail_by["weekly"].get(city, [])], key=lambda x: x["period"])
    fail_m = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _fail_by["monthly"].get(city, [])], key=lambda x: x["period"])
    camp_w = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _camp_by["weekly"].get(city, [])], key=lambda x: x["period"])
    camp_m = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in _camp_by["monthly"].get(city, [])], key=lambda x: x["period"])
    ops_w_raw = sorted(_ops_by["weekly"].get(city, []), key=lambda x: x["period"])
    ops_m_raw = sorted(_ops_by["monthly"].get(city, []), key=lambda x: x["period"])
    gmvp_w = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in sum(_finp_by["weekly"].get(city, {}).values(), [])], key=lambda x: x["period"])
    gmvp_m = sorted([{k: v for k, v in r.items() if k != "city_name"} for r in sum(_finp_by["monthly"].get(city, {}).values(), [])], key=lambda x: x["period"])

    # CP / operational (weekly, monthly from raw ops; quarterly by aggregating monthly raw)
    cp_w = [_ops_cp(r) for r in ops_w_raw]
    op_w = [_ops_op(r) for r in ops_w_raw]
    cp_m = [_ops_cp(r) for r in ops_m_raw]
    op_m = [_ops_op(r) for r in ops_m_raw]
    q_ops_groups = defaultdict(list)
    for r in ops_m_raw:
        q_ops_groups[quarter_key(r["period"])].append(r)
    ops_q_raw = [_agg_ops_raw(q_ops_groups[q], q) for q in sorted(q_ops_groups)]
    cp_q = [_ops_cp(r) for r in ops_q_raw]
    op_q = [_ops_op(r) for r in ops_q_raw]

    # Financial quarterly (aggregate monthly), failed quarterly, campaigns quarterly
    def _q_agg(rows, aggfn):
        groups = defaultdict(list)
        for r in rows:
            groups[quarter_key(r["period"])].append(r)
        out = []
        for q in sorted(groups):
            a = aggfn(groups[q])
            if a is not None:
                a["period"] = q
                out.append(a)
        return out
    fin_q = _q_agg(fin_m, aggregate_financial)
    fail_q = _q_agg(fail_m, aggregate_failed)
    camp_q = _q_agg(camp_m, aggregate_campaigns)

    # Quarterly GMV-by-partner (aggregate monthly per partner) for doughnuts + Financial-by-partner table
    _gmvp_q_groups = defaultdict(list)
    for r in gmvp_m:
        _gmvp_q_groups[(r.get("group_name"), quarter_key(r["period"]))].append(r)
    gmvp_q = []
    for (gn, q), rows in _gmvp_q_groups.items():
        a = aggregate_financial(rows)
        if a:
            a["group_name"] = gn
            a["period"] = q
            gmvp_q.append(a)

    # Partner ops table (merge failed pcts by group_name+period)
    def _partner_ops(gran):
        opsp = _opsp_by[gran].get(city, {})
        failp = _failp_by[gran].get(city, {})
        fidx = {}
        for gn, rows in failp.items():
            for r in rows:
                fidx[(gn, r["period"])] = r
        out = []
        for gn, rows in opsp.items():
            for r in rows:
                row = {"group_name": gn, "period": r["period"], "acceptance_rate": r.get("acceptance_rate"),
                       "availability_rate": r.get("availability_rate"), "avg_rating": r.get("avg_rating"),
                       "honey_order_rate": r.get("honey_rate"), "bad_order_rate": r.get("bad_rate"),
                       "avg_delivery_minutes": r.get("avg_delivery_min"), "cpo_eur": r.get("cpo_eur"),
                       "late_delivery_rate": r.get("late_delivery_rate"), "late_pickup_rate": r.get("late_pickup_rate"),
                       "cp_margin_pct": r.get("cp_margin_pct"), "cp_l2_margin_pct": r.get("cp_l2_margin_pct"),
                       "orders": r.get("orders")}
                fr = fidx.get((gn, r["period"]))
                row.update(_failed_pcts(fr) if fr else {"failed_rate_total": None, "failed_merchant_pct": None, "failed_bolt_courier_pct": None})
                out.append(row)
        return out

    def _partner_ops_q():
        # aggregate monthly partner ops to quarter
        opsp = _opsp_by["monthly"].get(city, {})
        failp = _failp_by["monthly"].get(city, {})
        out = []
        for gn, rows in opsp.items():
            qg = defaultdict(list)
            for r in rows:
                qg[quarter_key(r["period"])].append(r)
            fq = defaultdict(list)
            for r in failp.get(gn, []):
                fq[quarter_key(r["period"])].append(r)
            for q in sorted(qg):
                agg = _agg_ops_raw(qg[q], q)
                row = {"group_name": gn, "period": q, "acceptance_rate": agg.get("acceptance_rate"),
                       "availability_rate": agg.get("availability_rate"), "avg_rating": agg.get("avg_rating"),
                       "honey_order_rate": agg.get("honey_rate"), "bad_order_rate": agg.get("bad_rate"),
                       "avg_delivery_minutes": agg.get("avg_delivery_min"), "cpo_eur": agg.get("cpo_eur"),
                       "late_delivery_rate": agg.get("late_delivery_rate"), "late_pickup_rate": agg.get("late_pickup_rate"),
                       "cp_margin_pct": agg.get("cp_margin_pct"), "cp_l2_margin_pct": agg.get("cp_l2_margin_pct"),
                       "orders": agg.get("orders")}
                fa = aggregate_failed(fq[q]) if fq.get(q) else None
                row.update(_failed_pcts(fa) if fa else {"failed_rate_total": None, "failed_merchant_pct": None, "failed_bolt_courier_pct": None})
                out.append(row)
        return out

    def _partner_camp(gran):
        campp = _campp_by[gran].get(city, {})
        out = []
        for gn, rows in campp.items():
            for r in rows:
                out.append({"group_name": gn, "period": r["period"], "gmv_eur": r.get("gmv_eur"),
                            "orders": r.get("orders"), "campaign_orders": r.get("campaign_orders"),
                            "bolt_campaign_orders": r.get("bolt_campaign_orders"),
                            "campaigns_discount_eur": r.get("campaigns_discount_eur"), "bolt_spend_eur": r.get("bolt_spend_eur"),
                            "merchant_spend_eur": r.get("merchant_spend_eur")})
        return out

    def _partner_camp_q():
        campp = _campp_by["monthly"].get(city, {})
        out = []
        for gn, rows in campp.items():
            qg = defaultdict(list)
            for r in rows:
                qg[quarter_key(r["period"])].append(r)
            for q in sorted(qg):
                a = aggregate_campaigns(qg[q]); a["period"] = q; a["group_name"] = gn
                out.append(a)
        return out

    cities_data[city] = {
        "weekly": {"financial": fin_w, "cp_margins": cp_w, "operational": op_w, "failed_orders": fail_w, "campaigns": camp_w, "gmv_by_partner": gmvp_w},
        "monthly": {"financial": fin_m, "cp_margins": cp_m, "operational": op_m, "failed_orders": fail_m, "campaigns": camp_m, "gmv_by_partner": gmvp_m},
        "quarterly": {"financial": fin_q, "cp_margins": cp_q, "operational": op_q, "failed_orders": fail_q, "campaigns": camp_q, "gmv_by_partner": gmvp_q},
        "partner_ops": {"weekly": _partner_ops("weekly"), "monthly": _partner_ops("monthly"), "quarterly": _partner_ops_q()},
        "partner_campaigns": {"weekly": _partner_camp("weekly"), "monthly": _partner_camp("monthly"), "quarterly": _partner_camp_q()},
    }

# ======== EMPLOYEE GROUPS ========
EMPLOYEE_GROUPS = {
    "Mykhailo": ["LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK", "TAISTRA", "BEERLAND K", "WINETIME", "BRSM", "SPAR", "AUCHAN", "ATB", "FLOWERS UA", "OKKO MARKET"],
    "Viktor": ["VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "PYVNA BORODA", "ANRI-PHARM", "THRASH", "E-ZOO", "MASTER ZOO", "РОСТ", "BYLE TA SYKHE", "FORA", "ANC", "BLYZENKO", "LIKI 24"],
    "Khrystyna": ["TOCHKA", "LEPRUKON", "MAXBEER", "SPRAGA", "DIMPYVA", "ALTBIER", "FLOWER SHOP", "NO TABOO", "RODYNNA KOVBASKA", "VAPERY | VAPE SHOP", "VAPORS", "PIVASOV"],
}

OWNER_BY_PARTNER = {p: emp for emp, brands in EMPLOYEE_GROUPS.items() for p in brands}
SUBBRAND_KEYS = {"Kopiyka", "Kopiyka Mini", "Santim"}


def _pct(cur, prev):
    if cur is None or prev is None:
        return None
    try:
        prev = float(prev)
        cur = float(cur)
    except (TypeError, ValueError):
        return None
    if prev == 0:
        return None
    return (cur - prev) / abs(prev) * 100.0


def _pp(cur, prev):
    if cur is None or prev is None:
        return None
    try:
        return float(cur) - float(prev)
    except (TypeError, ValueError):
        return None


def _fmt_pct(v, digits=1):
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{digits}f}%"


def _fmt_pp(v, digits=1):
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{digits}f}pp"


def _fmt_eur(v, digits=0):
    if v is None:
        return "—"
    if digits == 0:
        return f"€{v:,.0f}"
    return f"€{v:,.{digits}f}"


def _fmt_num(v, digits=0):
    if v is None:
        return "—"
    if digits == 0:
        return f"{v:,.0f}"
    return f"{v:,.{digits}f}"


def _week_range_label(period):
    """Monday period → 'Aug 10 – Aug 16'."""
    from datetime import timedelta
    d = datetime.strptime(period[:10], "%Y-%m-%d")
    end = d + timedelta(days=6)
    return f"{d.strftime('%b %-d')} – {end.strftime('%b %-d')}"


def _month_label(period):
    d = datetime.strptime(period[:10], "%Y-%m-%d")
    return d.strftime("%B %Y")


def _by_period(rows):
    return {fmt_period(r["period"]): r for r in rows}


def _month_metric(label, current, previous, *, mode="pct", inverted=False, value_fmt="number",
                  threshold=3.0, basis="MTD rate vs prior full month"):
    delta = _pp(current, previous) if mode == "pp" else _pct(current, previous)
    notable = delta is not None and abs(delta) >= threshold
    good = None if delta is None else ((delta < 0) if inverted else (delta > 0))
    if delta is not None and abs(delta) < threshold * 0.2:
        good = None
    if value_fmt == "eur":
        value = _fmt_eur(current)
    elif value_fmt == "pct":
        value = f"{current:.1f}%" if current is not None else "—"
    elif value_fmt == "decimal":
        value = f"{current:.2f}" if current is not None else "—"
    else:
        value = _fmt_num(current)
    return {
        "label": label,
        "value": value,
        "change": _fmt_pp(delta) if mode == "pp" else _fmt_pct(delta),
        "delta": round(delta, 2) if delta is not None else None,
        "good": good,
        "notable": notable,
        "basis": basis,
    }


def _gmv_share(spend, gmv):
    if spend is None or not gmv:
        return None
    try:
        return float(spend) / float(gmv) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _month_spend_rr(label, spend_rr, prev_spend, gmv_rr, prev_gmv, *, month_name, prior_name):
    """Euro run-rate plus % of GMV (same ratio as MTD spend / MTD GMV)."""
    card = _month_metric(
        label, spend_rr, prev_spend,
        value_fmt="eur", inverted=True, threshold=5,
        basis=f"Projected {month_name} vs {prior_name}",
    )
    share = _gmv_share(spend_rr, gmv_rr)
    prev_share = _gmv_share(prev_spend, prev_gmv)
    share_pp = _pp(share, prev_share)
    if share is not None:
        card["value"] = f"{card['value']} ({share:.1f}%)"
        card["share_pct"] = round(share, 1)
    if share_pp is not None:
        card["share_change"] = _fmt_pp(share_pp)
    return card


def build_month_insights(current_week_period):
    """Current-month MTD/RR vs the previous full month, overall and by partner."""
    monthly_fin = sorted(overview_fin_monthly, key=lambda r: r["period"])
    if len(monthly_fin) < 2:
        return None

    cur_fin, prev_fin = monthly_fin[-1], monthly_fin[-2]
    current_month = cur_fin["period"][:7]
    if current_month != current_week_period[:7]:
        return None

    generated_raw = metadata.get("generated_at")
    try:
        generated_date = datetime.fromisoformat(generated_raw.replace("Z", "+00:00")).date()
    except (AttributeError, TypeError, ValueError):
        generated_date = datetime.now(timezone.utc).date()
    year, month = map(int, current_month.split("-"))
    days_in_month = calendar.monthrange(year, month)[1]
    # Monthly queries may contain a partial generation day; use completed days for a conservative RR.
    elapsed_days = max(1, min(generated_date.day - 1, days_in_month))
    multiplier = days_in_month / elapsed_days
    month_name = datetime(year, month, 1).strftime("%B %Y")
    prior_name = _month_label(prev_fin["period"])

    cur_cp = _by_period(overview_cp_monthly_computed).get(cur_fin["period"], {})
    prev_cp = _by_period(overview_cp_monthly_computed).get(prev_fin["period"], {})
    cur_ops = _by_period(overview_ops_monthly_computed).get(cur_fin["period"], {})
    prev_ops = _by_period(overview_ops_monthly_computed).get(prev_fin["period"], {})
    cur_fail = _by_period(failed_monthly).get(cur_fin["period"], {})
    prev_fail = _by_period(failed_monthly).get(prev_fin["period"], {})
    cur_camp = _by_period(overview_camp_monthly).get(cur_fin["period"], {})
    prev_camp = _by_period(overview_camp_monthly).get(prev_fin["period"], {})

    def rr(field, row=cur_fin):
        value = row.get(field)
        return value * multiplier if value is not None else None

    rr_values = {
        "gmv_eur": rr("gmv_eur"),
        "orders": rr("orders"),
        "users_activated": rr("users_activated"),
        # Directional only: monthly active users are distinct, so linear projection is explicitly labelled.
        "active_users": rr("active_users"),
        "campaigns_discount_eur": rr("campaigns_discount_eur", cur_camp),
        "bolt_spend_eur": rr("bolt_spend_eur", cur_camp),
        "merchant_spend_eur": rr("merchant_spend_eur", cur_camp),
    }
    spend_rr_kw = {"month_name": month_name, "prior_name": prior_name}
    rr_cards = [
        _month_metric("GMV RR", rr_values["gmv_eur"], prev_fin.get("gmv_eur"),
                      value_fmt="eur", threshold=3, basis=f"Projected {month_name} vs {prior_name}"),
        _month_metric("Orders RR", rr_values["orders"], prev_fin.get("orders"),
                      threshold=3, basis=f"Projected {month_name} vs {prior_name}"),
        _month_metric("Users activated RR", rr_values["users_activated"], prev_fin.get("users_activated"),
                      threshold=5, basis=f"Projected {month_name} vs {prior_name}"),
        _month_metric("Active users RR (directional)", rr_values["active_users"], prev_fin.get("active_users"),
                      threshold=5, basis=f"Linear projection; distinct-user RR vs {prior_name}"),
        _month_spend_rr("Campaign discount RR", rr_values["campaigns_discount_eur"],
                        prev_camp.get("campaigns_discount_eur"), rr_values["gmv_eur"], prev_fin.get("gmv_eur"),
                        **spend_rr_kw),
        _month_spend_rr("Bolt campaign spend RR", rr_values["bolt_spend_eur"],
                        prev_camp.get("bolt_spend_eur"), rr_values["gmv_eur"], prev_fin.get("gmv_eur"),
                        **spend_rr_kw),
        _month_spend_rr("Merchant spend RR", rr_values["merchant_spend_eur"],
                        prev_camp.get("merchant_spend_eur"), rr_values["gmv_eur"], prev_fin.get("gmv_eur"),
                        **spend_rr_kw),
    ]

    rate_cards = [
        _month_metric("AOV", cur_fin.get("aov_with_delivery"), prev_fin.get("aov_with_delivery"),
                      value_fmt="eur", threshold=2),
        _month_metric("Bolt+ GMV share", cur_fin.get("bolt_plus_gmv_share"), prev_fin.get("bolt_plus_gmv_share"),
                      mode="pp", value_fmt="pct", threshold=0.5),
        _month_metric("CP margin", cur_cp.get("cp_margin_pct"), prev_cp.get("cp_margin_pct"),
                      mode="pp", value_fmt="pct", threshold=0.3),
        _month_metric("CP L2 margin", cur_cp.get("cp_l2_margin_pct"), prev_cp.get("cp_l2_margin_pct"),
                      mode="pp", value_fmt="pct", threshold=0.5),
        _month_metric("Demand incentives % GMV", cur_cp.get("demand_incentives_gmv_share"),
                      prev_cp.get("demand_incentives_gmv_share"), mode="pp", value_fmt="pct",
                      inverted=True, threshold=0.5),
        _month_metric("Acceptance", cur_ops.get("acceptance_rate"), prev_ops.get("acceptance_rate"),
                      mode="pp", value_fmt="pct", threshold=0.3),
        _month_metric("Availability", cur_ops.get("availability_rate"), prev_ops.get("availability_rate"),
                      mode="pp", value_fmt="pct", threshold=0.5),
        _month_metric("Bad order rate", cur_ops.get("bad_order_rate"), prev_ops.get("bad_order_rate"),
                      mode="pp", value_fmt="pct", inverted=True, threshold=0.5),
        _month_metric("Failed rate", cur_fail.get("failed_rate_total"), prev_fail.get("failed_rate_total"),
                      mode="pp", value_fmt="pct", inverted=True, threshold=0.3),
        _month_metric("Average delivery", cur_ops.get("avg_delivery_minutes"), prev_ops.get("avg_delivery_minutes"),
                      value_fmt="decimal", inverted=True, threshold=2),
        _month_metric("CPO", cur_ops.get("cpo_eur"), prev_ops.get("cpo_eur"),
                      value_fmt="eur", inverted=True, threshold=2),
        _month_metric("Stores with orders", cur_ops.get("stores_with_orders"), prev_ops.get("stores_with_orders"),
                      threshold=2),
    ]

    improved = [m for m in rr_cards + rate_cards if m["notable"] and m["good"] is True]
    worsened = [m for m in rr_cards + rate_cards if m["notable"] and m["good"] is False]

    partner_month = []
    for name in partners_list:
        if name in SUBBRAND_KEYS:
            continue
        pdata = partners_data.get(name, {}).get("monthly", {})
        fin_rows = sorted(pdata.get("financial", []), key=lambda r: r["period"])
        if len(fin_rows) < 2:
            continue
        cfin = next((r for r in fin_rows if r["period"] == cur_fin["period"]), None)
        pfin = next((r for r in fin_rows if r["period"] == prev_fin["period"]), None)
        if not cfin or not pfin or max(cfin.get("gmv_eur") or 0, pfin.get("gmv_eur") or 0) < 500:
            continue
        cp_rows = _by_period(pdata.get("cp_margins", []))
        ops_rows = _by_period(pdata.get("operational", []))
        fail_rows = _by_period(pdata.get("failed_orders", []))
        ccp, pcp = cp_rows.get(cur_fin["period"], {}), cp_rows.get(prev_fin["period"], {})
        cops, pops = ops_rows.get(cur_fin["period"], {}), ops_rows.get(prev_fin["period"], {})
        cfail, pfail = fail_rows.get(cur_fin["period"], {}), fail_rows.get(prev_fin["period"], {})
        gmv_rr = (cfin.get("gmv_eur") or 0) * multiplier
        orders_rr = (cfin.get("orders") or 0) * multiplier
        activated_rr = (cfin.get("users_activated") or 0) * multiplier
        active_rr = (cfin.get("active_users") or 0) * multiplier
        partner_month.append({
            "name": name,
            "owner": OWNER_BY_PARTNER.get(name),
            "gmv_rr": gmv_rr,
            "gmv_change_pct": _pct(gmv_rr, pfin.get("gmv_eur")),
            "orders_change_pct": _pct(orders_rr, pfin.get("orders")),
            "users_activated_change_pct": _pct(activated_rr, pfin.get("users_activated")),
            "active_users_change_pct": _pct(active_rr, pfin.get("active_users")),
            "aov_change_pct": _pct(cfin.get("aov_with_delivery"), pfin.get("aov_with_delivery")),
            "availability_change_pp": _pp(cops.get("availability_rate"), pops.get("availability_rate")),
            "acceptance_change_pp": _pp(cops.get("acceptance_rate"), pops.get("acceptance_rate")),
            "bad_rate_change_pp": _pp(cops.get("bad_order_rate"), pops.get("bad_order_rate")),
            "failed_rate_change_pp": _pp(cfail.get("failed_rate_total"), pfail.get("failed_rate_total")),
            "cp_l2_change_pp": _pp(ccp.get("cp_l2_margin_pct"), pcp.get("cp_l2_margin_pct")),
            "demand_incentives_change_pp": _pp(ccp.get("demand_incentives_gmv_share"),
                                               pcp.get("demand_incentives_gmv_share")),
        })

    def partner_month_note(row):
        details = [
            f"GMV RR {_fmt_eur(row['gmv_rr'])} ({_fmt_pct(row['gmv_change_pct'])} vs {prior_name})",
            f"orders {_fmt_pct(row['orders_change_pct'])}",
            f"activated users {_fmt_pct(row['users_activated_change_pct'])}",
            f"active users RR {_fmt_pct(row['active_users_change_pct'])}",
        ]
        signals = []
        for label, key, inverted in (
            ("availability", "availability_change_pp", False),
            ("acceptance", "acceptance_change_pp", False),
            ("bad rate", "bad_rate_change_pp", True),
            ("failed rate", "failed_rate_change_pp", True),
            ("CP L2", "cp_l2_change_pp", False),
            ("demand incentives", "demand_incentives_change_pp", True),
        ):
            value = row.get(key)
            if value is not None and abs(value) >= 0.7:
                status = "better" if ((value < 0) if inverted else (value > 0)) else "worse"
                signals.append(f"{label} {_fmt_pp(value)} ({status})")
        if signals:
            details.append("; ".join(signals[:4]))
        return {
            "name": row["name"],
            "owner": row.get("owner"),
            "detail": " · ".join(details),
            "gmv_change_pct": round(row["gmv_change_pct"], 1) if row.get("gmv_change_pct") is not None else None,
        }

    def has_positive_signal(row):
        return (
            (row.get("gmv_change_pct") or 0) > 3
            or (row.get("users_activated_change_pct") or 0) > 10
            or (row.get("active_users_change_pct") or 0) > 10
            or (row.get("availability_change_pp") or 0) > 1
            or (row.get("acceptance_change_pp") or 0) > 1
            or (row.get("bad_rate_change_pp") or 0) < -1
            or (row.get("failed_rate_change_pp") or 0) < -1
            or (row.get("cp_l2_change_pp") or 0) > 2
        )

    def risk_score(row):
        score = max(0, -(row.get("gmv_change_pct") or 0) / 5)
        score += max(0, -(row.get("availability_change_pp") or 0))
        score += max(0, -(row.get("acceptance_change_pp") or 0))
        score += max(0, row.get("bad_rate_change_pp") or 0)
        score += max(0, row.get("failed_rate_change_pp") or 0)
        score += max(0, -(row.get("cp_l2_change_pp") or 0) / 2)
        score += max(0, (row.get("demand_incentives_change_pp") or 0) / 2)
        return score

    partner_up = sorted(
        [r for r in partner_month if has_positive_signal(r)],
        key=lambda r: -max(r.get("gmv_change_pct") or 0, r.get("users_activated_change_pct") or 0),
    )[:7]
    partner_down = sorted(
        [r for r in partner_month if risk_score(r) >= 1],
        key=risk_score,
        reverse=True,
    )[:7]

    return {
        "label": month_name,
        "prior_label": prior_name,
        "as_of_label": f"{month_name} MTD through day {elapsed_days}",
        "elapsed_days": elapsed_days,
        "days_in_month": days_in_month,
        "rr_multiplier": round(multiplier, 3),
        "note": (
            f"{elapsed_days} completed days · ×{multiplier:.2f} run-rate projection to day {days_in_month}. "
            f"Volume and user totals use RR vs {prior_name}; rates and ops compare MTD with {prior_name}."
        ),
        "rr_cards": rr_cards,
        "rate_cards": rate_cards,
        "improved": improved,
        "worsened": worsened,
        "partners_up": [partner_month_note(r) for r in partner_up],
        "partners_down": [partner_month_note(r) for r in partner_down],
    }


def build_weekly_insights():
    """Auto-generate WoW + month notes from the same data that powers the report."""
    fin_w = sorted(overview_fin_weekly, key=lambda r: r["period"])
    if len(fin_w) < 2:
        return None

    cur_fin, prev_fin = fin_w[-1], fin_w[-2]
    cur_p, prev_p = cur_fin["period"], prev_fin["period"]
    cp_map = _by_period(overview_cp_weekly)
    ops_map = _by_period(overview_ops_weekly)
    camp_map = _by_period(overview_camp_weekly)
    fail_map = _by_period(failed_overview_weekly)
    cur_cp, prev_cp = cp_map.get(cur_p, {}), cp_map.get(prev_p, {})
    cur_ops, prev_ops = ops_map.get(cur_p, {}), ops_map.get(prev_p, {})
    cur_camp, prev_camp = camp_map.get(cur_p, {}), camp_map.get(prev_p, {})
    cur_fail, prev_fail = fail_map.get(cur_p, {}), fail_map.get(prev_p, {})

    def metric_row(label, cur, prev, *, unit="number", inverted=False, threshold_pct=5.0, threshold_pp=0.5):
        if unit == "pp":
            delta = _pp(cur, prev)
            notable = delta is not None and abs(delta) >= threshold_pp
            wow = _fmt_pp(delta)
        else:
            delta = _pct(cur, prev)
            notable = delta is not None and abs(delta) >= threshold_pct
            wow = _fmt_pct(delta)
        if unit == "eur":
            value = _fmt_eur(cur)
        elif unit == "pct":
            value = f"{cur:.1f}%" if cur is not None else "—"
        elif unit == "pp":
            value = f"{cur:.1f}%" if cur is not None else "—"
        else:
            value = _fmt_num(cur)
        direction = "flat"
        if delta is not None:
            if delta > 0.05:
                direction = "up"
            elif delta < -0.05:
                direction = "down"
        good = None
        if delta is not None:
            good = (delta < 0) if inverted else (delta > 0)
            if abs(delta) < (threshold_pp if unit == "pp" else threshold_pct) * 0.2:
                good = None
        return {
            "label": label,
            "value": value,
            "wow": wow,
            "delta": round(delta, 2) if delta is not None else None,
            "direction": direction,
            "good": good,
            "notable": bool(notable),
            "inverted": inverted,
        }

    kpis = [
        metric_row("GMV", cur_fin.get("gmv_eur"), prev_fin.get("gmv_eur"), unit="eur"),
        metric_row("Orders", cur_fin.get("orders"), prev_fin.get("orders")),
        metric_row("AOV", cur_fin.get("aov_with_delivery"), prev_fin.get("aov_with_delivery"), unit="eur", threshold_pct=2.0),
        metric_row("Active users", cur_fin.get("active_users"), prev_fin.get("active_users")),
        metric_row("CP margin", cur_cp.get("cp_margin_pct"), prev_cp.get("cp_margin_pct"), unit="pp", threshold_pp=0.3),
        metric_row("CP L2 margin", cur_cp.get("cp_l2_margin_pct"), prev_cp.get("cp_l2_margin_pct"), unit="pp", threshold_pp=0.5),
        metric_row("Demand incentives % GMV", cur_cp.get("demand_incentives_gmv_share"), prev_cp.get("demand_incentives_gmv_share"), unit="pp", inverted=True, threshold_pp=0.5),
        metric_row("Availability", cur_ops.get("availability_rate"), prev_ops.get("availability_rate"), unit="pp", threshold_pp=0.5),
        metric_row("Acceptance", cur_ops.get("acceptance_rate"), prev_ops.get("acceptance_rate"), unit="pp", threshold_pp=0.3),
        metric_row("Bad order rate", cur_ops.get("bad_order_rate"), prev_ops.get("bad_order_rate"), unit="pp", inverted=True, threshold_pp=0.5),
        metric_row("Failed rate", cur_fail.get("failed_rate_total"), prev_fail.get("failed_rate_total"), unit="pp", inverted=True, threshold_pp=0.3),
        metric_row("Stores with orders", cur_ops.get("stores_with_orders"), prev_ops.get("stores_with_orders"), threshold_pct=2.0),
    ]

    improved = [k for k in kpis if k["notable"] and k["good"] is True]
    worsened = [k for k in kpis if k["notable"] and k["good"] is False]

    # Partner movers (exclude KOPIYKA sub-brands to avoid double-counting the group)
    pfin_by = defaultdict(dict)
    for r in partner_fin_weekly:
        name = r.get("group_name")
        if not name or name in SUBBRAND_KEYS:
            continue
        pfin_by[name][fmt_period(r["period"])] = r
    pops_by = defaultdict(dict)
    for r in ops_partners:
        name = r.get("group_name")
        if not name or name in SUBBRAND_KEYS:
            continue
        pops_by[name][fmt_period(r["period"])] = r

    movers = []
    for name, by_p in pfin_by.items():
        if cur_p not in by_p or prev_p not in by_p:
            continue
        c, p = by_p[cur_p], by_p[prev_p]
        g0, g1 = p.get("gmv_eur") or 0, c.get("gmv_eur") or 0
        if max(g0, g1) < 500:
            continue
        ops_c = pops_by.get(name, {}).get(cur_p, {})
        ops_p = pops_by.get(name, {}).get(prev_p, {})
        movers.append({
            "name": name,
            "owner": OWNER_BY_PARTNER.get(name),
            "gmv_eur": g1,
            "gmv_prev": g0,
            "gmv_wow_pct": _pct(g1, g0),
            "gmv_delta_eur": g1 - g0,
            "orders": c.get("orders"),
            "orders_wow_pct": _pct(c.get("orders"), p.get("orders")),
            "availability_rate": ops_c.get("availability_rate"),
            "availability_wow_pp": _pp(ops_c.get("availability_rate"), ops_p.get("availability_rate")),
            "bad_order_rate": ops_c.get("bad_order_rate"),
            "demand_incentives_gmv_share": ops_c.get("demand_incentives_gmv_share"),
        })

    partners_up = sorted(movers, key=lambda x: -(x["gmv_delta_eur"] or 0))[:5]
    partners_down = sorted(movers, key=lambda x: (x["gmv_delta_eur"] or 0))[:5]
    partners_down = [p for p in partners_down if (p["gmv_delta_eur"] or 0) < 0][:5]

    def partner_note(row, direction):
        bits = [f"GMV {_fmt_eur(row['gmv_eur'])} ({_fmt_pct(row['gmv_wow_pct'])} WoW)"]
        if row.get("orders_wow_pct") is not None:
            bits.append(f"orders {_fmt_pct(row['orders_wow_pct'])}")
        if row.get("availability_wow_pp") is not None and abs(row["availability_wow_pp"]) >= 1:
            bits.append(f"availability {_fmt_pp(row['availability_wow_pp'])}")
        if direction == "down" and row.get("bad_order_rate") is not None and row["bad_order_rate"] >= 18:
            bits.append(f"bad rate {row['bad_order_rate']:.1f}%")
        owner = f" · {row['owner']}" if row.get("owner") else ""
        return {"name": row["name"], "owner": row.get("owner"), "detail": ", ".join(bits) + owner,
                "gmv_wow_pct": round(row["gmv_wow_pct"], 1) if row.get("gmv_wow_pct") is not None else None,
                "gmv_delta_eur": round(row["gmv_delta_eur"], 0) if row.get("gmv_delta_eur") is not None else None}

    partners_up_notes = [partner_note(r, "up") for r in partners_up if (r["gmv_delta_eur"] or 0) > 0]
    partners_down_notes = [partner_note(r, "down") for r in partners_down]

    # Campaign intensity
    bolt_share = None
    bolt_share_prev = None
    merchant_share = None
    discount_share = None
    if cur_camp.get("gmv_eur"):
        gmv_w = cur_camp["gmv_eur"]
        bolt_share = (cur_camp.get("bolt_spend_eur") or 0) / gmv_w * 100
        merchant_share = (cur_camp.get("merchant_spend_eur") or 0) / gmv_w * 100
        discount_share = (cur_camp.get("campaigns_discount_eur") or 0) / gmv_w * 100
    if prev_camp.get("gmv_eur"):
        bolt_share_prev = (prev_camp.get("bolt_spend_eur") or 0) / prev_camp["gmv_eur"] * 100

    watchouts = []
    actions = []

    di = cur_cp.get("demand_incentives_gmv_share")
    di_prev = prev_cp.get("demand_incentives_gmv_share")
    di_pp = _pp(di, di_prev)
    if di is not None and (di >= 6 or (di_pp is not None and di_pp >= 2)):
        # Who drove incentives if available on partner ops
        di_movers = []
        for name, by_p in pops_by.items():
            c, p = by_p.get(cur_p), by_p.get(prev_p)
            if not c or not p:
                continue
            # approximate spend proxy: share * gmv
            fin_c = pfin_by.get(name, {}).get(cur_p, {})
            fin_p = pfin_by.get(name, {}).get(prev_p, {})
            g1, g0 = fin_c.get("gmv_eur") or 0, fin_p.get("gmv_eur") or 0
            s1 = (c.get("demand_incentives_gmv_share") or 0) / 100 * g1
            s0 = (p.get("demand_incentives_gmv_share") or 0) / 100 * g0
            di_movers.append((name, s1 - s0, s1, c.get("demand_incentives_gmv_share")))
        di_movers = sorted(di_movers, key=lambda x: -x[1])
        top = di_movers[0] if di_movers else None
        detail = f"Demand incentives at {di:.1f}% of GMV ({_fmt_pp(di_pp)} WoW)."
        if top and top[1] > 0:
            detail += f" Largest estimated uplift: {top[0]} ({_fmt_eur(top[1])} incremental; {top[3]:.1f}% of partner GMV)."
        if bolt_share is not None:
            detail += f" Bolt campaign spend ≈ {bolt_share:.1f}% of GMV ({_fmt_eur(cur_camp.get('bolt_spend_eur'))})."
        watchouts.append({"title": "Incentive intensity spiked", "detail": detail, "severity": "risk"})
        actions.append({
            "title": "Review demand spend concentration",
            "detail": "Check whether the incentive uplift is converting efficiently and whether spend is over-concentrated in 1–2 partners/campaigns. Tighten or rebalance before next week if CM L2 stays deep negative.",
            "owner_hint": top[0] if top else "Commercial / Incentives",
        })

    l2 = cur_cp.get("cp_l2_margin_pct")
    l2_pp = _pp(l2, prev_cp.get("cp_l2_margin_pct"))
    if l2 is not None and (l2 <= -5 or (l2_pp is not None and l2_pp <= -2)):
        watchouts.append({
            "title": "CP L2 margin deteriorated",
            "detail": f"CP L2 at {l2:.1f}% ({_fmt_pp(l2_pp)} WoW). Usually tracks incentive/refund pressure — pair with demand-cost review.",
            "severity": "risk",
        })
        actions.append({
            "title": "Protect unit economics",
            "detail": "Walk CP L2 bridge for the week (incentives, refunds, courier/CPO). Freeze low-ROI campaigns if L2 remains < −5%.",
            "owner_hint": "Finance / Commercial",
        })

    fr = cur_fail.get("failed_rate_total")
    fr_pp = _pp(fr, prev_fail.get("failed_rate_total"))
    fb = cur_fail.get("failed_bolt_courier")
    fb_prev = prev_fail.get("failed_bolt_courier")
    if fr is not None and (fr >= 7.5 or (fr_pp is not None and fr_pp >= 0.8)):
        detail = f"Failed rate {fr:.1f}% ({_fmt_pp(fr_pp)} WoW)."
        if fb is not None and fb_prev is not None:
            detail += f" Bolt+courier failures {_fmt_num(fb)} vs {_fmt_num(fb_prev)} prior week."
        watchouts.append({"title": "Failed orders up", "detail": detail, "severity": "warn"})
        actions.append({
            "title": "Investigate failed Bolt+courier spike",
            "detail": "Check courier coverage in top cities and peak hours; compare merchant vs Bolt+courier split.",
            "owner_hint": "Ops / Courier",
        })

    bad = cur_ops.get("bad_order_rate")
    bad_pp = _pp(bad, prev_ops.get("bad_order_rate"))
    if bad is not None and (bad >= 16 or (bad_pp is not None and bad_pp >= 1)):
        watchouts.append({
            "title": "Quality pressure (bad order rate)",
            "detail": f"Bad order rate {bad:.1f}% ({_fmt_pp(bad_pp)} WoW). Watch partners with high bad rate among GMV droppers.",
            "severity": "warn",
        })

    # Partner-specific CTAs for sharp drops
    for row in partners_down[:3]:
        if (row.get("gmv_wow_pct") or 0) <= -10 and (row.get("gmv_prev") or 0) >= 800:
            avail = row.get("availability_wow_pp")
            detail = f"{row['name']} GMV {_fmt_pct(row['gmv_wow_pct'])} WoW ({_fmt_eur(row['gmv_delta_eur'])})."
            if avail is not None and avail <= -2:
                detail += f" Availability also {_fmt_pp(avail)} — likely supply/online hours issue."
                action_detail = f"Confirm online hours, menu/availability and local demand for {row['name']}."
            else:
                action_detail = f"Review demand, assortment and campaign support for {row['name']}."
            actions.append({
                "title": f"Follow up: {row['name']}",
                "detail": action_detail + ((" Owner: " + row["owner"]) if row.get("owner") else ""),
                "owner_hint": row.get("owner") or row["name"],
            })
            watchouts.append({
                "title": f"{row['name']} soft week",
                "detail": detail,
                "severity": "warn",
            })

    # Headline
    gmv_wow = _pct(cur_fin.get("gmv_eur"), prev_fin.get("gmv_eur"))
    orders_wow = _pct(cur_fin.get("orders"), prev_fin.get("orders"))
    if gmv_wow is not None and gmv_wow >= 8:
        tone = "strong growth"
    elif gmv_wow is not None and gmv_wow <= -5:
        tone = "soft week"
    else:
        tone = "mixed week"
    headline = (
        f"{_week_range_label(cur_p)}: {tone} — GMV {_fmt_eur(cur_fin.get('gmv_eur'))} "
        f"({_fmt_pct(gmv_wow)}), orders {_fmt_num(cur_fin.get('orders'))} ({_fmt_pct(orders_wow)})"
    )

    summary_bits = []
    if partners_up_notes:
        top = partners_up_notes[0]
        summary_bits.append(f"Largest GMV contributor: {top['name']} ({top['detail']}).")
    if worsened:
        summary_bits.append("Key pressures: " + ", ".join(w["label"] for w in worsened[:4]) + ".")
    if improved:
        summary_bits.append("Improved: " + ", ".join(w["label"] for w in improved[:4]) + ".")
    summary = " ".join(summary_bits) if summary_bits else "See KPI and partner sections below."

    # Month context: MTD = weeks whose Monday falls in the current month; vs prior full month if available
    cur_month = cur_p[:7]
    mtd_rows = [r for r in fin_w if r["period"][:7] == cur_month]
    mtd_gmv = sum(r.get("gmv_eur") or 0 for r in mtd_rows)
    mtd_orders = sum(r.get("orders") or 0 for r in mtd_rows)
    mtd_end = datetime.strptime(cur_p[:10], "%Y-%m-%d")
    from datetime import timedelta as _td
    mtd_end_label = (mtd_end + _td(days=6)).strftime("%b %-d")
    month_name = _month_label(cur_p)

    prior_month_rows = [r for r in overview_fin_monthly if r["period"][:7] < cur_month]
    prior_month = prior_month_rows[-1] if prior_month_rows else None
    month_note = (
        f"{month_name} MTD through {mtd_end_label} (complete weeks only): "
        f"GMV {_fmt_eur(mtd_gmv)} · orders {_fmt_num(mtd_orders)} across {len(mtd_rows)} week(s)."
    )
    if prior_month:
        # Rough pace: MTD vs same days ratio using prior full month / days — keep simple: vs prior month total as context only
        month_note += (
            f" Prior full month ({_month_label(prior_month['period'])}): "
            f"GMV {_fmt_eur(prior_month.get('gmv_eur'))} · orders {_fmt_num(prior_month.get('orders'))}."
        )

    # Deduplicate actions by title
    seen = set()
    uniq_actions = []
    for a in actions:
        if a["title"] in seen:
            continue
        seen.add(a["title"])
        uniq_actions.append(a)

    return {
        "week_period": cur_p,
        "week_label": _week_range_label(cur_p),
        "prior_week_period": prev_p,
        "prior_week_label": _week_range_label(prev_p),
        "generated_at": metadata.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "headline": headline,
        "summary": summary,
        "kpis": kpis,
        "improved": [{"title": k["label"], "detail": f"{k['value']} · {k['wow']} WoW", "severity": "good"} for k in improved],
        "worsened": [{"title": k["label"], "detail": f"{k['value']} · {k['wow']} WoW", "severity": "risk"} for k in worsened],
        "partners_up": partners_up_notes,
        "partners_down": partners_down_notes,
        "watchouts": watchouts[:6],
        "actions": uniq_actions[:6],
        "month": {
            "label": month_name,
            "mtd_label": f"{month_name} MTD through {mtd_end_label}",
            "gmv_eur": round(mtd_gmv, 2),
            "orders": mtd_orders,
            "weeks_included": len(mtd_rows),
            "note": month_note,
        },
        "month_analysis": build_month_insights(cur_p),
        "campaigns": {
            "bolt_spend_eur": cur_camp.get("bolt_spend_eur"),
            "merchant_spend_eur": cur_camp.get("merchant_spend_eur"),
            "campaigns_discount_eur": cur_camp.get("campaigns_discount_eur"),
            "bolt_share_pct": round(bolt_share, 2) if bolt_share is not None else None,
            "merchant_share_pct": round(merchant_share, 2) if merchant_share is not None else None,
            "discount_share_pct": round(discount_share, 2) if discount_share is not None else None,
            "bolt_share_wow_pp": round(_pp(bolt_share, bolt_share_prev), 2) if bolt_share is not None and bolt_share_prev is not None else None,
        },
    }


print("Building weekly insights...")
weekly_insights = build_weekly_insights()
if weekly_insights:
    print(f"  Insights for {weekly_insights['week_label']}: {weekly_insights['headline'][:80]}...")
else:
    print("  WARNING: not enough weekly data for insights")

# ======== ASSEMBLE FINAL DATA ========
DATA = {
    "generated_at": metadata.get("generated_at", datetime.now(timezone.utc).isoformat()),
    "data_start": metadata.get("data_start", "2026-01-01"),
    "partners_list": partners_list,
    "tenth_partner": tenth_partner,
    "top_partners_gmv": top_partners,
    "overview": {
        "weekly": {
            "financial": overview_fin_weekly,
            "cp_margins": overview_cp_weekly,
            "operational": overview_ops_weekly,
            "failed_orders": failed_overview_weekly,
            "campaigns": overview_camp_weekly,
            "gmv_by_partner": gmv_weekly,
        },
        "monthly": {
            "financial": overview_fin_monthly,
            "cp_margins": overview_cp_monthly_computed,
            "operational": overview_ops_monthly_computed,
            "failed_orders": failed_monthly,
            "campaigns": overview_camp_monthly,
            "gmv_by_partner": gmv_monthly,
        },
        "quarterly": {
            "financial": overview_fin_quarterly,
            "cp_margins": overview_cp_quarterly,
            "operational": overview_ops_quarterly,
            "failed_orders": failed_quarterly,
            "campaigns": overview_camp_quarterly,
            "gmv_by_partner": gmv_monthly,
        },
    },
    "acceptance_availability": acceptance if acceptance else {"overview": []},
    "partners": partners_data,
    "item_discount_promo": item_discount_promo,
    "item_defects": item_defects,
    "city_breakdown_weekly": city_breakdown_weekly,
    "city_eater_fees_weekly": city_eater_fees_weekly,
    "partner_city_weekly": partner_city_weekly,
    "employee_groups": EMPLOYEE_GROUPS,
    "subbrand_keys": ["Kopiyka", "Kopiyka Mini", "Santim"],
    "subbrand_groups": {"KOPIYKA": ["Kopiyka", "Kopiyka Mini", "Santim"]},
    "cities": cities_data,
    "city_list": city_list,
    "active_stores_snapshot": active_stores_data if isinstance(active_stores_data, dict) else {},
    "weekly_insights": weekly_insights,
}

# ======== GENERATE HTML ========
print("\nGenerating HTML...")
with open(os.path.join(SCRIPT_DIR, "template.html"), "r") as f:
    template = f.read()

data_json = json.dumps(DATA)
html = template.replace("/*__REPORT_DATA__*/", f"const REPORT_DATA = {data_json};")

with open(os.path.join(SCRIPT_DIR, "index.html"), "w") as f:
    f.write(html)

print(f"Generated index.html ({len(html)//1024} KB)")
print(f"Partners: {len(partners_list)}")
print(f"Overview weekly financial entries: {len(overview_fin_weekly)}")
print(f"Overview monthly financial entries: {len(overview_fin_monthly)}")
last_week = overview_fin_weekly[-1] if overview_fin_weekly else {}
print(f"Last week: {last_week.get('period', 'N/A')} — {last_week.get('orders', 0)} orders, €{last_week.get('gmv_eur', 0):.0f} GMV")
