"""
elev_a14_mondego_plain.py
==========================
Elevation profile of the A14 / IP3 across the Mondego floodplain
(lezíria), from the A17 junction near Maiorca to the flat plain
east of the Mondego river crossing.

SECTION OF INTEREST
-------------------
The flat Mondego lezíria section of the A14/IP3, defined by two
GPS reference points observed on Google Maps:
  West end : A17/IP3 junction near Maiorca  lat=40.145, lon=-8.750
  East end : A14 flat plain section         lat=40.172, lon=-8.720

BOUNDING BOX
------------
BBOX = (S=40.138, W=-8.758, N=40.178, E=-8.712)
Chosen to contain only the flat lezíria crossing, excluding:
  - Elevated western approaches toward Figueira da Foz (lon < -8.758)
  - Elevated eastern junction near Coimbra / A17 east (lat > 40.178,
    lon > -8.712), confirmed by diagnostic run to show 25–35 m terrain

APPROACH
--------
Same method as elev_a1_vfx_carregado.py (which worked cleanly):
  1. Query all motorway/trunk ways inside the bbox
  2. Print ref tags found (for verification)
  3. Filter to A14/IP3 ways where ref contains "A 14" or "IP 3"
  4. Sample every 25 m
  5. Query EU-DEM 25m elevation

No route-relation complexity — direct bbox + ref filter.

FLOOD MECHANISM
---------------
Compound fluvial + SLR — same mechanism as the Mondego railway bypass.
Documented flood events: 2019, 2021, 2026.

INTERVAL  : 25 m
THRESHOLD : 5.0 m MSL

OUTPUTS
-------
  elev_a14_mondego_full.csv
  elev_a14_mondego_low_points.csv
  elev_a14_mondego_summary.txt

REQUIREMENTS
------------
  pip install requests
  python elev_a14_mondego_plain.py
"""

import time, math, csv, requests
from datetime import datetime, timezone

# ── CONFIG ────────────────────────────────────────────────────────────────────

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OPENTOPO_URL   = "https://api.opentopodata.org/v1/eudem25m"
HEADERS        = {"User-Agent": "InfraElevChecker/1.0 (dissertation research)"}
BATCH_SIZE     = 100
PAUSE_S        = 1.5

INTERVAL_M     = 25
THRESHOLD_M    = 5.0
MONDEGO_EVENTS = "2019, 2021, 2026"

# Tight bbox: A14/IP3 lezíria crossing, Maiorca ↔ east of Mondego bridge
# Excludes elevated eastern junction (lon > -8.712) and western hills (lon < -8.758)
BBOX = (40.138, -8.758, 40.178, -8.712)   # (S, W, N, E)


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


# ── API ───────────────────────────────────────────────────────────────────────

def fetch_ways():
    S, W, N, E = BBOX
    # Query motorway AND trunk — IP3 sections may be tagged either way
    query = f"""
        [out:json][timeout:90];
        (
          way["highway"="motorway"]({S},{W},{N},{E});
          way["highway"="trunk"]({S},{W},{N},{E});
        );
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
            all_ways = [el for el in r.json()["elements"] if el["type"] == "way"]

            # Print all refs found so we can verify
            refs  = sorted({w.get("tags", {}).get("ref",  "?") for w in all_ways})
            names = sorted({w.get("tags", {}).get("name", "?") for w in all_ways})
            print(f"     Ways found in bbox: {len(all_ways)}")
            print(f"     Refs : {refs}")
            print(f"     Names: {names}")

            # Filter to A14 / IP3
            a14 = [w for w in all_ways
                   if "A 14" in w.get("tags", {}).get("ref", "")
                   or "IP 3" in w.get("tags", {}).get("ref", "")
                   or "IP3"  in w.get("tags", {}).get("ref", "")]

            if a14:
                a14_refs = sorted({w.get("tags", {}).get("ref", "?") for w in a14})
                print(f"     → Filtered to A14/IP3: {len(a14)} ways  refs={a14_refs}")
                return a14

            # Fallback: if ref tags are missing, use all motorway/trunk ways
            # (in this tight corridor no other major road exists)
            print(f"     No A14/IP3 ref found — using all {len(all_ways)} ways in bbox")
            return all_ways

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
        last_elev = elevs[-1]
        last_pt   = batch[-1]
        elev_str  = f"{last_elev:.2f} m" if last_elev is not None else "None"
        print(f"     batch {i//BATCH_SIZE+1}/{total} ({len(batch)} pts)"
              f"  last = {elev_str}"
              f"  lat={last_pt[0]:.6f} lon={last_pt[1]:.6f}")
        time.sleep(PAUSE_S)
    return elevs


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    S, W, N, E = BBOX
    print("=" * 68)
    print("A14 / IP3 — Mondego Lezíria Elevation Check")
    print(f"Section          : Maiorca (A17 jct) → Mondego plain east")
    print(f"Reference points : lat 40.145 lon -8.750  →  lat 40.172 lon -8.720")
    print(f"Bbox             : S={S} W={W} N={N} E={E}")
    print(f"Mechanism        : Compound fluvial + SLR (same as Mondego railway)")
    print(f"Documented events: {MONDEGO_EVENTS}")
    print(f"Threshold flagged: < {THRESHOLD_M} m MSL")
    print(f"Sample interval  : {INTERVAL_M} m")
    print(f"Elevation source : EU-DEM 25m (EGM2008 ≈ mean sea level)")
    print("=" * 68)

    print("\n  → Fetching A14/IP3 ways from OSM...")
    ways = fetch_ways()
    if not ways:
        print("  ✗ No ways returned.")
        return
    print(f"     {sum(len(w.get('geometry',[])) for w in ways)} nodes across {len(ways)} ways")

    print(f"\n  → Sampling every {INTERVAL_M} m...")
    S, W, N, E = BBOX
    pts_raw = sample_ways(ways, INTERVAL_M)
    pts = [(lat, lon) for lat, lon in pts_raw
           if S <= lat <= N and W <= lon <= E]
    print(f"     {len(pts_raw)} sample points (pre-clip)"
          f"  →  {len(pts)} after bbox clip")

    if not pts:
        print("  ✗ No sample points generated.")
        return

    print(f"\n  → Querying EU-DEM 25m elevations...")
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

    # Credible minimum: filter noise below 1m (water/DEM artefacts at bridge deck)
    credible = [e for e in elev_vals if e >= 1.0]
    c_min = min(credible) if credible else e_min

    quality = "✓  GOOD" if e_mean < 10 else "⚠  STILL HIGH"

    print(f"\n  RESULTS")
    print(f"  Sample points     : {len(valid)}")
    print(f"  Minimum elevation : {e_min:.2f} m MSL")
    print(f"  Credible minimum  : {c_min:.2f} m MSL  (≥1.0 m filter, excludes water)")
    print(f"  Mean elevation    : {e_mean:.2f} m MSL  {quality}")
    print(f"  Maximum elevation : {e_max:.2f} m MSL")
    print(f"  Points < {THRESHOLD_M:.1f} m     : {len(below)}"
          f"  ({100*len(below)/len(valid):.1f}% of section)")

    if e_mean < 10 and below:
        low_pt = min(below, key=lambda x: x[1])
        print(f"  Lowest point      : {low_pt[1]:.2f} m  "
              f"lat={low_pt[0][0]:.6f} lon={low_pt[0][1]:.6f}")
        road_crown = c_min + 0.75
        print(f"  Est. road crown   : ~{road_crown:.2f} m MSL"
              f"  (DEM floor + 0.75 m embankment)")
        print(f"\n  Mondego railway track (same corridor): ~4.1 m MSL")
        if road_crown < 4.1:
            print(f"  → A14 crown (~{road_crown:.2f} m) < railway (~4.1 m)"
                  f" — A14 floods first")

    # Elevation bands for diagnostics
    print(f"\n  Elevation bands:")
    for label, fn in [("<0 m",    lambda e: e < 0),
                      ("0–5 m",   lambda e: 0 <= e < 5),
                      ("5–10 m",  lambda e: 5 <= e < 10),
                      ("10–20 m", lambda e: 10 <= e < 20),
                      (">20 m",   lambda e: e >= 20)]:
        n = sum(1 for _, e in valid if fn(e))
        if n:
            print(f"    {label:10s}: {n:4d} pts")

    # Outputs
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    full_csv = "elev_a14_mondego_full.csv"
    with open(full_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idx", "lat", "lon", "elev_m", "below_threshold"])
        for i, ((lat, lon), e) in enumerate(valid):
            w.writerow([i, round(lat,6), round(lon,6), round(e,3),
                        e < THRESHOLD_M])
    print(f"\n  Full CSV   → {full_csv}")

    if below:
        low_csv = "elev_a14_mondego_low_points.csv"
        with open(low_csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["lat", "lon", "elev_m"])
            for (lat, lon), e in sorted(below, key=lambda x: x[1]):
                w.writerow([round(lat,6), round(lon,6), round(e,3)])
        print(f"  Low CSV    → {low_csv}  ({len(below)} points)")

    txt = "elev_a14_mondego_summary.txt"
    with open(txt, "w") as f:
        f.write("A14 / IP3 — Mondego Lezíria Elevation Check\n")
        f.write("=" * 68 + "\n")
        f.write(f"Run date         : {ts}\n")
        f.write(f"OSM relation     : https://www.openstreetmap.org/relation/7301317\n")
        f.write(f"Section          : Maiorca (A17 jct) → east of Mondego bridge\n")
        f.write(f"Bbox             : S={S} W={W} N={N} E={E}\n")
        f.write(f"Sample interval  : {INTERVAL_M} m\n")
        f.write(f"Elevation source : EU-DEM 25m (EGM2008) via OpenTopoData\n")
        f.write(f"Documented events: {MONDEGO_EVENTS}\n\n")
        f.write("KEY RESULTS\n")
        f.write("-" * 68 + "\n")
        f.write(f"  Sample points : {len(valid)}\n")
        f.write(f"  Minimum       : {e_min:.2f} m MSL\n")
        f.write(f"  Credible min  : {c_min:.2f} m MSL  (≥1.0 m filter)\n")
        f.write(f"  Mean          : {e_mean:.2f} m MSL\n")
        f.write(f"  Maximum       : {e_max:.2f} m MSL\n")
        f.write(f"  Points <{THRESHOLD_M:.0f}m  : {len(below)} ({100*len(below)/len(valid):.1f}%)\n")
        if credible:
            f.write(f"  Est.road crown: ~{c_min+0.75:.2f} m MSL\n\n")
        f.write("CITATION\n")
        f.write("-" * 68 + "\n")
        f.write(f"Road geometry: OpenStreetMap (© contributors, ODbL),\n")
        f.write(f"retrieved via Overpass API, {ts[:10]}.\n")
        f.write("Elevation: EU-DEM 25m (EGM2008) via "
                "https://api.opentopodata.org/v1/eudem25m.\n")
    print(f"  Summary txt → {txt}")
    print("\nDone.")


if __name__ == "__main__":
    main()
