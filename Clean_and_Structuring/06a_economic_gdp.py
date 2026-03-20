"""
06a_economic_gdp.py  –  Pillar 1: GDP Area-Fraction Proxy  (Annual Time Series)
=================================================================================
Computes GDP at risk for every year 2025–2100 × 3 IPCC AR6 scenarios.

Strategy (memory-efficient, no per-year GeoTIFF files needed):
  1. Read the merged DEM once.
  2. Rasterize all 24 NUTS III regions onto the DEM grid once → region_labels.
  3. Extract only the "potentially floodable" coastal strip pixels
     (0 < elev ≤ 1.0 m) — typically ~250–300k pixels instead of 168M.
  4. Interpolate SLR for every year 2025–2100 from IPCC AR6 anchor values.
  5. For each year × scenario: threshold coastal pixels, count per region.
     This inner loop is pure NumPy and runs in < 1 second per year.

SLR source: IPCC AR6 WG1 Chapter 9 medians (North Atlantic / Iberian Peninsula).
  Anchor years: 2030, 2050, 2100. Intermediate years linearly interpolated.

Output: gdp_at_risk_pillar1.csv  (one row per year × scenario × NUTS III region)
        gdp_at_risk_pillar1_summary.csv  (aggregated by year × scenario)
"""

import json, sys
from pathlib import Path

import numpy as np
import pandas as pd
import openpyxl
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import rowcol
from shapely.geometry import shape as shapely_shape

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR      = Path(__file__).parent
DEM_PATH      = DATA_DIR / "dem_portugal_merged.tif"
GEOJSON_FILE  = DATA_DIR / "nuts3_wgs84.geojson"
PORDATA_NAMES = ["pordata.xlsx", "pordata-79025e9d.xlsx"]
GDP_YEAR      = 2022
YEAR_START    = 2025
YEAR_END      = 2100
OUTPUT_CSV    = DATA_DIR / "gdp_at_risk_pillar1.csv"
OUTPUT_SUM    = DATA_DIR / "gdp_at_risk_pillar1_summary.csv"

# ── SLR ANCHOR VALUES (metres above 1995–2014 baseline) ──────────────────
# Source: IPCC AR6 WG1 Ch. 9 medians, North Atlantic / Iberian Peninsula.
# All intermediate years are linearly interpolated.
SLR_ANCHORS = {
    "ssp126": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "ssp245": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "ssp585": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS  = ["ssp126", "ssp245", "ssp585"]
MAX_SLR    = 1.05   # slight buffer above max anchor value

def build_slr_series(anchors: dict, years: np.ndarray) -> np.ndarray:
    """Linearly interpolate SLR for every year from anchor dict."""
    anchor_yrs = np.array(sorted(anchors.keys()))
    anchor_vals = np.array([anchors[y] for y in anchor_yrs])
    return np.interp(years, anchor_yrs, anchor_vals)

# ── LOAD HELPERS ──────────────────────────────────────────────────────────
def read_nuts3(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"ERROR: {path.name} not found. Re-run the conversion step.")
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    out = []
    for feat in gj["features"]:
        p    = feat["properties"]
        name = p.get("nuts3") or p.get("NUTS3") or p.get("NAME_LATN")
        geom = shapely_shape(feat["geometry"])
        if name and geom and not geom.is_empty:
            out.append({"nuts3": str(name).strip(), "geometry": geom})
    return out

def find_pordata(data_dir: Path) -> Path:
    for n in PORDATA_NAMES:
        p = data_dir / n
        if p.exists():
            return p
    matches = sorted(data_dir.glob("pordata*.xlsx"))
    if matches:
        return matches[0]
    sys.exit(f"ERROR: No pordata*.xlsx in {data_dir}")

def read_gdp(xlsx_path: Path, year: int) -> dict[str, float]:
    wb  = openpyxl.load_workbook(str(xlsx_path), data_only=True)
    ws  = wb["Quadro"]
    rows = list(ws.iter_rows(values_only=True))
    hdr  = rows[11]
    col  = next((i for i, h in enumerate(hdr) if h == year), None)
    if col is None:
        sys.exit(f"Year {year} not in PORDATA")
    return {
        str(r[1]).strip(): float(r[col]) * 1_000
        for r in rows[12:]
        if r[0] == "NUTS III" and r[1] and r[col]
    }

# ── MAIN ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    years = np.arange(YEAR_START, YEAR_END + 1)   # 2025 … 2100

    # ── 1. Load inputs ────────────────────────────────────────────────────
    print("Loading NUTS III regions …")
    regions  = read_nuts3(GEOJSON_FILE)
    n_reg    = len(regions)
    reg_names = [r["nuts3"] for r in regions]
    print(f"  {n_reg} regions")

    print(f"Loading GDP {GDP_YEAR} …")
    gdp_dict = read_gdp(find_pordata(DATA_DIR), GDP_YEAR)
    gdp_arr  = np.array([gdp_dict.get(n, 0.0) for n in reg_names])
    matched  = sum(1 for n in reg_names if n in gdp_dict)
    print(f"  {matched}/{n_reg} names matched")

    print(f"Loading DEM: {DEM_PATH.name} …")
    if not DEM_PATH.exists():
        sys.exit(f"ERROR: DEM not found at {DEM_PATH}")
    with rasterio.open(DEM_PATH) as src:
        dem     = src.read(1)          # float32, shape (H, W)
        affine  = src.transform
        shape   = src.shape

    print(f"  DEM shape: {shape[0]}×{shape[1]}")

    # ── 2. Rasterize all regions ONCE → region_labels ────────────────────
    print("Rasterizing NUTS III regions onto DEM grid (one-time cost) …")
    region_labels = np.zeros(shape, dtype=np.int8)   # 0 = no region
    for i, r in enumerate(regions, start=1):
        mask = geometry_mask(
            [r["geometry"]], transform=affine,
            invert=True, out_shape=shape, all_touched=False
        )
        region_labels[mask] = i
        if i % 6 == 0:
            print(f"  … {i}/{n_reg}")
    print("  Done")

    # ── 3. Precompute total pixels per region (denominator for fraction) ──
    total_px_per_region = np.array(
        [(region_labels == i).sum() for i in range(1, n_reg + 1)]
    )   # shape (n_reg,)

    # ── 4. Extract coastal strip: only pixels that CAN flood (0 < z ≤ MAX_SLR)
    print(f"Extracting coastal strip (0 < elev ≤ {MAX_SLR} m) …")
    coastal_mask   = (dem > 0) & (dem <= MAX_SLR)
    coastal_elev   = dem[coastal_mask]              # (~250k values)
    coastal_region = region_labels[coastal_mask]    # region id per pixel

    # Precompute which coastal pixels belong to each region (boolean array)
    coastal_in_reg = np.stack(
        [coastal_region == i for i in range(1, n_reg + 1)], axis=0
    )   # shape (n_reg, n_coastal_pixels)

    print(f"  Coastal strip: {coastal_elev.size:,} pixels")

    # Free large arrays we no longer need
    del dem, region_labels, coastal_mask, coastal_region

    # ── 5. Annual loop ────────────────────────────────────────────────────
    print(f"\nComputing annual GDP at risk {YEAR_START}–{YEAR_END} …")

    rows_detail  = []
    rows_summary = []

    for scenario in SCENARIOS:
        slr_series = build_slr_series(SLR_ANCHORS[scenario], years)

        for yr, slr in zip(years, slr_series):
            # Flood mask on coastal strip only
            flooded = coastal_elev <= slr    # shape (n_coastal,)

            for i in range(n_reg):
                flooded_px = int((flooded & coastal_in_reg[i]).sum())
                total_px   = int(total_px_per_region[i])
                frac       = flooded_px / total_px if total_px > 0 else 0.0
                at_risk    = frac * gdp_arr[i]

                rows_detail.append({
                    "year"            : int(yr),
                    "scenario"        : scenario,
                    "slr_m"           : round(float(slr), 4),
                    "nuts3"           : reg_names[i],
                    "flooded_pixels"  : flooded_px,
                    "total_pixels"    : total_px,
                    "fraction_flooded": round(frac, 8),
                    "gdp_2022_eur"    : gdp_arr[i],
                    "gdp_at_risk_eur" : round(at_risk, 0),
                })

            total_at_risk = sum(
                r["gdp_at_risk_eur"] for r in rows_detail
                if r["year"] == int(yr) and r["scenario"] == scenario
            )
            rows_summary.append({
                "year"                : int(yr),
                "scenario"            : scenario,
                "slr_m"               : round(float(slr), 4),
                "total_gdp_at_risk_eur": round(total_at_risk, 0),
                "total_gdp_at_risk_bn" : round(total_at_risk / 1e9, 4),
            })

        # Print every 10 years for this scenario
        print(f"  {scenario.upper()}:")
        for r in rows_summary:
            if r["scenario"] == scenario and r["year"] % 10 == 0:
                print(f"    {r['year']}  SLR={r['slr_m']:.2f}m  → €{r['total_gdp_at_risk_bn']:.3f}B")

    # ── 6. Save ───────────────────────────────────────────────────────────
    df_detail  = pd.DataFrame(rows_detail)
    df_summary = pd.DataFrame(rows_summary)

    df_detail.to_csv(OUTPUT_CSV, index=False)
    df_summary.to_csv(OUTPUT_SUM, index=False)

    print(f"\nSaved detail  ({len(df_detail):,} rows): {OUTPUT_CSV.name}")
    print(f"Saved summary ({len(df_summary):,} rows): {OUTPUT_SUM.name}")

    # ── 7. Pivot preview ──────────────────────────────────────────────────
    pivot = df_summary.pivot(index="year", columns="scenario",
                             values="total_gdp_at_risk_bn")
    pivot.columns.name = None

    # Show every 5 years
    print("\n=== GDP AT RISK (€ billion) – every 5 years ===")
    print(pivot[pivot.index % 5 == 0].to_string())
    print("\nSource: IPCC AR6 WG1 Ch.9 medians, linearly interpolated.")
    print("NOTE: Indicative proxy. Pillar 2 (OSM infrastructure) is the primary metric.")
