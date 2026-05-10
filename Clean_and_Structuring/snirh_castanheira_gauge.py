"""
snirh_castanheira_gauge.py
===========================
Retrieve peak water-level readings from SNIRH (Sistema Nacional de Informação
de Recursos Hídricos / APA) at the hydrometric station at Castanheira do
Ribatejo (Tejo), covering the five documented railway flood events:

    2008  (Jan–Feb)
    2010  (Jan)
    2014  (Jan)
    2022  (Dec–Jan 2023)
    2026  (Jan–Feb)

PURPOSE
-------
Cross-validate the ~1.5 m MSL track-elevation threshold derived from the
EU-DEM / OSM route-relation analysis. If SNIRH peak gauge heights, once
converted to MSL, reach or exceed ~1.5 m during each documented event, the
threshold is independently supported.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANUAL DOWNLOAD (if the automated fetch is blocked in your environment)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1 — Go to SNIRH:
  https://snirh.apambiente.pt/

Step 2 — Navigate to:
  Monitorização → Hidrométrica → Consulta de dados

Step 3 — Select station:
  Search for "Castanheira do Ribatejo"  (code 14N/01H, river Tejo)
  If unavailable, use "Vila Franca de Xira" (14P/01H) as fallback.

Step 4 — Select parameter:
  "Nível" or "Cota"  (water level / gauge height, daily mean)

Step 5 — For each event, set date range and export CSV:
  2008 event : 2008-01-01 → 2008-03-31
  2010 event : 2010-01-01 → 2010-03-31
  2014 event : 2014-01-01 → 2014-03-31
  2022 event : 2022-11-01 → 2023-02-28
  2026 event : 2026-01-01 → 2026-04-30

Step 6 — Save each CSV as:
  snirh_manual_2008.csv
  snirh_manual_2010.csv
  snirh_manual_2014.csv
  snirh_manual_2022.csv
  snirh_manual_2026.csv

Step 7 — Run this script in the same folder as those CSVs.
  The script will auto-detect them and produce the peaks + summary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATUM NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SNIRH gauge heights are in local station datum (zero = benchmark level),
NOT necessarily mean sea level (MSL). EU-DEM uses EGM2008 ≈ MSL.

To compare: look up the station benchmark elevation in APA hydrometric
metadata. The SNIRH metadata page for each station lists "Cota do zero da
escala" (elevation of gauge zero), which when added to the gauge reading
gives MSL. Example: if gauge zero = -2.30 m MSL and peak reading = 4.10 m,
then flood peak = 4.10 + (-2.30) = 1.80 m MSL.

Alternatively, use tabulated flood peaks from APA flood reports (RJEAP,
PGRH) which already express levels in MSL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTOMATED FETCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The script tries two automated routes before falling back to manual CSVs:
  1. recursoshidricos library  (pip install recursoshidricos)
  2. Direct SNIRH CSV download (reverse-engineered endpoint)

REQUIREMENTS
------------
  pip install requests
  (optional) pip install recursoshidricos
  python snirh_castanheira_gauge.py
"""

import os, time, csv, requests, json
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "SNIRH-ResearchQuery/1.0 (dissertation research)"
}

SNIRH_DOWNLOAD = (
    "https://snirh.apambiente.pt/snirh/_dadosbase/site/"
    "licenciamento/dados_download.php"
)

STATIONS = [
    {
        "name":   "Castanheira do Ribatejo",
        "code":   "14N/01H",
        "obj_id": "0614N001",
        "river":  "Tejo",
        "note":   "Primary — closest to railway flood zone",
    },
    {
        "name":   "Vila Franca de Xira",
        "code":   "14P/01H",
        "obj_id": "0614P001",
        "river":  "Tejo",
        "note":   "Fallback — downstream, has tidal influence",
    },
    {
        "name":   "Almeirim",
        "code":   "14L/01H",
        "obj_id": "0614L001",
        "river":  "Tejo",
        "note":   "Fallback — upstream of Azambuja, less tidal",
    },
]

PARAM_NIVEL = "002"   # SNIRH parameter code for daily mean water level (cota)

EVENTS = [
    {"year": 2008, "label": "Jan–Feb 2008",       "start": "2008-01-01", "end": "2008-03-31"},
    {"year": 2010, "label": "Jan 2010",            "start": "2010-01-01", "end": "2010-03-31"},
    {"year": 2014, "label": "Jan 2014",            "start": "2014-01-01", "end": "2014-03-31"},
    {"year": 2022, "label": "Dec 2022 / Jan 2023", "start": "2022-11-01", "end": "2023-02-28"},
    {"year": 2026, "label": "Jan–Feb 2026",        "start": "2026-01-01", "end": "2026-04-30"},
]

PAUSE_S = 2.0

# Elevation of gauge zero (local datum → MSL) for Castanheira do Ribatejo.
# Set to None if unknown — the script will output raw gauge heights only.
# Obtain from APA metadata: "Cota do zero da escala" for station 14N/01H.
# Known value from SNIRH metadata (verify): approximately -2.02 m MSL.
GAUGE_ZERO_MSL = None   # set to e.g. -2.02 once confirmed from APA metadata


# ── APPROACH 1: recursoshidricos library ──────────────────────────────────────

def try_recursoshidricos(code, start, end):
    try:
        import recursoshidricos as rh
        print(f"     [recursoshidricos] {code}  {start} → {end}")
        try:
            data = rh.get_daily_data(code, "nivel", start, end)
        except Exception:
            data = rh.fetch(station=code, param="nivel", start=start, end=end)
        rows = [(r["date"], r["value"]) for r in data if r.get("value") is not None]
        return rows or None
    except ImportError:
        return None
    except Exception as e:
        print(f"     [recursoshidricos] Error: {e}")
        return None


# ── APPROACH 2: Direct SNIRH CSV download ────────────────────────────────────

def try_direct_csv(obj_id, start, end):
    url = SNIRH_DOWNLOAD
    params = {
        "format":  "csv",
        "objSite": obj_id,
        "objPar":  PARAM_NIVEL,
        "dtIni":   start.replace("-", ""),
        "dtFim":   end.replace("-", ""),
    }
    print(f"     [direct CSV] {url}  params={params}")
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        content = r.text.strip()
        if not content or "<html" in content.lower():
            print("     [direct CSV] Got HTML — endpoint may require authentication")
            return None
        rows = []
        for line in content.splitlines():
            parts = line.replace(",", ".").split(";")
            if len(parts) < 2:
                continue
            try:
                datetime.strptime(parts[0].strip(), "%Y-%m-%d")
                val = float(parts[1].strip())
                rows.append((parts[0].strip(), val))
            except ValueError:
                continue
        return rows or None
    except Exception as e:
        print(f"     [direct CSV] Failed: {e}")
        return None


# ── APPROACH 3: Manual CSV files ──────────────────────────────────────────────

MANUAL_CSV_MAP = {
    2008: "snirh_manual_2008.csv",
    2010: "snirh_manual_2010.csv",
    2014: "snirh_manual_2014.csv",
    2022: "snirh_manual_2022.csv",
    2026: "snirh_manual_2026.csv",
}

def try_manual_csv(year):
    fname = MANUAL_CSV_MAP.get(year)
    if not fname or not os.path.exists(fname):
        return None
    print(f"     [manual CSV] Reading {fname} ...")
    rows = []
    with open(fname, newline="", encoding="utf-8-sig") as f:
        # Try to be flexible about separator and date format
        sample = f.read(512)
        f.seek(0)
        sep = ";" if ";" in sample else ","
        reader = csv.reader(f, delimiter=sep)
        for line in reader:
            if len(line) < 2:
                continue
            date_part = line[0].strip().replace("/", "-")
            val_part  = line[1].strip().replace(",", ".")
            # Try multiple date formats
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(date_part, fmt)
                    date_str = dt.strftime("%Y-%m-%d")
                    val = float(val_part)
                    rows.append((date_str, val))
                    break
                except ValueError:
                    continue
    return rows or None


# ── COMBINED FETCH ────────────────────────────────────────────────────────────

def fetch_gauge_data(station, event):
    code   = station["code"]
    obj_id = station["obj_id"]
    start  = event["start"]
    end    = event["end"]
    year   = event["year"]

    result = try_recursoshidricos(code, start, end)
    if result:
        print(f"     → recursoshidricos: {len(result)} records")
        return result, "recursoshidricos"

    result = try_direct_csv(obj_id, start, end)
    if result:
        print(f"     → Direct CSV: {len(result)} records")
        return result, "SNIRH direct download"

    result = try_manual_csv(year)
    if result:
        print(f"     → Manual CSV: {len(result)} records")
        return result, f"Manual download ({MANUAL_CSV_MAP[year]})"

    return None, None


# ── ANALYSIS ──────────────────────────────────────────────────────────────────

def analyse(data, source):
    levels = [v for _, v in data if v is not None]
    if not levels:
        return None
    peak_val  = max(levels)
    peak_date = next(d for d, v in data if v == peak_val)
    mean_val  = sum(levels) / len(levels)
    days_high = sum(1 for v in levels if v >= peak_val * 0.85)

    peak_msl = None
    if GAUGE_ZERO_MSL is not None:
        peak_msl = round(peak_val + GAUGE_ZERO_MSL, 3)

    return {
        "n":          len(levels),
        "peak_gauge": round(peak_val, 3),
        "peak_date":  peak_date,
        "mean_gauge": round(mean_val, 3),
        "days_high":  days_high,
        "peak_msl":   peak_msl,
        "source":     source,
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("SNIRH Gauge Data — Tejo / Tagus at Castanheira do Ribatejo")
    print("Flood events: 2008, 2010, 2014, 2022, 2026")
    print(f"Cross-validation target: track elevation ~1.5 m MSL")
    if GAUGE_ZERO_MSL is not None:
        print(f"Gauge zero (MSL) : {GAUGE_ZERO_MSL:.3f} m  → levels will be converted")
    else:
        print("Gauge zero (MSL) : NOT SET — output will be raw gauge heights only")
        print("  → Set GAUGE_ZERO_MSL at top of script once confirmed from APA.")
    print("=" * 70)

    all_raw  = []
    peaks    = []
    summary  = []
    used_station = None
    used_source  = "unknown"

    for station in STATIONS:
        print(f"\n{'─'*60}")
        print(f"Station : {station['name']}  ({station['code']})")
        print(f"Note    : {station['note']}")
        print(f"{'─'*60}")

        station_success = 0

        for event in EVENTS:
            print(f"\n  Event: {event['label']}  ({event['start']} → {event['end']})")

            data, source = fetch_gauge_data(station, event)
            time.sleep(PAUSE_S)

            if not data:
                print("  ✗ No data — add manual CSV or check station code")
                peaks.append({
                    "station":    station["name"],
                    "event":      event["label"],
                    "peak_gauge": "N/A",
                    "peak_date":  "N/A",
                    "peak_msl":   "N/A",
                    "days_high":  "N/A",
                    "source":     "no data",
                })
                continue

            station_success += 1
            used_station = station["name"]
            used_source  = source
            res = analyse(data, source)

            print(f"  Readings    : {res['n']} daily values")
            print(f"  Peak gauge  : {res['peak_gauge']:.3f} m  on {res['peak_date']}")
            print(f"  Mean gauge  : {res['mean_gauge']:.3f} m")
            print(f"  Days ≥85%   : {res['days_high']} d")
            if res["peak_msl"] is not None:
                status = "≥ threshold" if res["peak_msl"] >= 1.5 else "< threshold"
                print(f"  Peak MSL    : {res['peak_msl']:.3f} m  "
                      f"[track ≈1.5 m → {status}]")

            for d, v in data:
                all_raw.append({
                    "station": station["name"],
                    "event":   event["label"],
                    "date":    d,
                    "gauge_m": round(v, 3) if v is not None else "",
                    "msl_m":   (round(v + GAUGE_ZERO_MSL, 3)
                                if GAUGE_ZERO_MSL is not None and v is not None
                                else ""),
                    "source":  source,
                })

            msl_str = (f"  →  {res['peak_msl']:.3f} m MSL"
                       if res["peak_msl"] is not None else "  (MSL: set GAUGE_ZERO_MSL)")
            summary.append(
                f"  {event['label']:26s}  peak = {res['peak_gauge']:.3f} m gauge"
                f"{msl_str}  ({res['days_high']} d ≥85%)"
            )
            peaks.append({
                "station":    station["name"],
                "event":      event["label"],
                "peak_gauge": res["peak_gauge"],
                "peak_date":  res["peak_date"],
                "peak_msl":   res["peak_msl"] if res["peak_msl"] is not None else "set GAUGE_ZERO_MSL",
                "days_high":  res["days_high"],
                "source":     source,
            })

        if station_success > 0:
            print(f"\n  → {station_success}/5 events retrieved from {station['name']}.")
            if station_success < 5:
                print(f"     Download remaining manual CSVs for missing events.")
            break

    # ── Write raw CSV ──────────────────────────────────────────────────────────
    if all_raw:
        raw_csv = "snirh_castanheira_raw.csv"
        with open(raw_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["station", "event", "date",
                                               "gauge_m", "msl_m", "source"])
            w.writeheader()
            w.writerows(all_raw)
        print(f"\n  Raw CSV     → {raw_csv}  ({len(all_raw)} rows)")
    else:
        print("\n  No raw data written — all approaches failed.")
        print("  Please download manual CSVs from SNIRH (see script header).")

    # ── Write peaks CSV ───────────────────────────────────────────────────────
    peaks_csv = "snirh_castanheira_peaks.csv"
    with open(peaks_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["station", "event", "peak_gauge",
                                           "peak_date", "peak_msl",
                                           "days_high", "source"])
        w.writeheader()
        w.writerows(peaks)
    print(f"  Peaks CSV   → {peaks_csv}")

    # ── Write text summary ────────────────────────────────────────────────────
    txt = "snirh_castanheira_summary.txt"
    ts  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    with open(txt, "w") as f:
        f.write("SNIRH Gauge Data — Tejo at Castanheira do Ribatejo\n")
        f.write("=" * 70 + "\n")
        f.write(f"Retrieved     : {ts}\n")
        f.write(f"Station       : {used_station or 'see individual event rows'}\n")
        f.write(f"Source        : {used_source}\n")
        f.write(f"Parameter     : Daily mean water level (gauge height, m)\n")
        f.write(f"Gauge zero    : {GAUGE_ZERO_MSL} m MSL "
                f"({'applied' if GAUGE_ZERO_MSL is not None else 'NOT SET — set GAUGE_ZERO_MSL'})\n\n")
        f.write("PEAK LEVELS BY FLOOD EVENT\n")
        f.write("-" * 70 + "\n")
        if summary:
            for s in summary:
                f.write(s + "\n")
        else:
            f.write("  No automated data retrieved. See manual download instructions\n")
            f.write("  in script header, then re-run.\n")
        f.write("\n")
        f.write("CROSS-VALIDATION LOGIC\n")
        f.write("-" * 70 + "\n")
        f.write("EU-DEM track elevation (OSM route relation, filtered ≥1.5 m):\n")
        f.write("  Minimum credible track elevation ≈ 1.5 m MSL\n")
        f.write("  (EU-DEM 25m; off-track points at <1.5 m excluded as water/\n")
        f.write("   floodplain terrain based on spot-check verification)\n\n")
        f.write("If SNIRH peak gauge + gauge_zero_MSL >= 1.5 m during a documented\n")
        f.write("railway closure event → threshold is independently supported.\n\n")
        f.write("STATION NOTES\n")
        f.write("-" * 70 + "\n")
        for s in STATIONS:
            f.write(f"  {s['code']:12s}  {s['name']:30s}  {s['note']}\n")
        f.write("\n")
        f.write("DATUM CONVERSION\n")
        f.write("-" * 70 + "\n")
        f.write("Gauge zero ('Cota do zero da escala') for 14N/01H:\n")
        f.write("  Obtain from: SNIRH station metadata page, or\n")
        f.write("  APA Ficha de Estação Hidrométrica for Castanheira do Ribatejo.\n")
        f.write("  Once known, set GAUGE_ZERO_MSL at the top of this script.\n\n")
        f.write("CITATION (for dissertation)\n")
        f.write("-" * 70 + "\n")
        f.write("APA / SNIRH (Agência Portuguesa do Ambiente / Sistema Nacional\n")
        f.write("de Informação de Recursos Hídricos). Daily hydrometric data,\n")
        f.write("Tejo at Castanheira do Ribatejo (station 14N/01H). Retrieved\n")
        f.write(f"from https://snirh.apambiente.pt/, {ts[:10]}.\n")
    print(f"  Summary txt → {txt}")
    print("\nDone.")


if __name__ == "__main__":
    main()
