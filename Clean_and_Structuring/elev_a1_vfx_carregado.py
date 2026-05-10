"""
elev_a1_vfx_carregado.py
=========================
Elevation profile of the A1 motorway through the Tagus lezíria,
focused on the vulnerable section between Vila Franca de Xira and
Carregado / Azambuja.

WHY THIS SECTION
----------------
The A1 between VFx and Carregado runs across the Tagus floodplain
at very low elevation — the same lezíria crossed by the Linha do Norte
railway. Both the railway and the A1 are at risk from compound
fluvial + tidal backwater flooding.

DOCUMENTED EVENTS
-----------------
  Carregado / Azambuja : 2022, 2026 (road disruption reported)
  Vila Franca de Xira  : 2026

OSM FIX
-------
The A1 in OSM is tagged  ref="A 1"  (with a space between A and 1).
Previous script used "A1" → filter failed → captured all motorways.
This version filters correctly on "A 1".

INTERVAL  : 25 m   (fine resolution — section is ~20 km)
THRESHOLD : 5.0 m  (flag for review)

OUTPUTS
-------
  elev_a1_vfx_carregado_full.csv        — all sample points
  elev_a1_vfx_carregado_low_points.csv  — flagged points only

REQUIREMENTS
------------
  pip install requests
  python elev_a1_vfx_carregado.py
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

INTERVAL_M   = 25     # 25 m — fine resolution
THRESHOLD_M  = 5.0

# Tight bbox: A1 corridor VFx → Carregado / Azambuja
# Excludes hills to west, A10 junction to east is handled by ref filter
BBOX = (38.940, -9.010, 39.110, -8.850)   # (S, W, N, E)

FLOOD_ZONES = [
    {"name": "Vila Franca de Xira approach",
     "lat_min": 38.940, "lat_max": 38.975, "events": "2026"},
    {"name": "Carregado / Azambuja",
     "lat_min": 38.975, "lat_max": 39.110, "events": "2022, 2026"},
]

A1_REF = "A 1"   # OSM uses a space: "A 1" not "A1"


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

def fetch_a1_ways():
    S, W, N, E = BBOX
    query = f"""
        [out:json][timeout:90];
        way["highway"="motorway"]["ref"="{A1_REF}"]({S},{W},{N},{E});
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
            names = sorted({w.get("tags", {}).get("name", "?") for w in ways})
            print(f"     refs={refs}  names={names}")
            print(f"     → {len(ways)} A1 ways returned")
            return ways
        except Exception as e:
            print(f"     Server {i+1} failed: {e}")

    # Fallback: query all motorways and filter manually
    print("     All servers failed with ref filter — trying without ref tag...")
    query_all = f"""
        [out:json][timeout:90];
        way["highway"="motorway"]({S},{W},{N},{E});
        out geom tags;
    """
    for i, server in enumerate(OVERPASS_SERVERS):
        try:
            r = requests.post(server, data={"data": query_all},
                              headers=HEADERS, timeout=120)
            r.raise_for_status()
            all_ways = [el for el in r.json()["elements"] if el["type"] == "way"]
            refs = sorted({w.get("tags", {}).get("ref", "?") for w in all_ways})
            print(f"     All motorway refs in bbox: {refs}")
            # Filter: keep only ways whose ref contains "A 1" or "A1"
            a1 = [w for w in all_ways
                  if "A 1" in w.get("tags", {}).get("ref", "")
                  or "A1"  in w.get("tags", {}).get("ref", "")]
            if a1:
                print(f"     Filtered to A1-containing ways: {len(a1)}")
                return a1
            print(f"     No A1 ways found — returning all {len(all_ways)} for inspection")
            return all_ways
        except Exception as e:
            print(f"     Fallback server {i+1} failed: {e}")
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

def main():
    print("=" * 68)
    print("A1 Motorway — Vila Franca de Xira → Carregado / Azambuja")
    print(f"OSM filter       : highway=motorway  ref=\"{A1_REF}\"")
    print(f"Mechanism        : Compound fluvial + tidal backwater (SLR-driven)")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 ≈ mean sea level)")
    print("=" * 68)

    print("\n  → Fetching A1 ways from OSM...")
    ways = fetch_a1_ways()
    print(f"     {len(ways)} way(s) | "
          f"{sum(len(w.get('geometry',[])) for w in ways)} nodes")

    if not ways:
        print("  ✗ No ways returned. Check bbox or OSM tag.")
        return

    print(f"\n  → Sampling every {INTERVAL_M} m...")
    pts = sample_ways(ways, INTERVAL_M)
    print(f"     {len(pts)} sample points")

    print("\n  → Querying EU-DEM 25m elevations...")
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

        # Plausible road-crown estimate
        # EU-DEM 25m reads terrain average. A1 embankment is ~0.5–1.5 m
        # above lezíria surface. Minimum plausible track = DEM floor + 0.5 m.
        credible = [(pt, e) for pt, e in valid if e >= 1.5]
        if credible:
            c_min = min(e for _, e in credible)
            print(f"\n  After filtering DEM noise (≥1.5 m filter):")
            print(f"  Credible minimum  : {c_min:.2f} m MSL")
            print(f"  Est. road crown   : ~{c_min + 0.75:.2f} m MSL"
                  f"  (DEM floor + 0.75 m embankment, conservative)")

        # By flood zone
        print(f"\n  Low points by zone:")
        zones_seen = {}
        for pt, e in below:
            lbl = flood_zone_label(pt[0]) or "unlabelled"
            if lbl not in zones_seen:
                zones_seen[lbl] = []
            zones_seen[lbl].append(e)
        for lbl, vals in sorted(zones_seen.items()):
            print(f"    {lbl[:55]:55s}  n={len(vals):4d}  "
                  f"min={min(vals):.2f} m  mean={sum(vals)/len(vals):.2f} m")

    # Full CSV
    full_csv = "elev_a1_vfx_carregado_full.csv"
    with open(full_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m",
                    "below_threshold", "flood_zone"])
        for i, ((lat, lon), e) in enumerate(valid):
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M, flood_zone_label(lat)])
    print(f"\n  Full CSV   → {full_csv}")

    # Low-points CSV (sorted by elevation)
    if below:
        below_sorted = sorted(below, key=lambda x: x[1])
        low_csv = "elev_a1_vfx_carregado_low_points.csv"
        with open(low_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["lat", "lon", "elev_m", "flood_zone"])
            for (lat, lon), e in below_sorted:
                w.writerow([round(lat,6), round(lon,6),
                            round(e,3), flood_zone_label(lat)])
        print(f"  Low CSV    → {low_csv}  ({len(below)} points)")

    print("\nDone.")


if __name__ == "__main__":
    main()
