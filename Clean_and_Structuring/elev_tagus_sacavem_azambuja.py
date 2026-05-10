"""
elev_tagus_sacavem_azambuja.py
================================
Fine-grained elevation profile of the Linha do Norte through the Tagus
floodplain (lezíria), from Sacavém to Azambuja.

SECTION COVERED: ~50 km, split into two sub-sections for API reliability
  A: Sacavém / Bobadela → Vila Franca de Xira   (~22 km)
  B: Vila Franca de Xira → Azambuja              (~28 km)

DOCUMENTED FLOOD EVENTS (for calibration context):
  Sacavém / Bobadela        : 2008, 2014, 2026
  Póvoa de Santa Iria       : 2008, 2010, 2026
  Alverca / Vila Franca     : 2026
  Castanheira / Azambuja    : 2022, 2026

FLOOD MECHANISM:
  Compound fluvial + tidal backwater. SLR raises mean sea level at the
  Tagus mouth (Lisboa), reducing the river's hydraulic discharge gradient.
  The same rainfall + dam-release events that flood the lezíria today become
  more frequent and longer-lasting as the baseline rises. This is the same
  mechanism modelled for the Mondego section (10a_mondego_bypass.py).
  NOT a direct SLR inundation model — this is a frequency/duration model.

FILTER: ["railway"="rail"]["usage"="main"][!"service"]
  usage=main  → intercity mainline only (excludes metro, suburban, tram)
  no service  → excludes sidings and yard tracks

INTERVAL: 50 m — fine resolution to detect localised low-lying stretches
THRESHOLD: 5.0 m — flag points below this for detailed review

OUTPUTS:
  elev_tagus_A_sacavem_vfx.csv
  elev_tagus_B_vfx_azambuja.csv
  elev_tagus_COMBINED_low_points.csv   ← only flagged points, sorted by elev

REQUIREMENTS:  pip install requests
               python elev_tagus_sacavem_azambuja.py
"""

import time, math, csv, requests

# ── CONFIG ────────────────────────────────────────────────────────────────────

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPENTOPO_URL = "https://api.opentopodata.org/v1/eudem25m"
HEADERS      = {"User-Agent": "InfraElevChecker/1.0 (dissertation research)"}
BATCH_SIZE   = 100
PAUSE_S      = 1.5

INTERVAL_M   = 50     # 50 m resolution — detects short vulnerable sections
THRESHOLD_M  = 5.0    # flag points below this (m MSL)

# Known flood locations for output annotation
FLOOD_ZONES = [
    {"name": "Sacavém / Bobadela",      "lat_min": 38.770, "lat_max": 38.855,
     "events": "2008, 2014, 2026"},
    {"name": "Póvoa de Santa Iria",     "lat_min": 38.855, "lat_max": 38.890,
     "events": "2008, 2010, 2026"},
    {"name": "Alverca / Vila Franca",   "lat_min": 38.890, "lat_max": 38.980,
     "events": "2026"},
    {"name": "Castanheira / Azambuja",  "lat_min": 38.980, "lat_max": 39.110,
     "events": "2022, 2026"},
]

SECTIONS = [
    {
        "name":    "A — Sacavém / Bobadela → Vila Franca de Xira (~22 km)",
        "bbox":    (38.770, -9.130, 38.975, -8.970),
        "out_csv": "elev_tagus_A_sacavem_vfx.csv",
    },
    {
        "name":    "B — Vila Franca de Xira → Azambuja (~28 km)",
        "bbox":    (38.950, -9.020, 39.100, -8.830),
        "out_csv": "elev_tagus_B_vfx_azambuja.csv",
    },
]


# ── GEOMETRY ──────────────────────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
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


def flood_zone_label(lat):
    for z in FLOOD_ZONES:
        if z["lat_min"] <= lat <= z["lat_max"]:
            return f"{z['name']} (events: {z['events']})"
    return ""


# ── API CALLS ─────────────────────────────────────────────────────────────────

def fetch_ways(bbox):
    S, W, N, E = bbox
    query = f"""
        [out:json][timeout:120];
        way["railway"="rail"]["usage"="main"][!"service"]({S},{W},{N},{E});
        out geom;
    """
    for i, server in enumerate(OVERPASS_SERVERS):
        try:
            if i > 0:
                print(f"     Trying server {i+1}...")
                time.sleep(6)
            r = requests.post(server, data={"data": query},
                              headers=HEADERS, timeout=150)
            r.raise_for_status()
            return [el for el in r.json()["elements"] if el["type"] == "way"]
        except Exception as e:
            print(f"     Server {i+1} failed: {e}")
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
                                 params={"locations": loc_str}, timeout=40)
                r.raise_for_status()
                for res in r.json()["results"]:
                    elevs.append(res["elevation"])
                break
            except Exception as e:
                if attempt == 2:
                    print(f"     ⚠ batch failed after 3 attempts: {e}")
                    elevs.extend([None] * len(batch))
                else:
                    time.sleep(4)
        last = elevs[-1]
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {f'{last:.2f} m' if last is not None else 'None'}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

all_low_points = []   # collected across both sections for combined CSV

def run(sec):
    print(f"\n{'='*68}")
    print(f"  SECTION {sec['name']}")
    print(f"{'='*68}")

    print("  → Fetching OSM mainline ways...")
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

    valid = [(pts[i], elevs[i]) for i in range(len(elevs))
             if elevs[i] is not None]
    if not valid:
        print("  ✗ No valid elevations.")
        return

    elev_vals = [e for _, e in valid]
    e_min  = min(elev_vals)
    e_mean = sum(elev_vals) / len(elev_vals)
    e_max  = max(elev_vals)
    below  = [(pt, e) for pt, e in valid if e < THRESHOLD_M]

    print(f"\n  RESULTS")
    print(f"  Sample points     : {len(valid)}")
    print(f"  Minimum elevation : {e_min:.2f} m MSL  ← key value")
    print(f"  Mean elevation    : {e_mean:.2f} m MSL")
    print(f"  Maximum elevation : {e_max:.2f} m MSL")
    print(f"  Points < {THRESHOLD_M:.1f} m     : {len(below)}"
          f"  ({100*len(below)/len(valid):.1f}% of section)")
    if below:
        low_pt = min(below, key=lambda x: x[1])
        zone   = flood_zone_label(low_pt[0][0])
        print(f"  Lowest point      : {low_pt[1]:.2f} m  "
              f"lat={low_pt[0][0]:.6f}, lon={low_pt[0][1]:.6f}")
        if zone:
            print(f"  Flood zone        : {zone}")

    # Full CSV for this section
    with open(sec["out_csv"], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m",
                    "below_threshold", "flood_zone"])
        for i, ((lat, lon), e) in enumerate(valid):
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M, flood_zone_label(lat)])
    print(f"  CSV saved → {sec['out_csv']}")

    # Collect flagged points for combined output
    for pt, e in below:
        all_low_points.append({
            "section": sec["name"],
            "lat": pt[0], "lon": pt[1],
            "elev_m": e,
            "flood_zone": flood_zone_label(pt[0]),
        })

    print("  (pausing 12 s before next section...)")
    time.sleep(12)


if __name__ == "__main__":
    print("Linha do Norte — Tagus Floodplain Elevation Check")
    print(f"Section          : Sacavém → Azambuja (~50 km)")
    print(f"Mechanism        : Compound fluvial + tidal backwater (SLR-driven)")
    print(f"Filter           : mainline only (usage=main, no service tag)")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 = mean sea level)")

    for s in SECTIONS:
        run(s)

    # Write combined low-points CSV, sorted by elevation
    if all_low_points:
        all_low_points.sort(key=lambda x: x["elev_m"])
        combined_csv = "elev_tagus_COMBINED_low_points.csv"
        with open(combined_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "lat", "lon", "elev_m", "flood_zone"])
            for p in all_low_points:
                w.writerow([p["section"], round(p["lat"],6),
                            round(p["lon"],6), round(p["elev_m"],3),
                            p["flood_zone"]])
        print(f"\n  Combined low-points CSV → {combined_csv}")
        print(f"  Total flagged points (< {THRESHOLD_M} m): {len(all_low_points)}")

    print("\nDone.")
