"""
elev_a1_tagus_floodplain.py
============================
Elevation profile of the A1 motorway through the Tagus floodplain.

SECTIONS COVERED
----------------
  A — Alverca do Ribatejo → Vila Franca de Xira    (~8 km)
  B — Vila Franca de Xira → Azambuja / Carregado   (~18 km)

These two sections cross the Tagus lezíria — the same low-lying
floodplain as the Linha do Norte railway checked in the companion
script. The A1 here runs on an embankment but the road crown is
only marginally above the surrounding terrain.

FLOOD MECHANISM
---------------
Compound fluvial + tidal backwater (same as railway section):
SLR raises mean sea level at the Tagus mouth → reduces hydraulic
gradient → same rainfall/dam-release events produce higher, longer
floodwater on the lezíria. NOT direct SLR inundation.

DOCUMENTED EVENTS
-----------------
  Alverca / Vila Franca : 2026 (road closures)
  Carregado / Azambuja  : 2022, 2026

OSM FILTER
----------
  highway=motorway  AND  ref=A1
  The ref tag on individual ways is often absent; we therefore
  query all motorway ways in the bbox and print the ref values
  found so results can be verified. In the A1 corridor between
  Alverca and Azambuja no other motorway exists.

INTERVAL : 100 m  (section is ~26 km total — good resolution)
THRESHOLD: 5.0 m  (flag for review; road crown likely 0.5–1.5 m
                   above surrounding terrain per AASHTO embankment)

OUTPUTS
-------
  elev_a1_sec_A_alverca_vfx.csv
  elev_a1_sec_B_vfx_azambuja.csv
  elev_a1_COMBINED_low_points.csv

REQUIREMENTS
------------
  pip install requests
  python elev_a1_tagus_floodplain.py
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

INTERVAL_M   = 100
THRESHOLD_M  = 5.0

# Documented flood zones for annotation
FLOOD_ZONES = [
    {"name": "Alverca / Vila Franca de Xira",
     "lat_min": 38.870, "lat_max": 38.975, "events": "2026"},
    {"name": "Carregado / Azambuja",
     "lat_min": 38.975, "lat_max": 39.110, "events": "2022, 2026"},
]

SECTIONS = [
    {
        "name":    "A — Alverca → Vila Franca de Xira (~8 km)",
        "bbox":    (38.870, -9.060, 38.975, -8.960),
        "out_csv": "elev_a1_sec_A_alverca_vfx.csv",
    },
    {
        "name":    "B — Vila Franca de Xira → Azambuja/Carregado (~18 km)",
        "bbox":    (38.950, -9.010, 39.110, -8.820),
        "out_csv": "elev_a1_sec_B_vfx_azambuja.csv",
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


# ── API ───────────────────────────────────────────────────────────────────────

def fetch_ways(bbox):
    S, W, N, E = bbox
    # Query all motorway ways — in this corridor only A1 exists.
    # We print the ref values found so you can verify.
    query = f"""
        [out:json][timeout:90];
        way["highway"="motorway"]({S},{W},{N},{E});
        out geom tags;
    """
    for i, server in enumerate(OVERPASS_SERVERS):
        try:
            if i > 0:
                print(f"     Trying server {i+1}...")
                time.sleep(6)
            r = requests.post(server, data={"data": query},
                              headers=HEADERS, timeout=120)
            r.raise_for_status()
            ways = [el for el in r.json()["elements"] if el["type"] == "way"]
            refs = sorted({w.get("tags", {}).get("ref", "?") for w in ways})
            print(f"     Motorway refs in bbox: {refs}")
            # Keep only A1 if ref tag is present; otherwise keep all
            # (in this corridor no other motorway exists)
            a1_ways = [w for w in ways if w.get("tags", {}).get("ref", "A1") == "A1"]
            if a1_ways:
                print(f"     Filtered to A1: {len(a1_ways)} ways")
                return a1_ways
            print(f"     No ref=A1 tag found — using all {len(ways)} motorway ways")
            return ways
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
                    print(f"     ⚠ batch failed: {e}")
                    elevs.extend([None] * len(batch))
                else:
                    time.sleep(4)
        last = elevs[-1]
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {f'{last:.2f} m' if last is not None else 'None'}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

all_low_points = []

def run(sec):
    print(f"\n{'='*68}")
    print(f"  SECTION {sec['name']}")
    print(f"{'='*68}")

    print("  → Fetching OSM motorway ways...")
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
              f"lat={low_pt[0][0]:.6f} lon={low_pt[0][1]:.6f}")
        if zone:
            print(f"  Flood zone        : {zone}")

    # Note on embankment correction
    print(f"\n  NOTE: EU-DEM reads terrain elevation (25m average).")
    print(f"  The A1 embankment crown is typically 0.5–1.5 m above")
    print(f"  surrounding lezíria terrain in this section.")
    print(f"  Effective road crown ≈ DEM minimum + ~1.0 m (conservative).")
    if below:
        print(f"  Estimated road crown at lowest DEM point: "
              f"~{min(e for _,e in below)+1.0:.2f} m MSL")

    with open(sec["out_csv"], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m",
                    "below_threshold", "flood_zone"])
        for i, ((lat, lon), e) in enumerate(valid):
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M, flood_zone_label(lat)])
    print(f"  CSV saved → {sec['out_csv']}")

    for pt, e in below:
        all_low_points.append({
            "section":    sec["name"],
            "lat":        pt[0], "lon": pt[1],
            "elev_m":     e,
            "flood_zone": flood_zone_label(pt[0]),
        })

    print("  (pausing 12 s before next section...)")
    time.sleep(12)


if __name__ == "__main__":
    print("A1 Motorway — Tagus Floodplain Elevation Check")
    print(f"Section          : Alverca → Azambuja/Carregado (~26 km)")
    print(f"Mechanism        : Compound fluvial + tidal backwater (SLR-driven)")
    print(f"Filter           : highway=motorway (ref=A1 where tagged)")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 ≈ mean sea level)")

    for s in SECTIONS:
        run(s)

    if all_low_points:
        all_low_points.sort(key=lambda x: x["elev_m"])
        combined = "elev_a1_COMBINED_low_points.csv"
        with open(combined, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "lat", "lon", "elev_m", "flood_zone"])
            for p in all_low_points:
                w.writerow([p["section"], round(p["lat"],6),
                            round(p["lon"],6), round(p["elev_m"],3),
                            p["flood_zone"]])
        print(f"\n  Combined low-points → {combined}")
        print(f"  Total flagged (< {THRESHOLD_M} m): {len(all_low_points)}")

    print("\nDone.")
