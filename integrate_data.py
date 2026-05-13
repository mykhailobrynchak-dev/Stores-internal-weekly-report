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

DATA["overview"]["monthly"]["cp_margins"] = overview_cp_monthly
DATA["overview"]["monthly"]["operational"] = overview_ops_monthly

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
