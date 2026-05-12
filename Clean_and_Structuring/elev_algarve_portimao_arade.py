"""
elev_algarve_portimao_arade.py
================================
Elevation profile of the Linha do Algarve — Portimão / Arade estuary section.

The Portimão–Arade segment crosses the tidal Arade estuary on a railway bridge
between Ferragudo/Mexilhoeira Grande (west bank) and Portimão (east bank). The
Arade is a mesotidal estuary with a tidal range of ~2–3 m and documented storm
surge flooding. The estuary floor and adjacent alluvial plain are at or near
sea level for several kilometres inland of the river mouth, making approach
embankments potentially vulnerable to compound flooding under SLR scenarios.

METHOD (identical to elev_linha_norte_relation.py and elev_algarve_faro_olhao.py)
----------------------------------------------------------------------------------
1. Query OSM for the Linha do Algarve route relation (ID 349295).
2. Extract all member ways tagged railway=rail.
3. Filter to the Portimão/Arade section using a tight lat/lon bounding box.
   (East–west line: both lat AND lon bounds applied; nodes sorted W→E.)
4. Sample every INTERVAL_M metres along the centreline.
5. Query EU-DEM 25m elevation at each sample point via OpenTopoData API.

BOUNDING BOX — Portimão / Arade estuary crossing
  LAT : 37.10°N – 37.18°N
  LON : -8.62°W – -8.46°W
  (approximately 13 km of track; captures the Arade estuary crossing,
  Portimão station approaches and the west bank approach from Mexilhoeira)

KNOWN LIMITATION
----------------
EU-DEM resolution is 25 m. Values represent mean terrain within a 25×25 m
cell and may include adjacent embankment faces or drainage channels. Values
treated as conservative lower bounds on actual track surface elevation.

OUTPUTS
-------
  algarve_portimao_arade_full_profile.csv   — all sample points with elevation
  algarve_portimao_arade_low_points.csv     — points below THRESHOLD_M, sorted
  algarve_portimao_arade_summary.txt        — text summary for dissertation
"""

import time, math, csv, requests, datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPENTOPO_URL = "https://api.opentopodata.org/v1/eudem25m"
HEADERS      = {"User-Agent": "AlgarveRailElevation/1.0 (dissertation research)"}

RELATION_ID  = 349295          # Linha do Algarve, confirmed OSM relation
INTERVAL_M   = 50              # sample every 50 m
THRESHOLD_M  = 5.0             # flag points below this (m MSL)
BATCH_SIZE   = 100
PAUSE_S      = 1.5

# Study section: west bank approach → Portimão station
# (captures the Arade estuary and its alluvial approaches)
#
# BBOX RATIONALE:
#   Portimão station sits at ~37.138°N, -8.538°W. The Arade crossing is just
#   west of the station at ~-8.525 to -8.545°W. Setting LON_MIN = -8.56 cuts
#   off the Lagos branch (heading further west) which was adding spurious low
#   points unrelated to the Arade crossing.
#
# EU-DEM BRIDGE LIMITATION:
#   Where the railway crosses the Arade on a bridge, EU-DEM samples the water
#   surface below, returning ~0m or negative values. These are invalid for
#   track elevation assessment and are excluded (ELEV_VALID_MIN filter below).
#   The meaningful data comes from the approach embankments on both banks,
#   which EU-DEM measures correctly at terrain level.
LAT_MIN =  37.12
LAT_MAX =  37.18
LON_MIN =  -8.56   # just west of Arade bridge west bank; excludes Lagos branch
LON_MAX =  -8.46   # east bound (beyond Portimão station)

# Minimum valid elevation: EU-DEM returns negative values over open water
# (estuarine water surface, river channel). Anything below this is a DEM
# water artifact, not a track surface reading — flag and exclude.
ELEV_VALID_MIN = 0.0

# Flood-risk zones for annotation
FLOOD_ZONES = [
    {
        "name":    "Arade Estuary Bridge Crossing",
        "lat_min":  37.120, "lat_max": 37.150,
        "lon_min":  -8.560, "lon_max": -8.510,
        "notes":   "Rail bridge over tidal Arade estuary; mesotidal range 2-3 m; "
                   "storm surge and compound flood exposure",
    },
    {
        "name":    "West Bank Approach (Ferragudo / Mexilhoeira)",
        "lat_min":  37.120, "lat_max": 37.150,
        "lon_min":  -8.560, "lon_max": -8.530,
        "notes":   "Alluvial plain west of Arade; low-lying approach embankment; "
                   "within Arade floodplain extent",
    },
    {
        "name":    "Portimão Station Approaches",
        "lat_min":  37.130, "lat_max": 37.180,
        "lon_min":  -8.530, "lon_max": -8.460,
        "notes":   "Urban approaches to Portimão station east of the Arade; "
                   "coastal urban area at mouth of estuary",
    },
]


# ── HELPERS ───────────────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def in_section(lat, lon):
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def flood_zone_label(lat, lon):
    for z in FLOOD_ZONES:
        if (z["lat_min"] <= lat <= z["lat_max"] and
                z["lon_min"] <= lon <= z["lon_max"]):
            return z["name"], z["notes"]
    return "", ""


def overpass_post(query):
    for i, server in enumerate(OVERPASS_SERVERS):
        try:
            if i > 0:
                print(f"  Retrying server {i+1}: {server}")
                time.sleep(6)
            r = requests.post(server, data={"data": query},
                              headers=HEADERS, timeout=210)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Server {i+1} failed: {e}")
    return None


# ── STEP 1: GET MEMBER WAYS ───────────────────────────────────────────────────

def get_relation_ways():
    """Retrieve all railway=rail member ways of relation 349295 with geometry."""
    query = f"""
        [out:json][timeout:180];
        relation({RELATION_ID})->.r;
        way(r.r)["railway"="rail"];
        out geom;
    """
    print(f"  Querying OSM relation {RELATION_ID} (Linha do Algarve)...")
    data = overpass_post(query)
    if data is None:
        return []
    return [el for el in data.get("elements", []) if el["type"] == "way"]


# ── STEP 2: FILTER AND SAMPLE ─────────────────────────────────────────────────

def filter_ways(ways):
    """Keep only ways that have at least one node inside the section bbox."""
    kept = []
    for way in ways:
        geom = way.get("geometry", [])
        if any(in_section(pt["lat"], pt["lon"]) for pt in geom):
            kept.append(way)
    return kept


def sample_ways(ways):
    """
    Flatten ways → nodes inside bbox, sort WEST→EAST by longitude,
    then sample every INTERVAL_M metres along the line.
    """
    nodes = []
    for way in ways:
        for pt in way.get("geometry", []):
            if in_section(pt["lat"], pt["lon"]):
                nodes.append((pt["lat"], pt["lon"]))
    if not nodes:
        return []

    # Remove duplicates (shared endpoints between adjacent ways)
    seen = set()
    unique = []
    for n in nodes:
        key = (round(n[0], 7), round(n[1], 7))
        if key not in seen:
            seen.add(key)
            unique.append(n)

    # Sort west → east (ascending longitude; both values are negative,
    # so -8.62 < -8.46, giving correct W→E ordering)
    unique.sort(key=lambda x: x[1])

    # Interpolate samples every INTERVAL_M metres
    samples = [unique[0]]
    carry = 0.0
    for i in range(1, len(unique)):
        seg = haversine_m(*unique[i-1], *unique[i])
        if seg < 1e-6:
            continue
        t = (INTERVAL_M - carry) / seg
        while t <= 1.0:
            lat = unique[i-1][0] + t * (unique[i][0] - unique[i-1][0])
            lon = unique[i-1][1] + t * (unique[i][1] - unique[i-1][1])
            samples.append((lat, lon))
            t += INTERVAL_M / seg
        carry = seg * (1.0 - (t - INTERVAL_M / seg))
        if carry >= INTERVAL_M:
            carry = 0.0
    return samples


# ── STEP 3: ELEVATION QUERY ───────────────────────────────────────────────────

def fetch_elevations(points):
    elevs = []
    total_batches = math.ceil(len(points) / BATCH_SIZE)
    for i in range(0, len(points), BATCH_SIZE):
        batch   = points[i : i + BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        for attempt in range(3):
            try:
                r = requests.get(OPENTOPO_URL,
                                 params={"locations": loc_str}, timeout=40)
                r.raise_for_status()
                for res in r.json()["results"]:
                    elevs.append(res["elevation"])
                break
            except Exception as e:
                if attempt == 2:
                    print(f"     ✗ Batch {i//BATCH_SIZE+1} failed after 3 attempts")
                    elevs.extend([None] * len(batch))
                else:
                    time.sleep(4)
        last = elevs[-1]
        print(f"     batch {i//BATCH_SIZE+1}/{total_batches}  "
              f"({len(batch)} pts)  last = "
              f"{f'{last:.2f} m' if last is not None else 'None'}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_date = datetime.date.today().isoformat()
    print("=" * 68)
    print("  Linha do Algarve — Portimão / Arade Estuary Section")
    print("  Elevation via OSM Route Relation + EU-DEM 25m")
    print(f"  Run date      : {run_date}")
    print(f"  Relation ID   : {RELATION_ID}")
    print(f"  Section bbox  : lat [{LAT_MIN}, {LAT_MAX}]  "
          f"lon [{LON_MIN}, {LON_MAX}]")
    print(f"  Interval      : {INTERVAL_M} m")
    print(f"  Threshold     : < {THRESHOLD_M} m MSL flagged")
    print(f"  Elevation src : EU-DEM 25m (EGM2008 datum)")
    print(f"  CITE AS: OSM relation {RELATION_ID}, retrieved {run_date}")
    print(f"    URL: https://www.openstreetmap.org/relation/{RELATION_ID}")
    print("=" * 68)

    # ── 1. Get ways from OSM ──────────────────────────────────────────────────
    print("\nSTEP 1: Fetching Linha do Algarve member ways from OSM...")
    all_ways = get_relation_ways()
    print(f"  Total railway=rail ways in relation: {len(all_ways)}")
    if not all_ways:
        print("  ✗ No ways returned. Check network and relation ID.")
        exit(1)

    ways_in_section = filter_ways(all_ways)
    print(f"  Ways with nodes inside section bbox: {len(ways_in_section)}")
    if not ways_in_section:
        print("  ✗ No ways in section bbox. Check LAT/LON bounds.")
        exit(1)

    # ── 2. Sample centreline ──────────────────────────────────────────────────
    print(f"\nSTEP 2: Sampling centreline every {INTERVAL_M} m (W→E)...")
    pts = sample_ways(ways_in_section)
    print(f"  Sample points generated: {len(pts)}")
    if not pts:
        print("  ✗ No sample points generated. Check geometry.")
        exit(1)

    # ── 3. Fetch elevations ───────────────────────────────────────────────────
    print(f"\nSTEP 3: Querying EU-DEM 25m elevations ({len(pts)} points)...")
    elevs = fetch_elevations(pts)

    # ── 4. Analyse ────────────────────────────────────────────────────────────
    all_returned = [(pts[i], elevs[i]) for i in range(len(elevs))
                    if elevs[i] is not None]

    # Separate DEM water artifacts (negative values = river/estuary surface)
    water_artifacts = [(pt, e) for pt, e in all_returned if e < ELEV_VALID_MIN]
    valid = [(pt, e) for pt, e in all_returned if e >= ELEV_VALID_MIN]

    if water_artifacts:
        print(f"\n  ⚠  EU-DEM water artifacts excluded : {len(water_artifacts)} points")
        print(f"     (negative elevations = DEM sampling Arade water surface,")
        print(f"      not bridge deck; EU-DEM cannot measure bridge elevation)")
        wa_min = min(e for _, e in water_artifacts)
        wa_max = max(e for _, e in water_artifacts)
        print(f"     artifact range: {wa_min:.3f} m to {wa_max:.3f} m")

    if not valid:
        print("  ✗ No valid terrain elevation values returned.")
        exit(1)

    elev_vals = [e for _, e in valid]
    e_min  = min(elev_vals)
    e_mean = sum(elev_vals) / len(elev_vals)
    e_max  = max(elev_vals)
    below  = [(pt, e) for pt, e in valid if e < THRESHOLD_M]

    # Track length estimates (each sample point represents INTERVAL_M metres)
    total_km   = len(valid)  * INTERVAL_M / 1000
    at_risk_km = len(below)  * INTERVAL_M / 1000

    print(f"\n{'='*68}")
    print(f"  RESULTS — Linha do Algarve  Portimão/Arade section")
    print(f"  OSM relation {RELATION_ID} — retrieved {run_date}")
    print(f"{'='*68}")
    print(f"  Valid sample points   : {len(valid)}")
    print(f"  Track length sampled  : {total_km:.1f} km")
    print(f"  Minimum elevation     : {e_min:.3f} m MSL  ← reported floor")
    print(f"  Mean elevation        : {e_mean:.3f} m MSL")
    print(f"  Maximum elevation     : {e_max:.3f} m MSL")
    print(f"  Points < {THRESHOLD_M} m MSL   : {len(below)}"
          f"  ({100*len(below)/max(len(valid),1):.1f}%)")
    print(f"  Track length at risk  : {at_risk_km:.1f} km  "
          f"(below {THRESHOLD_M} m MSL)")

    if below:
        lp = min(below, key=lambda x: x[1])
        zn, notes = flood_zone_label(lp[0][0], lp[0][1])
        print(f"  Lowest point          : {lp[1]:.3f} m  "
              f"lat={lp[0][0]:.6f}  lon={lp[0][1]:.6f}")
        if zn:
            print(f"  Flood zone            : {zn}")

    # Per flood zone breakdown
    print(f"\n  BY FLOOD ZONE (points < {THRESHOLD_M} m only):")
    zones_data = {}
    for pt, e in below:
        zn, notes = flood_zone_label(pt[0], pt[1])
        label = zn if zn else "Unclassified"
        zones_data.setdefault(label, {"notes": notes, "elevs": []})
        zones_data[label]["elevs"].append(e)
    for zn, zd in sorted(zones_data.items()):
        es = zd["elevs"]
        zone_km = len(es) * INTERVAL_M / 1000
        print(f"    {zn}")
        if zd["notes"]:
            print(f"      Context: {zd['notes'][:70]}...")
        print(f"      n={len(es)}  length={zone_km:.2f} km  "
              f"min={min(es):.3f} m  mean={sum(es)/len(es):.3f} m")

    # ── 5. Write outputs ──────────────────────────────────────────────────────
    print("\nSTEP 4: Saving outputs...")

    # Full profile
    outfile_full = "algarve_portimao_arade_full_profile.csv"
    with open(outfile_full, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m",
                    "below_threshold", "flood_zone", "zone_notes"])
        for i, ((lat, lon), e) in enumerate(valid):
            zn, notes = flood_zone_label(lat, lon)
            w.writerow([i, round(lat, 6), round(lon, 6), round(e, 3),
                        e < THRESHOLD_M, zn, notes])
    print(f"  → {outfile_full}  ({len(valid)} rows)")

    # Low points only, sorted by elevation
    outfile_low = "algarve_portimao_arade_low_points.csv"
    with open(outfile_low, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lon", "elev_m", "flood_zone", "zone_notes"])
        for pt, e in sorted(below, key=lambda x: x[1]):
            zn, notes = flood_zone_label(pt[0], pt[1])
            w.writerow([round(pt[0], 6), round(pt[1], 6), round(e, 3),
                        zn, notes])
    print(f"  → {outfile_low}  ({len(below)} rows)")

    # Text summary for dissertation
    outfile_txt = "algarve_portimao_arade_summary.txt"
    summary = [
        "LINHA DO ALGARVE — PORTIMÃO / ARADE ESTUARY SECTION",
        "Elevation Study — Arade Estuary Crossing",
        f"Generated : {run_date}",
        f"OSM data  : Relation {RELATION_ID} (Linha do Algarve)",
        f"URL       : https://www.openstreetmap.org/relation/{RELATION_ID}",
        f"Elev src  : EU-DEM 25m, EGM2008 datum (OpenTopoData API)",
        f"Section   : lat [{LAT_MIN}, {LAT_MAX}]  lon [{LON_MIN}, {LON_MAX}]",
        f"Interval  : {INTERVAL_M} m  |  Threshold  : {THRESHOLD_M} m MSL",
        "",
        "RESULTS",
        f"  Valid sample points : {len(valid)}",
        f"  Track length sampled: {total_km:.1f} km",
        f"  Minimum elevation   : {e_min:.3f} m MSL  ← reported floor",
        f"  Mean elevation      : {e_mean:.3f} m MSL",
        f"  Maximum elevation   : {e_max:.3f} m MSL",
        f"  Points < {THRESHOLD_M} m MSL  : {len(below)}"
        f"  ({100*len(below)/max(len(valid),1):.1f}%)",
        f"  Track at risk       : {at_risk_km:.1f} km  (below {THRESHOLD_M} m MSL)",
        "",
        "FLOOD ZONES (points below threshold)",
    ]
    for zn, zd in sorted(zones_data.items()):
        es = zd["elevs"]
        zone_km = len(es) * INTERVAL_M / 1000
        summary.append(f"  {zn}")
        summary.append(f"    Context : {zd['notes']}")
        summary.append(f"    length={zone_km:.2f} km  n={len(es)}  min={min(es):.3f} m  "
                       f"mean={sum(es)/len(es):.3f} m")
    summary += [
        "",
        f"EU-DEM WATER ARTIFACTS EXCLUDED: {len(water_artifacts)} points",
        f"  DEM returned negative elevation ({min((e for _,e in water_artifacts), default=0):.3f} m"
        f" to {max((e for _,e in water_artifacts), default=0):.3f} m) at points over the",
        "  Arade river channel — the DEM samples the water surface, not the bridge deck.",
        "  These points were excluded from all statistics and output CSVs.",
        "  NOTE: EU-DEM cannot measure bridge deck elevation; the bridge span itself",
        "  is assessed by design elevation (civil engineering drawings), not DEM.",
        "",
        "LIMITATION",
        "  EU-DEM 25m: each value is mean terrain within a 25×25 m cell.",
        "  May include embankment flanks or drainage features.",
        "  Values treated as conservative lower bounds on track surface.",
        "  Bridge spans over open water are outside EU-DEM scope.",
    ]
    with open(outfile_txt, "w") as f:
        f.write("\n".join(summary))
    print(f"  → {outfile_txt}")

    print("\nDone.")
