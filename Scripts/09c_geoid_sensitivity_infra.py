"""
09c_geoid_sensitivity_infra.py  —  Pillar 2 Geoid-Offset Sensitivity
======================================================================
Recomputes infrastructure replacement cost (Pillar 2: buildings, roads,
railways and utilities) under two SLR variants for KEY_YEARS:

  BASELINE  : IPCC AR6 SLR anchors evaluated at EGM2008 datum (standard)
  GEOID     : SLR + 0.15 m correction (Seeger & Minderhoud, Nature 2026)
              accounting for the ~0.15 m geoid–sea-surface discrepancy
              on the EU Atlantic coast.

Methodology is identical to 06b_osm_infrastructure.py / 06b_sensitivity.py:
  • Buildings  : flooded DEM pixels per NUTS3 × building density (INE 2021)
                 × storeys × replacement cost per m²
  • Roads      : OSM inventory segments where min_elev ≤ SLR threshold
  • Railways   : same as roads
  • Utilities  : km of non-motorway roads at risk × €800k/km bundle

Outputs
-------
  infra_geoid_sensitivity_summary.csv   — one row per scenario × year
  infra_geoid_sensitivity_detail.csv    — one row per scenario × year × variant
  Terminal table (style matches 09b_geoid_sensitivity.py)

Runtime: ~1–2 minutes (DOWNSAMPLE=4).
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from shapely.geometry import shape

# ── CONFIG ────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent

DEM1_PATH   = PROJECT_DIR / "COP DEM 1.tif"
DEM2_PATH   = PROJECT_DIR / "COP DEM 2.tif"
NUTS3_PATH  = PROJECT_DIR / "nuts3_wgs84.geojson"
INV_PATH    = PROJECT_DIR / "infrastructure_inventory.csv"

OUT_SUMMARY = PROJECT_DIR / "infra_geoid_sensitivity_summary.csv"
OUT_DETAIL  = PROJECT_DIR / "infra_geoid_sensitivity_detail.csv"

CLIP_BOUNDS  = dict(lon_min=-9.7, lon_max=-7.1, lat_min=36.8, lat_max=42.3)
DOWNSAMPLE   = 4
GEOID_OFFSET = 0.15
KEY_YEARS    = [2030, 2050, 2075, 2100]

SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]

# ── COST CONSTANTS (identical to 06b_osm_infrastructure.py) ──────────────────
BUILDING_COST_PER_M2       = 1_950    # construction + land, €/m² (INE 2025)
USEFUL_AREA_PER_STOREY_M2  = 102      # INE Census 2021 average
UTILITY_BUNDLE_KM          = 800_000  # water + sewage + electricity per km road

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

BASE_DENSITY = {   # buildings / km² — INE Census 2021 coastal estimates
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


# ── HELPERS ───────────────────────────────────────────────────────────────────
def slr_at_year(anchors, year, offset=0.0):
    ay = np.array(sorted(anchors))
    av = np.array([anchors[y] for y in ay])
    return float(np.interp(year, ay, av)) + offset


def pixel_area_km2(tf, center_lat=39.0):
    """Area in km² of a single DEM pixel given its affine transform."""
    deg_x   = abs(tf.a)
    deg_y   = abs(tf.e)
    cos_lat = math.cos(math.radians(center_lat))
    return deg_x * 111.139 * cos_lat * deg_y * 111.139


# ── DEM ───────────────────────────────────────────────────────────────────────
def load_dem():
    print("Loading DEM …")
    srcs    = [rasterio.open(DEM1_PATH), rasterio.open(DEM2_PATH)]
    mosaic, tf = merge(srcs)
    for s in srcs:
        s.close()

    dem = mosaic[0].astype("float32")

    # Clip to Portugal bounds
    b    = CLIP_BOUNDS
    cols = np.linspace(tf.c, tf.c + tf.a * dem.shape[1],
                       dem.shape[1], endpoint=False)
    rows = np.linspace(tf.f, tf.f + tf.e * dem.shape[0],
                       dem.shape[0], endpoint=False)
    col_mask = (cols >= b["lon_min"]) & (cols <= b["lon_max"])
    row_mask = (rows >= b["lat_min"]) & (rows <= b["lat_max"])
    dem = dem[np.ix_(np.where(row_mask)[0], np.where(col_mask)[0])]

    # Downsample
    if DOWNSAMPLE > 1:
        dem = dem[::DOWNSAMPLE, ::DOWNSAMPLE]

    # Recompute transform to match clipped+downsampled shape exactly
    tf_out = from_bounds(
        b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"],
        dem.shape[1], dem.shape[0]
    )

    # Replace nodata with sentinel
    dem[dem < -100] = -9999.0

    valid = dem[dem > -100]
    print(f"  Shape: {dem.shape}  |  Elev: {valid.min():.1f}–{valid.max():.1f} m")
    return dem, tf_out


# ── NUTS3 ─────────────────────────────────────────────────────────────────────
def rasterize_nuts3(dem_shape, tf):
    print("Rasterizing NUTS3 …")
    with open(NUTS3_PATH) as f:
        gj = json.load(f)

    # Auto-detect ID field
    id_field = None
    for candidate in ["nuts3", "NUTS_ID", "NUTS3", "nuts_id", "code", "CODIGO"]:
        if all(candidate in feat["properties"] for feat in gj["features"]):
            id_field = candidate
            break
    if id_field is None:
        id_field = list(gj["features"][0]["properties"].keys())[0]
    print(f"  NUTS3 ID field: '{id_field}'")

    labels  = sorted(set(f["properties"][id_field] for f in gj["features"]))
    id_map  = {lab: i + 1 for i, lab in enumerate(labels)}

    geom_val = [(shape(f["geometry"]), id_map[f["properties"][id_field]])
                for f in gj["features"]]
    raster = rasterize(geom_val, out_shape=dem_shape, transform=tf,
                       fill=0, dtype="int16")
    print(f"  Rasterized {len(labels)} NUTS3 regions.")
    return raster, id_map


# ── BUILDING ESTIMATE ─────────────────────────────────────────────────────────
def buildings_at_slr(dem, nuts3_raster, id_map, px_area, slr_val):
    """
    Estimate buildings at risk at a given SLR value.
    Mirrors the method in 06b_osm_infrastructure.py:
      flood_km² per NUTS3 × density × storeys × replacement cost/m²
    """
    flood_mask   = (dem > 0) & (dem <= slr_val)
    total_count  = 0.0
    total_eur    = 0.0

    for label, code in id_map.items():
        region_flood_px = int(np.sum((nuts3_raster == code) & flood_mask))
        flood_km2       = region_flood_px * px_area
        density         = BASE_DENSITY.get(label, BASE_DENSITY["_default"])
        n_bld           = flood_km2 * density
        storeys         = STOREY_MULTIPLIER.get(label, STOREY_MULTIPLIER["_default"])
        val_each        = USEFUL_AREA_PER_STOREY_M2 * storeys * BUILDING_COST_PER_M2
        total_count    += n_bld
        total_eur      += n_bld * val_each

    return total_count, total_eur


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":

    dem, tf           = load_dem()
    nuts3_raster, id_map = rasterize_nuts3(dem.shape, tf)
    px_area           = pixel_area_km2(tf)   # already correct for downsampled res

    # Load road / railway / utility inventory
    print("Loading infrastructure inventory …")
    inv        = pd.read_csv(INV_PATH)
    rr_elev    = inv["elev"].values
    rr_val     = inv["value_eur"].values
    rr_feat    = inv["feature"].values
    rr_subtype = inv["sub_type"].values
    rr_qty     = inv["quantity"].values
    print(f"  {len(inv)} segments loaded.\n")

    print("Running flood analysis …")
    summary_rows = []
    detail_rows  = []

    for scenario in SCENARIOS:
        anchors = SLR_ANCHORS[scenario]
        for year in KEY_YEARS:
            slr_base   = slr_at_year(anchors, year, offset=0.0)
            slr_offset = slr_at_year(anchors, year, offset=GEOID_OFFSET)

            result = {}
            for variant, slr_val in [("baseline", slr_base), ("geoid", slr_offset)]:

                # ── Buildings ──────────────────────────────────────────────
                n_bld, bld_eur = buildings_at_slr(
                    dem, nuts3_raster, id_map, px_area, slr_val)

                # ── Roads & railways ───────────────────────────────────────
                mask_rr   = (rr_elev > 0) & (rr_elev <= slr_val)
                road_mask = mask_rr & (rr_feat == "road")
                rail_mask = mask_rr & (rr_feat == "railway")
                road_eur  = float(rr_val[road_mask].sum())
                rail_eur  = float(rr_val[rail_mask].sum())

                # ── Utilities (co-located with non-motorway roads) ─────────
                non_mway = road_mask & (rr_subtype != "motorway")
                util_eur = float(rr_qty[non_mway].sum()) * UTILITY_BUNDLE_KM

                total_eur = bld_eur + road_eur + rail_eur + util_eur

                result[variant] = {
                    "buildings_count": round(n_bld, 0),
                    "buildings_bn":    round(bld_eur  / 1e9, 4),
                    "roads_bn":        round(road_eur / 1e9, 4),
                    "railways_bn":     round(rail_eur / 1e9, 4),
                    "utilities_bn":    round(util_eur / 1e9, 4),
                    "total_bn":        round(total_eur / 1e9, 4),
                }

                detail_rows.append({
                    "scenario":        scenario,
                    "year":            year,
                    "variant":         variant,
                    "variant_label":   ("Baseline (IPCC AR6)"
                                        if variant == "baseline"
                                        else "+0.15m Geoid Correction"),
                    "slr_m":           round(slr_val, 3),
                    **result[variant],
                })

            # ── Summary row ────────────────────────────────────────────────
            b = result["baseline"]
            g = result["geoid"]
            delta_bn  = round(g["total_bn"] - b["total_bn"], 4)
            delta_pct = round(100 * delta_bn / b["total_bn"], 1) if b["total_bn"] else 0.0

            summary_rows.append({
                "scenario":             scenario,
                "year":                 year,
                "slr_baseline_m":       round(slr_base,   3),
                "slr_offset_m":         round(slr_offset, 3),
                # Baseline
                "buildings_count":      b["buildings_count"],
                "buildings_bn":         b["buildings_bn"],
                "roads_bn":             b["roads_bn"],
                "railways_bn":          b["railways_bn"],
                "utilities_bn":         b["utilities_bn"],
                "total_bn":             b["total_bn"],
                # Geoid
                "buildings_count_geoid": g["buildings_count"],
                "buildings_bn_geoid":    g["buildings_bn"],
                "roads_bn_geoid":        g["roads_bn"],
                "railways_bn_geoid":     g["railways_bn"],
                "utilities_bn_geoid":    g["utilities_bn"],
                "total_bn_geoid":        g["total_bn"],
                # Delta
                "delta_total_bn":        delta_bn,
                "delta_total_pct":       delta_pct,
            })

            print(f"  {scenario} / {year}  ✓")

    # ── Save CSVs ─────────────────────────────────────────────────────────────
    df_sum = pd.DataFrame(summary_rows)
    df_det = pd.DataFrame(detail_rows)
    df_sum.to_csv(OUT_SUMMARY, index=False)
    df_det.to_csv(OUT_DETAIL,  index=False)
    print(f"\n  Saved: {OUT_SUMMARY.name}")
    print(f"  Saved: {OUT_DETAIL.name}")

    # ── Terminal table ────────────────────────────────────────────────────────
    W = 110
    print()
    print("═" * W)
    print("PILLAR 2 GEOID-OFFSET SENSITIVITY  —  Seeger & Minderhoud (Nature, 2026)"
          "  —  +0.15 m EU Atlantic")
    print("═" * W)
    print(f"{'Scenario':<12} {'Year':>6}  {'SLR':>6}  {'SLR+G':>6}  "
          f"{'Infra(€bn)':>12}  {'Infra+G(€bn)':>13}  {'ΔInfra':>9}  {'Δ%':>8}")
    print("─" * W)
    for _, r in df_sum.iterrows():
        print(f"{r.scenario:<12} {int(r.year):>6}  "
              f"{r.slr_baseline_m:>6.3f}  {r.slr_offset_m:>6.3f}  "
              f"{r.total_bn:>12.3f}  {r.total_bn_geoid:>13.3f}  "
              f"{r.delta_total_bn:>+9.3f}  {r.delta_total_pct:>+7.1f}%")
    print("─" * W)

    print("\nHEADLINE — YEAR 2100:")
    print("─" * W)
    for scen in SCENARIOS:
        r = df_sum[(df_sum["scenario"] == scen) & (df_sum["year"] == 2100)].iloc[0]
        print(f"  {scen:<10}  Infra:  "
              f"€{r.total_bn:.3f}bn → €{r.total_bn_geoid:.3f}bn  "
              f"({r.delta_total_pct:+.0f}%)")
        print(f"              breakdown  buildings: "
              f"€{r.buildings_bn:.3f}→€{r.buildings_bn_geoid:.3f}  "
              f"roads: €{r.roads_bn:.3f}→€{r.roads_bn_geoid:.3f}  "
              f"rail: €{r.railways_bn:.3f}→€{r.railways_bn_geoid:.3f}  "
              f"util: €{r.utilities_bn:.3f}→€{r.utilities_bn_geoid:.3f}")
    print("═" * W)
