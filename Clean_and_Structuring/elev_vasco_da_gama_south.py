"""
elev_vasco_da_gama_south.py
============================
Elevation profile of the southern approach to the Vasco da Gama bridge,
covering both the road (A12 motorway) and rail (Fertagus / Linha do Sul)
corridors as they cross the southern Tagus floodplain (lezíria sul).

GEOGRAPHY
---------
The Vasco da Gama bridge (17.2 km, opened 1998) spans the Tagus estuary
between Sacavém/Olivais (north) and Alcochete (south). On the south side,
both road and rail cross several kilometres of low-lying marshland and
reclaimed farmland before reaching higher ground near Pinhal Novo / Setúbal.

  Road (A12 / CRIPS): south approach viaduct → Alcochete → IC13 / A12
  Rail (Fertagus):    south end of bridge → Coina → Pinhal Novo

FLOOD MECHANISM
---------------
DIRECT SLR INUNDATION + STORM SURGE — different from the Tagus floodplain
railway section (which is compound fluvial). Here:
  • The southern shore is an estuarine margin; terrain sits at or very
    slightly above mean high water.
  • SLR raises the tidal range directly onto the marsh surface.
  • Storm surges (Tagus estuary is exposed to Atlantic SW swells funnelled
    into the estuary) compound the SLR signal.
  • No dam/river discharge component — purely tidal + surge driven.

DOCUMENTED EVENTS / CONCERNS
-----------------------------
  • 2010 : southern lezíria flooding (Alcochete / Samouco area)
  • 2023 : coastal flooding warnings for Tagus south margin (Setúbal district)
  • 2026 : Tagus estuary storm surge event

SECTIONS
--------
  A — Bridge south end → Alcochete (road approach viaduct, ~5 km)
       OSM: highway=motorway (A12 / CRIPS approach)
  B — Alcochete → IC13 junction (~8 km on flat lezíria)
       OSM: highway=motorway (A12) or primary
  C — Rail south approach: bridge end → Coina (~15 km)
       OSM: railway=rail [usage=main] — Fertagus / Linha do Sul

INTERVAL : 50 m  — fine resolution for short low-lying sections
THRESHOLD: 3.0 m — lower than inland sections; direct tidal risk

OUTPUTS
-------
  elev_vdg_sec_A_road_viaduct.csv
  elev_vdg_sec_B_road_alcochete.csv
  elev_vdg_sec_C_rail_south.csv
  elev_vdg_COMBINED_low_points.csv

REQUIREMENTS
------------
  pip install requests
  python elev_vasco_da_gama_south.py
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

INTERVAL_M   = 50
THRESHOLD_M  = 3.0    # lower — direct tidal/SLR exposure

# Documented flood/concern zones for annotation
FLOOD_ZONES = [
    {"name": "Bridge south approach viaduct",
     "lat_min": 38.650, "lat_max": 38.700, "events": "structural SLR exposure"},
    {"name": "Alcochete / Samouco marshes",
     "lat_min": 38.700, "lat_max": 38.760, "events": "2010, 2026"},
    {"name": "Rail south approach (Fertagus)",
     "lat_min": 38.600, "lat_max": 38.700, "events": "tidal/SLR exposure"},
]

SECTIONS = [
    {
        "name":     "A — Road viaduct: bridge south end → Alcochete (~5 km)",
        "bbox":     (38.640, -8.980, 38.710, -8.920),
        "osm_type": "motorway",       # highway=motorway
        "out_csv":  "elev_vdg_sec_A_road_viaduct.csv",
    },
    {
        "name":     "B — A12 road: Alcochete → IC13 junction (~8 km)",
        "bbox":     (38.700, -8.980, 38.790, -8.870),
        "osm_type": "motorway",
        "out_csv":  "elev_vdg_sec_B_road_alcochete.csv",
    },
    {
        "name":     "C — Rail south approach: bridge end → Coina (~15 km)",
        "bbox":     (38.580, -9.000, 38.720, -8.870),
        "osm_type": "rail",           # railway=rail usage=main
        "out_csv":  "elev_vdg_sec_C_rail_south.csv",
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
            return f"{z['name']} ({z['events']})"
    return ""


# ── API ───────────────────────────────────────────────────────────────────────

def fetch_ways(bbox, osm_type):
    S, W, N, E = bbox
    if osm_type == "motorway":
        query = f"""
            [out:json][timeout:90];
            way["highway"="motorway"]({S},{W},{N},{E});
            out geom tags;
        """
    else:  # rail
        query = f"""
            [out:json][timeout:90];
            way["railway"="rail"]["usage"="main"][!"service"]({S},{W},{N},{E});
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
            if osm_type == "motorway":
                refs = sorted({w.get("tags", {}).get("ref", "?") for w in ways})
                print(f"     Motorway refs found: {refs}")
                # Filter to A12 if tagged; otherwise keep all (no other motorway here)
                a12 = [w for w in ways if w.get("tags", {}).get("ref", "A12") == "A12"]
                if a12:
                    print(f"     Filtered to A12: {len(a12)} ways")
                    return a12
                print(f"     No ref=A12 found — using all {len(ways)} motorway ways")
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

    osm_label = "motorway (A12)" if sec["osm_type"] == "motorway" else "rail (usage=main)"
    print(f"  → Fetching OSM ways ({osm_label})...")
    ways = fetch_ways(sec["bbox"], sec["osm_type"])
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

    # Note on bridge deck — EU-DEM will read WATER for the bridge itself
    if sec["osm_type"] == "motorway" and "viaduct" in sec["name"].lower():
        print(f"\n  NOTE: The viaduct section over open water will return 0 m")
        print(f"  (EU-DEM reads sea/estuary surface). These points should be")
        print(f"  excluded — they represent water, not road deck elevation.")
        print(f"  The bridge deck itself is ~12–25 m above water (structural).")
        water_pts = sum(1 for _, e in valid if e <= 0.5)
        print(f"  Points ≤0.5 m (likely water/viaduct): {water_pts}")

    with open(sec["out_csv"], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m",
                    "below_threshold", "flood_zone", "note"])
        for i, ((lat, lon), e) in enumerate(valid):
            note = "water/viaduct — exclude" if e <= 0.5 else ""
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M, flood_zone_label(lat), note])
    print(f"  CSV saved → {sec['out_csv']}")

    # Collect flagged points (exclude likely water/bridge readings)
    for pt, e in below:
        if e > 0.5:   # exclude water surface readings
            all_low_points.append({
                "section":    sec["name"],
                "lat":        pt[0], "lon": pt[1],
                "elev_m":     e,
                "flood_zone": flood_zone_label(pt[0]),
            })

    print("  (pausing 12 s before next section...)")
    time.sleep(12)


if __name__ == "__main__":
    print("Vasco da Gama Bridge — South Approach Elevation Check")
    print(f"Sections         : Road viaduct, A12 flat approach, Rail south")
    print(f"Mechanism        : Direct SLR inundation + estuarine storm surge")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL  (tidal exposure → lower threshold)")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 ≈ mean sea level)")
    print(f"NOTE: Bridge deck over open water will read ~0 m — these are")
    print(f"      water-surface returns, not infrastructure elevation.")

    for s in SECTIONS:
        run(s)

    if all_low_points:
        all_low_points.sort(key=lambda x: x["elev_m"])
        combined = "elev_vdg_COMBINED_low_points.csv"
        with open(combined, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "lat", "lon", "elev_m", "flood_zone"])
            for p in all_low_points:
                w.writerow([p["section"], round(p["lat"],6),
                            round(p["lon"],6), round(p["elev_m"],3),
                            p["flood_zone"]])
        print(f"\n  Combined low-points → {combined}")
        print(f"  Total flagged >0.5 m and <{THRESHOLD_M} m: {len(all_low_points)}")

    print("\nDone.")
