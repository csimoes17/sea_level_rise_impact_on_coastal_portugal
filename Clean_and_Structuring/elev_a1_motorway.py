"""
elev_a1_motorway.py
====================
Elevation profile of the A1 motorway through the Tagus floodplain,
specifically the section at risk from sea-level rise / river flooding:

  SECTION — A1 Tagus floodplain (Carregado → Azambuja, ~12 km)

The A1 in OSM is tagged as highway=motorway. This script queries all
motorway ways in the bounding box — which in this area should return
only the A1 carriageways (northbound + southbound). No sidings filter
needed for motorways; the "service" tag is not used on motorway ways.

HOW IT WORKS
------------
OpenStreetMap motorway geometry → sample every INTERVAL_M metres →
EU-DEM 25m elevation at each point → min/mean/max + CSV.

Note: the A1 has two carriageways (northbound + southbound). Both are
sampled and results are combined. The minimum is the key value.

REQUIREMENTS
------------
  pip install requests
  python elev_a1_motorway.py
"""

import time, math, csv, requests

OVERPASS_URL  = "https://overpass-api.de/api/interpreter"
OPENTOPO_URL  = "https://api.opentopodata.org/v1/eudem25m"
HEADERS       = {"User-Agent": "InfraElevChecker/1.0 (dissertation research)"}
BATCH_SIZE    = 100
PAUSE_S       = 1.2

INTERVAL_M    = 100    # 100 m — section is short (~12 km), want good resolution
THRESHOLD_M   = 5.0    # flag points below this

SECTIONS = [
    {
        "name":    "A1 — Carregado → Azambuja (Tagus floodplain, ~12 km)",
        "bbox":    (38.940, -8.960, 39.100, -8.790),
        "out_csv": "elev_a1_carregado_azambuja.csv",
    },
    {
        "name":    "A1 — Extended check: Alverca → Vila Franca de Xira",
        "bbox":    (38.870, -9.040, 38.970, -8.950),
        "out_csv": "elev_a1_alverca_vfx.csv",
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
    nodes = []
    for way in ways:
        for pt in way.get("geometry", []):
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


def fetch_ways(bbox):
    S, W, N, E = bbox
    # Query motorway ways — both A1 carriageways will be returned
    # Also try motorway_link to catch slip roads if needed, but exclude
    # those here to keep only the main carriageway
    query = f"""
        [out:json][timeout:60];
        way["highway"="motorway"]({S},{W},{N},{E});
        out geom;
    """
    r = requests.post(OVERPASS_URL, data={"data": query},
                      headers=HEADERS, timeout=90)
    r.raise_for_status()
    ways = [el for el in r.json()["elements"] if el["type"] == "way"]
    # Print refs found so user can verify it's A1 and not another motorway
    refs = set(w.get("tags", {}).get("ref", "?") for w in ways)
    print(f"     Motorway refs found in bbox: {refs}")
    return ways


def fetch_elevations(points):
    elevs = []
    total = math.ceil(len(points) / BATCH_SIZE)
    for i in range(0, len(points), BATCH_SIZE):
        batch   = points[i : i + BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        r = requests.get(OPENTOPO_URL, params={"locations": loc_str}, timeout=30)
        r.raise_for_status()
        for res in r.json()["results"]:
            elevs.append(res["elevation"])
        last = elevs[-1]
        last_str = f"{last:.2f} m" if last is not None else "None (no data)"
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {last_str}")
        time.sleep(PAUSE_S)
    return elevs


def run(sec):
    print(f"\n{'='*68}")
    print(f"  {sec['name']}")
    print(f"{'='*68}")

    print("  → Fetching OSM motorway ways...")
    ways = fetch_ways(sec["bbox"])
    print(f"     {len(ways)} way(s) | "
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
    print("A1 Motorway — Tagus floodplain elevation check")
    print(f"Threshold flagged : < {THRESHOLD_M} m MSL")
    print(f"Sample interval   : {INTERVAL_M} m")
    print(f"Elevation source  : EU-DEM 25m (EGM2008 = mean sea level)")
    for s in SECTIONS:
        run(s)
    print("\nDone.")
