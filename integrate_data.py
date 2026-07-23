"""Assemble all fetched Databricks data into the final HTML report."""
import json, os, math
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
    return {
        "gmv_eur": round(total_gmv, 2),
        "campaigns_discount_eur": round(total_discount, 2),
        "bolt_spend_eur": round(total_bolt, 2),
        "merchant_spend_eur": round(total_merch, 2),
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
