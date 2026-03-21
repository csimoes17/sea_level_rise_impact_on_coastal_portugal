"""
07_export_tableau.py  –  Clean Export of All Analysis Outputs for Tableau
==========================================================================
Reads all intermediate CSVs produced by 06a and 06b and outputs a suite
of clean, Tableau-ready files.  No DEM, no Overpass, no heavy processing.

OUTPUT FILES
------------
tableau/
  01_timeseries_combined.csv      – P1 (GDP) + P2 (infrastructure) together,
                                    annual 2025–2100, all scenarios. Primary
                                    source for time-series line charts.

  02_timeseries_sensitivity.csv   – P2 base vs low density, all years/
                                    scenarios. For sensitivity fan charts.

  03_nuts3_spatial.csv            – Per-NUTS3 breakdown at key years
                                    (2025, 2030, 2050, 2075, 2100) for
                                    choropleth maps.

  04_roads_map.csv                – Road/rail inventory with midpoint
                                    lat/lon, for Tableau map layer.

  05_slr_scenarios.csv            – SLR projections only (2025–2100),
                                    for scenario reference chart.

TABLEAU TIPS (per file)
-----------------------
  01: Drag Year → Columns, Measure → Rows, Scenario → Color.
      Use dual-axis for GDP + infrastructure on same chart.
  02: Drag Year → Columns, Total_bn → Rows, filter by scenario.
      Add density_scenario to Color to show base vs low band.
  03: Use Built-in Map with nuts3 as geographic role (Custom Geocode)
      or join to nuts3_wgs84.geojson for spatial layer.
  04: Drag lon → Columns, lat → Rows → Show as Map.
      Color by feature (road/railway), Size by value_eur.
  05: Simple line chart; reference for dashboard annotations.
"""

import json, math
from pathlib import Path

import numpy as np
import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent
OUT_DIR    = DATA_DIR / "tableau"
OUT_DIR.mkdir(exist_ok=True)

# Input files
P1_SUM     = DATA_DIR / "gdp_at_risk_pillar1_summary.csv"
P1_DET     = DATA_DIR / "gdp_at_risk_pillar1.csv"
P2_SUM     = DATA_DIR / "infrastructure_at_risk_pillar2_summary.csv"
P2_DET     = DATA_DIR / "infrastructure_at_risk_pillar2_detail.csv"
P2_SENS    = DATA_DIR / "infrastructure_sensitivity.csv"
P2_INV     = DATA_DIR / "infrastructure_inventory.csv"
NUTS3_GEO  = DATA_DIR / "nuts3_wgs84.geojson"
OVERPASS_CACHE_PATTERN = "_overpass_cache_*.json"

KEY_YEARS  = [2025, 2030, 2040, 2050, 2060, 2075, 2100]

# SLR anchors (for standalone scenario table)
SLR_ANCHORS = {
    "ssp126": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "ssp245": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "ssp585": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
PIXEL_AREA_KM2 = 7.406799e-4   # from DEM transform (computed in 06b)


# ══════════════════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════════════════

def label_scenario(s):
    return {"ssp126": "SSP1-2.6 (Low)", "ssp245": "SSP2-4.5 (Intermediate)",
            "ssp585": "SSP5-8.5 (High)"}.get(s, s)

def haversine_km(lat1, lon1, lat2, lon2):
    R, d = 6371.0, math.radians
    a = (math.sin((d(lat2)-d(lat1))/2)**2
         + math.cos(d(lat1))*math.cos(d(lat2))
         * math.sin((d(lon2)-d(lon1))/2)**2)
    return 2 * R * math.asin(math.sqrt(a))

def way_length_km(nodes):
    return sum(haversine_km(nodes[i]["lat"], nodes[i]["lon"],
                            nodes[i+1]["lat"], nodes[i+1]["lon"])
               for i in range(len(nodes)-1))


# ══════════════════════════════════════════════════════════════════════════
#  01 · COMBINED TIME SERIES  (GDP + Infrastructure)
# ══════════════════════════════════════════════════════════════════════════

def build_timeseries_combined():
    print("  Building 01_timeseries_combined.csv …")
    p1 = pd.read_csv(P1_SUM)
    p2 = pd.read_csv(P2_SUM)
    # P2 base only for combined view
    p2_base = p2.copy()

    merged = p1.merge(
        p2_base[["year","scenario","slr_m",
                 "buildings_count","buildings_eur",
                 "roads_km","roads_eur",
                 "railways_km","railways_eur",
                 "utilities_total_eur",
                 "total_replacement_eur","total_bn_eur"]],
        on=["year","scenario","slr_m"], how="left")

    merged.rename(columns={
        "total_gdp_at_risk_bn"   : "gdp_at_risk_bn",
        "total_bn_eur"           : "infra_replacement_bn",
    }, inplace=True)

    merged["total_exposure_bn"] = (merged["gdp_at_risk_bn"]
                                   + merged["infra_replacement_bn"])
    merged["scenario_label"]    = merged["scenario"].apply(label_scenario)
    merged["infra_buildings_bn"] = merged["buildings_eur"] / 1e9
    merged["infra_roads_bn"]     = merged["roads_eur"] / 1e9
    merged["infra_railways_bn"]  = merged["railways_eur"] / 1e9
    merged["infra_utilities_bn"] = merged["utilities_total_eur"] / 1e9

    cols = ["year","scenario","scenario_label","slr_m",
            "gdp_at_risk_bn",
            "infra_replacement_bn",
            "infra_buildings_bn","infra_roads_bn",
            "infra_railways_bn","infra_utilities_bn",
            "total_exposure_bn",
            "buildings_count","roads_km","railways_km"]
    merged[cols].to_csv(OUT_DIR / "01_timeseries_combined.csv", index=False)
    print(f"    {len(merged)} rows → 01_timeseries_combined.csv")
    return merged


# ══════════════════════════════════════════════════════════════════════════
#  02 · SENSITIVITY TIME SERIES
# ══════════════════════════════════════════════════════════════════════════

def build_timeseries_sensitivity():
    print("  Building 02_timeseries_sensitivity.csv …")
    sens = pd.read_csv(P2_SENS)
    p1   = pd.read_csv(P1_SUM)[["year","scenario","slr_m","total_gdp_at_risk_bn"]]

    sens = sens.merge(p1, on=["year","scenario","slr_m"], how="left")
    sens.rename(columns={
        "total_bn_eur"         : "infra_replacement_bn",
        "total_gdp_at_risk_bn" : "gdp_at_risk_bn",
        "buildings_eur"        : "buildings_eur",
    }, inplace=True)

    sens["total_exposure_bn"]   = sens["gdp_at_risk_bn"] + sens["infra_replacement_bn"]
    sens["scenario_label"]      = sens["scenario"].apply(label_scenario)
    sens["density_label"]       = sens["density_scenario"].map(
        {"base": "Base estimate", "low": "Low estimate (50% density)"})
    sens["infra_buildings_bn"]  = sens["buildings_eur"] / 1e9

    cols = ["year","scenario","scenario_label","slr_m",
            "density_scenario","density_label",
            "buildings_count","infra_buildings_bn",
            "roads_eur","railways_eur","utilities_eur",
            "infra_replacement_bn","gdp_at_risk_bn","total_exposure_bn"]
    sens[cols].to_csv(OUT_DIR / "02_timeseries_sensitivity.csv", index=False)
    print(f"    {len(sens)} rows → 02_timeseries_sensitivity.csv")


# ══════════════════════════════════════════════════════════════════════════
#  03 · NUTS3 SPATIAL BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════

def build_nuts3_spatial():
    print("  Building 03_nuts3_spatial.csv …")

    p1_det = pd.read_csv(P1_DET)
    p2_det = pd.read_csv(P2_DET)

    # Compute bn column (detail file only has raw EUR)
    p1_det["gdp_at_risk_bn"] = p1_det["gdp_at_risk_eur"] / 1e9

    # Flood area from flooded pixels
    p1_det["flood_area_km2"] = p1_det["flooded_pixels"] * PIXEL_AREA_KM2

    # Filter to key years only for both
    p1_key = p1_det[p1_det["year"].isin(KEY_YEARS)].copy()
    p2_key = p2_det[p2_det["year"].isin(KEY_YEARS)].copy()
    p2_key = p2_key.rename(columns={"value_eur": "buildings_value_eur",
                                    "buildings": "buildings_count"})

    # Merge P1 + P2 on nuts3 / year / scenario
    merged = p1_key.merge(
        p2_key[["year","scenario","nuts3","buildings_count",
                "buildings_value_eur","storeys"]],
        on=["year","scenario","nuts3"], how="left")

    merged["gdp_at_risk_bn"]     = merged["gdp_at_risk_bn"]
    merged["buildings_value_bn"] = merged["buildings_value_eur"].fillna(0) / 1e9
    merged["scenario_label"]     = merged["scenario"].apply(label_scenario)

    cols = ["year","scenario","scenario_label","nuts3",
            "slr_m","flood_area_km2","flooded_pixels",
            "gdp_at_risk_bn",
            "buildings_count","buildings_value_bn","storeys"]
    merged[cols].sort_values(["scenario","year","nuts3"])\
                .to_csv(OUT_DIR / "03_nuts3_spatial.csv", index=False)
    print(f"    {len(merged)} rows → 03_nuts3_spatial.csv")


# ══════════════════════════════════════════════════════════════════════════
#  04 · ROADS/RAILWAYS MAP  (add midpoint lat/lon from Overpass cache)
# ══════════════════════════════════════════════════════════════════════════

def build_roads_map():
    print("  Building 04_roads_map.csv …")

    # Load the at-risk inventory (already filtered by elevation in 06b)
    inv = pd.read_csv(P2_INV)
    print(f"    {len(inv)} segments in inventory")

    # Try to enrich with midpoint coordinates from Overpass cache files
    # We rebuild the way→midpoint mapping from cached JSON
    cache_files = list(DATA_DIR.glob(OVERPASS_CACHE_PATTERN))

    if not cache_files:
        print("    WARNING: No Overpass cache files found — "
              "exporting inventory without coordinates.")
        inv["lat"] = None
        inv["lon"] = None
        inv.to_csv(OUT_DIR / "04_roads_map.csv", index=False)
        return

    # Build a lookup: (feature, sub_type, quantity_rounded) → (mid_lat, mid_lon)
    # We round quantity to 4dp to match floats written by 06b
    print(f"    Reading {len(cache_files)} Overpass cache file(s) …")

    # We need the same filtering logic as 06b to find matching ways
    # Key: for each way, compute length and midpoint coords, then match to inventory
    # Since inventory rows may not be unique by length alone, we use a list approach
    MAX_SLR = 1.05
    ROAD_TYPES = {"motorway","trunk","primary","secondary",
                  "tertiary","unclassified","residential","living_street"}
    RAIL_TYPES = {"rail","light_rail","tram","narrow_gauge"}

    enriched_rows = []

    for cf in sorted(cache_files):
        with open(cf, encoding="utf-8") as f:
            data = json.load(f)

        for el in data.get("elements", []):
            if el.get("type") != "way":
                continue
            geom = el.get("geometry", [])
            tags = el.get("tags", {})
            if len(geom) < 2:
                continue

            # Determine feature type
            if "highway" in tags and tags["highway"] in ROAD_TYPES:
                feat     = "road"
                sub_type = tags["highway"]
            elif "railway" in tags and tags["railway"] in RAIL_TYPES:
                feat     = "railway"
                sub_type = tags.get("railway","rail")
            else:
                continue

            # Quick length check — only process ways that could be in inventory
            length_km = way_length_km(geom)

            # Midpoint coordinates
            mid_idx = len(geom) // 2
            mid_lat = geom[mid_idx]["lat"]
            mid_lon = geom[mid_idx]["lon"]

            # Start/end for Tableau path lines (optional)
            start_lat = geom[0]["lat"]
            start_lon = geom[0]["lon"]
            end_lat   = geom[-1]["lat"]
            end_lon   = geom[-1]["lon"]

            enriched_rows.append({
                "feature"   : feat,
                "sub_type"  : sub_type,
                "length_km" : round(length_km, 4),
                "mid_lat"   : round(mid_lat, 6),
                "mid_lon"   : round(mid_lon, 6),
                "start_lat" : round(start_lat, 6),
                "start_lon" : round(start_lon, 6),
                "end_lat"   : round(end_lat, 6),
                "end_lon"   : round(end_lon, 6),
            })

    if not enriched_rows:
        print("    WARNING: No ways extracted from cache.")
        inv.to_csv(OUT_DIR / "04_roads_map.csv", index=False)
        return

    enrich_df = pd.DataFrame(enriched_rows)

    # Merge inventory (elev, value_eur) with enriched coords
    # Match on feature + sub_type + rounded length
    inv["length_km"] = inv["quantity"].round(4)
    merged_map = inv.merge(
        enrich_df[["feature","sub_type","length_km",
                   "mid_lat","mid_lon","start_lat","start_lon",
                   "end_lat","end_lon"]],
        on=["feature","sub_type","length_km"],
        how="left")

    # Drop any duplicates from multiple cache files
    merged_map = merged_map.drop_duplicates(
        subset=["feature","sub_type","length_km","elev"])

    # Add readable labels for Tableau
    merged_map["feature_label"] = merged_map["feature"].str.capitalize()
    merged_map["value_m_eur"]   = (merged_map["value_eur"] / 1e6).round(2)
    merged_map["type_label"]    = (merged_map["sub_type"]
                                   .str.replace("_", " ").str.capitalize())

    cols = ["feature","feature_label","sub_type","type_label",
            "elev","length_km","value_eur","value_m_eur",
            "mid_lat","mid_lon","start_lat","start_lon","end_lat","end_lon"]
    merged_map[cols].to_csv(OUT_DIR / "04_roads_map.csv", index=False)
    matched = merged_map["mid_lat"].notna().sum()
    print(f"    {len(merged_map)} rows, {matched} with coordinates → 04_roads_map.csv")


# ══════════════════════════════════════════════════════════════════════════
#  05 · SLR SCENARIOS REFERENCE
# ══════════════════════════════════════════════════════════════════════════

def build_slr_scenarios():
    print("  Building 05_slr_scenarios.csv …")
    years = np.arange(2025, 2101)
    rows  = []
    for scen, anchors in SLR_ANCHORS.items():
        yrs  = np.array(sorted(anchors))
        vals = np.array([anchors[y] for y in yrs])
        slr  = np.interp(years, yrs, vals)
        for yr, s in zip(years, slr):
            rows.append({
                "year"           : int(yr),
                "scenario"       : scen,
                "scenario_label" : label_scenario(scen),
                "slr_m"          : round(float(s), 4),
                "slr_cm"         : round(float(s) * 100, 2),
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "05_slr_scenarios.csv", index=False)
    print(f"    {len(df)} rows → 05_slr_scenarios.csv")


# ══════════════════════════════════════════════════════════════════════════
#  COPY NUTS3 GEOJSON (for Tableau spatial join)
# ══════════════════════════════════════════════════════════════════════════

def copy_geojson():
    import shutil
    if NUTS3_GEO.exists():
        dest = OUT_DIR / "nuts3_wgs84.geojson"
        shutil.copy2(NUTS3_GEO, dest)
        print(f"  Copied nuts3_wgs84.geojson → tableau/")
    else:
        print(f"  WARNING: {NUTS3_GEO.name} not found — skip copy.")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("07_export_tableau.py — Tableau Export")
    print("=" * 60)

    # Verify required inputs
    missing = [f for f in [P1_SUM, P1_DET, P2_SUM, P2_DET, P2_SENS, P2_INV]
               if not f.exists()]
    if missing:
        print("\nERROR: Missing input files:")
        for f in missing:
            print(f"  {f.name}")
        print("Run 06a and 06b (+ sensitivity) first.")
        raise SystemExit(1)

    print(f"\nOutput folder: {OUT_DIR}\n")

    combined = build_timeseries_combined()
    build_timeseries_sensitivity()
    build_nuts3_spatial()
    build_roads_map()
    build_slr_scenarios()
    copy_geojson()

    # ── Summary of what was produced ──────────────────────────────────
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE — Files in /tableau/")
    print("=" * 60)

    for f in sorted(OUT_DIR.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:<42} {size_kb:6.1f} KB")

    # ── Key numbers for dissertation reference ────────────────────────
    print("\n── KEY NUMBERS (2100 anchor year) ───────────────────────")
    df = combined[combined["year"] == 2100]
    for _, r in df.iterrows():
        print(f"  {r['scenario_label']:<30}  "
              f"GDP at risk: €{r['gdp_at_risk_bn']:.2f}B  "
              f"Infra: €{r['infra_replacement_bn']:.1f}B  "
              f"Total: €{r['total_exposure_bn']:.1f}B")

    print()
    print("── ROAD/RAIL SUMMARY (max exposure at SLR 1.05m) ────────")
    inv = pd.read_csv(P2_INV)
    for feat in ["road", "railway"]:
        sub = inv[inv["feature"] == feat]
        print(f"  {feat.capitalize()}: {sub['quantity'].sum():.1f} km, "
              f"€{sub['value_eur'].sum()/1e6:.0f}M replacement value")
        for stype, grp in sub.groupby("sub_type"):
            print(f"    {stype:<20} {grp['quantity'].sum():6.1f} km  "
                  f"€{grp['value_eur'].sum()/1e6:7.1f}M")
