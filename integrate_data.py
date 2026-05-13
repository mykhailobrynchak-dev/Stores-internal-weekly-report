"""Integrate all corrected Databricks data into the report."""
import json, os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load existing build data (defines DATA, PARTNER_WEEKLY_FIN etc.)
exec(open(os.path.join(SCRIPT_DIR, "build_initial.py")).read().split("# Generate HTML")[0])

ALL_PARTNERS = [
    "LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK",
    "VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "TAISTRA", "BEERLAND K",
    "PYVNA BORODA", "WINETIME", "LEPRUKON", "TOCHKA", "SPRAGA",
    "DIMPYVA", "MAXBEER", "CHILL TIME", "FLOWER SHOP", "MAXBEER GROUP",
    "RODYNNA KOVBASKA", "NO TABOO", "BEERLAND", "SPAR"
]

def load_json(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)

# ======== CORRECTED OVERVIEW WEEKLY DATA ========
overview_corrected = load_json("overview_corrected_weekly.json")

# Build corrected cp_margins and operational from the unified data
overview_cp_weekly = []
overview_ops_weekly = []
for r in overview_corrected:
    period = r["period"] + " 00:00:00"
    overview_cp_weekly.append({
        "period": period,
        "cp_margin_pct": r["cp_margin_pct"],
        "cp_l2_margin_pct": r["cp_l2_margin_pct"],
        "commission_gmv_pct": r["commission_gmv_pct"],
        "commission_aov_pct": r["commission_aov_pct"]
    })
    overview_ops_weekly.append({
        "period": period,
        "delivered_orders": int(r["orders"]),
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

# Prepend January financial weeks to overview weekly financial
jan_fin_weeks = [
    {"period":"2026-01-05 00:00:00","orders":3229,"gmv_eur":37517,"aov_with_delivery":12.77,"aov_items_only":11.62,"eater_fees_per_order":1.50,"delivery_fee_per_order":1.0,"small_order_fee_per_order":0.11,"service_fee_per_order":0.40,"bolt_plus_gmv_share":14.97,"users_activated":127,"active_users":0,"delivery_fee_total":0,"small_order_fee_total":0,"service_fee_total":0,"refund_rate_pct":0},
    {"period":"2026-01-12 00:00:00","orders":3270,"gmv_eur":37295,"aov_with_delivery":12.51,"aov_items_only":11.41,"eater_fees_per_order":1.56,"delivery_fee_per_order":0.89,"small_order_fee_per_order":0.13,"service_fee_per_order":0.53,"bolt_plus_gmv_share":12.03,"users_activated":151,"active_users":0,"delivery_fee_total":0,"small_order_fee_total":0,"service_fee_total":0,"refund_rate_pct":0},
    {"period":"2026-01-19 00:00:00","orders":3657,"gmv_eur":42997,"aov_with_delivery":12.80,"aov_items_only":11.76,"eater_fees_per_order":1.42,"delivery_fee_per_order":0.73,"small_order_fee_per_order":0.13,"service_fee_per_order":0.56,"bolt_plus_gmv_share":15.66,"users_activated":124,"active_users":0,"delivery_fee_total":0,"small_order_fee_total":0,"service_fee_total":0,"refund_rate_pct":0},
]
existing_fin = DATA["overview"]["weekly"]["financial"]
DATA["overview"]["weekly"]["financial"] = jan_fin_weeks + existing_fin

# Replace overview weekly cp and ops
DATA["overview"]["weekly"]["cp_margins"] = overview_cp_weekly
DATA["overview"]["weekly"]["operational"] = overview_ops_weekly

# Compute monthly aggregates from weekly data
monthly_groups = defaultdict(list)
for r in overview_corrected:
    month_key = r["period"][:7] + "-01 00:00:00"
    monthly_groups[month_key].append(r)

overview_cp_monthly = []
overview_ops_monthly = []
for period in sorted(monthly_groups.keys()):
    rows = monthly_groups[period]
    n = len(rows)
    avg = lambda key: round(sum(r[key] for r in rows if r[key] is not None) / max(1, sum(1 for r in rows if r[key] is not None)), 2)
    total = lambda key: sum(r[key] for r in rows if r[key] is not None)

    overview_cp_monthly.append({
        "period": period,
        "cp_margin_pct": avg("cp_margin_pct"),
        "cp_l2_margin_pct": avg("cp_l2_margin_pct"),
        "commission_gmv_pct": avg("commission_gmv_pct"),
        "commission_aov_pct": avg("commission_aov_pct")
    })
    overview_ops_monthly.append({
        "period": period,
        "delivered_orders": int(total("orders")),
        "active_stores": max(r["active_stores"] for r in rows),
        "acceptance_rate": avg("acceptance_rate"),
        "availability_rate": avg("availability_rate"),
        "avg_rating": avg("avg_rating"),
        "honey_order_rate": avg("honey_rate"),
        "bad_order_rate": avg("bad_rate"),
        "late_delivery_rate": avg("late_delivery_rate"),
        "late_pickup_rate": avg("late_pickup_rate"),
        "avg_delivery_minutes": avg("avg_delivery_min"),
        "replacement_rate": 0,
        "adjustment_rate": 0
    })

# Compute monthly financial from weekly financial data
monthly_fin_groups = defaultdict(list)
for r in DATA["overview"]["weekly"]["financial"]:
    mkey = r["period"][:7].replace(" ", "") + "-01 00:00:00"
    if not mkey.startswith("20"):
        mkey = r["period"].replace(" 00:00:00","")[:7] + "-01 00:00:00"
    monthly_fin_groups[mkey].append(r)

overview_fin_monthly = []
for period in sorted(monthly_fin_groups.keys()):
    rows = monthly_fin_groups[period]
    total_orders = sum(r["orders"] for r in rows)
    total_gmv = sum(r["gmv_eur"] for r in rows)
    if total_orders == 0:
        continue
    overview_fin_monthly.append({
        "period": period,
        "orders": total_orders,
        "gmv_eur": round(total_gmv, 0),
        "aov_with_delivery": round(sum(r["aov_with_delivery"] * r["orders"] for r in rows) / total_orders, 2),
        "aov_items_only": round(total_gmv / total_orders, 2),
        "eater_fees_per_order": round(sum(r["eater_fees_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "delivery_fee_per_order": round(sum(r["delivery_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "small_order_fee_per_order": round(sum(r["small_order_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "service_fee_per_order": round(sum(r["service_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "bolt_plus_gmv_share": round(sum(r.get("bolt_plus_gmv_share", 0) * r["orders"] for r in rows) / total_orders, 2),
        "users_activated": sum(r.get("users_activated", 0) for r in rows),
        "active_users": max((r.get("active_users", 0) for r in rows), default=0)
    })

DATA["overview"]["monthly"]["financial"] = overview_fin_monthly
DATA["overview"]["monthly"]["cp_margins"] = overview_cp_monthly
DATA["overview"]["monthly"]["operational"] = overview_ops_monthly

# Compute quarterly aggregates from weekly data
import math
quarterly_groups = defaultdict(list)
for r in overview_corrected:
    parts = r["period"].split("-")
    q = math.ceil(int(parts[1]) / 3)
    quarter_key = f"{parts[0]}-{q*3-2:02d}-01 00:00:00"  # Q1=01-01, Q2=04-01
    quarterly_groups[quarter_key].append(r)

overview_cp_quarterly = []
overview_ops_quarterly = []
for period in sorted(quarterly_groups.keys()):
    rows = quarterly_groups[period]
    avg = lambda key: round(sum(r[key] for r in rows if r[key] is not None) / max(1, sum(1 for r in rows if r[key] is not None)), 2)
    total = lambda key: sum(r[key] for r in rows if r[key] is not None)

    overview_cp_quarterly.append({
        "period": period,
        "cp_margin_pct": avg("cp_margin_pct"),
        "cp_l2_margin_pct": avg("cp_l2_margin_pct"),
        "commission_gmv_pct": avg("commission_gmv_pct"),
        "commission_aov_pct": avg("commission_aov_pct")
    })
    overview_ops_quarterly.append({
        "period": period,
        "delivered_orders": int(total("orders")),
        "active_stores": max(r["active_stores"] for r in rows),
        "acceptance_rate": avg("acceptance_rate"),
        "availability_rate": avg("availability_rate"),
        "avg_rating": avg("avg_rating"),
        "honey_order_rate": avg("honey_rate"),
        "bad_order_rate": avg("bad_rate"),
        "late_delivery_rate": avg("late_delivery_rate"),
        "late_pickup_rate": avg("late_pickup_rate"),
        "avg_delivery_minutes": avg("avg_delivery_min"),
        "replacement_rate": 0,
        "adjustment_rate": 0
    })

# Compute quarterly financial from weekly financial
quarterly_fin_groups = defaultdict(list)
for r in DATA["overview"]["weekly"]["financial"]:
    parts = r["period"].replace(" 00:00:00","").split("-")
    q = math.ceil(int(parts[1]) / 3)
    qkey = f"{parts[0]}-{q*3-2:02d}-01 00:00:00"
    quarterly_fin_groups[qkey].append(r)

overview_fin_quarterly = []
for period in sorted(quarterly_fin_groups.keys()):
    rows = quarterly_fin_groups[period]
    total_orders = sum(r["orders"] for r in rows)
    total_gmv = sum(r["gmv_eur"] for r in rows)
    if total_orders == 0:
        continue
    overview_fin_quarterly.append({
        "period": period,
        "orders": total_orders,
        "gmv_eur": round(total_gmv, 0),
        "aov_with_delivery": round(sum(r["aov_with_delivery"] * r["orders"] for r in rows) / total_orders, 2),
        "aov_items_only": round(total_gmv / total_orders, 2),
        "eater_fees_per_order": round(sum(r["eater_fees_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "delivery_fee_per_order": round(sum(r["delivery_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "small_order_fee_per_order": round(sum(r["small_order_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "service_fee_per_order": round(sum(r["service_fee_per_order"] * r["orders"] for r in rows) / total_orders, 2),
        "bolt_plus_gmv_share": round(sum(r.get("bolt_plus_gmv_share", 0) * r["orders"] for r in rows) / total_orders, 2),
        "users_activated": sum(r.get("users_activated", 0) for r in rows),
        "active_users": max((r.get("active_users", 0) for r in rows), default=0)
    })

# Quarterly campaigns from monthly campaigns
quarterly_camp_groups = defaultdict(list)
for r in DATA["overview"]["monthly"].get("campaigns", []):
    parts = r["period"].replace(" 00:00:00","").split("-")
    q = math.ceil(int(parts[1]) / 3)
    qkey = f"{parts[0]}-{q*3-2:02d}-01 00:00:00"
    quarterly_camp_groups[qkey].append(r)

overview_camp_quarterly = []
for period in sorted(quarterly_camp_groups.keys()):
    rows = quarterly_camp_groups[period]
    overview_camp_quarterly.append({
        "period": period,
        "campaigns_discount_eur": sum(r["campaigns_discount_eur"] for r in rows),
        "bolt_spend_eur": sum(r["bolt_spend_eur"] for r in rows),
        "merchant_spend_eur": sum(r["merchant_spend_eur"] for r in rows),
        "gmv_eur": sum(r["gmv_eur"] for r in rows)
    })

DATA["overview"]["quarterly"] = {
    "financial": overview_fin_quarterly,
    "cp_margins": overview_cp_quarterly,
    "operational": overview_ops_quarterly,
    "failed_orders": [],
    "campaigns": overview_camp_quarterly,
    "gmv_by_partner": DATA["overview"]["monthly"].get("gmv_by_partner", [])
}

# ======== CORRECTED PARTNER DATA ========
partner_data_raw = load_json("partners_corrected_batch1.json") + load_json("partners_corrected_batch2.json")

# Group by partner
partner_by_name = defaultdict(list)
for r in partner_data_raw:
    partner_by_name[r["group_name"]].append(r)

# Build partner structures
DATA["partners_list"] = ALL_PARTNERS

for pname in ALL_PARTNERS:
    if pname not in DATA["partners"]:
        DATA["partners"][pname] = {
            "monthly": {"financial": [], "cp_margins": [], "operational": [], "failed_orders": [], "campaigns": []},
            "weekly": {"financial": [], "cp_margins": [], "operational": [], "failed_orders": [], "campaigns": []}
        }

    rows = sorted(partner_by_name.get(pname, []), key=lambda x: x["period"])
    if not rows:
        continue

    pw = DATA["partners"][pname]["weekly"]

    # Build cp_margins
    cp_list = []
    ops_list = []
    for r in rows:
        period = r["period"] + " 00:00:00"
        cp_list.append({
            "period": period,
            "cp_margin_pct": r["cp_margin_pct"],
            "cp_l2_margin_pct": r["cp_l2_margin_pct"],
            "commission_gmv_pct": r["commission_gmv_pct"],
            "commission_aov_pct": r["commission_aov_pct"]
        })
        ops_list.append({
            "period": period,
            "delivered_orders": int(r["orders"]) if r["orders"] else 0,
            "active_stores": r["active_stores"],
            "acceptance_rate": r["acceptance_rate"],
            "availability_rate": r["availability_rate"],
            "avg_rating": r["avg_rating"],
            "honey_order_rate": r["honey_order_rate"],
            "bad_order_rate": r["bad_order_rate"],
            "late_delivery_rate": r["late_delivery_rate"],
            "late_pickup_rate": r["late_pickup_rate"],
            "avg_delivery_minutes": r["avg_delivery_minutes"],
            "replacement_rate": r["replacement_rate"],
            "adjustment_rate": r["adjustment_rate"]
        })

    pw["cp_margins"] = cp_list
    pw["operational"] = ops_list

    # Keep existing financial and campaign data
    # (from build_initial.py partner_weekly_data.json and new_partners_fin_raw.json)

# Load additional financial data for partners that don't have it yet
new_fin_raw = load_json("new_partners_fin_raw.json")
if new_fin_raw:
    new_fin_by_partner = defaultdict(list)
    for row in new_fin_raw:
        gn = row.get("group_name")
        if gn in set(ALL_PARTNERS):
            period = row["period"].replace("T00:00:00.000Z", " 00:00:00").replace("T", " ").rstrip("Z")
            if not period.endswith("00:00:00"):
                period += " 00:00:00"
            new_fin_by_partner[gn].append({
                "period": period,
                "orders": int(row["orders"]),
                "gmv_eur": float(row["gmv_eur"]),
                "aov_with_delivery": float(row["aov_with_delivery"]),
                "aov_items_only": float(row["aov_items_only"]),
                "eater_fees_per_order": float(row["eater_fees_per_order"]),
                "delivery_fee_per_order": float(row["delivery_fee_per_order"]),
                "small_order_fee_per_order": float(row["small_order_fee_per_order"]),
                "service_fee_per_order": float(row["service_fee_per_order"]),
                "bolt_plus_gmv_share": float(row["bolt_plus_gmv_share"]),
                "users_activated": int(row["users_activated"]),
                "active_users": int(row["active_users"])
            })
    for pname in ALL_PARTNERS:
        pw = DATA["partners"][pname]["weekly"]
        if not pw["financial"] and pname in new_fin_by_partner:
            pw["financial"] = new_fin_by_partner[pname]

# Load campaign data
camp_raw = load_json("all_partners_camp_raw.json")
if camp_raw:
    camp_by_partner = defaultdict(list)
    for row in camp_raw:
        gn = row["group_name"]
        if gn in set(ALL_PARTNERS):
            period = row["period"].replace("T00:00:00.000Z", " 00:00:00").replace("T", " ").rstrip("Z")
            if not period.endswith("00:00:00"):
                period += " 00:00:00"
            camp_by_partner[gn].append({
                "period": period,
                "campaigns_discount_eur": float(row["campaigns_discount_eur"]),
                "bolt_spend_eur": float(row["bolt_spend_eur"]),
                "merchant_spend_eur": float(row["merchant_spend_eur"]),
                "gmv_eur": float(row["gmv_eur"])
            })
    for pname in ALL_PARTNERS:
        pw = DATA["partners"][pname]["weekly"]
        if pname in camp_by_partner:
            pw["campaigns"] = camp_by_partner[pname]

# GMV by partner for pie chart
gmv_by_partner = []
if camp_raw:
    for row in camp_raw:
        period = row["period"].replace("T00:00:00.000Z", " 00:00:00").replace("T", " ").rstrip("Z")
        if not period.endswith("00:00:00"):
            period += " 00:00:00"
        gmv_by_partner.append({
            "period": period,
            "group_name": row["group_name"],
            "gmv_eur": float(row["gmv_eur"]),
            "orders": 0
        })
    DATA["overview"]["weekly"]["gmv_by_partner"] = gmv_by_partner

# ======== QUARTERLY DATA FOR PARTNERS ========
import math as _math
for pname in ALL_PARTNERS:
    pw = DATA["partners"][pname]["weekly"]
    if not pw.get("cp_margins") or not pw.get("operational"):
        DATA["partners"][pname]["quarterly"] = {"financial": [], "cp_margins": [], "operational": [], "failed_orders": [], "campaigns": []}
        continue

    p_quarterly_cp_groups = defaultdict(list)
    for r in pw["cp_margins"]:
        parts = r["period"].replace(" 00:00:00", "").split("-")
        q = _math.ceil(int(parts[1]) / 3)
        qkey = f"{parts[0]}-{q*3-2:02d}-01 00:00:00"
        p_quarterly_cp_groups[qkey].append(r)

    p_quarterly_ops_groups = defaultdict(list)
    for r in pw["operational"]:
        parts = r["period"].replace(" 00:00:00", "").split("-")
        q = _math.ceil(int(parts[1]) / 3)
        qkey = f"{parts[0]}-{q*3-2:02d}-01 00:00:00"
        p_quarterly_ops_groups[qkey].append(r)

    def pavg(rows, key):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    p_cp_q = []
    for period in sorted(p_quarterly_cp_groups.keys()):
        rows = p_quarterly_cp_groups[period]
        p_cp_q.append({
            "period": period,
            "cp_margin_pct": pavg(rows, "cp_margin_pct"),
            "cp_l2_margin_pct": pavg(rows, "cp_l2_margin_pct"),
            "commission_gmv_pct": pavg(rows, "commission_gmv_pct"),
            "commission_aov_pct": pavg(rows, "commission_aov_pct")
        })

    p_ops_q = []
    for period in sorted(p_quarterly_ops_groups.keys()):
        rows = p_quarterly_ops_groups[period]
        p_ops_q.append({
            "period": period,
            "delivered_orders": sum(int(r.get("delivered_orders") or 0) for r in rows),
            "active_stores": max((r.get("active_stores") or 0) for r in rows),
            "acceptance_rate": pavg(rows, "acceptance_rate"),
            "availability_rate": pavg(rows, "availability_rate"),
            "avg_rating": pavg(rows, "avg_rating"),
            "honey_order_rate": pavg(rows, "honey_order_rate"),
            "bad_order_rate": pavg(rows, "bad_order_rate"),
            "late_delivery_rate": pavg(rows, "late_delivery_rate"),
            "late_pickup_rate": pavg(rows, "late_pickup_rate"),
            "avg_delivery_minutes": pavg(rows, "avg_delivery_minutes"),
            "replacement_rate": pavg(rows, "replacement_rate"),
            "adjustment_rate": pavg(rows, "adjustment_rate")
        })

    DATA["partners"][pname]["quarterly"] = {
        "financial": DATA["partners"][pname].get("monthly", {}).get("financial", []),
        "cp_margins": p_cp_q,
        "operational": p_ops_q,
        "failed_orders": [],
        "campaigns": pw.get("campaigns", [])
    }

# ======== ITEM-LEVEL DISCOUNT PROMO SHARE ========
promo_raw = load_json("partner_item_discount_promo.json")
if promo_raw:
    item_discount_promo = {}
    for pname, periods in promo_raw.items():
        item_discount_promo[pname] = []
        for period, value in sorted(periods.items()):
            item_discount_promo[pname].append({"period": period + " 00:00:00", "value": value})
    DATA["item_discount_promo"] = item_discount_promo

# ======== GENERATE HTML ========
with open(os.path.join(SCRIPT_DIR, "template.html"), "r") as f:
    template = f.read()

data_json = json.dumps(DATA)
html = template.replace("/*__REPORT_DATA__*/", f"const REPORT_DATA = {data_json};")

with open(os.path.join(SCRIPT_DIR, "index.html"), "w") as f:
    f.write(html)

print(f"Generated index.html ({len(html)//1024} KB)")
print(f"Partners: {len(ALL_PARTNERS)}")
print(f"Overview weekly CP entries: {len(overview_cp_weekly)}")
print(f"Overview monthly CP entries: {len(overview_cp_monthly)}")
print(f"Partners with weekly ops: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['operational'])}")
print(f"Partners with weekly CP: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['cp_margins'])}")
# Verify key data point
may4_cp = next((r for r in overview_cp_weekly if '2026-05-04' in r['period']), None)
if may4_cp:
    print(f"May 4 overview: CP={may4_cp['cp_margin_pct']}%, CP_L2={may4_cp['cp_l2_margin_pct']}%, Comm_GMV={may4_cp['commission_gmv_pct']}%, Comm_AOV={may4_cp['commission_aov_pct']}%")
