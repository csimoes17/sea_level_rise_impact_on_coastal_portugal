"""
06b_sensitivity.py  –  Building Density Sensitivity Analysis for Pillar 2
==========================================================================
Re-runs the building cost component of Pillar 2 under two density scenarios:

  BASE  : Current COASTAL_BUILDING_DENSITY (from 06b)
  LOW   : 50% of base density values — lower-bound estimate reflecting
          the possibility that the sub-1m coastal strip contains more
          parks, ports, industrial land and undeveloped estuarine areas
          than assumed in the base case.

Road, railway and utility costs are UNCHANGED between scenarios (they
depend only on the OSM road inventory, not on building density).

This script reads the already-computed road/rail inventory CSV from the
base run rather than re-querying Overpass or re-sampling the DEM for
roads, keeping runtime to a minimum.

OUTPUT
------
  infrastructure_sensitivity.csv
    Columns: year, scenario, slr_m, density_scenario,
             buildings_count, buildings_eur,
             roads_eur, railways_eur, utilities_eur,
             total_replacement_eur, total_bn_eur
  (228 base rows + 228 low rows = 456 rows total)
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent
DEM_PATH    = DATA_DIR / "dem_portugal_merged.tif"
PILLAR1_DET = DATA_DIR / "gdp_at_risk_pillar1.csv"
INV_PATH    = DATA_DIR / "infrastructure_inventory.csv"   # from base 06b run
OUTPUT_PATH = DATA_DIR / "infrastructure_sensitivity.csv"

YEAR_START, YEAR_END = 2025, 2100
MAX_SLR = 1.05

# ── SLR (identical to 06a / 06b) ─────────────────────────────────────────
SLR_ANCHORS = {
    "ssp126": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "ssp245": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "ssp585": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS = ["ssp126", "ssp245", "ssp585"]

def slr_series(anchors, years):
    yrs  = np.array(sorted(anchors))
    vals = np.array([anchors[y] for y in yrs])
    return np.interp(years, yrs, vals)


# ── COST CONSTANTS (identical to 06b) ────────────────────────────────────
BUILDING_COST_PER_M2         = 1_950   # construction + land
USEFUL_AREA_PER_STOREY_M2    = 102

STOREY_MULTIPLIER = {
    "Grande Lisboa"              : 5.0,
    "Área Metropolitana do Porto": 4.0,
    "Algarve"                    : 3.0,
    "Região de Aveiro"           : 2.5,
    "Região de Coimbra"          : 2.5,
    "Oeste"                      : 2.5,
    "Península de Setúbal"       : 3.0,
    "Cávado"                     : 2.5,
    "Região de Leiria"           : 2.0,
    "Alto Minho"                 : 1.5,
    "Alentejo Litoral"           : 1.5,
    "Baixo Alentejo"             : 1.5,
    "Lezíria do Tejo"            : 1.5,
    "_default"                   : 2.0,
}

# BASE building densities (buildings/km²) — from 06b
BASE_DENSITY = {
    "Grande Lisboa"              : 800,
    "Península de Setúbal"       : 400,
    "Oeste"                      : 120,
    "Algarve"                    : 200,
    "Alentejo Litoral"           : 30,
    "Baixo Alentejo"             : 15,
    "Região de Aveiro"           : 250,
    "Região de Coimbra"          : 80,
    "Região de Leiria"           : 100,
    "Alto Minho"                 : 60,
    "Cávado"                     : 200,
    "Área Metropolitana do Porto": 500,
    "Lezíria do Tejo"            : 40,
    "_default"                   : 20,
}

# LOW density = 50% of base (lower bound)
LOW_DENSITY = {k: v * 0.5 for k, v in BASE_DENSITY.items()}

UTILITY_BUNDLE_KM = 800_000   # water + sewage + electricity per km non-motorway road


# ── PIXEL AREA FROM DEM TRANSFORM ────────────────────────────────────────
def compute_pixel_area_km2(transform, center_lat=39.0):
    deg_x = abs(transform.a)
    deg_y = abs(transform.e)
    cos_lat = math.cos(math.radians(center_lat))
    return deg_x * 111.139 * cos_lat * deg_y * 111.139


# ── BUILDING ESTIMATE ─────────────────────────────────────────────────────
def estimate_buildings(pillar1_detail_path, pixel_area_km2, density_dict):
    """
    Returns {(year, scenario): {nuts3: (n_buildings, value_eur)}}
    using the given density_dict (base or low).
    """
    detail = pd.read_csv(pillar1_detail_path)
    required = {"year", "scenario", "nuts3", "flooded_pixels"}
    if not required.issubset(set(detail.columns)):
        print(f"  ERROR: Missing columns: {required - set(detail.columns)}")
        return {}

    result = {}
    for (yr, scen), grp in detail.groupby(["year", "scenario"]):
        nuts3_data = {}
        for _, row in grp.iterrows():
            nuts3    = row["nuts3"]
            flood_km2 = float(row["flooded_pixels"]) * pixel_area_km2
            density  = density_dict.get(nuts3, density_dict["_default"])
            n_bld    = flood_km2 * density
            storeys  = STOREY_MULTIPLIER.get(nuts3, STOREY_MULTIPLIER["_default"])
            val_each = USEFUL_AREA_PER_STOREY_M2 * storeys * BUILDING_COST_PER_M2
            nuts3_data[nuts3] = (n_bld, n_bld * val_each)
        result[(int(yr), scen)] = nuts3_data
    return result


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":

    years = np.arange(YEAR_START, YEAR_END + 1)

    # ── 1. Pixel area from DEM transform ──────────────────────────────
    print("Reading DEM transform …")
    with rasterio.open(DEM_PATH) as src:
        transform = src.transform
    pixel_area_km2 = compute_pixel_area_km2(transform)
    print(f"  Pixel area: {pixel_area_km2:.6e} km²\n")

    # ── 2. Load road/rail inventory from base 06b run ─────────────────
    print("Loading road/rail inventory from base run …")
    if not INV_PATH.exists():
        raise FileNotFoundError(
            f"Inventory not found: {INV_PATH}\n"
            "Run 06b_osm_infrastructure.py first to generate it.")
    inv = pd.read_csv(INV_PATH)
    print(f"  {len(inv)} segments loaded\n")

    rr_elev    = inv["elev"].values
    rr_val     = inv["value_eur"].values
    rr_feat    = inv["feature"].values
    rr_subtype = inv["sub_type"].values
    rr_qty     = inv["quantity"].values

    # ── 3. Building estimates for both density scenarios ───────────────
    density_scenarios = {
        "base": BASE_DENSITY,
        "low" : LOW_DENSITY,
    }
    bld_results = {}
    for ds_name, density_dict in density_scenarios.items():
        print(f"Estimating buildings — {ds_name} density …")
        bld_results[ds_name] = estimate_buildings(
            PILLAR1_DET, pixel_area_km2, density_dict)
        # Quick sanity print for 2100/SSP5-8.5
        sample = bld_results[ds_name].get((2100, "ssp585"), {})
        n  = sum(v[0] for v in sample.values())
        vb = sum(v[1] for v in sample.values()) / 1e9
        print(f"  2100/SSP5-8.5: {n:,.0f} buildings → €{vb:.1f}B\n")

    # ── 4. Annual cost loop (both density scenarios) ───────────────────
    print(f"Computing annual costs {YEAR_START}–{YEAR_END} …\n")
    all_rows = []

    for ds_name, bld_by_scenario in bld_results.items():
        print(f"  Density scenario: {ds_name.upper()}")
        for scenario in SCENARIOS:
            slr = slr_series(SLR_ANCHORS[scenario], years)

            for yr, s in zip(years, slr):
                yr_int = int(yr)

                # ── Roads + railways (identical for both density scenarios)
                mask_rr   = (rr_elev > 0) & (rr_elev <= s)
                road_mask = mask_rr & (rr_feat == "road")
                rail_mask = mask_rr & (rr_feat == "railway")
                road_eur  = float(rr_val[road_mask].sum())
                rail_eur  = float(rr_val[rail_mask].sum())

                # ── Utilities
                non_mway = road_mask & (rr_subtype != "motorway")
                util_eur = float(rr_qty[non_mway].sum()) * UTILITY_BUNDLE_KM

                # ── Buildings
                bld_data = bld_by_scenario.get((yr_int, scenario), None)
                if bld_data is None:
                    same_scen = [(k, v) for k, v in bld_by_scenario.items()
                                 if k[1] == scenario]
                    if same_scen:
                        closest  = min(same_scen, key=lambda x: abs(x[0][0] - yr_int))
                        bld_data = closest[1]
                bld_count = sum(v[0] for v in bld_data.values()) if bld_data else 0
                bld_eur   = sum(v[1] for v in bld_data.values()) if bld_data else 0

                total_eur = bld_eur + road_eur + rail_eur + util_eur

                all_rows.append({
                    "year"                 : yr_int,
                    "scenario"             : scenario,
                    "slr_m"                : round(float(s), 4),
                    "density_scenario"     : ds_name,
                    "buildings_count"      : round(bld_count, 0),
                    "buildings_eur"        : round(bld_eur, 0),
                    "roads_eur"            : round(road_eur, 0),
                    "railways_eur"         : round(rail_eur, 0),
                    "utilities_eur"        : round(util_eur, 0),
                    "total_replacement_eur": round(total_eur, 0),
                    "total_bn_eur"         : round(total_eur / 1e9, 4),
                })

    # ── 5. Save ───────────────────────────────────────────────────────
    df = pd.DataFrame(all_rows)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved: {OUTPUT_PATH.name}  ({len(df)} rows)\n")

    # ── 6. Summary pivot — 2100 only ──────────────────────────────────
    df2100 = df[df["year"] == 2100].copy()
    print("=== 2100 SENSITIVITY SUMMARY (€B) ===")
    print(f"{'Scenario':<12} {'BASE':>10} {'LOW (50%)':>12} {'Difference':>12}")
    print("-" * 48)
    for scen in SCENARIOS:
        base_val = df2100.loc[(df2100.scenario == scen) &
                              (df2100.density_scenario == "base"),
                              "total_bn_eur"].values[0]
        low_val  = df2100.loc[(df2100.scenario == scen) &
                              (df2100.density_scenario == "low"),
                              "total_bn_eur"].values[0]
        diff     = base_val - low_val
        print(f"  {scen:<10}  {base_val:>8.1f}B  {low_val:>10.1f}B  {diff:>+10.1f}B")

    print()
    print("=== 2100 BUILDING COUNT: BASE vs LOW ===")
    print(f"{'Scenario':<12} {'BASE bldgs':>12} {'LOW bldgs':>12}")
    print("-" * 38)
    for scen in SCENARIOS:
        base_n = df2100.loc[(df2100.scenario == scen) &
                            (df2100.density_scenario == "base"),
                            "buildings_count"].values[0]
        low_n  = df2100.loc[(df2100.scenario == scen) &
                            (df2100.density_scenario == "low"),
                            "buildings_count"].values[0]
        print(f"  {scen:<10}  {base_n:>10,.0f}  {low_n:>10,.0f}")

    print()
    print("Note: Road, railway and utility costs are identical across")
    print("density scenarios — only building counts and values differ.")
    print(f"\nBuilding density: BASE = INE Census 2021 coastal estimates")
    print(f"                  LOW  = 50% of BASE (accounts for parks,")
    print(f"                  ports, industrial land, undeveloped estuarine")
    print(f"                  areas in the sub-1m flood zone)")
