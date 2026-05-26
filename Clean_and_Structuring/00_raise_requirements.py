"""
00_raise_requirements.py
========================
Single source of truth for required raise heights across all
Pillar 3 critical infrastructure sections.

For each section this script:
  1. Reads or retrieves the terrain floor elevation (m MSL)
  2. Applies the design flood formula:
       required_raise = MHWS + surge_100yr + SLR_2100 + freeboard - terrain_floor
  3. Assigns a proposed adaptation method based on asset type and raise magnitude
  4. Exports raise_requirements.csv — consumed by all 10x/11x adaptation scripts

SLR scenarios (IPCC AR6, 2100 median):
  SSP2-4.5   +0.43 m  — minimum adequate investment (lower bound, high-confidence)
  SSP5-8.5   +0.82 m  — recommended long-run investment (headline design scenario)
  SSP5+geoid +1.15 m  — sensitivity case only (precautionary upper bound)

Method thresholds agreed 2026-05-12 (D26):
  Railway:  raise ≤ 0.80m             → Embankment raising
            0.80m < raise ≤ 1.50m     → Elevated embankment (reinforced)
            1.50m < raise ≤ 2.50m     → Viaduct / bypass / realignment
            raise > 2.50m             → Managed retreat / line discontinuation
  Road:     raise ≤ 1.00m             → Road embankment raising
            1.00m < raise ≤ 2.00m     → Elevated road on reinforced structure
            raise > 2.00m             → Full structural reconstruction
  Special:  Fluvial mechanism         → Bypass (tidal formula not applicable)

REQUIREMENTS: pip install (none — standard library only)
"""

import csv
import os
import sys

# ── PATH SETUP ────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def data_path(filename):
    return os.path.join(SCRIPT_DIR, filename)

# ── SLR SCENARIOS (IPCC AR6 2100 median, m) ───────────────────────────────────
SLR_SCENARIOS = [
    ("SSP2-4.5",   0.43, "minimum adequate investment — lower bound"),
    ("SSP5-8.5",   0.82, "recommended long-run investment — headline"),
    ("SSP5+geoid", 1.15, "sensitivity case only — precautionary upper bound"),
]
DESIGN_SCENARIO = "SSP5-8.5"    # headline scenario used for method selection
FREEBOARD_M     = 0.30           # standard freeboard, linear transport infrastructure

# ── METHOD SELECTION ──────────────────────────────────────────────────────────
def adaptation_method(raise_m, asset_type):
    """Return proposed adaptation method given required raise height and asset type."""
    if asset_type == "railway":
        if raise_m <= 0.80:
            return "Embankment raising"
        elif raise_m <= 1.50:
            return "Elevated embankment (reinforced)"
        elif raise_m <= 2.50:
            return "Viaduct / bypass / realignment"
        else:
            return "Managed retreat / line discontinuation"
    elif asset_type == "road":
        if raise_m <= 1.00:
            return "Road embankment raising"
        elif raise_m <= 2.00:
            return "Elevated road on reinforced structure"
        else:
            return "Full structural reconstruction"
    return "—"

# ── TERRAIN FLOOR READER ──────────────────────────────────────────────────────
def floor_from_csv(filename, elev_col="elev_m", valid_min=0.0):
    """
    Read terrain floor (minimum valid elevation) from an elevation profile CSV.
    Returns (floor_m, source_description) or exits on failure.
    """
    path = data_path(filename)
    if not os.path.exists(path):
        return None, f"FILE NOT FOUND: {filename}"
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None, f"EMPTY FILE: {filename}"
    valid = []
    for r in rows:
        raw = r.get(elev_col, "")
        if raw in (None, "", "None", "nan"):
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        if v >= valid_min:
            valid.append(v)
    if not valid:
        return None, f"NO VALID ELEVATIONS in {filename} (valid_min={valid_min})"
    floor = min(valid)
    return floor, f"CSV min of {len(valid)} valid pts ≥{valid_min}m  ← {filename}"

# ── SECTION DEFINITIONS ───────────────────────────────────────────────────────
#
# terrain_floor: numeric (m MSL) if known; None = read from CSV
# floor_csv:     elevation profile CSV to read when terrain_floor is None
# floor_valid_min: minimum acceptable elevation when reading CSV
#                  (0.0 filters EU-DEM water-surface artifacts)
# mhws_m:        Mean High Water Springs, m MSL, at this location
# surge_100yr_m: 1-in-100yr storm surge (m, additive to MHWS)
# at_risk_len_m: length of section exposed below risk threshold (m)
# asset_type:    "railway" | "road"
# mechanism:     "tidal" | "fluvial"
# source_script: parent adaptation script (informational)
# notes:         methodology flags and caveats

SECTIONS = [
    # ── Linha do Norte Railway ────────────────────────────────────────────────
    {
        "section_id":       "mondego_railway",
        "section_name":     "Mondego Railway — Alfarelos junction",
        "asset_type":       "railway",
        "mechanism":        "fluvial",
        "terrain_floor":    6.0,
        "floor_source":     "estimate — inland valley; tidal framework does not apply",
        "mhws_m":           None,
        "surge_100yr_m":    None,
        "at_risk_len_m":    4_000,
        "source_script":    "10a_mondego_bypass.py",
        "notes": (
            "FLUVIAL MECHANISM. Primary driver is Mondego river overflow from upstream "
            "rainfall, not tidal inundation. SLR role: raises tidal base at Figueira da Foz, "
            "reducing hydraulic drainage gradient and prolonging flood duration. "
            "Bypass to higher ground (Soure ~60m) is correct adaptation regardless of SLR. "
            "10a is EXEMPT from raise-height revision."
        ),
    },
    {
        "section_id":       "tagus_railway",
        "section_name":     "Tagus Railway — VFX to Azambuja",
        "asset_type":       "railway",
        "mechanism":        "tidal",
        "terrain_floor":    2.00,
        "floor_source":     "constant (10b: TRACK_ELEVATION_M = 2.00)",
        "mhws_m":           2.00,
        "surge_100yr_m":    0.65,
        "at_risk_len_m":    10_000,
        "source_script":    "10b_tagus_floodplain.py",
        "notes": (
            "Tagus estuary. Embankment at 2.0m MSL above Lezíria Grande floodplain. "
            "10b Option 1 used +0.50m — now superseded. "
            "Required raise exceeds 1.5m under all scenarios → viaduct or realignment."
        ),
    },
    {
        "section_id":       "aveiro_cacia_estarreja",
        "section_name":     "Aveiro — Cacia–Estarreja (Ria de Aveiro Lagoon Fringe, km 265–275)",
        "asset_type":       "railway",
        "mechanism":        "tidal",
        "terrain_floor":    -0.40,
        "floor_source":     "EU-DEM minimum via OpenTopoData API (2026-05-10); km 265–275 track corridor",
        "mhws_m":           1.80,
        "surge_100yr_m":    0.50,
        "at_risk_len_m":    10_000,
        "source_script":    "10c_aveiro_ria.py",
        "notes": (
            "CORRECTED SECTION (2026-05-24): Previously modelled as Zone A (Ovar–Estarreja, "
            "km 251–260, hardcoded 1.2m) — found at ~6.4m MSL minimum via EU-DEM (2026-05-10); "
            "NOT vulnerable to SLR before 2100; excluded. "
            "Cacia–Estarreja (km 265–275) is the correct at-risk section: EU-DEM terrain "
            "minimum −0.40m MSL (OpenTopoData API, 2026-05-10). Estimated track elevation "
            "~0.3m MSL (embankment above terrain minimum; flagged for field verification). "
            "Required raise exceeds 2.50m under all scenarios → managed retreat / line "
            "discontinuation or full Ria bypass as primary adaptation."
        ),
    },
    # ── Linha do Algarve Railway ──────────────────────────────────────────────
    {
        "section_id":       "faro_olhao",
        "section_name":     "Algarve Railway — Faro to Olhão (Ria Formosa)",
        "asset_type":       "railway",
        "mechanism":        "tidal",
        "terrain_floor":    2.341,
        "floor_source":     "CSV min of 264 valid pts ≥0.0m ← algarve_faro_olhao_full_profile.csv (elev_algarve_faro_olhao.py, 2026-05-10)",
        "mhws_m":           1.80,
        "surge_100yr_m":    0.50,
        "at_risk_len_m":    4_900,
        "source_script":    "11e_algarve_faro_olhao.py",
        "notes": (
            "Only section in study where embankment raising is the viable method. "
            "Natura 2000 AIA required for any earthworks in Ria Formosa. "
            "Under SSP5+geoid (+1.41m) approaches elevated embankment boundary."
        ),
    },
    {
        "section_id":       "portimao_arade",
        "section_name":     "Algarve Railway — Portimão / Arade estuary",
        "asset_type":       "railway",
        "mechanism":        "tidal",
        "terrain_floor":    0.585,
        "floor_source":     "CSV min of 301 valid pts ≥0.0m ← algarve_portimao_arade_full_profile.csv (elev_algarve_portimao_arade.py, 2026-05-10)",
        "mhws_m":           1.80,
        "surge_100yr_m":    0.55,
        "at_risk_len_m":    1_500,
        "source_script":    "11f_algarve_portimao_arade.py",
        "notes": (
            "Terrain floor lies below SLR projection alone under SSP5+geoid — existential risk. "
            "Three options: (A) managed retreat + bus replacement, "
            "(B) short viaduct on current alignment, "
            "(C) short realignment to higher ground. "
            "No break-even exists under options B/C. Terrain check for option C pending."
        ),
    },
    # ── Motorways ─────────────────────────────────────────────────────────────
    {
        "section_id":       "a1_tagus",
        "section_name":     "A1 Motorway — Tagus floodplain",
        "asset_type":       "road",
        "mechanism":        "tidal",
        "terrain_floor":    2.40,
        "floor_source":     "constant (11c: EU-DEM terrain minimum 2.4m; carriageway crown ~2.50m)",
        "mhws_m":           2.00,
        "surge_100yr_m":    0.65,
        "at_risk_len_m":    12_000,
        "source_script":    "11c_a1_motorway.py",
        "notes": (
            "Lisbon–Porto critical corridor. Carriageway width 26m (2+2 lanes + shoulders). "
            "Under SSP2-4.5 (+0.98m) elevated embankment is viable. "
            "Under SSP5+geoid (+1.70m) structural road deck required. "
            "Prior +0.50m raise now superseded."
        ),
    },
    {
        "section_id":       "a14_mondego",
        "section_name":     "A14/IP3 Motorway — Mondego plain",
        "asset_type":       "road",
        "mechanism":        "tidal",
        "terrain_floor":    1.63,
        "floor_source":     "constant (11d: EU-DEM credible minimum 1.63m; road crown ~2.38m)",
        "mhws_m":           2.00,
        "surge_100yr_m":    0.65,
        "at_risk_len_m":    12_000,
        "source_script":    "11d_a14_mondego.py",
        "notes": (
            "All scenarios require full structural reconstruction — no simple embankment raise. "
            "Prior +0.50m raise massively understated costs. "
            "Road crown already sits at ~2.38m but terrain floor is 1.63m. "
            "12km of dual carriageway on Mondego alluvial plain."
        ),
    },
]

# ── COMPUTE RAISES ────────────────────────────────────────────────────────────
print("\nResolving terrain floors...")
computed = []

for sec in SECTIONS:
    row = {k: v for k, v in sec.items()}

    # Resolve terrain floor from CSV if not hardcoded
    if sec["terrain_floor"] is None:
        floor, source = floor_from_csv(
            sec["floor_csv"],
            valid_min=sec.get("floor_valid_min", 0.0),
        )
        if floor is None:
            print(f"  ✗ {sec['section_id']}: {source}")
            sys.exit(1)
        row["terrain_floor"]  = round(floor, 3)
        row["floor_source"]   = source
        print(f"  ✓ {sec['section_id']}: floor = {floor:.3f} m  ({source})")
    else:
        print(f"  ✓ {sec['section_id']}: floor = {sec['terrain_floor']:.2f} m  ({sec.get('floor_source','')})")

    # Fluvial sections: no raise calculation
    if sec["mechanism"] == "fluvial":
        for label, _, _ in SLR_SCENARIOS:
            key = label.replace("-", "_").replace("+", "_").replace(".", "_")
            row[f"raise_{key}"]  = None
            row[f"method_{key}"] = "Bypass — fluvial mechanism (tidal formula N/A)"
        row["design_raise_m"] = None
        row["design_method"]  = "Bypass to higher ground — 10a EXEMPT from raise revision"
        computed.append(row)
        continue

    # Tidal sections: apply formula
    mhws  = sec["mhws_m"]
    surge = sec["surge_100yr_m"]
    floor = row["terrain_floor"]

    for label, slr_val, _ in SLR_SCENARIOS:
        raise_m = mhws + surge + slr_val + FREEBOARD_M - floor
        key = label.replace("-", "_").replace("+", "_").replace(".", "_")
        row[f"raise_{key}"]  = round(raise_m, 3)
        row[f"method_{key}"] = adaptation_method(raise_m, sec["asset_type"])

    # Design scenario (SSP5-8.5)
    design_slr   = next(v for lbl, v, _ in SLR_SCENARIOS if lbl == DESIGN_SCENARIO)
    design_raise = mhws + surge + design_slr + FREEBOARD_M - floor
    row["design_raise_m"] = round(design_raise, 3)
    row["design_method"]  = adaptation_method(design_raise, sec["asset_type"])

    computed.append(row)

# ── TERMINAL TABLE ────────────────────────────────────────────────────────────
col_w = 46
print()
print("=" * 108)
print("  REQUIRED RAISE HEIGHTS — ALL PILLAR 3 SECTIONS")
print(f"  Formula: MHWS + surge_100yr + SLR_2100 + {FREEBOARD_M}m freeboard − terrain_floor")
print(f"  Design scenario: {DESIGN_SCENARIO} (headline) | SSP2-4.5 (lower bound) | SSP5+geoid (sensitivity)")
print("=" * 108)
print(f"  {'Section':<44}  {'Floor':>6}  {'SSP2-4.5':>10}  {'SSP5-8.5':>10}  {'SSP5+geoid':>11}  Design method")
print("-" * 108)

def _key(label):
    return label.replace("-", "_").replace("+", "_").replace(".", "_")

for r in computed:
    floor_str = f"{r['terrain_floor']:.2f}m"

    def fval(label):
        v = r.get(f"raise_{_key(label)}")
        return f"+{v:.2f}m" if v is not None else "FLUVIAL"

    s245 = fval("SSP2-4.5")
    s585 = fval("SSP5-8.5")
    s5g  = fval("SSP5+geoid")
    meth = r["design_method"][:38]
    name = r["section_name"][:44]
    print(f"  {name:<44}  {floor_str:>6}  {s245:>10}  {s585:>10}  {s5g:>11}  {meth}")

print("=" * 108)

# SLR reference
print("\n  SLR reference (IPCC AR6 SSP 2100 medians):")
for label, val, desc in SLR_SCENARIOS:
    marker = " ◄ design scenario" if label == DESIGN_SCENARIO else ""
    print(f"    {label:<14}  +{val:.2f} m  — {desc}{marker}")

print(f"\n  Freeboard: {FREEBOARD_M}m standard for all linear transport infrastructure")
print()

# ── CSV OUTPUT ────────────────────────────────────────────────────────────────
OUT_CSV = data_path("raise_requirements.csv")

fieldnames = [
    "section_id", "section_name", "asset_type", "mechanism",
    "terrain_floor", "floor_source",
    "mhws_m", "surge_100yr_m", "freeboard_m",
    "at_risk_len_m",
    "slr_SSP2_4_5", "slr_SSP5_8_5", "slr_SSP5_geoid",
    "raise_SSP2_4_5", "raise_SSP5_8_5", "raise_SSP5_geoid",
    "method_SSP2_4_5", "method_SSP5_8_5", "method_SSP5_geoid",
    "design_scenario", "design_raise_m", "design_method",
    "source_script", "notes",
]

with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in computed:
        out = {k: r.get(k, "") for k in fieldnames}
        out["freeboard_m"]     = FREEBOARD_M
        out["design_scenario"] = DESIGN_SCENARIO
        out["slr_SSP2_4_5"]    = 0.43
        out["slr_SSP5_8_5"]    = 0.82
        out["slr_SSP5_geoid"]  = 1.15
        writer.writerow(out)

print(f"  ✓ raise_requirements.csv written → {OUT_CSV}")
print(f"    {len(computed)} sections | {len(fieldnames)} columns")
print()
print("  ► Downstream scripts (10b, 10c, 11c, 11d, 11e, 11f) should read")
print("    raise_SSP2_4_5 (lower bound) and raise_SSP5_8_5 (design)")
print("    from raise_requirements.csv rather than hardcoding raise heights.")
print()
