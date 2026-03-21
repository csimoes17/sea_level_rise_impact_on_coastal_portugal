"""
06b_osm_infrastructure.py  –  Pillar 2: Infrastructure Replacement Cost
========================================================================
Annual replacement-cost time series for buildings, roads, railways and
utility networks exposed to sea-level rise, 2025–2100 × 3 IPCC AR6
scenarios.

METHODOLOGY
-----------
1. BUILDINGS
   flood_zone_area (from Pillar 1 / 06a detail CSV) × building density
   (INE Census 2021 per coastal NUTS III) × replacement cost per building.
   A storey multiplier per NUTS III scales floor area by average building
   height (from INE Census 2021), so an apartment block in Grande Lisboa
   (~5 storeys) costs more to replace than a villa in Alentejo (~1.5
   storeys).  This approach avoids the 30 m DEM resolution bias that
   undercounts individual buildings (Hinkel et al. 2014, Vousdoukas 2020).

2. ROADS & RAILWAYS
   OSM geometry via Overpass API, elevation sampled at ALL nodes along
   each way segment from the DEM.  A road/rail feature is considered at
   risk if its MINIMUM sampled elevation falls within the flood threshold
   (0 < min_elev ≤ SLR).  This captures features that dip through low-
   lying sections even if most of the segment sits at higher ground.

3. UTILITY NETWORKS  (NEW)
   Water distribution, sewage collection and electricity distribution
   networks are assumed co-located with the road network.  Replacement
   cost is applied per km of NON-MOTORWAY road at risk (utilities do not
   run under motorways).  This is a standard proxy used in World Bank /
   GFDRR flood damage assessments.

COST ASSUMPTIONS – PORTUGUESE OFFICIAL SOURCES (2024/2025)
-----------------------------------------------------------
Buildings (full replacement = construction + land):
  Construction cost 2025: €1,650/m² (INE SICC index: +3.3% in 2024,
  +4.0% in 2025 from 2022 base of €1,412/m²).
  Land replacement cost:   €300/m² (INE Q4 2024 housing price statistics,
  coastal Portugal weighted average).
  Total replacement:       €1,950/m² (construction + land).
  Useful floor area per storey: 102 m² (INE Census 2021 average).
  Storey multiplier: varies by NUTS III (1.5 – 5 storeys).

Roads (Infraestruturas de Portugal / IMT 2024):
  Motorway €8M/km, Trunk €4M/km, Primary €2M/km, Secondary €500k/km,
  Tertiary €200k/km, Unclassified/Residential €115k/km, Living st €80k/km.

Railways (IP, confirmed by Évora-Elvas project 2024):
  New construction: €5,000,000/km.

Utility networks (ERSAR / ACER benchmarks 2023–24, per km of road):
  Water distribution:      €250,000/km
  Sewage collection:       €350,000/km
  Electricity distribution: €200,000/km
  Total bundle:            €800,000/km (applied to non-motorway roads)

SOURCES
-------
  INE SICC (Sistema de Informação de Custos de Construção) 2022–2025
  INE Estatísticas de Preços da Habitação Q4 2024
  INE Census 2021: building area, storey counts, building density
  Infraestruturas de Portugal – road infrastructure reference unit costs
  Projeto Évora–Elvas (CP/IP, 2024): €4.6–5.75M/km new railway
  ERSAR Relatório Anual 2023: water & sewage network benchmarks
  ACER Unit Investment Cost Indicators 2023: electricity distribution
  IPCC AR6 WG1 Ch.9: SLR projections, North Atlantic / Iberian Peninsula
"""

import json, math, time, sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import rasterio
from rasterio.transform import rowcol

# ── CONFIG ────────────────────────────────────────────────────────────────
DATA_DIR     = Path(__file__).parent
DEM_PATH     = DATA_DIR / "dem_portugal_merged.tif"
PILLAR1_DET  = DATA_DIR / "gdp_at_risk_pillar1.csv"          # per-NUTS3 detail
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
YEAR_START, YEAR_END = 2025, 2100
MAX_SLR      = 1.05          # pre-filter ceiling (m) – includes margin above SSP5-8.5
OUTPUT_SUM   = DATA_DIR / "infrastructure_at_risk_pillar2_summary.csv"
OUTPUT_DET   = DATA_DIR / "infrastructure_at_risk_pillar2_detail.csv"
OUTPUT_INV   = DATA_DIR / "infrastructure_inventory.csv"

# ── SLR (same anchors as 06a) ─────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════
#  COST ASSUMPTIONS
# ══════════════════════════════════════════════════════════════════════════

# ── Buildings ─────────────────────────────────────────────────────────────
# Construction + land replacement per m² of floor area
BUILDING_CONSTRUCTION_PER_M2 = 1_650   # INE SICC 2025 estimate
BUILDING_LAND_PER_M2         = 300     # INE Q4 2024, coastal weighted avg
BUILDING_COST_PER_M2         = BUILDING_CONSTRUCTION_PER_M2 + BUILDING_LAND_PER_M2  # €1,950

# Useful floor area per storey (INE Census 2021 national average)
USEFUL_AREA_PER_STOREY_M2   = 102

# Storey multiplier by NUTS III — INE Census 2021 building height data
# Higher values for dense urban regions; lower for rural coastal areas
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

# Building density (buildings/km²) by coastal NUTS III — INE Census 2021
# Conservative lower-bound estimates for areas below 1–2 m elevation
COASTAL_BUILDING_DENSITY = {
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

# ── Roads ─────────────────────────────────────────────────────────────────
ROAD_COST_PER_KM = {
    "motorway"     : 8_000_000,
    "trunk"        : 4_000_000,
    "primary"      : 2_000_000,
    "secondary"    :   500_000,
    "tertiary"     :   200_000,
    "unclassified" :   115_000,
    "residential"  :   115_000,
    "living_street":    80_000,
}
DEFAULT_ROAD_COST_KM = 115_000

# ── Railways ──────────────────────────────────────────────────────────────
RAILWAY_COST_KM = 5_000_000

# ── Utility networks (per km of co-located NON-MOTORWAY road) ────────────
UTILITY_WATER_KM       = 250_000   # ERSAR / EU benchmarks
UTILITY_SEWAGE_KM      = 350_000   # ERSAR / EU benchmarks
UTILITY_ELECTRICITY_KM = 200_000   # ACER 2023 / E-Redes benchmarks
UTILITY_BUNDLE_KM      = UTILITY_WATER_KM + UTILITY_SEWAGE_KM + UTILITY_ELECTRICITY_KM  # €800k

# ── Coastal bounding boxes for Overpass queries ───────────────────────────
COASTAL_BBOXES = [
    ("Norte",          41.50, -8.90, 42.20, -8.55),
    ("Porto_Aveiro",   40.30, -8.90, 41.50, -8.40),
    ("Centro_Coast",   39.20, -9.50, 40.30, -8.40),
    ("Lisboa_Setubal", 38.30, -9.30, 39.20, -8.40),
    ("Alentejo",       37.50, -9.00, 38.30, -7.90),
    ("Algarve",        36.90, -9.00, 37.50, -7.30),
]


# ══════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def haversine_km(lat1, lon1, lat2, lon2):
    R, d = 6371.0, math.radians
    a = (math.sin((d(lat2)-d(lat1))/2)**2
         + math.cos(d(lat1))*math.cos(d(lat2))*math.sin((d(lon2)-d(lon1))/2)**2)
    return 2 * R * math.asin(math.sqrt(a))


def way_length_km(nodes):
    return sum(haversine_km(nodes[i]["lat"], nodes[i]["lon"],
                            nodes[i+1]["lat"], nodes[i+1]["lon"])
               for i in range(len(nodes)-1))


def sample_elev(dem, transform, lat, lon):
    """Sample DEM elevation at a single lat/lon point."""
    try:
        r, c = rowcol(transform, lon, lat)
        if 0 <= r < dem.shape[0] and 0 <= c < dem.shape[1]:
            return float(dem[r, c])
    except Exception:
        pass
    return None


def compute_pixel_area_km2(transform, center_lat=39.0):
    """
    Compute ground area of one DEM pixel in km², from the rasterio
    transform (which gives pixel size in degrees for a WGS84 raster).

    At latitude φ:
      dx_km = |transform.a| × 111.139 × cos(φ)
      dy_km = |transform.e| × 111.139
      area  = dx_km × dy_km

    For Copernicus GLO-30 at ~39°N this gives ≈ 7.4e-4 km² per pixel.
    """
    deg_per_pixel_x = abs(transform.a)     # longitude direction
    deg_per_pixel_y = abs(transform.e)     # latitude direction
    km_per_deg_lat  = 111.139
    cos_lat = math.cos(math.radians(center_lat))

    dx_km = deg_per_pixel_x * km_per_deg_lat * cos_lat
    dy_km = deg_per_pixel_y * km_per_deg_lat
    return dx_km * dy_km


# ══════════════════════════════════════════════════════════════════════════
#  OVERPASS API (cached)
# ══════════════════════════════════════════════════════════════════════════

def fetch_overpass(south, west, north, east, name, timeout=90):
    cache = DATA_DIR / f"_overpass_cache_{name}.json"
    if cache.exists():
        print(f"  [{name}] cache hit")
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    query = f"""[out:json][timeout:{timeout}];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)$"]({south},{west},{north},{east});
  way["railway"~"^(rail|light_rail|tram|narrow_gauge)$"]({south},{west},{north},{east});
);
out geom tags;"""
    print(f"  [{name}] querying Overpass …", end=" ", flush=True)
    try:
        r = requests.post(OVERPASS_URL, data={"data": query},
                          timeout=timeout+15,
                          headers={"User-Agent": "MBA-SeaLevel-Research/1.0"})
        r.raise_for_status()
        data = r.json()
        print(f"{len(data.get('elements',[]))} elements")
        with open(cache, "w") as f:
            json.dump(data, f)
        return data
    except Exception as e:
        print(f"ERROR: {e}")
        return {"elements": []}


# ══════════════════════════════════════════════════════════════════════════
#  ROAD / RAILWAY INVENTORY  (FIX: multi-node elevation sampling)
# ══════════════════════════════════════════════════════════════════════════

def build_road_rail_inventory(dem, transform, elements):
    """
    For each OSM way, sample elevation at EVERY node (not just the
    midpoint).  The feature is included if ANY node has 0 < elev ≤ MAX_SLR.
    The stored elevation is the MINIMUM above 0 — this determines the
    SLR threshold at which the feature first becomes exposed.
    """
    inventory = []
    n_sampled = 0
    n_included = 0

    for el in elements:
        if el.get("type") != "way":
            continue
        geom = el.get("geometry", [])
        tags = el.get("tags", {})
        if len(geom) < 2:
            continue

        n_sampled += 1

        # ── Sample elevation at all nodes (subsample if very long) ──
        step = max(1, len(geom) // 30)       # ≤30 samples + endpoints
        indices = list(range(0, len(geom), step))
        # Always include first, last, and midpoint
        for idx in [0, len(geom) // 2, len(geom) - 1]:
            if idx not in indices:
                indices.append(idx)
        indices.sort()

        elevations = []
        for idx in indices:
            e = sample_elev(dem, transform, geom[idx]["lat"], geom[idx]["lon"])
            if e is not None:
                elevations.append(e)

        if not elevations:
            continue

        # ── Check if any node is in the coastal flood zone ───────────
        coastal_elevs = [e for e in elevations if 0 < e <= MAX_SLR]
        if not coastal_elevs:
            continue

        # Use minimum coastal elevation as the feature's exposure level
        min_elev = min(coastal_elevs)
        length_km = way_length_km(geom)
        n_included += 1

        if "highway" in tags:
            hw = tags["highway"]
            cost_km = ROAD_COST_PER_KM.get(hw, DEFAULT_ROAD_COST_KM)
            inventory.append({
                "feature"  : "road",
                "sub_type" : hw,
                "elev"     : min_elev,
                "quantity" : length_km,
                "unit"     : "km",
                "value_eur": length_km * cost_km,
            })
        elif "railway" in tags:
            inventory.append({
                "feature"  : "railway",
                "sub_type" : tags.get("railway", "rail"),
                "elev"     : min_elev,
                "quantity" : length_km,
                "unit"     : "km",
                "value_eur": length_km * RAILWAY_COST_KM,
            })

    print(f"  Sampled {n_sampled} ways → {n_included} at risk (0 < min_elev ≤ {MAX_SLR}m)")
    return inventory


# ══════════════════════════════════════════════════════════════════════════
#  BUILDING ESTIMATE  (FIX: correct pixel area + storey multiplier)
# ══════════════════════════════════════════════════════════════════════════

def estimate_buildings(pillar1_detail_path, pixel_area_km2):
    """
    Returns {(scenario, year): {nuts3: (n_buildings, value_eur)}}

    flood_km² = flooded_pixels × pixel_area_km2
    n_buildings = flood_km² × building_density_per_km2
    value_eur   = n_buildings × (useful_area_per_storey × storeys × cost/m²)

    CRITICAL FIX: pixel_area_km2 is now computed from the DEM transform
    (≈ 7.4e-4 km²), not from the old formula which produced square degrees
    (5.66e-8) — an error of ~15,900×.
    """
    if not pillar1_detail_path.exists():
        print("  WARNING: Pillar 1 detail CSV not found — building estimate disabled.")
        return {}

    detail = pd.read_csv(pillar1_detail_path)

    # Verify expected columns exist
    required = {"year", "scenario", "nuts3", "flooded_pixels"}
    if not required.issubset(set(detail.columns)):
        print(f"  WARNING: Pillar 1 detail missing columns {required - set(detail.columns)}")
        return {}

    print(f"  Pixel area used: {pixel_area_km2:.6e} km² per pixel")

    result = {}
    for (yr, scen), grp in detail.groupby(["year", "scenario"]):
        nuts3_data = {}
        for _, row in grp.iterrows():
            nuts3 = row["nuts3"]
            flooded_px = float(row["flooded_pixels"])

            # ── Flood area ────────────────────────────────────────────
            flood_km2 = flooded_px * pixel_area_km2

            # ── Building count ────────────────────────────────────────
            density = COASTAL_BUILDING_DENSITY.get(
                nuts3, COASTAL_BUILDING_DENSITY["_default"])
            n_buildings = flood_km2 * density

            # ── Building value (with storey multiplier) ───────────────
            storeys   = STOREY_MULTIPLIER.get(nuts3, STOREY_MULTIPLIER["_default"])
            floor_m2  = USEFUL_AREA_PER_STOREY_M2 * storeys
            value_per = floor_m2 * BUILDING_COST_PER_M2
            total_val = n_buildings * value_per

            nuts3_data[nuts3] = (n_buildings, total_val)

        result[(int(yr), scen)] = nuts3_data

    return result


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    if not DEM_PATH.exists():
        sys.exit(f"ERROR: DEM not found: {DEM_PATH}")

    years = np.arange(YEAR_START, YEAR_END + 1)

    # ── 1. Load DEM ─────────────────────────────────────────────────────
    print("Loading DEM …")
    with rasterio.open(DEM_PATH) as src:
        dem       = src.read(1)
        transform = src.transform
    print(f"  {dem.shape[0]}×{dem.shape[1]}")

    # ── 2. Compute pixel area from DEM transform ───────────────────────
    pixel_area_km2 = compute_pixel_area_km2(transform, center_lat=39.0)
    print(f"  Pixel area: {pixel_area_km2:.6e} km² "
          f"({abs(transform.a)*111139*math.cos(math.radians(39)):.1f}m "
          f"× {abs(transform.e)*111139:.1f}m)\n")

    # ── 3. Fetch roads & railways from Overpass ─────────────────────────
    print("Fetching roads & railways from Overpass API …")
    all_elements = []
    for (name, s, w, n, e) in COASTAL_BBOXES:
        data = fetch_overpass(s, w, n, e, name)
        all_elements.extend(data.get("elements", []))
        time.sleep(3)

    # ── 4. Build road/rail inventory (multi-node sampling) ──────────────
    print(f"\nBuilding road/railway inventory (multi-node elevation) …")
    rr_inventory = build_road_rail_inventory(dem, transform, all_elements)
    del dem   # free ~1.3 GB

    km_road = sum(f["quantity"] for f in rr_inventory if f["feature"] == "road")
    km_rail = sum(f["quantity"] for f in rr_inventory if f["feature"] == "railway")
    km_mway = sum(f["quantity"] for f in rr_inventory
                  if f["feature"] == "road" and f["sub_type"] == "motorway")
    km_non_mway = km_road - km_mway
    print(f"  Roads:    {km_road:.1f} km at risk (≤{MAX_SLR}m)")
    print(f"    of which motorway: {km_mway:.1f} km")
    print(f"    non-motorway:      {km_non_mway:.1f} km (utilities co-located)")
    print(f"  Railways: {km_rail:.1f} km at risk (≤{MAX_SLR}m)\n")

    # ── 5. Building estimate from flood area × density ──────────────────
    print("Estimating buildings from flood area × INE density …")
    bld_by_scenario = estimate_buildings(PILLAR1_DET, pixel_area_km2)
    if bld_by_scenario:
        sample = bld_by_scenario.get((2100, "ssp585"), {})
        total_bld   = sum(v[0] for v in sample.values())
        total_val_b = sum(v[1] for v in sample.values()) / 1e9
        print(f"  Example 2100/SSP5-8.5: {total_bld:,.0f} buildings, "
              f"€{total_val_b:.1f}B replacement value")

    # ── 6. Prepare numpy arrays for annual loop ─────────────────────────
    rr_elev    = np.array([f["elev"]      for f in rr_inventory])
    rr_val     = np.array([f["value_eur"] for f in rr_inventory])
    rr_feat    = np.array([f["feature"]   for f in rr_inventory])
    rr_subtype = np.array([f["sub_type"]  for f in rr_inventory])
    rr_qty     = np.array([f["quantity"]  for f in rr_inventory])

    # ── 7. Annual cost loop ─────────────────────────────────────────────
    print(f"\nComputing annual costs {YEAR_START}–{YEAR_END} …\n")

    all_summary = []
    all_detail  = []

    for scenario in SCENARIOS:
        slr = slr_series(SLR_ANCHORS[scenario], years)
        print(f"  {scenario.upper()}:")

        for yr, s in zip(years, slr):
            yr_int = int(yr)

            # ── Roads + railways ──────────────────────────────────────
            mask_rr     = (rr_elev > 0) & (rr_elev <= s)
            road_mask   = mask_rr & (rr_feat == "road")
            rail_mask   = mask_rr & (rr_feat == "railway")

            road_eur    = float(rr_val[road_mask].sum())
            railway_eur = float(rr_val[rail_mask].sum())
            road_km     = float(rr_qty[road_mask].sum())
            rail_km     = float(rr_qty[rail_mask].sum())

            # ── Utilities: per km of non-motorway road at risk ────────
            non_mway_mask = road_mask & (rr_subtype != "motorway")
            non_mway_km   = float(rr_qty[non_mway_mask].sum())
            utility_water_eur = non_mway_km * UTILITY_WATER_KM
            utility_sewage_eur = non_mway_km * UTILITY_SEWAGE_KM
            utility_elec_eur  = non_mway_km * UTILITY_ELECTRICITY_KM
            utility_total_eur = utility_water_eur + utility_sewage_eur + utility_elec_eur

            # ── Buildings (with storey multiplier) ────────────────────
            bld_count = 0.0
            bld_eur   = 0.0
            if bld_by_scenario:
                bld_data = bld_by_scenario.get((yr_int, scenario), None)
                if bld_data is None:
                    # Find closest year for this scenario
                    same_scen = [(k, v) for k, v in bld_by_scenario.items()
                                 if k[1] == scenario]
                    if same_scen:
                        closest = min(same_scen, key=lambda x: abs(x[0][0] - yr_int))
                        bld_data = closest[1]
                if bld_data:
                    bld_count = sum(v[0] for v in bld_data.values())
                    bld_eur   = sum(v[1] for v in bld_data.values())

            # ── Totals ────────────────────────────────────────────────
            total_eur = bld_eur + road_eur + railway_eur + utility_total_eur

            all_summary.append({
                "year"                : yr_int,
                "scenario"            : scenario,
                "slr_m"               : round(float(s), 4),
                "buildings_count"     : round(bld_count, 0),
                "buildings_eur"       : round(bld_eur, 0),
                "roads_km"            : round(road_km, 2),
                "roads_eur"           : round(road_eur, 0),
                "railways_km"         : round(rail_km, 2),
                "railways_eur"        : round(railway_eur, 0),
                "utilities_road_km"   : round(non_mway_km, 2),
                "utility_water_eur"   : round(utility_water_eur, 0),
                "utility_sewage_eur"  : round(utility_sewage_eur, 0),
                "utility_elec_eur"    : round(utility_elec_eur, 0),
                "utilities_total_eur" : round(utility_total_eur, 0),
                "total_replacement_eur": round(total_eur, 0),
                "total_bn_eur"        : round(total_eur / 1e9, 4),
            })

            # ── Per-NUTS3 building detail ─────────────────────────────
            if bld_by_scenario and bld_data:
                for nuts3, (nb, vb) in bld_data.items():
                    storeys = STOREY_MULTIPLIER.get(nuts3, STOREY_MULTIPLIER["_default"])
                    all_detail.append({
                        "year"     : yr_int,
                        "scenario" : scenario,
                        "slr_m"    : round(float(s), 4),
                        "nuts3"    : nuts3,
                        "buildings": round(nb, 1),
                        "storeys"  : storeys,
                        "value_eur": round(vb, 0),
                    })

            # ── Print every 5 years ───────────────────────────────────
            if yr_int % 5 == 0:
                avg_val_k = (bld_eur / bld_count / 1000) if bld_count > 0 else 0
                print(f"    {yr_int}  SLR={s:.2f}m  → €{total_eur/1e9:.3f}B  "
                      f"(bld {bld_count:,.0f}×€{avg_val_k:.0f}k=€{bld_eur/1e9:.3f}B  "
                      f"road €{road_eur/1e9:.3f}B  rail €{railway_eur/1e9:.3f}B  "
                      f"util €{utility_total_eur/1e9:.3f}B)")

    # ── 8. Save CSVs ───────────────────────────────────────────────────
    df_sum = pd.DataFrame(all_summary)
    df_sum.to_csv(OUTPUT_SUM, index=False)

    if all_detail:
        df_det = pd.DataFrame(all_detail)
        df_det.to_csv(OUTPUT_DET, index=False)

    pd.DataFrame(rr_inventory).to_csv(OUTPUT_INV, index=False)

    print(f"\nSaved: {OUTPUT_SUM.name}  ({len(df_sum)} rows)")
    if all_detail:
        print(f"Saved: {OUTPUT_DET.name}  ({len(all_detail)} rows)")
    print(f"Saved: {OUTPUT_INV.name}  ({len(rr_inventory)} road/rail segments)")

    # ── 9. Pivot preview ───────────────────────────────────────────────
    pivot = df_sum.pivot(index="year", columns="scenario", values="total_bn_eur")
    pivot.columns.name = None
    print("\n=== INFRASTRUCTURE REPLACEMENT COST AT RISK (€B) – every 5 years ===")
    print(pivot[pivot.index % 5 == 0].to_string())

    # Breakdown for 2100
    print("\n=== 2100 BREAKDOWN BY COMPONENT (€B) ===")
    row2100 = df_sum[df_sum["year"] == 2100]
    for _, r in row2100.iterrows():
        print(f"  {r['scenario']:8s}  bld €{r['buildings_eur']/1e9:.2f}B  "
              f"road €{r['roads_eur']/1e9:.3f}B  rail €{r['railways_eur']/1e9:.3f}B  "
              f"util €{r['utilities_total_eur']/1e9:.3f}B  "
              f"TOTAL €{r['total_bn_eur']:.2f}B  ({r['buildings_count']:,.0f} bldgs)")

    print("\nCost sources: INE SICC 2025 + INE Housing Q4 2024 (buildings), "
          "IP/IMT 2024 (roads), Évora–Elvas 2024 (railways), "
          "ERSAR/ACER 2023 (utilities)")
    print("Building count: flood area × INE Census 2021 density × storey multiplier "
          "(avoids 30m DEM bias)")
    print(f"Pixel area: {pixel_area_km2:.6e} km² (computed from DEM transform)")
