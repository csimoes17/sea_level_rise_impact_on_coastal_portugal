"""
09_flood_animation.py – Sea-Level Rise Flood Inundation Animation (v3)
======================================================================
Generates MP4 animations of progressive coastal inundation along mainland
Portugal, 2025–2100, under three IPCC AR6 SSP scenarios.

NEW IN v3:  Geoid-offset sensitivity (Seeger & Minderhoud, Nature 2026).
  Adds +0.15 m to SLR to account for the gap between geoid-based elevation
  and measured mean sea level along European Atlantic coasts.

OUTPUTS  (saved to  PROJECT_DIR/animations/)
─────────────────────────────────────────────
  simple/          → 3 individual + 1 combined  (baseline)
  technical/       → 3 individual + 1 combined  (baseline)
  comparison/      → 2×3 grid: top=baseline, bottom=+geoid offset
                     (simple + technical)

REQUIREMENTS:  pip install rasterio matplotlib numpy
               conda install -c conda-forge ffmpeg
"""

from pathlib import Path
import json, math, time, warnings
warnings.filterwarnings("ignore")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
from matplotlib.colors import LightSource, Normalize
from matplotlib.patheffects import withStroke
from matplotlib.patches import Rectangle

import rasterio
from rasterio.merge import merge as rio_merge
from rasterio.transform import Affine


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

PROJECT_DIR = Path(__file__).parent

DEM1_PATH    = PROJECT_DIR / "COP DEM 1.tif"
DEM2_PATH    = PROJECT_DIR / "COP DEM 2.tif"
GEOJSON_PATH = PROJECT_DIR / "nuts3_wgs84.geojson"
OUT_DIR      = PROJECT_DIR / "animations"

YEAR_START = 2025
YEAR_END   = 2100
FPS        = 5

DOWNSAMPLE = 4
DPI_SIMPLE = 120
DPI_TECH   = 150

CLIP_BOUNDS = {
    "lon_min": -9.7, "lon_max": -7.1,
    "lat_min": 36.8, "lat_max": 42.3,
}

# IPCC AR6 SLR anchors (m above 2020 baseline)
SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS = list(SLR_ANCHORS.keys())

# Geoid offset (Seeger & Minderhoud, Nature 2026)
# European Atlantic coast: ~0.15 m (conservative; global mean is 0.24–0.27 m)
GEOID_OFFSET = 0.15

SCENARIO_COLOR = {
    "SSP1-2.6": "#29B6F6", "SSP2-4.5": "#FFA726", "SSP5-8.5": "#EF5350",
}

# Flood colour: RED with yellow-orange leading edge
FLOOD_FRESH = np.array([1.00, 0.85, 0.30])
FLOOD_MID   = np.array([0.95, 0.20, 0.10])
FLOOD_OLD   = np.array([0.60, 0.05, 0.05])
FRESH_YEARS = 8
FLOOD_LEGEND_COLOR = "#E53935"

PE_HEAVY = [withStroke(linewidth=3, foreground="black")]
PE_LIGHT = [withStroke(linewidth=2, foreground="black")]


# ══════════════════════════════════════════════════════════════════════════════
#  1.  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_dem():
    print("Loading & merging DEM tiles …")
    with rasterio.open(DEM2_PATH) as s2, rasterio.open(DEM1_PATH) as s1:
        arr, tf = rio_merge([s2, s1])
    dem = arr[0].astype(np.float32)
    for nd in (-32768.0, 32767.0, -9999.0):
        dem[np.abs(dem - nd) < 0.5] = np.nan
    h_raw, w_raw = dem.shape
    if CLIP_BOUNDS is not None:
        lons = tf.c + np.arange(w_raw) * tf.a
        lats = tf.f + np.arange(h_raw) * tf.e
        c0 = int(np.searchsorted(lons, CLIP_BOUNDS["lon_min"]))
        c1 = int(np.searchsorted(lons, CLIP_BOUNDS["lon_max"]))
        r0 = int(np.searchsorted(-lats, -CLIP_BOUNDS["lat_max"]))
        r1 = int(np.searchsorted(-lats, -CLIP_BOUNDS["lat_min"]))
        c0, c1 = max(0, c0), min(w_raw, c1)
        r0, r1 = max(0, r0), min(h_raw, r1)
        dem = dem[r0:r1, c0:c1]
        tf = Affine(tf.a, tf.b, tf.c + c0*tf.a, tf.d, tf.e, tf.f + r0*tf.e)
    dem = dem[::DOWNSAMPLE, ::DOWNSAMPLE]
    tf = Affine(tf.a*DOWNSAMPLE, tf.b, tf.c, tf.d, tf.e*DOWNSAMPLE, tf.f)
    h, w = dem.shape
    extent = [tf.c, tf.c + tf.a*w, tf.f + tf.e*h, tf.f]
    valid = dem[~np.isnan(dem)]
    print(f"  Shape: {dem.shape}  |  Elev: {valid.min():.1f}–{valid.max():.1f} m")
    return dem, tf, extent


def load_nuts3():
    if not GEOJSON_PATH.exists():
        return None
    with open(GEOJSON_PATH, "r") as f:
        data = json.load(f)
    rings = []
    for feat in data.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            continue
        if geom["type"] == "Polygon":
            rings.append(geom["coordinates"][0])
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                rings.append(poly[0])
    print(f"  Loaded {len(rings)} NUTS3 rings.")
    return rings


# ══════════════════════════════════════════════════════════════════════════════
#  2.  TERRAIN
# ══════════════════════════════════════════════════════════════════════════════

def make_terrain_rgba(dem):
    dem_f = np.where(np.isnan(dem), 0.0, dem)
    ls = LightSource(azdeg=315, altdeg=45)
    shade = ls.hillshade(dem_f, vert_exag=3, dx=1, dy=1)
    norm = Normalize(vmin=0.0, vmax=400.0)
    rgb = plt.cm.terrain(norm(np.clip(dem_f, 0, 400)))[:, :, :3]
    rgba = np.zeros((*dem.shape, 4), dtype=np.float32)
    for c in range(3):
        rgba[:, :, c] = rgb[:, :, c] * (0.55 + 0.45 * shade)
    rgba[:, :, 3] = 1.0
    SEA = [0.08, 0.15, 0.25, 1.0]
    rgba[dem <= 0] = SEA
    rgba[np.isnan(dem)] = SEA
    return rgba


# ══════════════════════════════════════════════════════════════════════════════
#  3.  SLR & FIRST-FLOOD-YEAR
# ══════════════════════════════════════════════════════════════════════════════

def build_slr_dict(anchors, offset=0.0):
    """Interpolate SLR for each year. Optional offset added to all values."""
    years = np.arange(YEAR_START, YEAR_END + 1)
    ay = np.array(sorted(anchors))
    av = np.array([anchors[y] for y in ay])
    vals = np.interp(years, ay, av) + offset
    return {int(y): float(v) for y, v in zip(years, vals)}


def first_flood_year_map(dem, slr):
    years = sorted(slr)
    slr_vals = np.array([slr[y] for y in years])
    max_slr = slr_vals[-1]
    ffy = np.zeros(dem.shape, dtype=np.int16)
    ok = (dem > 0) & (dem <= max_slr) & ~np.isnan(dem)
    if ok.any():
        elev = dem[ok]
        idx = np.searchsorted(slr_vals, elev, side="left")
        idx = np.clip(idx, 0, len(years) - 1)
        found = np.where(slr_vals[idx] >= elev,
                         np.array(years, dtype=np.int16)[idx], 0)
        ffy[ok] = found
    return ffy


def pixel_area_km2(tf, lat=39.5):
    return abs(tf.a)*111.139*math.cos(math.radians(lat))*abs(tf.e)*111.139


def flooded_km2(ffy, year, px_km2):
    return float(((ffy > 0) & (ffy <= year)).sum() * px_km2)


# ══════════════════════════════════════════════════════════════════════════════
#  4.  FLOOD RGBA (RED)
# ══════════════════════════════════════════════════════════════════════════════

def flood_rgba(ffy, year):
    overlay = np.zeros((*ffy.shape, 4), dtype=np.float32)
    mask = (ffy > 0) & (ffy <= year)
    if not mask.any():
        return overlay
    age = (year - ffy[mask]).astype(np.float32)
    max_age = max(float(year - YEAR_START), 1.0)
    fresh_n = np.clip(age / FRESH_YEARS, 0.0, 1.0)
    old_n = np.clip((age - FRESH_YEARS) / max(max_age - FRESH_YEARS, 1.0), 0.0, 1.0)
    r = FLOOD_FRESH[0] + fresh_n*(FLOOD_MID[0]-FLOOD_FRESH[0]) + old_n*(FLOOD_OLD[0]-FLOOD_MID[0])
    g = FLOOD_FRESH[1] + fresh_n*(FLOOD_MID[1]-FLOOD_FRESH[1]) + old_n*(FLOOD_OLD[1]-FLOOD_MID[1])
    b = FLOOD_FRESH[2] + fresh_n*(FLOOD_MID[2]-FLOOD_FRESH[2]) + old_n*(FLOOD_OLD[2]-FLOOD_MID[2])
    overlay[mask, 0] = np.clip(r, 0, 1)
    overlay[mask, 1] = np.clip(g, 0, 1)
    overlay[mask, 2] = np.clip(b, 0, 1)
    overlay[mask, 3] = 0.82 + 0.13 * fresh_n
    return overlay


# ══════════════════════════════════════════════════════════════════════════════
#  5.  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def overlay_nuts3(ax, rings, color="white", lw=0.5, alpha=0.55):
    if rings is None:
        return
    for ring in rings:
        ax.plot([p[0] for p in ring], [p[1] for p in ring],
                color=color, linewidth=lw, alpha=alpha, solid_capstyle="round")


def _setup_ax(ax, terrain_rgba, ffy, extent):
    ax.set_facecolor("#0d1117"); ax.set_axis_off()
    ax.imshow(terrain_rgba, extent=extent, origin="upper",
              interpolation="bilinear", aspect="auto")
    return ax.imshow(np.zeros((*ffy.shape, 4), dtype=np.float32),
                     extent=extent, origin="upper",
                     interpolation="bilinear", aspect="auto")


def _progress_bar(ax, color):
    ax.add_patch(Rectangle((0.01, 0.010), 0.98, 0.007,
                            transform=ax.transAxes, facecolor="#333333",
                            alpha=0.75, zorder=10, clip_on=False))
    return ax.add_patch(Rectangle((0.01, 0.010), 0.0, 0.007,
                                   transform=ax.transAxes, facecolor=color,
                                   alpha=0.90, zorder=11, clip_on=False))


def _flood_legend(ax, x=0.03, y=0.81):
    ax.add_patch(Rectangle((x, y), 0.025, 0.013, transform=ax.transAxes,
                            facecolor=FLOOD_LEGEND_COLOR, alpha=0.9, zorder=12))
    ax.text(x+0.035, y+0.006, "Flooded area", transform=ax.transAxes,
            fontsize=9, color="#cccccc", va="center", path_effects=PE_LIGHT)


def save_anim(anim, path, dpi):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        writer = FFMpegWriter(fps=FPS, codec="libx264",
                              extra_args=["-pix_fmt", "yuv420p", "-crf", "20"])
        anim.save(str(path), writer=writer, dpi=dpi)
        print(f"  ✓  {path.name}  ({path.stat().st_size/1e6:.1f} MB)")
    except Exception as exc:
        gif = path.with_suffix(".gif")
        print(f"  ffmpeg error → GIF fallback")
        anim.save(str(gif), writer=PillowWriter(fps=FPS), dpi=dpi)
        print(f"  ✓  {gif.name}  ({gif.stat().st_size/1e6:.1f} MB)")


# ══════════════════════════════════════════════════════════════════════════════
#  6.  SIMPLE INDIVIDUAL
# ══════════════════════════════════════════════════════════════════════════════

def anim_simple_individual(scen, terrain_rgba, ffy, slr_d, extent, rings, out_dir,
                           label_suffix="", folder="simple"):
    years = list(range(YEAR_START, YEAR_END + 1))
    color = SCENARIO_COLOR[scen]
    fig, ax = plt.subplots(figsize=(10, 12))
    fig.patch.set_facecolor("#0d1117")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fim = _setup_ax(ax, terrain_rgba, ffy, extent)
    overlay_nuts3(ax, rings, color="white", lw=0.5, alpha=0.45)
    bar_fg = _progress_bar(ax, color)
    _flood_legend(ax, x=0.03, y=0.81)
    display_name = scen + label_suffix
    year_t = ax.text(0.03, 0.95, str(YEAR_START), transform=ax.transAxes,
                     fontsize=36, fontweight="bold", color="white", va="top",
                     path_effects=PE_HEAVY)
    slr_t = ax.text(0.03, 0.88, "SLR: +0.00 m", transform=ax.transAxes,
                    fontsize=14, color=color, va="top", path_effects=PE_LIGHT)
    ax.text(0.97, 0.95, display_name, transform=ax.transAxes, fontsize=12,
            fontweight="bold", color=color, va="top", ha="right",
            path_effects=PE_LIGHT)
    ax.text(0.50, 0.017,
            "Sea-Level Rise Inundation  ·  Coastal Portugal  ·  IPCC AR6",
            transform=ax.transAxes, fontsize=8.5, color="#aaaaaa",
            va="bottom", ha="center")

    def update(frame):
        yr = years[frame]
        frac = (yr - YEAR_START) / (YEAR_END - YEAR_START)
        fim.set_data(flood_rgba(ffy, yr))
        year_t.set_text(str(yr))
        slr_t.set_text(f"SLR: +{slr_d[yr]:.2f} m")
        bar_fg.set_width(0.98 * frac)

    anim = FuncAnimation(fig, update, frames=len(years),
                         interval=1000/FPS, blit=False)
    key = scen.replace("-","").replace(".","").lower()
    sfx = "_geoid" if label_suffix else ""
    save_anim(anim, out_dir / folder / f"flood_{key}{sfx}_simple.mp4", DPI_SIMPLE)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
#  7.  TECHNICAL INDIVIDUAL
# ══════════════════════════════════════════════════════════════════════════════

def anim_tech_individual(scen, terrain_rgba, ffy, slr_d, extent,
                         rings, px_km2, out_dir,
                         label_suffix="", folder="technical"):
    years = list(range(YEAR_START, YEAR_END + 1))
    color = SCENARIO_COLOR[scen]
    display_name = scen + label_suffix

    fig = plt.figure(figsize=(14, 12), facecolor="#0d1117")
    gs = gridspec.GridSpec(1, 2, width_ratios=[4.2, 1], left=0.005, right=0.995,
                           top=0.97, bottom=0.03, wspace=0.015)
    ax_m = fig.add_subplot(gs[0])
    ax_p = fig.add_subplot(gs[1])

    fim = _setup_ax(ax_m, terrain_rgba, ffy, extent)
    overlay_nuts3(ax_m, rings, color="white", lw=0.55, alpha=0.50)
    bar_fg = _progress_bar(ax_m, color)
    _flood_legend(ax_m, x=0.03, y=0.87)
    year_t = ax_m.text(0.03, 0.95, str(YEAR_START), transform=ax_m.transAxes,
                       fontsize=42, fontweight="bold", color="white", va="top",
                       path_effects=PE_HEAVY)

    ax_p.set_facecolor("#0d1117"); ax_p.set_axis_off()
    kw = dict(transform=ax_p.transAxes, ha="left", va="top", fontfamily="monospace")
    ax_p.text(0.06, 0.97, display_name, fontsize=13, fontweight="bold",
              color=color, **kw)
    ax_p.text(0.06, 0.92, "─"*19, fontsize=7, color="#444444", **kw)
    ax_p.text(0.06, 0.88, "SEA-LEVEL RISE", fontsize=8, color="#888888", **kw)
    slr_v = ax_p.text(0.06, 0.83, "+0.000 m", fontsize=16, fontweight="bold",
                      color=color, **kw)
    ax_p.text(0.06, 0.77, "─"*19, fontsize=7, color="#444444", **kw)
    ax_p.text(0.06, 0.73, "FLOODED AREA", fontsize=8, color="#888888", **kw)
    area_v = ax_p.text(0.06, 0.68, "0 km²", fontsize=15, fontweight="bold",
                       color=FLOOD_LEGEND_COLOR, **kw)
    pct_v = ax_p.text(0.06, 0.63, "0.0% of coastal zone", fontsize=9,
                      color="#aaaaaa", **kw)
    ax_p.text(0.06, 0.57, "─"*19, fontsize=7, color="#444444", **kw)
    ax_p.text(0.06, 0.53, "NEWLY FLOODED", fontsize=8, color="#888888", **kw)
    new_v = ax_p.text(0.06, 0.48, "+0 km²", fontsize=13, color="#cccccc", **kw)
    ax_p.text(0.06, 0.34, "─"*19, fontsize=7, color="#444444", **kw)
    ax_p.text(0.06, 0.30,
              "Methodology\n─────────────\n"
              "Static bathtub\nmodel · IPCC AR6\n"
              "Copernicus DEM\nGLO-30 (30 m)\n"
              f"Rendered at\n{30*DOWNSAMPLE} m",
              fontsize=6.5, color="#555555", **kw)
    if label_suffix:
        ax_p.text(0.06, 0.14, "─"*19, fontsize=7, color="#444444", **kw)
        ax_p.text(0.06, 0.10,
                  f"Geoid offset\n+{GEOID_OFFSET:.2f} m\n(Minderhoud &\nSeeger 2026)",
                  fontsize=7, color="#FF8A65", **kw)

    fig.text(0.5, 0.008,
             "Sea-Level Rise Inundation  ·  Coastal Portugal  ·  IPCC AR6",
             ha="center", fontsize=8.5, color="#666666")

    total_coastal_km2 = float((ffy > 0).sum() * px_km2)
    prev = [0.0]

    def update(frame):
        yr = years[frame]
        km2 = flooded_km2(ffy, yr, px_km2)
        new = max(km2 - prev[0], 0.0)
        pct = (km2/total_coastal_km2*100) if total_coastal_km2 > 0 else 0.0
        frac = (yr - YEAR_START) / (YEAR_END - YEAR_START)
        prev[0] = km2
        fim.set_data(flood_rgba(ffy, yr))
        year_t.set_text(str(yr))
        bar_fg.set_width(0.98 * frac)
        slr_v.set_text(f"+{slr_d[yr]:.3f} m")
        area_v.set_text(f"{km2:,.0f} km²")
        pct_v.set_text(f"{pct:.1f}% of coastal zone")
        new_v.set_text(f"+{new:,.0f} km²")

    anim = FuncAnimation(fig, update, frames=len(years),
                         interval=1000/FPS, blit=False)
    key = scen.replace("-","").replace(".","").lower()
    sfx = "_geoid" if label_suffix else ""
    save_anim(anim, out_dir / folder / f"flood_{key}{sfx}_technical.mp4", DPI_TECH)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
#  8.  SIMPLE COMBINED (3 panels)
# ══════════════════════════════════════════════════════════════════════════════

def anim_simple_combined(terrain_rgba, ffy_all, slr_all, extent, rings, out_dir):
    years = list(range(YEAR_START, YEAR_END + 1))
    ref_ffy = list(ffy_all.values())[0]
    fig, axes = plt.subplots(1, 3, figsize=(24, 12))
    fig.patch.set_facecolor("#0d1117")
    plt.subplots_adjust(left=0.003, right=0.997, top=0.93, bottom=0.04, wspace=0.01)
    fims, year_txts, slr_txts, bar_fgs = [], [], [], []
    for i, scen in enumerate(SCENARIOS):
        ax = axes[i]; color = SCENARIO_COLOR[scen]
        fims.append(_setup_ax(ax, terrain_rgba, ref_ffy, extent))
        overlay_nuts3(ax, rings, color="white", lw=0.40, alpha=0.40)
        ax.set_title(scen, fontsize=14, fontweight="bold", color=color, pad=6)
        year_txts.append(ax.text(0.04, 0.94, str(YEAR_START),
                     transform=ax.transAxes, fontsize=24, fontweight="bold",
                     color="white", va="top", path_effects=PE_HEAVY))
        slr_txts.append(ax.text(0.04, 0.87, "+0.00 m", transform=ax.transAxes,
                     fontsize=12, color=color, va="top", path_effects=PE_LIGHT))
        bar_fgs.append(_progress_bar(ax, color))
        _flood_legend(ax, x=0.04, y=0.80)
    fig.text(0.5, 0.010,
             "Sea-Level Rise Inundation  ·  Coastal Portugal  ·  IPCC AR6",
             ha="center", fontsize=9, color="#888888")

    def update(frame):
        yr = years[frame]; frac = (yr-YEAR_START)/(YEAR_END-YEAR_START)
        for i, scen in enumerate(SCENARIOS):
            fims[i].set_data(flood_rgba(ffy_all[scen], yr))
            year_txts[i].set_text(str(yr))
            slr_txts[i].set_text(f"+{slr_all[scen][yr]:.2f} m")
            bar_fgs[i].set_width(0.98*frac)

    anim = FuncAnimation(fig, update, frames=len(years), interval=1000/FPS, blit=False)
    save_anim(anim, out_dir / "simple" / "flood_combined_simple.mp4", DPI_SIMPLE)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
#  9.  TECHNICAL COMBINED (3 panels + stats)
# ══════════════════════════════════════════════════════════════════════════════

def anim_tech_combined(terrain_rgba, ffy_all, slr_all, extent, px_km2, rings, out_dir):
    years = list(range(YEAR_START, YEAR_END + 1))
    ref_ffy = list(ffy_all.values())[0]
    fig = plt.figure(figsize=(24, 13), facecolor="#0d1117")
    gs = gridspec.GridSpec(2, 3, height_ratios=[10, 0.85], hspace=0.04, wspace=0.01,
                           left=0.003, right=0.997, top=0.93, bottom=0.06)
    axes_map = [fig.add_subplot(gs[0, i]) for i in range(3)]
    axes_stat = [fig.add_subplot(gs[1, i]) for i in range(3)]
    fims, year_txts, stat_txts, bar_fgs = [], [], [], []
    for i, scen in enumerate(SCENARIOS):
        ax = axes_map[i]; color = SCENARIO_COLOR[scen]
        fims.append(_setup_ax(ax, terrain_rgba, ref_ffy, extent))
        overlay_nuts3(ax, rings, color="white", lw=0.45, alpha=0.45)
        ax.set_title(scen, fontsize=14, fontweight="bold", color=color, pad=6)
        year_txts.append(ax.text(0.04, 0.94, str(YEAR_START),
                     transform=ax.transAxes, fontsize=30, fontweight="bold",
                     color="white", va="top", path_effects=PE_HEAVY))
        bar_fgs.append(_progress_bar(ax, color))
        _flood_legend(ax, x=0.04, y=0.87)
        ax_s = axes_stat[i]; ax_s.set_facecolor("#111111"); ax_s.set_axis_off()
        stat_txts.append(ax_s.text(0.5, 0.5,
                       "SLR +0.000 m  │  Flooded: 0 km²",
                       transform=ax_s.transAxes, ha="center", va="center",
                       fontsize=10, color=color, fontfamily="monospace"))
    fig.text(0.5, 0.010,
             "Sea-Level Rise Inundation  ·  Coastal Portugal  ·  IPCC AR6",
             ha="center", fontsize=8, color="#666666")
    prev = [0.0, 0.0, 0.0]

    def update(frame):
        yr = years[frame]; frac = (yr-YEAR_START)/(YEAR_END-YEAR_START)
        for i, scen in enumerate(SCENARIOS):
            km2 = flooded_km2(ffy_all[scen], yr, px_km2)
            prev[i] = km2
            fims[i].set_data(flood_rgba(ffy_all[scen], yr))
            year_txts[i].set_text(str(yr))
            bar_fgs[i].set_width(0.98*frac)
            stat_txts[i].set_text(
                f"SLR +{slr_all[scen][yr]:.3f} m  │  Flooded: {km2:,.0f} km²")

    anim = FuncAnimation(fig, update, frames=len(years), interval=1000/FPS, blit=False)
    save_anim(anim, out_dir / "technical" / "flood_combined_technical.mp4", DPI_TECH)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
#  10.  COMPARISON GRID  (2 rows × 3 cols: baseline vs geoid offset)
# ══════════════════════════════════════════════════════════════════════════════

def anim_comparison_grid(terrain_rgba, ffy_base, ffy_offset,
                         slr_base, slr_offset,
                         extent, px_km2, rings, out_dir, version="simple"):
    """
    2×3 grid animation:
      Row 0 = IPCC AR6 baseline
      Row 1 = +0.15 m geoid offset (Seeger & Minderhoud 2026)
    """
    years = list(range(YEAR_START, YEAR_END + 1))
    ref_ffy = list(ffy_base.values())[0]
    is_tech = (version == "technical")
    dpi = DPI_TECH if is_tech else DPI_SIMPLE

    fig = plt.figure(figsize=(24, 16), facecolor="#0d1117")
    gs = gridspec.GridSpec(2, 3, hspace=0.06, wspace=0.01,
                           left=0.003, right=0.997, top=0.91, bottom=0.04)

    row_labels = ["IPCC AR6 Baseline", f"+ Geoid Offset (+{GEOID_OFFSET:.2f} m)"]
    all_ffy = [ffy_base, ffy_offset]
    all_slr = [slr_base, slr_offset]

    fims, year_txts, slr_txts, area_txts = [], [], [], []

    for row in range(2):
        for col, scen in enumerate(SCENARIOS):
            ax = fig.add_subplot(gs[row, col])
            color = SCENARIO_COLOR[scen]
            ffy_dict = all_ffy[row]

            fim = _setup_ax(ax, terrain_rgba, ref_ffy, extent)
            fims.append(fim)
            overlay_nuts3(ax, rings, color="white", lw=0.35, alpha=0.35)
            _flood_legend(ax, x=0.04, y=0.78)

            # Title: only on top row
            if row == 0:
                ax.set_title(scen, fontsize=14, fontweight="bold",
                             color=color, pad=6)

            yt = ax.text(0.04, 0.94, str(YEAR_START), transform=ax.transAxes,
                         fontsize=22, fontweight="bold", color="white", va="top",
                         path_effects=PE_HEAVY)
            year_txts.append(yt)

            st = ax.text(0.04, 0.87, "+0.00 m", transform=ax.transAxes,
                         fontsize=11, color=color, va="top", path_effects=PE_LIGHT)
            slr_txts.append(st)

            if is_tech:
                at = ax.text(0.96, 0.04, "0 km²", transform=ax.transAxes,
                             fontsize=11, color="#ffffff", va="bottom", ha="right",
                             fontweight="bold", path_effects=PE_LIGHT)
            else:
                at = None
            area_txts.append(at)

    # Row labels on left side
    fig.text(0.008, 0.72, row_labels[0], fontsize=12, color="#aaaaaa",
             rotation=90, va="center", ha="center")
    fig.text(0.008, 0.28, row_labels[1], fontsize=12, color="#FF8A65",
             rotation=90, va="center", ha="center", fontweight="bold")

    fig.suptitle(
        "Sea-Level Rise Inundation: Baseline vs Geoid-Corrected "
        f"(+{GEOID_OFFSET:.2f} m, Seeger & Minderhoud 2026)",
        fontsize=14, color="white", y=0.96)
    fig.text(0.5, 0.010,
             "Coastal Portugal  ·  IPCC AR6  ·  Static Bathtub Model  "
             "·  Copernicus DEM GLO-30",
             ha="center", fontsize=9, color="#888888")

    def update(frame):
        yr = years[frame]
        idx = 0
        for row in range(2):
            for col, scen in enumerate(SCENARIOS):
                slr_d = all_slr[row][scen]
                ffy_d = all_ffy[row][scen]
                fims[idx].set_data(flood_rgba(ffy_d, yr))
                year_txts[idx].set_text(str(yr))
                slr_txts[idx].set_text(f"+{slr_d[yr]:.2f} m")
                if area_txts[idx] is not None:
                    km2 = flooded_km2(ffy_d, yr, px_km2)
                    area_txts[idx].set_text(f"{km2:,.0f} km²")
                idx += 1

    anim = FuncAnimation(fig, update, frames=len(years),
                         interval=1000/FPS, blit=False)
    save_anim(anim, out_dir / "comparison" / f"flood_comparison_{version}.mp4", dpi)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    for d in ["simple", "technical", "comparison"]:
        (OUT_DIR / d).mkdir(parents=True, exist_ok=True)

    dem, tf, extent = load_dem()

    print("\nRendering hillshade terrain …")
    terrain_rgba = make_terrain_rgba(dem)
    print("  Done.")

    # ── SLR series: baseline + offset ────────────────────────────────────────
    slr_base   = {s: build_slr_dict(SLR_ANCHORS[s], offset=0.0)
                  for s in SCENARIOS}
    slr_offset = {s: build_slr_dict(SLR_ANCHORS[s], offset=GEOID_OFFSET)
                  for s in SCENARIOS}

    # ── First-flood-year maps: baseline + offset ──────────────────────────────
    print("\nComputing first-flood-year maps …")
    px_km2 = pixel_area_km2(tf)
    ffy_base, ffy_offset = {}, {}

    for scen in SCENARIOS:
        ffy_base[scen]   = first_flood_year_map(dem, slr_base[scen])
        ffy_offset[scen] = first_flood_year_map(dem, slr_offset[scen])
        nb = int((ffy_base[scen] > 0).sum())
        no = int((ffy_offset[scen] > 0).sum())
        print(f"  {scen}:  baseline {nb:,} px ({nb*px_km2:,.1f} km²)  │  "
              f"+geoid {no:,} px ({no*px_km2:,.1f} km²)  "
              f"[+{(no-nb)*px_km2:,.1f} km², +{(no-nb)/max(nb,1)*100:.0f}%]")

    print("\nLoading NUTS3 boundaries …")
    rings = load_nuts3()

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*64)
    print("GENERATING BASELINE ANIMATIONS")
    print("═"*64)

    for scen in SCENARIOS:
        print(f"\n[SIMPLE]     {scen}")
        anim_simple_individual(scen, terrain_rgba, ffy_base[scen],
                               slr_base[scen], extent, rings, OUT_DIR)
    for scen in SCENARIOS:
        print(f"\n[TECHNICAL]  {scen}")
        anim_tech_individual(scen, terrain_rgba, ffy_base[scen],
                             slr_base[scen], extent, rings, px_km2, OUT_DIR)
    print("\n[SIMPLE COMBINED]")
    anim_simple_combined(terrain_rgba, ffy_base, slr_base, extent, rings, OUT_DIR)
    print("\n[TECHNICAL COMBINED]")
    anim_tech_combined(terrain_rgba, ffy_base, slr_base, extent, px_km2, rings, OUT_DIR)

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*64)
    print(f"GENERATING GEOID-OFFSET ANIMATIONS  (+{GEOID_OFFSET:.2f} m)")
    print("═"*64)

    sfx = f"\n+{GEOID_OFFSET:.2f}m geoid"
    for scen in SCENARIOS:
        print(f"\n[SIMPLE+GEOID]     {scen}")
        anim_simple_individual(scen, terrain_rgba, ffy_offset[scen],
                               slr_offset[scen], extent, rings, OUT_DIR,
                               label_suffix=sfx, folder="simple")
    for scen in SCENARIOS:
        print(f"\n[TECHNICAL+GEOID]  {scen}")
        anim_tech_individual(scen, terrain_rgba, ffy_offset[scen],
                             slr_offset[scen], extent, rings, px_km2, OUT_DIR,
                             label_suffix=sfx, folder="technical")

    # ══════════════════════════════════════════════════════════════════════════
    print("\n" + "═"*64)
    print("GENERATING COMPARISON GRIDS  (baseline vs geoid)")
    print("═"*64)

    print("\n[COMPARISON / SIMPLE]")
    anim_comparison_grid(terrain_rgba, ffy_base, ffy_offset,
                         slr_base, slr_offset,
                         extent, px_km2, rings, OUT_DIR, version="simple")
    print("\n[COMPARISON / TECHNICAL]")
    anim_comparison_grid(terrain_rgba, ffy_base, ffy_offset,
                         slr_base, slr_offset,
                         extent, px_km2, rings, OUT_DIR, version="technical")

    mins = (time.time() - t0) / 60
    print(f"\n{'═'*64}")
    print(f"ALL DONE  ({mins:.1f} min total)")
    print(f"Output: {OUT_DIR}")
    print(f"  simple/      → baseline + geoid-offset individual")
    print(f"  technical/   → baseline + geoid-offset individual")
    print(f"  comparison/  → 2×3 grids (baseline vs geoid)")
    print(f"{'═'*64}")
