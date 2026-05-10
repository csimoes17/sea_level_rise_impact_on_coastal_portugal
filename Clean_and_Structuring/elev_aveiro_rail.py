"""
elev_aveiro_rail.py
===================
Elevation profile of two Linha do Norte sections near the Ria de Aveiro:

  SECTION 1 — Zone B: Aveiro Lagoon Fringe (Cacia → Estarreja, ~10 km)
  SECTION 2 — Coastal stretch: Ovar → Arcozelo (close to Atlantic coast, ~20 km)

HOW IT WORKS
------------
1. Downloads the actual GPS centreline of the railway from OpenStreetMap
   (Overpass API). Filter [!"service"] excludes sidings and yard tracks —
   only mainline track ways are returned.
2. Places sample points every INTERVAL_M metres along the track geometry.
3. Queries the EU-DEM 25m elevation (EGM2008 / mean sea level datum) at
   each sample point via OpenTopoData API.
4. Reports min / mean / max elevation and saves a CSV.

REQUIREMENTS
------------
  pip install requests
  python elev_aveiro_rail.py
"""

import time, math, csv, requests

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
OPENTOPO_URL  = "https://api.opentopodata.org/v1/eudem25m"
HEADERS       = {"User-Agent": "InfraElevChecker/1.0 (dissertation research)"}
BATCH_SIZE    = 100    # max points per OpenTopoData request
PAUSE_S       = 1.2    # seconds between API calls

INTERVAL_M    = 100    # sample every 100 m along track
THRESHOLD_M   = 3.0    # flag points below this elevation (m MSL)

SECTIONS = [
    {
        "name":    "Zone B — Aveiro Lagoon Fringe (Cacia → Estarreja)",
        "bbox":    (40.620, -8.620, 40.760, -8.550),  # S, W, N, E
        "out_csv": "elev_zone_b_aveiro.csv",
    },
    {
        "name":    "Coastal stretch — Ovar → Arcozelo (Atlantic coast)",
        "bbox":    (40.850, -8.680, 41.060, -8.510),
        "out_csv": "elev_ovar_arcozelo.csv",
    },
]


# ── GEOMETRY ──────────────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def sample_ways(ways, interval_m):
    """Flatten OSM ways into one polyline and sample every interval_m metres."""
    nodes = []
    for way in ways:
        geom = way.get("geometry", [])
        if not geom:
            continue
        # Simple append — for a linear section this is fine
        for pt in geom:
            nodes.append((pt["lat"], pt["lon"]))

    if not nodes:
        return []

    samples = [nodes[0]]
    carry   = 0.0

    for i in range(1, len(nodes)):
        seg = haversine_m(*nodes[i-1], *nodes[i])
        if seg < 1e-6:
            continue
        needed = interval_m - carry
        t = needed / seg
        while t <= 1.0:
            lat = nodes[i-1][0] + t * (nodes[i][0] - nodes[i-1][0])
            lon = nodes[i-1][1] + t * (nodes[i][1] - nodes[i-1][1])
            samples.append((lat, lon))
            t += interval_m / seg
        carry = seg * (1.0 - (t - interval_m / seg))
        if carry >= interval_m:
            carry = 0.0

    return samples


# ── API CALLS ─────────────────────────────────────────────────────────────────

def fetch_ways(bbox):
    S, W, N, E = bbox
    query = f"""
        [out:json][timeout:60];
        way["railway"="rail"]["usage"="main"][!"service"]({S},{W},{N},{E});
        out geom;
    """
    r = requests.post(OVERPASS_URL, data={"data": query},
                      headers=HEADERS, timeout=90)
    r.raise_for_status()
    return [el for el in r.json()["elements"] if el["type"] == "way"]


def fetch_elevations(points):
    elevs = []
    for i in range(0, len(points), BATCH_SIZE):
        batch   = points[i : i + BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        r = requests.get(OPENTOPO_URL, params={"locations": loc_str}, timeout=30)
        r.raise_for_status()
        for res in r.json()["results"]:
            elevs.append(res["elevation"])
        last = elevs[-1]
        last_str = f"{last:.2f} m" if last is not None else "None (no data)"
        print(f"     batch {i//BATCH_SIZE+1}/{math.ceil(len(points)/BATCH_SIZE)}"
              f"  ({len(batch)} pts)  last = {last_str}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run(sec):
    print(f"\n{'='*68}")
    print(f"  {sec['name']}")
    print(f"{'='*68}")

    print("  → Fetching OSM mainline ways...")
    ways = fetch_ways(sec["bbox"])
    print(f"     {len(ways)} mainline way(s) | "
          f"{sum(len(w.get('geometry',[])) for w in ways)} nodes")

    if not ways:
        print("  ✗ No ways returned. Check bounding box.")
        return

    print(f"  → Sampling every {INTERVAL_M} m...")
    pts = sample_ways(ways, INTERVAL_M)
    print(f"     {len(pts)} sample points")

    print("  → Querying EU-DEM 25m elevations...")
    elevs = fetch_elevations(pts)

    valid = [e for e in elevs if e is not None]
    e_min  = min(valid);  e_max = max(valid)
    e_mean = sum(valid) / len(valid)
    below  = [(pts[i], valid[i]) for i in range(len(valid))
               if valid[i] < THRESHOLD_M]

    print(f"\n  RESULTS")
    print(f"  Sample points     : {len(valid)}")
    print(f"  Minimum elevation : {e_min:.2f} m MSL  ← key value")
    print(f"  Mean elevation    : {e_mean:.2f} m MSL")
    print(f"  Maximum elevation : {e_max:.2f} m MSL")
    print(f"  Points < {THRESHOLD_M:.1f} m     : {len(below)}"
          f"  ({100*len(below)/len(valid):.1f}% of section)")
    if below:
        low_pt = min(below, key=lambda b: b[1])
        print(f"  Lowest point      : {low_pt[1]:.2f} m at "
              f"lat={low_pt[0][0]:.6f}, lon={low_pt[0][1]:.6f}")

    with open(sec["out_csv"], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m", "below_threshold"])
        for i, ((lat, lon), e) in enumerate(zip(pts, valid)):
            w.writerow([i, round(lat,6), round(lon,6),
                        round(e,3), e < THRESHOLD_M])
    print(f"  CSV saved → {sec['out_csv']}")


if __name__ == "__main__":
    print("Linha do Norte — Aveiro / Coastal elevation check")
    print(f"Threshold flagged : < {THRESHOLD_M} m MSL")
    print(f"Sample interval   : {INTERVAL_M} m")
    print(f"Elevation source  : EU-DEM 25m (EGM2008 = mean sea level)")
    for s in SECTIONS:
        run(s)
    print("\nDone.")
