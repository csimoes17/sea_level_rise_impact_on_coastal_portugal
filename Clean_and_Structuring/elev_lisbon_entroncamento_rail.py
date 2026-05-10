"""
elev_lisbon_entroncamento_rail.py
==================================
Elevation profile of the Linha do Norte between Lisboa and Entroncamento.

KEY FILTER: ["railway"="rail"]["usage"="main"][!"service"]
  - "usage"="main"  → intercity mainline only (excludes metro, suburban,
                       commuter, tram, and industrial lines)
  - [!"service"]    → excludes sidings and yard tracks
  This combination gives us only the Linha do Norte mainline ways.

Three segments (easier to read + avoids server timeouts on large queries):
  SEG 1 — Lisboa → Vila Franca de Xira      (~35 km)
  SEG 2 — Vila Franca de Xira → Azambuja    (~25 km)  ← Tagus floodplain
  SEG 3 — Azambuja → Entroncamento           (~60 km)

REQUIREMENTS:  pip install requests
"""

import time, math, csv, requests

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPENTOPO_URL  = "https://api.opentopodata.org/v1/eudem25m"
HEADERS       = {"User-Agent": "InfraElevChecker/1.0 (dissertation research)"}
BATCH_SIZE    = 100
PAUSE_S       = 1.5

INTERVAL_M    = 200    # 200 m — total ~120 km
THRESHOLD_M   = 5.0    # flag points below this

SECTIONS = [
    {
        "name":    "Seg 1 — Lisboa → Vila Franca de Xira",
        "bbox":    (38.700, -9.150, 38.970, -8.980),
        "out_csv": "elev_seg1_lisboa_vfx.csv",
    },
    {
        "name":    "Seg 2 — Vila Franca de Xira → Azambuja  [TAGUS FLOODPLAIN]",
        "bbox":    (38.950, -9.020, 39.120, -8.820),
        "out_csv": "elev_seg2_vfx_azambuja.csv",
    },
    {
        "name":    "Seg 3 — Azambuja → Entroncamento",
        "bbox":    (39.100, -8.900, 39.480, -8.450),
        "out_csv": "elev_seg3_azambuja_entroncamento.csv",
    },
]


# ── GEOMETRY ──────────────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def sample_ways(ways, interval_m):
    nodes = []
    for way in ways:
        for pt in way.get("geometry", []):
            nodes.append((pt["lat"], pt["lon"]))
    if not nodes:
        return []
    samples = [nodes[0]]
    carry = 0.0
    for i in range(1, len(nodes)):
        seg = haversine_m(*nodes[i-1], *nodes[i])
        if seg < 1e-6:
            continue
        t = (interval_m - carry) / seg
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

def fetch_ways(bbox, retries=3):
    S, W, N, E = bbox
    # usage=main → intercity mainline only; excludes metro/suburban/tram
    query = f"""
        [out:json][timeout:120];
        way["railway"="rail"]["usage"="main"][!"service"]({S},{W},{N},{E});
        out geom;
    """
    for attempt, server in enumerate(OVERPASS_SERVERS):
        try:
            if attempt > 0:
                print(f"     Retrying with server {attempt+1}...")
                time.sleep(5)
            r = requests.post(server, data={"data": query},
                              headers=HEADERS, timeout=150)
            r.raise_for_status()
            ways = [el for el in r.json()["elements"] if el["type"] == "way"]
            return ways
        except Exception as e:
            print(f"     Server {attempt+1} failed: {e}")
    return []


def fetch_elevations(points):
    elevs = []
    total = math.ceil(len(points) / BATCH_SIZE)
    for i in range(0, len(points), BATCH_SIZE):
        batch   = points[i : i + BATCH_SIZE]
        loc_str = "|".join(f"{lat},{lon}" for lat, lon in batch)
        for attempt in range(3):
            try:
                r = requests.get(OPENTOPO_URL,
                                 params={"locations": loc_str}, timeout=30)
                r.raise_for_status()
                for res in r.json()["results"]:
                    elevs.append(res["elevation"])
                break
            except Exception as e:
                if attempt == 2:
                    elevs.extend([None] * len(batch))
                else:
                    time.sleep(3)
        last = elevs[-1]
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {f'{last:.2f} m' if last is not None else 'None'}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run(sec):
    print(f"\n{'='*68}")
    print(f"  {sec['name']}")
    print(f"{'='*68}")

    print("  → Fetching OSM mainline ways (usage=main filter)...")
    ways = fetch_ways(sec["bbox"])
    print(f"     {len(ways)} way(s) | "
          f"{sum(len(w.get('geometry',[])) for w in ways)} nodes")

    if not ways:
        print("  ✗ No ways returned.")
        return

    print(f"  → Sampling every {INTERVAL_M} m...")
    pts = sample_ways(ways, INTERVAL_M)
    print(f"     {len(pts)} sample points")

    print("  → Querying EU-DEM 25m elevations...")
    elevs = fetch_elevations(pts)

    valid = [e for e in elevs if e is not None]
    if not valid:
        print("  ✗ No valid elevations.")
        return

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
        print(f"  Lowest point      : {low_pt[1]:.2f} m  at "
              f"lat={low_pt[0][0]:.6f}, lon={low_pt[0][1]:.6f}")

    with open(sec["out_csv"], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m", "below_threshold"])
        for i, ((lat, lon), e) in enumerate(zip(pts, valid)):
            w.writerow([i, round(lat,6), round(lon,6),
                        round(e,3), e < THRESHOLD_M])
    print(f"  CSV saved → {sec['out_csv']}")

    # Pause between segments to avoid server overload
    print("  (pausing 10 s before next segment...)")
    time.sleep(10)


if __name__ == "__main__":
    print("Linha do Norte — Lisboa to Entroncamento elevation check")
    print(f"Filter           : mainline only (usage=main, no service tag)")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 = mean sea level)")
    for s in SECTIONS:
        run(s)
    print("\nDone.")
