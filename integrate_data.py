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
    "DIMPYVA", "MAXBEER", "CHILL TIME", "FLOWER SHOP", "MAXBEER GROUP",
    "RODYNNA KOVBASKA", "NO TABOO", "BEERLAND", "SPAR", "ANRI-PHARM"
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
overview_cp_monthly = load_json("data_overview_cp_monthly.json")
failed_monthly = load_json("data_failed_orders_monthly.json")
gmv_monthly = load_json("data_gmv_by_partner_monthly.json")
gmv_weekly = load_json("data_gmv_by_partner_weekly.json")
ops_overview = load_json("data_ops_overview_weekly.json")
ops_partners = load_json("data_ops_partners_weekly.json")
partner_fin_monthly = load_json("data_partner_fin_monthly.json")
partner_fin_weekly = load_json("data_partner_fin_weekly.json")
partner_camp_monthly = load_json("data_partner_camp_monthly.json")
partner_camp_weekly = load_json("data_partner_camp_weekly.json")
acceptance = load_json("data_acceptance.json")

partners_list = metadata.get("partners_list", ALL_TRACKED_PARTNERS)
tenth_partner = metadata.get("tenth_partner")

# Normalize all periods
for lst in [overview_fin_weekly, overview_fin_monthly, overview_camp_weekly, overview_camp_monthly,
            overview_cp_monthly, failed_monthly, gmv_monthly, gmv_weekly,
            partner_fin_monthly, partner_fin_weekly, partner_camp_monthly, partner_camp_weekly]:
    for r in lst:
        r["period"] = fmt_period(r["period"])

# Sanitize campaign data: clamp negative values to 0 (data quality issues in source)
for lst in [overview_camp_weekly, overview_camp_monthly, partner_camp_monthly, partner_camp_weekly]:
    for r in lst:
        for key in ["campaigns_discount_eur", "bolt_spend_eur", "merchant_spend_eur"]:
            if r.get(key) is not None and r[key] < 0:
                r[key] = 0.0

# ======== BUILD OVERVIEW CP/OPS FROM fact_provider_weekly ========
overview_cp_weekly = []
overview_ops_weekly = []
for r in ops_overview:
    period = fmt_period(r["period"])
    overview_cp_weekly.append({
        "period": period,
        "cp_margin_pct": r["cp_margin_pct"],
        "cp_l2_margin_pct": r["cp_l2_margin_pct"],
        "commission_gmv_pct": r["commission_gmv_pct"],
        "commission_aov_pct": r["commission_aov_pct"]
    })
    overview_ops_weekly.append({
        "period": period,
        "delivered_orders": r["orders"],
        "active_stores": r["active_stores"],
        "acceptance_rate": r["acceptance_rate"],
        "availability_rate": r["availability_rate"],
        "avg_rating": r["avg_rating"],
        "honey_order_rate": r["honey_rate"],
        "bad_order_rate": r["bad_rate"],
        "late_delivery_rate": r["late_delivery_rate"],
        "late_pickup_rate": r["late_pickup_rate"],
        "avg_delivery_minutes": r["avg_delivery_min"],
        "replacement_rate": 0,
        "adjustment_rate": 0
    })

# Monthly CP/OPS aggregated from weekly
monthly_ops_groups = defaultdict(list)
for r in ops_overview:
    mkey = r["period"][:7] + "-01 00:00:00"
    monthly_ops_groups[mkey].append(r)

overview_cp_monthly_computed = []
overview_ops_monthly_computed = []
for period in sorted(monthly_ops_groups.keys()):
    rows = monthly_ops_groups[period]
    overview_cp_monthly_computed.append({
        "period": period,
        "cp_margin_pct": avg_vals(rows, "cp_margin_pct"),
        "cp_l2_margin_pct": avg_vals(rows, "cp_l2_margin_pct"),
        "commission_gmv_pct": avg_vals(rows, "commission_gmv_pct"),
        "commission_aov_pct": avg_vals(rows, "commission_aov_pct")
    })
    overview_ops_monthly_computed.append({
        "period": period,
        "delivered_orders": sum(r["orders"] for r in rows),
        "active_stores": max(r["active_stores"] for r in rows),
        "acceptance_rate": avg_vals(rows, "acceptance_rate"),
        "availability_rate": avg_vals(rows, "availability_rate"),
        "avg_rating": avg_vals(rows, "avg_rating"),
        "honey_order_rate": avg_vals(rows, "honey_rate"),
        "bad_order_rate": avg_vals(rows, "bad_rate"),
        "late_delivery_rate": avg_vals(rows, "late_delivery_rate"),
        "late_pickup_rate": avg_vals(rows, "late_pickup_rate"),
        "avg_delivery_minutes": avg_vals(rows, "avg_delivery_min"),
        "replacement_rate": 0,
        "adjustment_rate": 0
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

# CP/OPS
q_ops_groups = group_by_quarter([{"period": fmt_period(r["period"]), **r} for r in ops_overview])
overview_cp_quarterly = []
overview_ops_quarterly = []
for period in sorted(q_ops_groups.keys()):
    rows = q_ops_groups[period]
    overview_cp_quarterly.append({
        "period": period,
        "cp_margin_pct": avg_vals(rows, "cp_margin_pct"),
        "cp_l2_margin_pct": avg_vals(rows, "cp_l2_margin_pct"),
        "commission_gmv_pct": avg_vals(rows, "commission_gmv_pct"),
        "commission_aov_pct": avg_vals(rows, "commission_aov_pct")
    })
    overview_ops_quarterly.append({
        "period": period,
        "delivered_orders": sum(r["orders"] for r in rows),
        "active_stores": max(r["active_stores"] for r in rows),
        "acceptance_rate": avg_vals(rows, "acceptance_rate"),
        "availability_rate": avg_vals(rows, "availability_rate"),
        "avg_rating": avg_vals(rows, "avg_rating"),
        "honey_order_rate": avg_vals(rows, "honey_rate"),
        "bad_order_rate": avg_vals(rows, "bad_rate"),
        "late_delivery_rate": avg_vals(rows, "late_delivery_rate"),
        "late_pickup_rate": avg_vals(rows, "late_pickup_rate"),
        "avg_delivery_minutes": avg_vals(rows, "avg_delivery_min"),
        "replacement_rate": 0,
        "adjustment_rate": 0
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

# Failed orders quarterly
q_fail_groups = defaultdict(list)
for r in failed_monthly:
    q_fail_groups[quarter_key(r["period"])].append(r)
failed_quarterly = []
for period in sorted(q_fail_groups.keys()):
    rows = q_fail_groups[period]
    failed_quarterly.append({
        "period": period,
        "total_placed": sum(r.get("total_placed", 0) or 0 for r in rows),
        "delivered": sum(r.get("delivered", 0) or 0 for r in rows),
        "failed_merchant": sum(r.get("failed_merchant", 0) or 0 for r in rows),
        "failed_bolt_courier": sum(r.get("failed_bolt_courier", 0) or 0 for r in rows),
        "failed_rate_total": round(sum(r.get("failed_merchant", 0) or 0 for r in rows) + sum(r.get("failed_bolt_courier", 0) or 0 for r in rows)) / max(1, sum(r.get("total_placed", 0) or 0 for r in rows)) * 100
    })

# ======== BUILD PARTNER DATA ========
print("Building partner data...")
ops_by_partner = defaultdict(list)
for r in ops_partners:
    ops_by_partner[r["group_name"]].append(r)

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
    rows = sorted(ops_by_partner.get(pname, []), key=lambda x: x["period"])

    # Weekly CP + OPS
    weekly_cp = []
    weekly_ops = []
    for r in rows:
        period = fmt_period(r["period"])
        weekly_cp.append({
            "period": period,
            "cp_margin_pct": r["cp_margin_pct"],
            "cp_l2_margin_pct": r["cp_l2_margin_pct"],
            "commission_gmv_pct": r["commission_gmv_pct"],
            "commission_aov_pct": r["commission_aov_pct"]
        })
        weekly_ops.append({
            "period": period,
            "delivered_orders": r["orders"],
            "active_stores": r["active_stores"],
            "acceptance_rate": r["acceptance_rate"],
            "availability_rate": r["availability_rate"],
            "avg_rating": r["avg_rating"],
            "honey_order_rate": r["honey_order_rate"],
            "bad_order_rate": r["bad_order_rate"],
            "late_delivery_rate": r["late_delivery_rate"],
            "late_pickup_rate": r["late_pickup_rate"],
            "avg_delivery_minutes": r["avg_delivery_minutes"],
            "replacement_rate": r.get("replacement_rate", 0),
            "adjustment_rate": r.get("adjustment_rate", 0)
        })

    # Monthly CP (from weekly)
    m_cp_groups = defaultdict(list)
    for r in weekly_cp:
        m_cp_groups[r["period"][:7] + "-01 00:00:00"].append(r)
    monthly_cp = []
    for mp in sorted(m_cp_groups.keys()):
        monthly_cp.append({
            "period": mp,
            "cp_margin_pct": avg_vals(m_cp_groups[mp], "cp_margin_pct"),
            "cp_l2_margin_pct": avg_vals(m_cp_groups[mp], "cp_l2_margin_pct"),
            "commission_gmv_pct": avg_vals(m_cp_groups[mp], "commission_gmv_pct"),
            "commission_aov_pct": avg_vals(m_cp_groups[mp], "commission_aov_pct")
        })

    # Monthly OPS (from weekly)
    m_ops_groups = defaultdict(list)
    for r in weekly_ops:
        m_ops_groups[r["period"][:7] + "-01 00:00:00"].append(r)
    monthly_ops = []
    for mp in sorted(m_ops_groups.keys()):
        g = m_ops_groups[mp]
        monthly_ops.append({
            "period": mp,
            "delivered_orders": sum(r["delivered_orders"] for r in g),
            "active_stores": max(r["active_stores"] for r in g),
            "acceptance_rate": avg_vals(g, "acceptance_rate"),
            "availability_rate": avg_vals(g, "availability_rate"),
            "avg_rating": avg_vals(g, "avg_rating"),
            "honey_order_rate": avg_vals(g, "honey_order_rate"),
            "bad_order_rate": avg_vals(g, "bad_order_rate"),
            "late_delivery_rate": avg_vals(g, "late_delivery_rate"),
            "late_pickup_rate": avg_vals(g, "late_pickup_rate"),
            "avg_delivery_minutes": avg_vals(g, "avg_delivery_minutes"),
            "replacement_rate": avg_vals(g, "replacement_rate"),
            "adjustment_rate": avg_vals(g, "adjustment_rate")
        })

    # Weekly/Monthly financial from fact_order_delivery
    p_fin_w = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pfin_weekly_by_partner.get(pname, [])]
    p_fin_m = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pfin_monthly_by_partner.get(pname, [])]

    # Weekly/Monthly campaigns from fact_order_delivery
    p_camp_w = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pcamp_weekly_by_partner.get(pname, [])]
    p_camp_m = [{"period": fmt_period(r["period"]), **{k: v for k, v in r.items() if k not in ("period", "group_name")}} for r in pcamp_monthly_by_partner.get(pname, [])]

    # Quarterly aggregation
    q_cp_groups = group_by_quarter(weekly_cp)
    q_ops_groups_p = group_by_quarter(weekly_ops)
    q_fin_groups_p = group_by_quarter(p_fin_m) if p_fin_m else {}
    q_camp_groups_p = group_by_quarter(p_camp_m) if p_camp_m else {}

    quarterly_cp = []
    for qp in sorted(q_cp_groups.keys()):
        quarterly_cp.append({
            "period": qp,
            "cp_margin_pct": avg_vals(q_cp_groups[qp], "cp_margin_pct"),
            "cp_l2_margin_pct": avg_vals(q_cp_groups[qp], "cp_l2_margin_pct"),
            "commission_gmv_pct": avg_vals(q_cp_groups[qp], "commission_gmv_pct"),
            "commission_aov_pct": avg_vals(q_cp_groups[qp], "commission_aov_pct")
        })

    quarterly_ops = []
    for qp in sorted(q_ops_groups_p.keys()):
        g = q_ops_groups_p[qp]
        quarterly_ops.append({
            "period": qp,
            "delivered_orders": sum(r["delivered_orders"] for r in g),
            "active_stores": max(r["active_stores"] for r in g),
            "acceptance_rate": avg_vals(g, "acceptance_rate"),
            "availability_rate": avg_vals(g, "availability_rate"),
            "avg_rating": avg_vals(g, "avg_rating"),
            "honey_order_rate": avg_vals(g, "honey_order_rate"),
            "bad_order_rate": avg_vals(g, "bad_order_rate"),
            "late_delivery_rate": avg_vals(g, "late_delivery_rate"),
            "late_pickup_rate": avg_vals(g, "late_pickup_rate"),
            "avg_delivery_minutes": avg_vals(g, "avg_delivery_minutes"),
            "replacement_rate": avg_vals(g, "replacement_rate"),
            "adjustment_rate": avg_vals(g, "adjustment_rate")
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

    partners_data[pname] = {
        "weekly": {"financial": p_fin_w, "cp_margins": weekly_cp, "operational": weekly_ops, "failed_orders": [], "campaigns": p_camp_w},
        "monthly": {"financial": p_fin_m, "cp_margins": monthly_cp, "operational": monthly_ops, "failed_orders": [], "campaigns": p_camp_m},
        "quarterly": {"financial": quarterly_fin, "cp_margins": quarterly_cp, "operational": quarterly_ops, "failed_orders": [], "campaigns": quarterly_camp}
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
            "failed_orders": [],
            "campaigns": overview_camp_weekly,
            "gmv_by_partner": gmv_weekly
        },
        "monthly": {
            "financial": overview_fin_monthly,
            "cp_margins": overview_cp_monthly_computed,
            "operational": overview_ops_monthly_computed,
            "failed_orders": failed_monthly,
            "campaigns": overview_camp_monthly,
            "gmv_by_partner": gmv_monthly
        },
        "quarterly": {
            "financial": overview_fin_quarterly,
            "cp_margins": overview_cp_quarterly,
            "operational": overview_ops_quarterly,
            "failed_orders": failed_quarterly,
            "campaigns": overview_camp_quarterly,
            "gmv_by_partner": gmv_monthly
        }
    },
    "acceptance_availability": acceptance if acceptance else {"overview": []},
    "partners": partners_data,
    "item_discount_promo": item_discount_promo
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
