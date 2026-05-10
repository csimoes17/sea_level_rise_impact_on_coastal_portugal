"""
elev_linha_norte_relation.py
=============================
Elevation profile of the Linha do Norte mainline using the OSM ROUTE RELATION
rather than a bounding box.

METHODOLOGICAL IMPROVEMENT vs. previous scripts
------------------------------------------------
Previous approach: bounding box → all railway ways in area → many off-track
  ways included (sidings, yards, parallel infrastructure, misaligned geometry).

This approach:
  1. Query OSM for the Linha do Norte route RELATION (a specific named object
     that enumerates exactly which ways form the mainline).
  2. Retrieve only those member ways — no sidings, no adjacent infrastructure.
  3. Filter to the study section by latitude (Sacavém → Azambuja).
  4. Sample at INTERVAL_M metres along the centreline.
  5. Query EU-DEM 25m elevation at each sample point.

The relation ID is printed at runtime and should be cited in the dissertation
as the data source (e.g. "OSM relation ID 123456, retrieved YYYY-MM-DD").

KNOWN LIMITATION
----------------
EU-DEM resolution is 25 m. Each elevation value represents the mean terrain
within a 25×25 m cell centred on the sample point. This may include adjacent
ground (embankment sides, ditches). Values are therefore conservative lower
bounds on the true track surface elevation, and are reported as such.

OUTPUTS
-------
  elev_relation_full_profile.csv      — all sample points with elevation
  elev_relation_low_points.csv        — points below THRESHOLD_M only, sorted
  elev_relation_summary.txt           — text summary for dissertation reference

REQUIREMENTS:  pip install requests
               python elev_linha_norte_relation.py
"""

import time, math, csv, requests, datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPENTOPO_URL = "https://api.opentopodata.org/v1/eudem25m"
HEADERS      = {"User-Agent": "LinhaDoNorteElevation/1.0 (dissertation research)"}

INTERVAL_M   = 50      # sample every 50 m along mainline
THRESHOLD_M  = 5.0     # flag points below this (m MSL)
BATCH_SIZE   = 100
PAUSE_S      = 1.5

# Study section: Sacavém (south) → Azambuja (north)
# Ways outside this latitude band are excluded
LAT_MIN = 38.770   # south of Sacavém
LAT_MAX = 39.110   # north of Azambuja

# Flood zone labels (for annotation)
FLOOD_ZONES = [
    {"name": "Sacavém / Bobadela",    "lat_min": 38.770, "lat_max": 38.855,
     "events": "2008, 2014, 2026"},
    {"name": "Póvoa de Santa Iria",   "lat_min": 38.855, "lat_max": 38.890,
     "events": "2008, 2010, 2026"},
    {"name": "Alverca / Vila Franca", "lat_min": 38.890, "lat_max": 38.980,
     "events": "2026"},
    {"name": "Castanheira / Azambuja","lat_min": 38.980, "lat_max": 39.110,
     "events": "2022, 2026"},
]


# ── STEP 1: FIND THE LINHA DO NORTE ROUTE RELATION ───────────────────────────

def find_relation(server):
    """Return list of OSM relations named 'Linha do Norte' with route tag."""
    query = """
        [out:json][timeout:60];
        relation["name"~"Linha do Norte"]["type"="route"];
        out tags;
    """
    r = requests.post(server, data={"data": query},
                      headers=HEADERS, timeout=90)
    r.raise_for_status()
    return r.json().get("elements", [])


# ── STEP 2: GET MEMBER WAYS OF THE RELATION ───────────────────────────────────

def get_relation_ways(relation_id, server):
    """Get all member ways of the relation with full geometry."""
    query = f"""
        [out:json][timeout:180];
        relation({relation_id})->.r;
        way(r.r)["railway"="rail"];
        out geom;
    """
    r = requests.post(server, data={"data": query},
                      headers=HEADERS, timeout=210)
    r.raise_for_status()
    return [el for el in r.json().get("elements", [])
            if el["type"] == "way"]


def filter_ways_by_lat(ways, lat_min, lat_max):
    """Keep only ways that have at least one node in the study latitude band."""
    result = []
    for way in ways:
        geom = way.get("geometry", [])
        if any(lat_min <= pt["lat"] <= lat_max for pt in geom):
            result.append(way)
    return result


# ── STEP 3: GEOMETRY SAMPLING ─────────────────────────────────────────────────

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def sample_ways(ways, interval_m, lat_min, lat_max):
    """
    Flatten ways into a node list, keep only nodes in [lat_min, lat_max],
    then sample every interval_m metres.
    """
    nodes = []
    for way in ways:
        for pt in way.get("geometry", []):
            if lat_min <= pt["lat"] <= lat_max:
                nodes.append((pt["lat"], pt["lon"]))
    if not nodes:
        return []

    # Sort by latitude (south to north) for clean profile output
    nodes.sort(key=lambda x: x[0])

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


# ── STEP 4: ELEVATION QUERY ───────────────────────────────────────────────────

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
                    elevs.extend([None] * len(batch))
                else:
                    time.sleep(4)
        last = elevs[-1]
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {f'{last:.2f} m' if last is not None else 'None'}")
        time.sleep(PAUSE_S)
    return elevs


# ── HELPERS ───────────────────────────────────────────────────────────────────

def flood_zone(lat):
    for z in FLOOD_ZONES:
        if z["lat_min"] <= lat <= z["lat_max"]:
            return z["name"], z["events"]
    return "", ""


def overpass_request(query, servers=OVERPASS_SERVERS):
    for i, server in enumerate(servers):
        try:
            if i > 0:
                print(f"  Retrying on server {i+1}...")
                time.sleep(6)
            r = requests.post(server, data={"data": query},
                              headers=HEADERS, timeout=210)
            r.raise_for_status()
            return r.json(), server
        except Exception as e:
            print(f"  Server {i+1} failed: {e}")
    return None, None


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_date = datetime.date.today().isoformat()
    print("=" * 68)
    print("  Linha do Norte — Elevation via OSM Route Relation")
    print(f"  Run date      : {run_date}")
    print(f"  Study section : Sacavém → Azambuja ({LAT_MIN}°N – {LAT_MAX}°N)")
    print(f"  Interval      : {INTERVAL_M} m")
    print(f"  Threshold     : < {THRESHOLD_M} m MSL flagged")
    print(f"  Elevation src : EU-DEM 25m (EGM2008 datum)")
    print("=" * 68)

    # ── 1. Find relation ──────────────────────────────────────────────────────
    print("\nSTEP 1: Searching for Linha do Norte route relation in OSM...")
    server_used = OVERPASS_SERVERS[0]
    relations = []
    for server in OVERPASS_SERVERS:
        try:
            relations = find_relation(server)
            server_used = server
            break
        except Exception as e:
            print(f"  Server failed: {e}")

    if not relations:
        print("  ✗ Could not find any Linha do Norte relations. Check connection.")
        exit(1)

    print(f"  Found {len(relations)} relation(s):")
    for rel in relations:
        tags = rel.get("tags", {})
        print(f"    ID={rel['id']}  name='{tags.get('name','')}'"
              f"  route='{tags.get('route','')}'"
              f"  ref='{tags.get('ref','')}'")

    # Use the first relation (or prompt user if multiple found)
    # For Linha do Norte there is typically one main relation
    rel_id = relations[0]["id"]
    rel_name = relations[0].get("tags", {}).get("name", "Linha do Norte")
    print(f"\n  → Using relation ID: {rel_id} ('{rel_name}')")
    print(f"  → CITE AS: OpenStreetMap relation {rel_id}, retrieved {run_date}")
    print(f"    URL: https://www.openstreetmap.org/relation/{rel_id}")

    # ── 2. Get member ways ────────────────────────────────────────────────────
    print(f"\nSTEP 2: Fetching member ways of relation {rel_id}...")
    ways = []
    for server in OVERPASS_SERVERS:
        try:
            ways = get_relation_ways(rel_id, server)
            break
        except Exception as e:
            print(f"  Server failed: {e}")

    print(f"  Total member ways: {len(ways)}")

    # Filter to study section
    ways_in_section = filter_ways_by_lat(ways, LAT_MIN, LAT_MAX)
    print(f"  Ways in study section ({LAT_MIN}°–{LAT_MAX}°N): "
          f"{len(ways_in_section)}")

    if not ways_in_section:
        print("  ✗ No ways found in study section. Check LAT_MIN / LAT_MAX.")
        exit(1)

    # ── 3. Sample centreline ──────────────────────────────────────────────────
    print(f"\nSTEP 3: Sampling centreline every {INTERVAL_M} m...")
    pts = sample_ways(ways_in_section, INTERVAL_M, LAT_MIN, LAT_MAX)
    print(f"  Sample points generated: {len(pts)}")

    # ── 4. Query elevations ───────────────────────────────────────────────────
    print(f"\nSTEP 4: Querying EU-DEM 25m elevations ({len(pts)} points)...")
    elevs = fetch_elevations(pts)

    # ── 5. Analyse ────────────────────────────────────────────────────────────
    valid = [(pts[i], elevs[i]) for i in range(len(elevs))
             if elevs[i] is not None]
    elev_vals = [e for _, e in valid]

    e_min  = min(elev_vals)
    e_mean = sum(elev_vals) / len(elev_vals)
    e_max  = max(elev_vals)
    below  = [(pt, e) for pt, e in valid if e < THRESHOLD_M]

    print(f"\n{'='*68}")
    print(f"  RESULTS — OSM relation {rel_id} — section {LAT_MIN}°–{LAT_MAX}°N")
    print(f"{'='*68}")
    print(f"  Sample points     : {len(valid)}")
    print(f"  Minimum elevation : {e_min:.3f} m MSL  ← reported floor")
    print(f"  Mean elevation    : {e_mean:.3f} m MSL")
    print(f"  Maximum elevation : {e_max:.3f} m MSL")
    print(f"  Points < {THRESHOLD_M} m    : {len(below)}"
          f"  ({100*len(below)/len(valid):.1f}%)")
    if below:
        lp = min(below, key=lambda x: x[1])
        zn, ev = flood_zone(lp[0][0])
        print(f"  Lowest point      : {lp[1]:.3f} m  "
              f"lat={lp[0][0]:.6f}, lon={lp[0][1]:.6f}")
        if zn:
            print(f"  Flood zone        : {zn} (documented events: {ev})")

    # By flood zone
    print(f"\n  BY FLOOD ZONE (points < {THRESHOLD_M} m only):")
    zones_data = {}
    for pt, e in below:
        zn, ev = flood_zone(pt[0])
        if zn:
            zones_data.setdefault(zn, {"events": ev, "elevs": []})
            zones_data[zn]["elevs"].append(e)
    for zn, zd in sorted(zones_data.items()):
        es = zd["elevs"]
        print(f"    {zn} (events: {zd['events']})")
        print(f"      n={len(es)}  min={min(es):.3f} m  mean={sum(es)/len(es):.3f} m")

    # ── 6. Write outputs ──────────────────────────────────────────────────────
    print("\nSTEP 5: Saving outputs...")

    # Full profile
    with open("elev_relation_full_profile.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx","lat","lon","elev_m","below_threshold",
                    "flood_zone","documented_events"])
        for i, ((lat, lon), e) in enumerate(valid):
            zn, ev = flood_zone(lat)
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M, zn, ev])
    print("  → elev_relation_full_profile.csv")

    # Low points only, sorted
    with open("elev_relation_low_points.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat","lon","elev_m","flood_zone","documented_events"])
        for pt, e in sorted(below, key=lambda x: x[1]):
            zn, ev = flood_zone(pt[0])
            w.writerow([round(pt[0],6), round(pt[1],6), round(e,3), zn, ev])
    print("  → elev_relation_low_points.csv")

    # Text summary for dissertation reference
    summary = [
        "LINHA DO NORTE — TRACK ELEVATION STUDY SECTION",
        f"Generated : {run_date}",
        f"Data source (OSM): relation ID {rel_id} — {rel_name}",
        f"URL: https://www.openstreetmap.org/relation/{rel_id}",
        f"Elevation source: EU-DEM 25m, EGM2008 datum (OpenTopoData API)",
        f"Study section: Sacavém → Azambuja ({LAT_MIN}°N – {LAT_MAX}°N)",
        f"Sample interval: {INTERVAL_M} m",
        "",
        "RESULTS",
        f"  Sample points : {len(valid)}",
        f"  Minimum elev  : {e_min:.3f} m MSL",
        f"  Mean elevation: {e_mean:.3f} m MSL",
        f"  Maximum elev  : {e_max:.3f} m MSL",
        f"  Points < {THRESHOLD_M} m  : {len(below)} ({100*len(below)/len(valid):.1f}%)",
        "",
        "LIMITATION",
        "  EU-DEM 25m resolution means each value is the mean terrain elevation",
        "  within a 25x25 m cell. Values may include adjacent ground and are",
        "  treated as conservative lower bounds on the true track surface.",
        "",
        "FLOOD ZONES (points below threshold)",
    ]
    for zn, zd in sorted(zones_data.items()):
        es = zd["elevs"]
        summary.append(f"  {zn}")
        summary.append(f"    Documented events: {zd['events']}")
        summary.append(f"    n={len(es)}  min={min(es):.3f} m  mean={sum(es)/len(es):.3f} m")

    with open("elev_relation_summary.txt", "w") as f:
        f.write("\n".join(summary))
    print("  → elev_relation_summary.txt")

    print("\nDone.")
