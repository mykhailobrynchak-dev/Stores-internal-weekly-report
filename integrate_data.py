"""Integrate all Databricks query results into the report data."""
import json, os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load existing build data module
exec(open(os.path.join(SCRIPT_DIR, "build_initial.py")).read().split("# Generate HTML")[0])

ALL_PARTNERS = [
    "LOKO", "KOPIYKA", "HOP HEY", "BEER MARKET", "CAFE RYNOK",
    "VARUS", "RUKAVYCHKA", "REMESLO BREWERY", "TAISTRA", "BEERLAND K",
    "PYVNA BORODA", "WINETIME", "LEPRUKON", "TOCHKA", "SPRAGA",
    "DIMPYVA", "MAXBEER", "CHILL TIME", "FLOWER SHOP", "MAXBEER GROUP",
    "RODYNNA KOVBASKA", "NO TABOO", "BEERLAND", "SPAR"
]

RELEVANT_PARTNERS = set(ALL_PARTNERS)

# Mapping from Databricks group_name to our canonical names
PARTNER_NAME_MAP = {
    "CRAFT BEER MARKET GROUP": None,
    "BEER MARKET GROUP": None,
    "WINETIME GROUP": None,
    "REMESLO BREWERY GROUP": None,
    "DIMPYVAA": None,
    "AMELI FLOWERS": None,
    "DON BUTON FLOWERS": None,
    "FRESH FLOWERS": None,
    "IN LOVE FLOWERS": None,
    "JUST FLOWERS": None,
    "KATRIN'S FLOWERS": None,
    "LAVANDA FLOWERS": None,
    "LIME FLOWERS&DECOR": None,
    "MILANO FLOWERS": None,
    "NAF FLOWERS": None,
    "ODA FLOWERS": None,
    "SIMPLE FLOWERS": None,
    "TEONA-FLOWERS": None,
    "TRUE FLOWERS": None,
    "UKRAINE FLOWERS": None,
    "RV-FLOWER": None,
    "FLOWERS": None,
    "SOLOD BEER MARKET": None,
}

def normalize_partner(name):
    if name in PARTNER_NAME_MAP:
        return PARTNER_NAME_MAP[name]
    if name in RELEVANT_PARTNERS:
        return name
    return None

def ts_to_period(ts):
    return ts.replace("T00:00:00.000Z", " 00:00:00").replace("T", " ").rstrip("Z")

# ======== CORRECT CP MARGINS (from fact_delivery_country_weekly) ========
cp_data = json.loads(open(os.path.join(SCRIPT_DIR, "correct_cp_margins.json")).read())

# Replace overview CP margins with correct data
DATA["overview"]["weekly"]["cp_margins"] = cp_data["overview_weekly"]
DATA["overview"]["monthly"]["cp_margins"] = cp_data["overview_monthly"]

# Merge acceptance/availability/rating into overview weekly operational data
overview_aa = {r["period"]: r for r in cp_data["overview_aa_weekly"]}
for op_row in DATA["overview"]["weekly"]["operational"]:
    aa = overview_aa.get(op_row["period"])
    if aa:
        op_row["acceptance_rate"] = aa["acceptance_rate"]
        op_row["availability_rate"] = aa["availability_rate"]
        op_row["avg_rating"] = aa["avg_rating"]

# Compute monthly averages for acceptance/availability/rating from weekly data
monthly_aa_sums = defaultdict(lambda: {"acceptance_rate": [], "availability_rate": [], "avg_rating": []})
for r in cp_data["overview_aa_weekly"]:
    period_date = r["period"].split(" ")[0]  # "2026-02-02"
    month_key = period_date[:7] + "-01 00:00:00"  # "2026-02-01 00:00:00"
    monthly_aa_sums[month_key]["acceptance_rate"].append(r["acceptance_rate"])
    monthly_aa_sums[month_key]["availability_rate"].append(r["availability_rate"])
    monthly_aa_sums[month_key]["avg_rating"].append(r["avg_rating"])

for op_row in DATA["overview"]["monthly"]["operational"]:
    aa_lists = monthly_aa_sums.get(op_row["period"])
    if aa_lists:
        op_row["acceptance_rate"] = round(sum(aa_lists["acceptance_rate"]) / len(aa_lists["acceptance_rate"]), 1)
        op_row["availability_rate"] = round(sum(aa_lists["availability_rate"]) / len(aa_lists["availability_rate"]), 1)
        op_row["avg_rating"] = round(sum(aa_lists["avg_rating"]) / len(aa_lists["avg_rating"]), 2)

# ======== PARTNER REPLACEMENT & ADJUSTMENT RATES ========
_repl_path = os.path.join(SCRIPT_DIR, "partner_replacement_rates.json")
if os.path.exists(_repl_path):
    PARTNER_REPL_RAW = json.loads(open(_repl_path).read())
    partner_repl_by_name = defaultdict(dict)
    for row in PARTNER_REPL_RAW:
        gn = row["group_name"]
        period = row["period"] + " 00:00:00"
        partner_repl_by_name[gn][period] = row

# ======== NEW PARTNERS WEEKLY FINANCIAL DATA ========
NEW_FIN_RAW = json.loads(open(os.path.join(SCRIPT_DIR, "new_partners_fin_raw.json")).read())
new_fin_by_partner = {}
for row in NEW_FIN_RAW:
    gn = row["group_name"]
    if gn not in RELEVANT_PARTNERS:
        continue
    if gn not in new_fin_by_partner:
        new_fin_by_partner[gn] = []
    new_fin_by_partner[gn].append({
        "period": ts_to_period(row["period"]),
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

# ======== ALL PARTNERS WEEKLY OPERATIONAL DATA ========
OPS_RAW = json.loads(open(os.path.join(SCRIPT_DIR, "all_partners_ops_raw.json")).read())
ops_by_partner = {}
for row in OPS_RAW:
    gn = row["group_name"]
    if gn not in RELEVANT_PARTNERS:
        continue
    if gn not in ops_by_partner:
        ops_by_partner[gn] = []
    ops_by_partner[gn].append({
        "period": ts_to_period(row["period"]),
        "delivered_orders": 0,
        "active_stores": int(row["active_stores"]),
        "honey_order_rate": round(float(row["honey_order_rate"]), 2),
        "bad_order_rate": round(float(row["bad_order_rate"]), 2),
        "late_delivery_rate": round(float(row["late_delivery_rate"]), 2),
        "late_pickup_rate": round(float(row["late_pickup_rate"]), 2),
        "avg_delivery_minutes": float(row["avg_delivery_minutes"]) if row["avg_delivery_minutes"] else 0,
        "replacement_rate": 0,
        "adjustment_rate": 0
    })

# ======== ALL PARTNERS WEEKLY CAMPAIGN DATA ========
CAMP_RAW = json.loads(open(os.path.join(SCRIPT_DIR, "all_partners_camp_raw.json")).read())
camp_by_partner = {}
for row in CAMP_RAW:
    gn = row["group_name"]
    if gn not in RELEVANT_PARTNERS:
        continue
    if gn not in camp_by_partner:
        camp_by_partner[gn] = []
    camp_by_partner[gn].append({
        "period": ts_to_period(row["period"]),
        "campaigns_discount_eur": float(row["campaigns_discount_eur"]),
        "bolt_spend_eur": float(row["bolt_spend_eur"]),
        "merchant_spend_eur": float(row["merchant_spend_eur"]),
        "gmv_eur": float(row["gmv_eur"])
    })

# ======== GMV BY PARTNER (weekly, for pie chart) ========
gmv_by_partner_weekly = []
for row in CAMP_RAW:
    gn = row["group_name"]
    gmv_by_partner_weekly.append({
        "period": ts_to_period(row["period"]),
        "group_name": gn,
        "gmv_eur": float(row["gmv_eur"]),
        "orders": 0
    })

# ======== PARTNER CP MARGINS (from fact_provider_weekly) ========
# These are pre-computed and stored inline from Databricks queries
PARTNER_CP_WEEKLY_RAW = [
    # Jan 26
    {"period":"2026-01-26","group_name":"BEER MARKET","cp_margin_pct":-4.56,"cp_l2_margin_pct":-8.36},
    {"period":"2026-01-26","group_name":"BEERLAND","cp_margin_pct":-0.85,"cp_l2_margin_pct":-0.85},
    {"period":"2026-01-26","group_name":"BEERLAND K","cp_margin_pct":-0.85,"cp_l2_margin_pct":-2.44},
    {"period":"2026-01-26","group_name":"CAFE RYNOK","cp_margin_pct":-17.2,"cp_l2_margin_pct":-22.92},
    {"period":"2026-01-26","group_name":"CHILL TIME","cp_margin_pct":-8.8,"cp_l2_margin_pct":-9.5},
    {"period":"2026-01-26","group_name":"DIMPYVA","cp_margin_pct":-9.28,"cp_l2_margin_pct":-11.74},
    {"period":"2026-01-26","group_name":"FLOWER SHOP","cp_margin_pct":4.95,"cp_l2_margin_pct":2.68},
    {"period":"2026-01-26","group_name":"HOP HEY","cp_margin_pct":-8.42,"cp_l2_margin_pct":-11.24},
    {"period":"2026-01-26","group_name":"KOPIYKA","cp_margin_pct":-12.49,"cp_l2_margin_pct":-15.73},
    {"period":"2026-01-26","group_name":"LEPRUKON","cp_margin_pct":-13.11,"cp_l2_margin_pct":-14.61},
    {"period":"2026-01-26","group_name":"MAXBEER","cp_margin_pct":0.44,"cp_l2_margin_pct":-0.05},
    {"period":"2026-01-26","group_name":"MAXBEER GROUP","cp_margin_pct":1.2,"cp_l2_margin_pct":-0.64},
    {"period":"2026-01-26","group_name":"PYVNA BORODA","cp_margin_pct":-2.12,"cp_l2_margin_pct":-4.18},
    {"period":"2026-01-26","group_name":"REMESLO BREWERY","cp_margin_pct":7.34,"cp_l2_margin_pct":4.76},
    {"period":"2026-01-26","group_name":"RUKAVYCHKA","cp_margin_pct":-31.38,"cp_l2_margin_pct":-39.41},
    {"period":"2026-01-26","group_name":"SPRAGA","cp_margin_pct":-3.59,"cp_l2_margin_pct":-6.15},
    {"period":"2026-01-26","group_name":"TAISTRA","cp_margin_pct":-19.98,"cp_l2_margin_pct":-26.99},
    {"period":"2026-01-26","group_name":"TOCHKA","cp_margin_pct":-1.53,"cp_l2_margin_pct":-1.75},
    {"period":"2026-01-26","group_name":"WINETIME","cp_margin_pct":4.13,"cp_l2_margin_pct":4.13},
    # Feb 2 - May 11 partner CP data
    {"period":"2026-02-02","group_name":"BEER MARKET","cp_margin_pct":-9.21,"cp_l2_margin_pct":-12.24},
    {"period":"2026-02-02","group_name":"BEERLAND","cp_margin_pct":3.14,"cp_l2_margin_pct":3.14},
    {"period":"2026-02-02","group_name":"BEERLAND K","cp_margin_pct":-2.92,"cp_l2_margin_pct":-5.79},
    {"period":"2026-02-02","group_name":"CAFE RYNOK","cp_margin_pct":-16.92,"cp_l2_margin_pct":-22.86},
    {"period":"2026-02-02","group_name":"CHILL TIME","cp_margin_pct":-6.48,"cp_l2_margin_pct":-8.12},
    {"period":"2026-02-02","group_name":"DIMPYVA","cp_margin_pct":-9.97,"cp_l2_margin_pct":-11.41},
    {"period":"2026-02-02","group_name":"FLOWER SHOP","cp_margin_pct":4.92,"cp_l2_margin_pct":-0.3},
    {"period":"2026-02-02","group_name":"HOP HEY","cp_margin_pct":-9.43,"cp_l2_margin_pct":-11.67},
    {"period":"2026-02-02","group_name":"KOPIYKA","cp_margin_pct":-14.93,"cp_l2_margin_pct":-19.46},
    {"period":"2026-02-02","group_name":"LEPRUKON","cp_margin_pct":-16.11,"cp_l2_margin_pct":-19.46},
    {"period":"2026-02-02","group_name":"LOKO","cp_margin_pct":-10.18,"cp_l2_margin_pct":-10.18},
    {"period":"2026-02-02","group_name":"MAXBEER","cp_margin_pct":2.71,"cp_l2_margin_pct":-3.47},
    {"period":"2026-02-02","group_name":"MAXBEER GROUP","cp_margin_pct":-6.76,"cp_l2_margin_pct":-8.17},
    {"period":"2026-02-02","group_name":"PYVNA BORODA","cp_margin_pct":-4.07,"cp_l2_margin_pct":-5.21},
    {"period":"2026-02-02","group_name":"REMESLO BREWERY","cp_margin_pct":6.28,"cp_l2_margin_pct":2.43},
    {"period":"2026-02-02","group_name":"RUKAVYCHKA","cp_margin_pct":-29.76,"cp_l2_margin_pct":-37.76},
    {"period":"2026-02-02","group_name":"SPRAGA","cp_margin_pct":-3.99,"cp_l2_margin_pct":-13.98},
    {"period":"2026-02-02","group_name":"TAISTRA","cp_margin_pct":-19.66,"cp_l2_margin_pct":-25.83},
    {"period":"2026-02-02","group_name":"TOCHKA","cp_margin_pct":-3.13,"cp_l2_margin_pct":-3.39},
    {"period":"2026-02-02","group_name":"WINETIME","cp_margin_pct":-1.91,"cp_l2_margin_pct":-2.19},
    {"period":"2026-02-09","group_name":"BEER MARKET","cp_margin_pct":-7.51,"cp_l2_margin_pct":-7.51},
    {"period":"2026-02-09","group_name":"BEERLAND","cp_margin_pct":12.28,"cp_l2_margin_pct":12.28},
    {"period":"2026-02-09","group_name":"BEERLAND K","cp_margin_pct":-1.53,"cp_l2_margin_pct":-3.22},
    {"period":"2026-02-09","group_name":"CAFE RYNOK","cp_margin_pct":-15.03,"cp_l2_margin_pct":-20.51},
    {"period":"2026-02-09","group_name":"CHILL TIME","cp_margin_pct":-5.82,"cp_l2_margin_pct":-6.71},
    {"period":"2026-02-09","group_name":"DIMPYVA","cp_margin_pct":-8.58,"cp_l2_margin_pct":-9.5},
    {"period":"2026-02-09","group_name":"FLOWER SHOP","cp_margin_pct":-1.53,"cp_l2_margin_pct":-7.46},
    {"period":"2026-02-09","group_name":"HOP HEY","cp_margin_pct":-10.45,"cp_l2_margin_pct":-11.96},
    {"period":"2026-02-09","group_name":"KOPIYKA","cp_margin_pct":-17.66,"cp_l2_margin_pct":-20.4},
    {"period":"2026-02-09","group_name":"LEPRUKON","cp_margin_pct":-22.45,"cp_l2_margin_pct":-25.5},
    {"period":"2026-02-09","group_name":"LOKO","cp_margin_pct":-9.99,"cp_l2_margin_pct":-9.99},
    {"period":"2026-02-09","group_name":"MAXBEER","cp_margin_pct":-0.56,"cp_l2_margin_pct":-6.8},
    {"period":"2026-02-09","group_name":"MAXBEER GROUP","cp_margin_pct":-4.21,"cp_l2_margin_pct":-8.96},
    {"period":"2026-02-09","group_name":"PYVNA BORODA","cp_margin_pct":-2.28,"cp_l2_margin_pct":-4.23},
    {"period":"2026-02-09","group_name":"REMESLO BREWERY","cp_margin_pct":7.61,"cp_l2_margin_pct":4.73},
    {"period":"2026-02-09","group_name":"RUKAVYCHKA","cp_margin_pct":-26.03,"cp_l2_margin_pct":-34.23},
    {"period":"2026-02-09","group_name":"SPRAGA","cp_margin_pct":-4.64,"cp_l2_margin_pct":-23.79},
    {"period":"2026-02-09","group_name":"TAISTRA","cp_margin_pct":-22.08,"cp_l2_margin_pct":-28.58},
    {"period":"2026-02-09","group_name":"TOCHKA","cp_margin_pct":-1.85,"cp_l2_margin_pct":-3.14},
    {"period":"2026-02-09","group_name":"WINETIME","cp_margin_pct":-2.41,"cp_l2_margin_pct":-2.59},
    {"period":"2026-02-16","group_name":"BEER MARKET","cp_margin_pct":-7.48,"cp_l2_margin_pct":-7.51},
    {"period":"2026-02-16","group_name":"BEERLAND","cp_margin_pct":-0.48,"cp_l2_margin_pct":-0.48},
    {"period":"2026-02-16","group_name":"BEERLAND K","cp_margin_pct":-1.29,"cp_l2_margin_pct":-3.14},
    {"period":"2026-02-16","group_name":"CAFE RYNOK","cp_margin_pct":-13.53,"cp_l2_margin_pct":-14.66},
    {"period":"2026-02-16","group_name":"CHILL TIME","cp_margin_pct":-7.24,"cp_l2_margin_pct":-7.76},
    {"period":"2026-02-16","group_name":"DIMPYVA","cp_margin_pct":-7.2,"cp_l2_margin_pct":-9.28},
    {"period":"2026-02-16","group_name":"FLOWER SHOP","cp_margin_pct":3.87,"cp_l2_margin_pct":-3.89},
    {"period":"2026-02-16","group_name":"HOP HEY","cp_margin_pct":-9.18,"cp_l2_margin_pct":-10.83},
    {"period":"2026-02-16","group_name":"KOPIYKA","cp_margin_pct":-16.97,"cp_l2_margin_pct":-22.36},
    {"period":"2026-02-16","group_name":"LEPRUKON","cp_margin_pct":-12.76,"cp_l2_margin_pct":-25.05},
    {"period":"2026-02-16","group_name":"LOKO","cp_margin_pct":-8.29,"cp_l2_margin_pct":-8.29},
    {"period":"2026-02-16","group_name":"MAXBEER","cp_margin_pct":2.18,"cp_l2_margin_pct":-3.18},
    {"period":"2026-02-16","group_name":"MAXBEER GROUP","cp_margin_pct":-1.16,"cp_l2_margin_pct":-7.74},
    {"period":"2026-02-16","group_name":"PYVNA BORODA","cp_margin_pct":-4.15,"cp_l2_margin_pct":-5.67},
    {"period":"2026-02-16","group_name":"REMESLO BREWERY","cp_margin_pct":7.81,"cp_l2_margin_pct":6.21},
    {"period":"2026-02-16","group_name":"RUKAVYCHKA","cp_margin_pct":-23.2,"cp_l2_margin_pct":-23.25},
    {"period":"2026-02-16","group_name":"SPRAGA","cp_margin_pct":-6.07,"cp_l2_margin_pct":-19.74},
    {"period":"2026-02-16","group_name":"TAISTRA","cp_margin_pct":-18.49,"cp_l2_margin_pct":-18.92},
    {"period":"2026-02-16","group_name":"TOCHKA","cp_margin_pct":-4.79,"cp_l2_margin_pct":-5.81},
    {"period":"2026-02-16","group_name":"WINETIME","cp_margin_pct":-2.21,"cp_l2_margin_pct":-2.21},
    {"period":"2026-02-23","group_name":"BEER MARKET","cp_margin_pct":-6.9,"cp_l2_margin_pct":-8.98},
    {"period":"2026-02-23","group_name":"BEERLAND","cp_margin_pct":4.58,"cp_l2_margin_pct":4.58},
    {"period":"2026-02-23","group_name":"BEERLAND K","cp_margin_pct":-3.21,"cp_l2_margin_pct":-4.03},
    {"period":"2026-02-23","group_name":"CAFE RYNOK","cp_margin_pct":-9.42,"cp_l2_margin_pct":-11.62},
    {"period":"2026-02-23","group_name":"CHILL TIME","cp_margin_pct":-5.59,"cp_l2_margin_pct":-6.7},
    {"period":"2026-02-23","group_name":"DIMPYVA","cp_margin_pct":-9.79,"cp_l2_margin_pct":-11.6},
    {"period":"2026-02-23","group_name":"FLOWER SHOP","cp_margin_pct":3.61,"cp_l2_margin_pct":-0.37},
    {"period":"2026-02-23","group_name":"HOP HEY","cp_margin_pct":-10.77,"cp_l2_margin_pct":-14.02},
    {"period":"2026-02-23","group_name":"KOPIYKA","cp_margin_pct":-15.46,"cp_l2_margin_pct":-18.64},
    {"period":"2026-02-23","group_name":"LEPRUKON","cp_margin_pct":-16.87,"cp_l2_margin_pct":-32.61},
    {"period":"2026-02-23","group_name":"LOKO","cp_margin_pct":-10.33,"cp_l2_margin_pct":-10.33},
    {"period":"2026-02-23","group_name":"MAXBEER","cp_margin_pct":2.9,"cp_l2_margin_pct":-0.89},
    {"period":"2026-02-23","group_name":"MAXBEER GROUP","cp_margin_pct":-1.85,"cp_l2_margin_pct":-4.4},
    {"period":"2026-02-23","group_name":"PYVNA BORODA","cp_margin_pct":-3.38,"cp_l2_margin_pct":-3.78},
    {"period":"2026-02-23","group_name":"REMESLO BREWERY","cp_margin_pct":8.3,"cp_l2_margin_pct":6.35},
    {"period":"2026-02-23","group_name":"RUKAVYCHKA","cp_margin_pct":-18.46,"cp_l2_margin_pct":-21.98},
    {"period":"2026-02-23","group_name":"SPRAGA","cp_margin_pct":-8.65,"cp_l2_margin_pct":-23.65},
    {"period":"2026-02-23","group_name":"TAISTRA","cp_margin_pct":-20.91,"cp_l2_margin_pct":-23.73},
    {"period":"2026-02-23","group_name":"TOCHKA","cp_margin_pct":-4.25,"cp_l2_margin_pct":-4.77},
    {"period":"2026-02-23","group_name":"WINETIME","cp_margin_pct":-0.76,"cp_l2_margin_pct":-0.76},
    {"period":"2026-03-02","group_name":"BEER MARKET","cp_margin_pct":-10.54,"cp_l2_margin_pct":-14.24},
    {"period":"2026-03-02","group_name":"BEERLAND","cp_margin_pct":-5.6,"cp_l2_margin_pct":-5.6},
    {"period":"2026-03-02","group_name":"BEERLAND K","cp_margin_pct":-5.23,"cp_l2_margin_pct":-7.4},
    {"period":"2026-03-02","group_name":"CAFE RYNOK","cp_margin_pct":-12.97,"cp_l2_margin_pct":-18.42},
    {"period":"2026-03-02","group_name":"CHILL TIME","cp_margin_pct":-11.01,"cp_l2_margin_pct":-12.25},
    {"period":"2026-03-02","group_name":"DIMPYVA","cp_margin_pct":-12.27,"cp_l2_margin_pct":-14.6},
    {"period":"2026-03-02","group_name":"FLOWER SHOP","cp_margin_pct":-2.93,"cp_l2_margin_pct":-11.12},
    {"period":"2026-03-02","group_name":"HOP HEY","cp_margin_pct":-16.78,"cp_l2_margin_pct":-21.61},
    {"period":"2026-03-02","group_name":"KOPIYKA","cp_margin_pct":-23.8,"cp_l2_margin_pct":-30.2},
    {"period":"2026-03-02","group_name":"LEPRUKON","cp_margin_pct":-18.24,"cp_l2_margin_pct":-40.46},
    {"period":"2026-03-02","group_name":"LOKO","cp_margin_pct":-17.9,"cp_l2_margin_pct":-17.9},
    {"period":"2026-03-02","group_name":"MAXBEER","cp_margin_pct":-3.63,"cp_l2_margin_pct":-7.8},
    {"period":"2026-03-02","group_name":"MAXBEER GROUP","cp_margin_pct":-6.5,"cp_l2_margin_pct":-9.31},
    {"period":"2026-03-02","group_name":"NO TABOO","cp_margin_pct":-3.91,"cp_l2_margin_pct":-3.91},
    {"period":"2026-03-02","group_name":"PYVNA BORODA","cp_margin_pct":-9.39,"cp_l2_margin_pct":-10.78},
    {"period":"2026-03-02","group_name":"REMESLO BREWERY","cp_margin_pct":3.3,"cp_l2_margin_pct":0.2},
    {"period":"2026-03-02","group_name":"RUKAVYCHKA","cp_margin_pct":-24.26,"cp_l2_margin_pct":-31.98},
    {"period":"2026-03-02","group_name":"SPRAGA","cp_margin_pct":-10.18,"cp_l2_margin_pct":-28.99},
    {"period":"2026-03-02","group_name":"TAISTRA","cp_margin_pct":-23.74,"cp_l2_margin_pct":-30.1},
    {"period":"2026-03-02","group_name":"TOCHKA","cp_margin_pct":-9.03,"cp_l2_margin_pct":-10.29},
    {"period":"2026-03-02","group_name":"WINETIME","cp_margin_pct":-9.56,"cp_l2_margin_pct":-13.87},
    {"period":"2026-03-09","group_name":"BEER MARKET","cp_margin_pct":-9.09,"cp_l2_margin_pct":-12.09},
    {"period":"2026-03-09","group_name":"BEERLAND","cp_margin_pct":3.73,"cp_l2_margin_pct":3.73},
    {"period":"2026-03-09","group_name":"BEERLAND K","cp_margin_pct":-2.45,"cp_l2_margin_pct":-5.3},
    {"period":"2026-03-09","group_name":"CAFE RYNOK","cp_margin_pct":-12.07,"cp_l2_margin_pct":-15.85},
    {"period":"2026-03-09","group_name":"CHILL TIME","cp_margin_pct":-11.91,"cp_l2_margin_pct":-13.29},
    {"period":"2026-03-09","group_name":"DIMPYVA","cp_margin_pct":-13.26,"cp_l2_margin_pct":-14.68},
    {"period":"2026-03-09","group_name":"FLOWER SHOP","cp_margin_pct":-2.11,"cp_l2_margin_pct":-10.57},
    {"period":"2026-03-09","group_name":"HOP HEY","cp_margin_pct":-14.15,"cp_l2_margin_pct":-18.18},
    {"period":"2026-03-09","group_name":"KOPIYKA","cp_margin_pct":-23.42,"cp_l2_margin_pct":-29.43},
    {"period":"2026-03-09","group_name":"LEPRUKON","cp_margin_pct":-18.27,"cp_l2_margin_pct":-38.2},
    {"period":"2026-03-09","group_name":"LOKO","cp_margin_pct":-17.06,"cp_l2_margin_pct":-17.96},
    {"period":"2026-03-09","group_name":"MAXBEER","cp_margin_pct":-3.75,"cp_l2_margin_pct":-6.84},
    {"period":"2026-03-09","group_name":"MAXBEER GROUP","cp_margin_pct":-5.85,"cp_l2_margin_pct":-11.47},
    {"period":"2026-03-09","group_name":"NO TABOO","cp_margin_pct":-12.93,"cp_l2_margin_pct":-12.93},
    {"period":"2026-03-09","group_name":"PYVNA BORODA","cp_margin_pct":-7.24,"cp_l2_margin_pct":-8.26},
    {"period":"2026-03-09","group_name":"REMESLO BREWERY","cp_margin_pct":3.49,"cp_l2_margin_pct":0.88},
    {"period":"2026-03-09","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-19.95,"cp_l2_margin_pct":-19.95},
    {"period":"2026-03-09","group_name":"RUKAVYCHKA","cp_margin_pct":-24.96,"cp_l2_margin_pct":-29.88},
    {"period":"2026-03-09","group_name":"SPRAGA","cp_margin_pct":-11.99,"cp_l2_margin_pct":-33.41},
    {"period":"2026-03-09","group_name":"TAISTRA","cp_margin_pct":-23.71,"cp_l2_margin_pct":-28.67},
    {"period":"2026-03-09","group_name":"TOCHKA","cp_margin_pct":-9.46,"cp_l2_margin_pct":-10.27},
    {"period":"2026-03-09","group_name":"WINETIME","cp_margin_pct":-6.22,"cp_l2_margin_pct":-8.36},
    {"period":"2026-03-16","group_name":"BEER MARKET","cp_margin_pct":-8.63,"cp_l2_margin_pct":-12.27},
    {"period":"2026-03-16","group_name":"BEERLAND","cp_margin_pct":3.11,"cp_l2_margin_pct":3.11},
    {"period":"2026-03-16","group_name":"BEERLAND K","cp_margin_pct":-1.35,"cp_l2_margin_pct":-3.35},
    {"period":"2026-03-16","group_name":"CAFE RYNOK","cp_margin_pct":-11.43,"cp_l2_margin_pct":-14.58},
    {"period":"2026-03-16","group_name":"CHILL TIME","cp_margin_pct":-13.85,"cp_l2_margin_pct":-16.07},
    {"period":"2026-03-16","group_name":"DIMPYVA","cp_margin_pct":-13.61,"cp_l2_margin_pct":-15.02},
    {"period":"2026-03-16","group_name":"FLOWER SHOP","cp_margin_pct":-4.84,"cp_l2_margin_pct":-11.96},
    {"period":"2026-03-16","group_name":"HOP HEY","cp_margin_pct":-12.37,"cp_l2_margin_pct":-16.54},
    {"period":"2026-03-16","group_name":"KOPIYKA","cp_margin_pct":-23.03,"cp_l2_margin_pct":-27.75},
    {"period":"2026-03-16","group_name":"LEPRUKON","cp_margin_pct":-19.07,"cp_l2_margin_pct":-36.06},
    {"period":"2026-03-16","group_name":"LOKO","cp_margin_pct":-17.05,"cp_l2_margin_pct":-17.16},
    {"period":"2026-03-16","group_name":"MAXBEER","cp_margin_pct":-2.9,"cp_l2_margin_pct":-4.4},
    {"period":"2026-03-16","group_name":"MAXBEER GROUP","cp_margin_pct":-7.41,"cp_l2_margin_pct":-11.75},
    {"period":"2026-03-16","group_name":"NO TABOO","cp_margin_pct":-22.37,"cp_l2_margin_pct":-22.37},
    {"period":"2026-03-16","group_name":"PYVNA BORODA","cp_margin_pct":-8.12,"cp_l2_margin_pct":-9.75},
    {"period":"2026-03-16","group_name":"REMESLO BREWERY","cp_margin_pct":4.89,"cp_l2_margin_pct":1.92},
    {"period":"2026-03-16","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-70.89,"cp_l2_margin_pct":-70.89},
    {"period":"2026-03-16","group_name":"RUKAVYCHKA","cp_margin_pct":-23.81,"cp_l2_margin_pct":-28.29},
    {"period":"2026-03-16","group_name":"SPRAGA","cp_margin_pct":-11.18,"cp_l2_margin_pct":-27.11},
    {"period":"2026-03-16","group_name":"TAISTRA","cp_margin_pct":-24.07,"cp_l2_margin_pct":-29.62},
    {"period":"2026-03-16","group_name":"TOCHKA","cp_margin_pct":-7.46,"cp_l2_margin_pct":-8.13},
    {"period":"2026-03-16","group_name":"WINETIME","cp_margin_pct":-3.57,"cp_l2_margin_pct":-4.35},
    {"period":"2026-03-23","group_name":"BEER MARKET","cp_margin_pct":-9.34,"cp_l2_margin_pct":-13.53},
    {"period":"2026-03-23","group_name":"BEERLAND","cp_margin_pct":-2.49,"cp_l2_margin_pct":-2.49},
    {"period":"2026-03-23","group_name":"BEERLAND K","cp_margin_pct":-0.79,"cp_l2_margin_pct":-1.77},
    {"period":"2026-03-23","group_name":"CAFE RYNOK","cp_margin_pct":-11.32,"cp_l2_margin_pct":-14.83},
    {"period":"2026-03-23","group_name":"CHILL TIME","cp_margin_pct":-14.96,"cp_l2_margin_pct":-15.81},
    {"period":"2026-03-23","group_name":"DIMPYVA","cp_margin_pct":-16.86,"cp_l2_margin_pct":-17.93},
    {"period":"2026-03-23","group_name":"FLOWER SHOP","cp_margin_pct":0.38,"cp_l2_margin_pct":-3.94},
    {"period":"2026-03-23","group_name":"HOP HEY","cp_margin_pct":-13.32,"cp_l2_margin_pct":-17.4},
    {"period":"2026-03-23","group_name":"KOPIYKA","cp_margin_pct":-22.62,"cp_l2_margin_pct":-29.17},
    {"period":"2026-03-23","group_name":"LEPRUKON","cp_margin_pct":-18.66,"cp_l2_margin_pct":-30.68},
    {"period":"2026-03-23","group_name":"LOKO","cp_margin_pct":-16.2,"cp_l2_margin_pct":-16.61},
    {"period":"2026-03-23","group_name":"MAXBEER","cp_margin_pct":-3.9,"cp_l2_margin_pct":-6.82},
    {"period":"2026-03-23","group_name":"MAXBEER GROUP","cp_margin_pct":-10.36,"cp_l2_margin_pct":-13.08},
    {"period":"2026-03-23","group_name":"NO TABOO","cp_margin_pct":-0.32,"cp_l2_margin_pct":-0.32},
    {"period":"2026-03-23","group_name":"PYVNA BORODA","cp_margin_pct":-10.55,"cp_l2_margin_pct":-11.95},
    {"period":"2026-03-23","group_name":"REMESLO BREWERY","cp_margin_pct":3.72,"cp_l2_margin_pct":2.45},
    {"period":"2026-03-23","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-22.75,"cp_l2_margin_pct":-22.75},
    {"period":"2026-03-23","group_name":"RUKAVYCHKA","cp_margin_pct":-24.11,"cp_l2_margin_pct":-29.84},
    {"period":"2026-03-23","group_name":"SPAR","cp_margin_pct":-25.71,"cp_l2_margin_pct":-25.71},
    {"period":"2026-03-23","group_name":"SPRAGA","cp_margin_pct":-9.49,"cp_l2_margin_pct":-22.78},
    {"period":"2026-03-23","group_name":"TAISTRA","cp_margin_pct":-23.05,"cp_l2_margin_pct":-28.92},
    {"period":"2026-03-23","group_name":"TOCHKA","cp_margin_pct":-10.23,"cp_l2_margin_pct":-10.75},
    {"period":"2026-03-23","group_name":"WINETIME","cp_margin_pct":-5.98,"cp_l2_margin_pct":-6.01},
    {"period":"2026-03-30","group_name":"BEER MARKET","cp_margin_pct":-2.29,"cp_l2_margin_pct":-4.68},
    {"period":"2026-03-30","group_name":"BEERLAND","cp_margin_pct":-4.73,"cp_l2_margin_pct":-4.73},
    {"period":"2026-03-30","group_name":"BEERLAND K","cp_margin_pct":5.58,"cp_l2_margin_pct":4.44},
    {"period":"2026-03-30","group_name":"CAFE RYNOK","cp_margin_pct":-6.5,"cp_l2_margin_pct":-10.49},
    {"period":"2026-03-30","group_name":"CHILL TIME","cp_margin_pct":-5.81,"cp_l2_margin_pct":-5.81},
    {"period":"2026-03-30","group_name":"DIMPYVA","cp_margin_pct":-10.07,"cp_l2_margin_pct":-11.56},
    {"period":"2026-03-30","group_name":"FLOWER SHOP","cp_margin_pct":8.24,"cp_l2_margin_pct":8.24},
    {"period":"2026-03-30","group_name":"HOP HEY","cp_margin_pct":-3.79,"cp_l2_margin_pct":-6.34},
    {"period":"2026-03-30","group_name":"KOPIYKA","cp_margin_pct":-13.24,"cp_l2_margin_pct":-15.8},
    {"period":"2026-03-30","group_name":"LEPRUKON","cp_margin_pct":-9.29,"cp_l2_margin_pct":-26.02},
    {"period":"2026-03-30","group_name":"LOKO","cp_margin_pct":-9.67,"cp_l2_margin_pct":-14.21},
    {"period":"2026-03-30","group_name":"MAXBEER","cp_margin_pct":2.42,"cp_l2_margin_pct":-0.96},
    {"period":"2026-03-30","group_name":"MAXBEER GROUP","cp_margin_pct":1.75,"cp_l2_margin_pct":-0.55},
    {"period":"2026-03-30","group_name":"NO TABOO","cp_margin_pct":6.58,"cp_l2_margin_pct":6.58},
    {"period":"2026-03-30","group_name":"PYVNA BORODA","cp_margin_pct":-2.27,"cp_l2_margin_pct":-3.89},
    {"period":"2026-03-30","group_name":"REMESLO BREWERY","cp_margin_pct":11.13,"cp_l2_margin_pct":9.56},
    {"period":"2026-03-30","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-30.19,"cp_l2_margin_pct":-43.96},
    {"period":"2026-03-30","group_name":"RUKAVYCHKA","cp_margin_pct":-14.86,"cp_l2_margin_pct":-18.0},
    {"period":"2026-03-30","group_name":"SPAR","cp_margin_pct":-8.18,"cp_l2_margin_pct":-8.18},
    {"period":"2026-03-30","group_name":"SPRAGA","cp_margin_pct":-2.18,"cp_l2_margin_pct":-13.28},
    {"period":"2026-03-30","group_name":"TAISTRA","cp_margin_pct":-13.95,"cp_l2_margin_pct":-16.07},
    {"period":"2026-03-30","group_name":"TOCHKA","cp_margin_pct":-1.52,"cp_l2_margin_pct":-2.65},
    {"period":"2026-03-30","group_name":"WINETIME","cp_margin_pct":3.9,"cp_l2_margin_pct":2.68},
    {"period":"2026-04-06","group_name":"BEER MARKET","cp_margin_pct":-0.46,"cp_l2_margin_pct":-3.45},
    {"period":"2026-04-06","group_name":"BEERLAND","cp_margin_pct":8.46,"cp_l2_margin_pct":8.46},
    {"period":"2026-04-06","group_name":"BEERLAND K","cp_margin_pct":8.28,"cp_l2_margin_pct":4.66},
    {"period":"2026-04-06","group_name":"CAFE RYNOK","cp_margin_pct":-2.11,"cp_l2_margin_pct":-4.0},
    {"period":"2026-04-06","group_name":"CHILL TIME","cp_margin_pct":-6.9,"cp_l2_margin_pct":-7.32},
    {"period":"2026-04-06","group_name":"DIMPYVA","cp_margin_pct":-9.25,"cp_l2_margin_pct":-10.93},
    {"period":"2026-04-06","group_name":"FLOWER SHOP","cp_margin_pct":-5.48,"cp_l2_margin_pct":-11.92},
    {"period":"2026-04-06","group_name":"HOP HEY","cp_margin_pct":-1.04,"cp_l2_margin_pct":-3.55},
    {"period":"2026-04-06","group_name":"KOPIYKA","cp_margin_pct":-9.06,"cp_l2_margin_pct":-12.2},
    {"period":"2026-04-06","group_name":"LEPRUKON","cp_margin_pct":-9.52,"cp_l2_margin_pct":-23.56},
    {"period":"2026-04-06","group_name":"LOKO","cp_margin_pct":-7.07,"cp_l2_margin_pct":-8.55},
    {"period":"2026-04-06","group_name":"MAXBEER","cp_margin_pct":4.08,"cp_l2_margin_pct":0.55},
    {"period":"2026-04-06","group_name":"MAXBEER GROUP","cp_margin_pct":7.93,"cp_l2_margin_pct":5.47},
    {"period":"2026-04-06","group_name":"PYVNA BORODA","cp_margin_pct":-0.71,"cp_l2_margin_pct":-2.03},
    {"period":"2026-04-06","group_name":"REMESLO BREWERY","cp_margin_pct":12.84,"cp_l2_margin_pct":9.3},
    {"period":"2026-04-06","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-9.17,"cp_l2_margin_pct":-15.53},
    {"period":"2026-04-06","group_name":"RUKAVYCHKA","cp_margin_pct":-9.4,"cp_l2_margin_pct":-12.74},
    {"period":"2026-04-06","group_name":"SPRAGA","cp_margin_pct":-1.02,"cp_l2_margin_pct":-12.22},
    {"period":"2026-04-06","group_name":"TAISTRA","cp_margin_pct":-12.64,"cp_l2_margin_pct":-15.65},
    {"period":"2026-04-06","group_name":"TOCHKA","cp_margin_pct":-2.24,"cp_l2_margin_pct":-3.62},
    {"period":"2026-04-06","group_name":"WINETIME","cp_margin_pct":4.37,"cp_l2_margin_pct":3.47},
    {"period":"2026-04-13","group_name":"BEER MARKET","cp_margin_pct":0.04,"cp_l2_margin_pct":-3.13},
    {"period":"2026-04-13","group_name":"BEERLAND","cp_margin_pct":15.99,"cp_l2_margin_pct":15.99},
    {"period":"2026-04-13","group_name":"BEERLAND K","cp_margin_pct":9.52,"cp_l2_margin_pct":8.23},
    {"period":"2026-04-13","group_name":"CAFE RYNOK","cp_margin_pct":-2.54,"cp_l2_margin_pct":-4.52},
    {"period":"2026-04-13","group_name":"CHILL TIME","cp_margin_pct":-3.53,"cp_l2_margin_pct":-4.8},
    {"period":"2026-04-13","group_name":"DIMPYVA","cp_margin_pct":-6.54,"cp_l2_margin_pct":-9.09},
    {"period":"2026-04-13","group_name":"FLOWER SHOP","cp_margin_pct":9.81,"cp_l2_margin_pct":5.17},
    {"period":"2026-04-13","group_name":"HOP HEY","cp_margin_pct":0.42,"cp_l2_margin_pct":-1.51},
    {"period":"2026-04-13","group_name":"KOPIYKA","cp_margin_pct":-8.37,"cp_l2_margin_pct":-11.84},
    {"period":"2026-04-13","group_name":"LEPRUKON","cp_margin_pct":-8.65,"cp_l2_margin_pct":-24.76},
    {"period":"2026-04-13","group_name":"LOKO","cp_margin_pct":-7.13,"cp_l2_margin_pct":-7.14},
    {"period":"2026-04-13","group_name":"MAXBEER","cp_margin_pct":5.02,"cp_l2_margin_pct":2.73},
    {"period":"2026-04-13","group_name":"MAXBEER GROUP","cp_margin_pct":6.98,"cp_l2_margin_pct":5.02},
    {"period":"2026-04-13","group_name":"NO TABOO","cp_margin_pct":2.28,"cp_l2_margin_pct":2.28},
    {"period":"2026-04-13","group_name":"PYVNA BORODA","cp_margin_pct":-1.9,"cp_l2_margin_pct":-1.94},
    {"period":"2026-04-13","group_name":"REMESLO BREWERY","cp_margin_pct":13.04,"cp_l2_margin_pct":10.63},
    {"period":"2026-04-13","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-3.13,"cp_l2_margin_pct":-8.1},
    {"period":"2026-04-13","group_name":"RUKAVYCHKA","cp_margin_pct":-13.83,"cp_l2_margin_pct":-16.77},
    {"period":"2026-04-13","group_name":"SPRAGA","cp_margin_pct":-1.11,"cp_l2_margin_pct":-13.33},
    {"period":"2026-04-13","group_name":"TAISTRA","cp_margin_pct":-12.33,"cp_l2_margin_pct":-15.65},
    {"period":"2026-04-13","group_name":"TOCHKA","cp_margin_pct":-2.12,"cp_l2_margin_pct":-2.93},
    {"period":"2026-04-13","group_name":"WINETIME","cp_margin_pct":3.62,"cp_l2_margin_pct":2.7},
    {"period":"2026-04-20","group_name":"BEER MARKET","cp_margin_pct":0.02,"cp_l2_margin_pct":-3.14},
    {"period":"2026-04-20","group_name":"BEERLAND","cp_margin_pct":13.21,"cp_l2_margin_pct":13.21},
    {"period":"2026-04-20","group_name":"BEERLAND K","cp_margin_pct":9.98,"cp_l2_margin_pct":9.3},
    {"period":"2026-04-20","group_name":"CAFE RYNOK","cp_margin_pct":-2.42,"cp_l2_margin_pct":-4.59},
    {"period":"2026-04-20","group_name":"CHILL TIME","cp_margin_pct":-0.54,"cp_l2_margin_pct":-1.05},
    {"period":"2026-04-20","group_name":"DIMPYVA","cp_margin_pct":-4.1,"cp_l2_margin_pct":-4.74},
    {"period":"2026-04-20","group_name":"FLOWER SHOP","cp_margin_pct":10.36,"cp_l2_margin_pct":10.36},
    {"period":"2026-04-20","group_name":"HOP HEY","cp_margin_pct":-0.87,"cp_l2_margin_pct":-3.12},
    {"period":"2026-04-20","group_name":"KOPIYKA","cp_margin_pct":-9.36,"cp_l2_margin_pct":-12.75},
    {"period":"2026-04-20","group_name":"LEPRUKON","cp_margin_pct":-7.25,"cp_l2_margin_pct":-21.49},
    {"period":"2026-04-20","group_name":"LOKO","cp_margin_pct":-7.09,"cp_l2_margin_pct":-13.91},
    {"period":"2026-04-20","group_name":"MAXBEER","cp_margin_pct":6.17,"cp_l2_margin_pct":4.34},
    {"period":"2026-04-20","group_name":"MAXBEER GROUP","cp_margin_pct":8.17,"cp_l2_margin_pct":4.37},
    {"period":"2026-04-20","group_name":"NO TABOO","cp_margin_pct":3.16,"cp_l2_margin_pct":3.16},
    {"period":"2026-04-20","group_name":"PYVNA BORODA","cp_margin_pct":0.43,"cp_l2_margin_pct":-0.3},
    {"period":"2026-04-20","group_name":"REMESLO BREWERY","cp_margin_pct":14.09,"cp_l2_margin_pct":13.05},
    {"period":"2026-04-20","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-5.5,"cp_l2_margin_pct":-11.56},
    {"period":"2026-04-20","group_name":"RUKAVYCHKA","cp_margin_pct":-17.12,"cp_l2_margin_pct":-19.96},
    {"period":"2026-04-20","group_name":"SPRAGA","cp_margin_pct":-2.42,"cp_l2_margin_pct":-12.82},
    {"period":"2026-04-20","group_name":"TAISTRA","cp_margin_pct":-11.0,"cp_l2_margin_pct":-13.82},
    {"period":"2026-04-20","group_name":"TOCHKA","cp_margin_pct":1.57,"cp_l2_margin_pct":0.36},
    {"period":"2026-04-20","group_name":"WINETIME","cp_margin_pct":5.87,"cp_l2_margin_pct":4.79},
    {"period":"2026-04-27","group_name":"BEER MARKET","cp_margin_pct":-0.32,"cp_l2_margin_pct":-3.87},
    {"period":"2026-04-27","group_name":"BEERLAND","cp_margin_pct":21.28,"cp_l2_margin_pct":21.28},
    {"period":"2026-04-27","group_name":"BEERLAND K","cp_margin_pct":7.98,"cp_l2_margin_pct":7.06},
    {"period":"2026-04-27","group_name":"CAFE RYNOK","cp_margin_pct":-3.11,"cp_l2_margin_pct":-5.18},
    {"period":"2026-04-27","group_name":"CHILL TIME","cp_margin_pct":-5.24,"cp_l2_margin_pct":-5.24},
    {"period":"2026-04-27","group_name":"DIMPYVA","cp_margin_pct":-7.18,"cp_l2_margin_pct":-7.81},
    {"period":"2026-04-27","group_name":"FLOWER SHOP","cp_margin_pct":7.81,"cp_l2_margin_pct":7.81},
    {"period":"2026-04-27","group_name":"HOP HEY","cp_margin_pct":-0.31,"cp_l2_margin_pct":-2.85},
    {"period":"2026-04-27","group_name":"KOPIYKA","cp_margin_pct":-8.29,"cp_l2_margin_pct":-12.18},
    {"period":"2026-04-27","group_name":"LEPRUKON","cp_margin_pct":-10.21,"cp_l2_margin_pct":-20.95},
    {"period":"2026-04-27","group_name":"LOKO","cp_margin_pct":-7.42,"cp_l2_margin_pct":-13.81},
    {"period":"2026-04-27","group_name":"MAXBEER","cp_margin_pct":6.1,"cp_l2_margin_pct":1.82},
    {"period":"2026-04-27","group_name":"MAXBEER GROUP","cp_margin_pct":7.84,"cp_l2_margin_pct":4.93},
    {"period":"2026-04-27","group_name":"NO TABOO","cp_margin_pct":7.01,"cp_l2_margin_pct":7.01},
    {"period":"2026-04-27","group_name":"PYVNA BORODA","cp_margin_pct":1.78,"cp_l2_margin_pct":0.66},
    {"period":"2026-04-27","group_name":"REMESLO BREWERY","cp_margin_pct":14.82,"cp_l2_margin_pct":13.17},
    {"period":"2026-04-27","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-23.17,"cp_l2_margin_pct":-35.88},
    {"period":"2026-04-27","group_name":"RUKAVYCHKA","cp_margin_pct":-8.33,"cp_l2_margin_pct":-10.94},
    {"period":"2026-04-27","group_name":"SPRAGA","cp_margin_pct":0.95,"cp_l2_margin_pct":-8.76},
    {"period":"2026-04-27","group_name":"TAISTRA","cp_margin_pct":-8.76,"cp_l2_margin_pct":-11.85},
    {"period":"2026-04-27","group_name":"TOCHKA","cp_margin_pct":1.38,"cp_l2_margin_pct":-0.09},
    {"period":"2026-04-27","group_name":"VARUS","cp_margin_pct":-14.47,"cp_l2_margin_pct":-22.82},
    {"period":"2026-04-27","group_name":"WINETIME","cp_margin_pct":5.14,"cp_l2_margin_pct":2.17},
    {"period":"2026-05-04","group_name":"BEER MARKET","cp_margin_pct":0.82,"cp_l2_margin_pct":-3.07},
    {"period":"2026-05-04","group_name":"BEERLAND","cp_margin_pct":13.52,"cp_l2_margin_pct":13.52},
    {"period":"2026-05-04","group_name":"BEERLAND K","cp_margin_pct":8.98,"cp_l2_margin_pct":7.8},
    {"period":"2026-05-04","group_name":"CAFE RYNOK","cp_margin_pct":-3.47,"cp_l2_margin_pct":-5.34},
    {"period":"2026-05-04","group_name":"CHILL TIME","cp_margin_pct":-2.44,"cp_l2_margin_pct":-3.43},
    {"period":"2026-05-04","group_name":"DIMPYVA","cp_margin_pct":-4.94,"cp_l2_margin_pct":-6.85},
    {"period":"2026-05-04","group_name":"FLOWER SHOP","cp_margin_pct":9.61,"cp_l2_margin_pct":8.63},
    {"period":"2026-05-04","group_name":"HOP HEY","cp_margin_pct":2.46,"cp_l2_margin_pct":-0.27},
    {"period":"2026-05-04","group_name":"KOPIYKA","cp_margin_pct":-4.3,"cp_l2_margin_pct":-7.92},
    {"period":"2026-05-04","group_name":"LEPRUKON","cp_margin_pct":-11.39,"cp_l2_margin_pct":-20.37},
    {"period":"2026-05-04","group_name":"LOKO","cp_margin_pct":-7.16,"cp_l2_margin_pct":-7.26},
    {"period":"2026-05-04","group_name":"MAXBEER","cp_margin_pct":8.67,"cp_l2_margin_pct":5.81},
    {"period":"2026-05-04","group_name":"MAXBEER GROUP","cp_margin_pct":3.59,"cp_l2_margin_pct":1.68},
    {"period":"2026-05-04","group_name":"NO TABOO","cp_margin_pct":4.02,"cp_l2_margin_pct":4.02},
    {"period":"2026-05-04","group_name":"PYVNA BORODA","cp_margin_pct":0.59,"cp_l2_margin_pct":0.11},
    {"period":"2026-05-04","group_name":"REMESLO BREWERY","cp_margin_pct":14.69,"cp_l2_margin_pct":12.33},
    {"period":"2026-05-04","group_name":"RODYNNA KOVBASKA","cp_margin_pct":-4.71,"cp_l2_margin_pct":-18.88},
    {"period":"2026-05-04","group_name":"RUKAVYCHKA","cp_margin_pct":-7.11,"cp_l2_margin_pct":-10.3},
    {"period":"2026-05-04","group_name":"SPRAGA","cp_margin_pct":0.43,"cp_l2_margin_pct":-9.13},
    {"period":"2026-05-04","group_name":"TAISTRA","cp_margin_pct":-9.55,"cp_l2_margin_pct":-12.49},
    {"period":"2026-05-04","group_name":"TOCHKA","cp_margin_pct":3.08,"cp_l2_margin_pct":1.69},
    {"period":"2026-05-04","group_name":"VARUS","cp_margin_pct":-10.18,"cp_l2_margin_pct":-18.19},
    {"period":"2026-05-04","group_name":"WINETIME","cp_margin_pct":5.64,"cp_l2_margin_pct":3.91},
]

# Build partner CP margin lookup
partner_cp_by_name = {}
for row in PARTNER_CP_WEEKLY_RAW:
    gn = row["group_name"]
    if gn not in RELEVANT_PARTNERS:
        continue
    if gn not in partner_cp_by_name:
        partner_cp_by_name[gn] = []
    partner_cp_by_name[gn].append({
        "period": row["period"] + " 00:00:00",
        "cp_margin_pct": row["cp_margin_pct"],
        "cp_l2_margin_pct": row["cp_l2_margin_pct"]
    })

# ======== BUILD FINAL DATA ========
DATA["partners_list"] = ALL_PARTNERS

DATA["overview"]["weekly"]["gmv_by_partner"] = gmv_by_partner_weekly

for pname in ALL_PARTNERS:
    if pname not in DATA["partners"]:
        DATA["partners"][pname] = {
            "monthly": {"financial": [], "cp_margins": [], "operational": [], "failed_orders": [], "campaigns": []},
            "weekly": {"financial": [], "cp_margins": [], "operational": [], "failed_orders": [], "campaigns": []}
        }

    pw = DATA["partners"][pname]["weekly"]

    if not pw["financial"] and pname in new_fin_by_partner:
        pw["financial"] = new_fin_by_partner[pname]
    elif pname in new_fin_by_partner and pname not in PARTNER_WEEKLY_FIN:
        pw["financial"] = new_fin_by_partner[pname]

    if pname in ops_by_partner:
        pw["operational"] = ops_by_partner[pname]

    # Merge replacement/adjustment rates into partner operational data
    if os.path.exists(_repl_path) and pname in partner_repl_by_name:
        repl_lookup = partner_repl_by_name[pname]
        for op_row in pw["operational"]:
            repl_data = repl_lookup.get(op_row["period"])
            if repl_data:
                if repl_data["replacement_rate"] is not None:
                    op_row["replacement_rate"] = repl_data["replacement_rate"]
                if repl_data["adjustment_rate"] is not None:
                    op_row["adjustment_rate"] = repl_data["adjustment_rate"]

    if pname in camp_by_partner:
        pw["campaigns"] = camp_by_partner[pname]

    if pname in partner_cp_by_name:
        pw["cp_margins"] = sorted(partner_cp_by_name[pname], key=lambda x: x["period"])

# Generate HTML
with open(os.path.join(SCRIPT_DIR, "template.html"), "r") as f:
    template = f.read()

data_json = json.dumps(DATA)
html = template.replace("/*__REPORT_DATA__*/", f"const REPORT_DATA = {data_json};")

with open(os.path.join(SCRIPT_DIR, "index.html"), "w") as f:
    f.write(html)

print(f"Generated index.html ({len(html)//1024} KB)")
print(f"Partners: {len(ALL_PARTNERS)}")
print(f"Partners with weekly fin: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['financial'])}")
print(f"Partners with weekly ops: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['operational'])}")
print(f"Partners with weekly camp: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['campaigns'])}")
print(f"Partners with weekly CP: {sum(1 for p in ALL_PARTNERS if DATA['partners'][p]['weekly']['cp_margins'])}")
print(f"Overview weekly CP entries: {len(DATA['overview']['weekly']['cp_margins'])}")
print(f"Overview monthly CP entries: {len(DATA['overview']['monthly']['cp_margins'])}")
