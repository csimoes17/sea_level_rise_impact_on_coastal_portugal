"""
check_track_elevation.py
========================
Pulls the actual centreline geometry of a railway or road from OpenStreetMap
(via the Overpass API), samples it at regular intervals, and queries the
EU-DEM 25m elevation for each point via OpenTopoData API.

Outputs:
  - Console summary: min / mean / max elevation along the infrastructure
  - CSV: full point-by-point elevation profile
  - Flags any segment where elevation < a user-defined flood threshold

USAGE
-----
  pip install requests shapely
  python check_track_elevation.py

Edit the SECTIONS dict below to add/change infrastructure sections.
Each section needs:
  - name        : label for outputs
  - osm_query   : Overpass QL query string to pull the OSM ways
  - interval_m  : sampling interval in metres along the centreline
  - threshold_m : flood risk threshold (m MSL) — points below this are flagged
  - out_csv     : output CSV filename
"""

import time
import math
import csv
import requests

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

SECTIONS = {

    "aveiro_zone_b": {
        "name": "Linha do Norte — Aveiro Lagoon Fringe (Zone B, Cacia–Salreu)",
        "osm_query": """
            [out:json][timeout:60];
            way["railway"="rail"]
              (40.640,-8.610,40.730,-8.560);
            out geom;
        """,
        "interval_m":   100,
        "threshold_m":  3.0,
        "out_csv":      "elev_aveiro_zone_b.csv",
    },

    "aveiro_zone_a": {
        "name": "Linha do Norte — Ovar–Estarreja Causeway (Zone A)",
        "osm_query": """
            [out:json][timeout:60];
            way["railway"="rail"]
              (40.730,-8.600,40.870,-8.540);
            out geom;
        """,
        "interval_m":   100,
        "threshold_m":  3.0,
        "out_csv":      "elev_aveiro_zone_a.csv",
    },

    "a1_azambuja": {
        "name": "A1 Motorway — Azambuja flood plain section (km 50–62)",
        "osm_query": """
            [out:json][timeout:60];
            way["highway"="motorway"]
              (38.960,-8.920,39.120,-8.750);
            out geom;
        """,
        "interval_m":   200,
        "threshold_m":  4.0,
        "out_csv":      "elev_a1_azambuja.csv",
    },

}

OVERPASS_URL   = "https://overpass-api.de/api/interpreter"
OPENTOPO_URL   = "https://api.opentopodata.org/v1/eudem25m"
BATCH_SIZE     = 100   # OpenTopoData max per request
PAUSE_BETWEEN  = 1.2   # seconds between API calls (rate limit)

# ── GEOMETRY HELPERS ──────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in metres between two lat/lon points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def interpolate_along_ways(ways, interval_m):
    """
    Given a list of OSM ways (each with a 'geometry' list of {lat, lon} dicts),
    produce a list of (lat, lon) points sampled every interval_m metres along
    the combined centreline.
    """
    # Flatten all nodes from all ways into one continuous polyline.
    # (Ways may be in any order; we do a simple concatenation here — good enough
    #  for a contiguous infrastructure section.)
    nodes = []
    for way in ways:
        geom = way.get("geometry", [])
        if not geom:
            continue
        if nodes and haversine_m(nodes[-1][0], nodes[-1][1],
                                  geom[0]["lat"], geom[0]["lon"]) > haversine_m(
                                  nodes[-1][0], nodes[-1][1],
                                  geom[-1]["lat"], geom[-1]["lon"]):
            geom = list(reversed(geom))
        for pt in geom:
            nodes.append((pt["lat"], pt["lon"]))

    if not nodes:
        return []

    samples = [nodes[0]]
    accumulated = 0.0

    for i in range(1, len(nodes)):
        seg_len = haversine_m(nodes[i-1][0], nodes[i-1][1],
                               nodes[i][0],   nodes[i][1])
        remaining = interval_m - accumulated

        if seg_len < 1e-6:
            continue

        t = remaining / seg_len
        while t <= 1.0:
            lat = nodes[i-1][0] + t * (nodes[i][0] - nodes[i-1][0])
            lon = nodes[i-1][1] + t * (nodes[i][1] - nodes[i-1][1])
            samples.append((lat, lon))
            t += interval_m / seg_len

        accumulated = seg_len * (1.0 - (t - interval_m / seg_len))
        if accumulated >= interval_m:
            accumulated = 0.0

    return samples


# ── API CALLS ─────────────────────────────────────────────────────────────────

def fetch_osm_ways(query):
    print("  → Querying OpenStreetMap (Overpass API)...")
    headers = {"User-Agent": "InfraElevationChecker/1.0 (dissertation research)"}
    r = requests.post(OVERPASS_URL, data={"data": query},
                      headers=headers, timeout=90)
    r.raise_for_status()
    data = r.json()
    ways = [el for el in data["elements"] if el["type"] == "way"]
    print(f"     {len(ways)} way(s) returned, "
          f"{sum(len(w.get('geometry',[])) for w in ways)} total nodes.")
    return ways


def fetch_elevations(points):
    """Batch-query OpenTopoData for a list of (lat, lon) tuples."""
    elevations = []
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        r = requests.get(OPENTOPO_URL, params={"locations": loc_str}, timeout=30)
        r.raise_for_status()
        data = r.json()
        for res in data["results"]:
            elevations.append(res["elevation"])
        print(f"     elevation batch {i//BATCH_SIZE + 1}: "
              f"{len(batch)} points queried, last={elevations[-1]:.2f} m")
        time.sleep(PAUSE_BETWEEN)
    return elevations


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run_section(key, cfg):
    print(f"\n{'='*70}")
    print(f"SECTION: {cfg['name']}")
    print(f"{'='*70}")

    # 1. Get OSM centreline
    ways = fetch_osm_ways(cfg["osm_query"])
    if not ways:
        print("  ✗ No ways returned — check OSM query / bounding box.")
        return

    # 2. Sample along centreline
    print(f"  → Sampling every {cfg['interval_m']} m along centreline...")
    points = interpolate_along_ways(ways, cfg["interval_m"])
    print(f"     {len(points)} sample points generated.")

    if not points:
        print("  ✗ No sample points generated.")
        return

    # 3. Query elevations
    print(f"  → Querying EU-DEM 25m elevations ({len(points)} points "
          f"in {math.ceil(len(points)/BATCH_SIZE)} batch(es))...")
    elevations = fetch_elevations(points)

    # 4. Statistics
    valid = [e for e in elevations if e is not None]
    if not valid:
        print("  ✗ No valid elevations returned.")
        return

    elev_min  = min(valid)
    elev_mean = sum(valid) / len(valid)
    elev_max  = max(valid)
    below     = [(points[i], valid[i]) for i in range(len(valid))
                 if valid[i] < cfg["threshold_m"]]

    print(f"\n  RESULTS — {cfg['name']}")
    print(f"  Sample points : {len(valid)}")
    print(f"  Minimum       : {elev_min:.2f} m MSL  ← critical value")
    print(f"  Mean          : {elev_mean:.2f} m MSL")
    print(f"  Maximum       : {elev_max:.2f} m MSL")
    print(f"  Points below {cfg['threshold_m']:.1f} m : {len(below)}")
    if below:
        print(f"  Lowest flagged: {min(b[1] for b in below):.2f} m "
              f"at {min(below, key=lambda b: b[1])[0]}")

    # 5. Write CSV
    out_path = cfg["out_csv"]
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["point_index", "lat", "lon",
                    "elevation_m", "below_threshold"])
        for i, ((lat, lon), elev) in enumerate(zip(points, valid)):
            w.writerow([i, round(lat, 6), round(lon, 6),
                        round(elev, 3), elev < cfg["threshold_m"]])
    print(f"  CSV saved: {out_path}")


if __name__ == "__main__":
    print("Infrastructure Elevation Checker")
    print("Dataset: EU-DEM 25m (EGM2008 / MSL datum)")
    print("Source:  OpenTopoData API + OpenStreetMap Overpass")

    # Run only the sections you want — comment out others
    sections_to_run = [
        "aveiro_zone_b",
        "aveiro_zone_a",
        "a1_azambuja",
    ]

    for key in sections_to_run:
        if key in SECTIONS:
            run_section(key, SECTIONS[key])
        else:
            print(f"\nUnknown section key: {key}")

    print("\nDone.")
