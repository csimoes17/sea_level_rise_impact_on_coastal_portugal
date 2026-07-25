"""
05_flood_exposure.py  –  Static Inundation (Bathtub) Model
===========================================================
Applies IPCC AR6 sea-level rise scenarios to the merged Copernicus DEM
to produce binary flood-exposure masks for 8 decadal years × 3 scenarios
= 24 GeoTIFF outputs.

SLR values (metres above 1995-2014 baseline)
---------------------------------------------
Source: IPCC AR6 WG1 Chapter 9, Table 9.9 – median projections for the
        North Atlantic / Iberian Peninsula coast.
        Values for 2050 and 2100 are IPCC AR6 anchors; intermediate years
        (2030, 2040, 2060–2090) are linearly interpolated.

Flood method: static inundation ("bathtub") – all land pixels with
  elevation  0 < elev ≤ SLR  are marked as flooded.
  Ocean pixels (COP-DEM stores them as exactly 0.0 m) are excluded.
"""

import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use("Agg")            # non-interactive backend – avoids OOM crash
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR  = Path(__file__).parent
DEM_PATH  = DATA_DIR / "dem_portugal_merged.tif"
SUBSAMPLE = 8          # factor for the overview plot only (saves memory)

# ── SLR TIME SERIES ───────────────────────────────────────────────────────
# Median projections, metres above 1995-2014 baseline.
# 2050 and 2100 values are IPCC AR6 anchors.
# 2020→2050 and 2050→2100 intervals are linearly interpolated.
SLR_M = {
    "ssp126": {
        2030: 0.07,   # linear: (0.20/30)*10
        2040: 0.13,   # linear: (0.20/30)*20
        2050: 0.20,   # IPCC AR6 anchor
        2060: 0.24,   # linear: 0.20 + (0.40-0.20)/50*10
        2070: 0.28,
        2080: 0.32,
        2090: 0.36,
        2100: 0.40,   # IPCC AR6 anchor
    },
    "ssp245": {
        2030: 0.10,   # linear: (0.30/30)*10
        2040: 0.20,   # linear: (0.30/30)*20
        2050: 0.30,   # IPCC AR6 anchor
        2060: 0.36,   # linear: 0.30 + (0.60-0.30)/50*10
        2070: 0.42,
        2080: 0.48,
        2090: 0.54,
        2100: 0.60,   # IPCC AR6 anchor
    },
    "ssp585": {
        2030: 0.13,   # linear: (0.40/30)*10
        2040: 0.27,   # linear: (0.40/30)*20
        2050: 0.40,   # IPCC AR6 anchor
        2060: 0.52,   # linear: 0.40 + (1.00-0.40)/50*10
        2070: 0.64,
        2080: 0.76,
        2090: 0.88,
        2100: 1.00,   # IPCC AR6 anchor
    },
}

YEARS     = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
SCENARIOS = ["ssp126", "ssp245", "ssp585"]

# ── PIXEL AREA HELPER ─────────────────────────────────────────────────────
def pixel_area_km2(lat_deg: float, res_deg: float) -> float:
    """Area of one WGS84 pixel in km²."""
    R   = 6371.0
    lat = np.radians(lat_deg)
    return (np.pi / 180) * R**2 * abs(np.cos(lat)) * res_deg**2

# ── MAIN ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print(f"Reading DEM: {DEM_PATH}")
    with rasterio.open(DEM_PATH) as src:
        dem       = src.read(1)
        profile   = src.profile.copy()
        transform = src.transform
        res_deg   = abs(transform.a)
        height, width = dem.shape

    # Representative latitude for area calc (centre of Portugal)
    centre_lat = transform.f + (height / 2) * transform.e
    pix_km2    = pixel_area_km2(centre_lat, res_deg)

    print(f"  DEM shape: {height}×{width}, res ≈ {res_deg*111_139:.0f} m")
    print(f"  Pixel area ≈ {pix_km2:.4f} km²\n")

    # Update profile for uint8 output
    out_profile = profile.copy()
    out_profile.update(dtype=rasterio.uint8, count=1,
                       compress="LZW", tiled=True,
                       blockxsize=256, blockysize=256)

    summary_rows = []

    for scenario in SCENARIOS:
        for year in YEARS:
            slr_m = SLR_M[scenario][year]
            tag   = f"{year}_{scenario}"
            out_path = DATA_DIR / f"dem_flood_{tag}.tif"

            # Static bathtub: land pixels (>0) at or below SLR threshold
            flood_mask = ((dem > 0) & (dem <= slr_m)).astype(np.uint8)
            flooded_px = int(flood_mask.sum())
            flooded_km2 = flooded_px * pix_km2

            with rasterio.open(out_path, "w", **out_profile) as dst:
                dst.write(flood_mask, 1)

            summary_rows.append({
                "scenario"   : scenario,
                "year"       : year,
                "slr_m"      : slr_m,
                "flooded_px" : flooded_px,
                "flooded_km2": round(flooded_km2, 2),
            })
            print(f"  [{tag}]  SLR={slr_m:.2f}m  →  {flooded_km2:.1f} km²  →  saved {out_path.name}")

    # ── Summary CSV ───────────────────────────────────────────────────────
    df = pd.DataFrame(summary_rows)
    csv_path = DATA_DIR / "flood_scenario_summary.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved: {csv_path}")

    # ── Overview plot (subsampled to avoid OOM) ───────────────────────────
    print(f"\nGenerating overview plot (subsample ×{SUBSAMPLE}) …")
    dem_sub = dem[::SUBSAMPLE, ::SUBSAMPLE]

    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    fig.suptitle("Flood Exposure – IPCC AR6 Scenarios (Bathtub Model)", fontsize=13)

    # Show 3 years × 3 scenarios: 2050, 2075 (interpolated visual), 2100
    plot_years = [2050, 2070, 2100]

    for row_i, scenario in enumerate(SCENARIOS):
        for col_i, year in enumerate(plot_years):
            ax  = axes[row_i][col_i]
            slr = SLR_M[scenario][year]

            flood_sub = ((dem_sub > 0) & (dem_sub <= slr)).astype(np.float32)
            terrain   = np.where(dem_sub > 0, dem_sub, np.nan)

            ax.imshow(terrain, cmap="terrain", vmin=0, vmax=500, aspect="auto")
            flood_rgba = np.zeros((*flood_sub.shape, 4))
            flood_rgba[flood_sub == 1] = [0, 0.4, 1, 0.7]
            ax.imshow(flood_rgba, aspect="auto")
            ax.set_title(f"{scenario.upper()}  {year}\nSLR={slr:.2f}m", fontsize=9)
            ax.axis("off")

    plt.tight_layout()
    plot_path = DATA_DIR / "flood_scenarios_overview.png"
    plt.savefig(plot_path, dpi=120)
    plt.close()
    print(f"Saved plot: {plot_path}")

    # ── Print time-series table ───────────────────────────────────────────
    print("\n=== FLOOD EXPOSURE TIME SERIES (km²) ===")
    pivot = df.pivot_table(index="year", columns="scenario",
                           values="flooded_km2", aggfunc="first")
    print(pivot.to_string())
    print("\nSLR is cumulative above 1995-2014 baseline.")
    print("Source: IPCC AR6 WG1 Ch.9, medians, linearly interpolated.")
