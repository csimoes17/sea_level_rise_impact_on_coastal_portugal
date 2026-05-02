"""
09b_geoid_sensitivity.py – Geoid-Offset Sensitivity Analysis
=============================================================
Computes the impact of a +0.15 m geoid offset on flooded area and
GDP at risk, following Seeger & Minderhoud (Nature, 2026).

For each IPCC AR6 scenario and key reference years, compares:
  • Baseline:     SLR as per IPCC AR6 median projections
  • +Geoid offset: SLR + 0.15 m (European Atlantic coast correction)

OUTPUTS  (saved to PROJECT_DIR/)
─────────────────────────────────
  geoid_sensitivity_area.csv      — flooded km² per scenario × year × variant
  geoid_sensitivity_gdp.csv       — GDP at risk per NUTS3 × scenario × year × variant
  geoid_sensitivity_summary.csv   — headline comparison table

Also prints a formatted summary table to the terminal.

REQUIREMENTS:  pip install rasterio numpy pandas shapely
"""

from pathlib import Path
import json, math, time, warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge as rio_merge
from rasterio.transform import Affine
import rasterio.features
from shapely.geometry import shape as shp_shape


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

PROJECT_DIR = Path(
    "/Users/celsosimoes/Desktop/csimoes/celsosimoes/"
    "Ensino/MBA Data Science/Project/Python/Clean_and_Structuring"
)

DEM1_PATH    = PROJECT_DIR / "COP DEM 1.tif"
DEM2_PATH    = PROJECT_DIR / "COP DEM 2.tif"
GEOJSON_PATH = PROJECT_DIR / "nuts3_wgs84.geojson"
P1_DETAIL_PATH = PROJECT_DIR / "gdp_at_risk_pillar1.csv"   # ← correct filename

GEOID_OFFSET = 0.15   # metres (Seeger & Minderhoud 2026, EU Atlantic)

KEY_YEARS = [2030, 2050, 2075, 2100]

# Use DOWNSAMPLE=4 for speed (~120m); set to 1 for full 30m accuracy (slower)
DOWNSAMPLE = 4

CLIP_BOUNDS = {
    "lon_min": -9.7, "lon_max": -7.1,
    "lat_min": 36.8, "lat_max": 42.3,
}

SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS = list(SLR_ANCHORS.keys())


# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def slr_at_year(anchors, year, offset=0.0):
    ay = np.array(sorted(anchors))
    av = np.array([anchors[y] for y in ay])
    return float(np.interp(year, ay, av)) + offset


def load_dem():
    print("Loading DEM …")
    with rasterio.open(DEM2_PATH) as s2, rasterio.open(DEM1_PATH) as s1:
        arr, tf = rio_merge([s2, s1])
    dem = arr[0].astype(np.float32)
    for nd in (-32768.0, 32767.0, -9999.0):
        dem[np.abs(dem - nd) < 0.5] = np.nan

    h, w = dem.shape
    if CLIP_BOUNDS:
        lons = tf.c + np.arange(w) * tf.a
        lats = tf.f + np.arange(h) * tf.e
        c0 = max(0, int(np.searchsorted(lons, CLIP_BOUNDS["lon_min"])))
        c1 = min(w, int(np.searchsorted(lons, CLIP_BOUNDS["lon_max"])))
        r0 = max(0, int(np.searchsorted(-lats, -CLIP_BOUNDS["lat_max"])))
        r1 = min(h, int(np.searchsorted(-lats, -CLIP_BOUNDS["lat_min"])))
        dem = dem[r0:r1, c0:c1]
        tf = Affine(tf.a, tf.b, tf.c + c0*tf.a,
                    tf.d, tf.e, tf.f + r0*tf.e)

    if DOWNSAMPLE > 1:
        dem = dem[::DOWNSAMPLE, ::DOWNSAMPLE]
        tf = Affine(tf.a*DOWNSAMPLE, tf.b, tf.c,
                    tf.d, tf.e*DOWNSAMPLE, tf.f)

    valid = dem[~np.isnan(dem)]
    print(f"  Shape: {dem.shape}  |  Elev: {valid.min():.1f}–{valid.max():.1f} m")
    return dem, tf


def pixel_area_km2(tf, lat=39.5):
    return abs(tf.a)*111.139*math.cos(math.radians(lat))*abs(tf.e)*111.139


def rasterize_nuts3(geojson_path, dem_shape, tf):
    """Rasterize NUTS3 polygons onto DEM grid using shapely + rasterio.features."""
    with open(geojson_path) as f:
        data = json.load(f)

    # Auto-detect the NUTS3 code field in GeoJSON properties
    props = data["features"][0]["properties"]
    id_field = None
    for candidate in ["nuts3", "NUTS_ID", "NUTS3", "nuts_id", "code", "CODIGO"]:
        if candidate in props:
            id_field = candidate
            break
    if id_field is None:
        for k, v in props.items():
            if isinstance(v, str) and (v.startswith("PT") or len(v) <= 10):
                id_field = k
                break
    if id_field is None:
        id_field = list(props.keys())[0]

    print(f"  NUTS3 ID field: '{id_field}'")

    shapes, id_map = [], {}
    for i, feat in enumerate(data["features"]):
        geom = shp_shape(feat["geometry"])
        code = str(feat["properties"].get(id_field, f"region_{i}"))
        label = i + 1
        shapes.append((geom, label))
        id_map[label] = code

    raster = rasterio.features.rasterize(
        shapes, out_shape=dem_shape, transform=tf,
        fill=0, dtype=np.int16,
    )
    # Count total pixels per region (denominator for fraction_flooded)
    total_px = {code: int((raster == lbl).sum()) for lbl, code in id_map.items()}
    print(f"  Rasterized {len(id_map)} NUTS3 regions.")
    return raster, id_map, total_px


def load_gdp_per_nuts3(path):
    """Extract GDP 2022 (EUR) per NUTS3 from the Pillar 1 detail CSV."""
    df = pd.read_csv(path)
    print(f"  Columns found: {list(df.columns)}")
    gdp = df.groupby("nuts3")["gdp_2022_eur"].first().to_dict()
    print(f"  GDP loaded for {len(gdp)} regions.")
    return gdp


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def run_analysis():
    t0 = time.time()

    dem, tf           = load_dem()
    px_km2            = pixel_area_km2(tf)
    print("\nRasterizing NUTS3 …")
    nuts3_r, id_map, total_px = rasterize_nuts3(GEOJSON_PATH, dem.shape, tf)
    print("\nLoading GDP data …")
    gdp_data          = load_gdp_per_nuts3(P1_DETAIL_PATH)

    VARIANTS = [("baseline", 0.0), ("geoid_offset", GEOID_OFFSET)]

    area_rows, gdp_rows = [], []

    print("\nRunning flood analysis …")
    for scen in SCENARIOS:
        anchors = SLR_ANCHORS[scen]
        for year in KEY_YEARS:
            for variant, offset in VARIANTS:
                slr = slr_at_year(anchors, year, offset)
                flood_mask = (dem > 0) & (dem <= slr) & ~np.isnan(dem)
                total_px_flooded = int(flood_mask.sum())

                area_rows.append({
                    "scenario":        scen,
                    "year":            year,
                    "variant":         variant,
                    "slr_m":           round(slr, 4),
                    "flooded_pixels":  total_px_flooded,
                    "flooded_km2":     round(total_px_flooded * px_km2, 2),
                })

                # Per-region breakdown
                for label, code in id_map.items():
                    reg_mask    = nuts3_r == label
                    reg_flooded = int((flood_mask & reg_mask).sum())
                    reg_total   = total_px.get(code, 0)
                    frac        = reg_flooded / reg_total if reg_total > 0 else 0.0
                    gdp_eur     = gdp_data.get(code, 0.0)

                    gdp_rows.append({
                        "scenario":         scen,
                        "year":             year,
                        "variant":          variant,
                        "slr_m":            round(slr, 4),
                        "nuts3":            code,
                        "flooded_pixels":   reg_flooded,
                        "total_pixels":     reg_total,
                        "fraction_flooded": round(frac, 8),
                        "gdp_2022_eur":     gdp_eur,
                        "gdp_at_risk_eur":  round(frac * gdp_eur, 2),
                    })

            print(f"  {scen} / {year}  ✓")

    df_area = pd.DataFrame(area_rows)
    df_gdp  = pd.DataFrame(gdp_rows)

    # ── Summary: baseline vs offset ──────────────────────────────────────────
    summary_rows = []
    for scen in SCENARIOS:
        for year in KEY_YEARS:
            b = df_area[(df_area.scenario==scen)&(df_area.year==year)&
                        (df_area.variant=="baseline")].iloc[0]
            o = df_area[(df_area.scenario==scen)&(df_area.year==year)&
                        (df_area.variant=="geoid_offset")].iloc[0]

            gdp_b = df_gdp[(df_gdp.scenario==scen)&(df_gdp.year==year)&
                           (df_gdp.variant=="baseline")]["gdp_at_risk_eur"].sum()
            gdp_o = df_gdp[(df_gdp.scenario==scen)&(df_gdp.year==year)&
                           (df_gdp.variant=="geoid_offset")]["gdp_at_risk_eur"].sum()

            da_km2 = o.flooded_km2 - b.flooded_km2
            da_pct = da_km2 / b.flooded_km2 * 100 if b.flooded_km2 > 0 else 0.0
            dg     = gdp_o - gdp_b
            dg_pct = dg / gdp_b * 100 if gdp_b > 0 else 0.0

            summary_rows.append({
                "scenario":          scen,
                "year":              year,
                "slr_baseline_m":    b.slr_m,
                "slr_offset_m":      o.slr_m,
                "area_baseline_km2": b.flooded_km2,
                "area_offset_km2":   o.flooded_km2,
                "area_delta_km2":    round(da_km2, 2),
                "area_delta_pct":    round(da_pct, 1),
                "gdp_baseline_bn":   round(gdp_b / 1e9, 3),
                "gdp_offset_bn":     round(gdp_o / 1e9, 3),
                "gdp_delta_bn":      round(dg / 1e9, 3),
                "gdp_delta_pct":     round(dg_pct, 1),
            })

    df_summary = pd.DataFrame(summary_rows)

    # ── Save ─────────────────────────────────────────────────────────────────
    df_area.to_csv(PROJECT_DIR / "geoid_sensitivity_area.csv", index=False)
    df_gdp.to_csv( PROJECT_DIR / "geoid_sensitivity_gdp.csv",  index=False)
    df_summary.to_csv(PROJECT_DIR / "geoid_sensitivity_summary.csv", index=False)
    print("\n  Saved: geoid_sensitivity_area.csv")
    print(  "  Saved: geoid_sensitivity_gdp.csv")
    print(  "  Saved: geoid_sensitivity_summary.csv")

    # ── Terminal output ───────────────────────────────────────────────────────
    print("\n" + "═"*100)
    print("GEOID-OFFSET SENSITIVITY  —  Seeger & Minderhoud (Nature, 2026)  —  +0.15 m EU Atlantic")
    print("═"*100)
    print(f"\n{'Scenario':<12} {'Year':>5}  {'SLR':>6} {'SLR+G':>6}  "
          f"{'Area(km²)':>10} {'Area+G':>10} {'ΔArea':>8} {'Δ%':>6}  "
          f"{'GDP(€bn)':>9} {'GDP+G':>9} {'ΔGDP':>8} {'Δ%':>6}")
    print("─"*100)
    for _, r in df_summary.iterrows():
        print(f"{r.scenario:<12} {r.year:>5}  "
              f"{r.slr_baseline_m:>6.3f} {r.slr_offset_m:>6.3f}  "
              f"{r.area_baseline_km2:>10.1f} {r.area_offset_km2:>10.1f} "
              f"{r.area_delta_km2:>+8.1f} {r.area_delta_pct:>+5.1f}%  "
              f"{r.gdp_baseline_bn:>9.3f} {r.gdp_offset_bn:>9.3f} "
              f"{r.gdp_delta_bn:>+8.3f} {r.gdp_delta_pct:>+5.1f}%")

    print("\n" + "─"*100)
    print("HEADLINE — YEAR 2100:")
    print("─"*100)
    for scen in SCENARIOS:
        r = df_summary[(df_summary.scenario==scen)&(df_summary.year==2100)].iloc[0]
        print(f"  {scen:<12}  "
              f"Area:  {r.area_baseline_km2:>6.0f} → {r.area_offset_km2:>6.0f} km²  "
              f"({r.area_delta_pct:>+.0f}%)    "
              f"GDP at risk:  €{r.gdp_baseline_bn:.3f}bn → €{r.gdp_offset_bn:.3f}bn  "
              f"({r.gdp_delta_pct:>+.0f}%)")

    print(f"\nCompleted in {(time.time()-t0)/60:.1f} min.")
    print("═"*100)


if __name__ == "__main__":
    run_analysis()
