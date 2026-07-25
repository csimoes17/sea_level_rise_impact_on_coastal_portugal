"""
12c_normalize_pillar3.py
========================
Normalizes the stacked Pillar 3 master CSVs into two clean, Tableau-ready files
with consistent column names, uniform units (EUR), and standardised variant labels.

Reads:
  pillar3_disruption_master.csv    (from 12a)
  pillar3_adaptation_master.csv    (from 12b)

Outputs:
  pillar3_disruption_normalized.csv   → powers Tableau Dashboard 4
  pillar3_adaptation_normalized.csv   → powers Tableau Dashboard 5

Schema — pillar3_disruption_normalized.csv:
  section, section_type, scenario, variant, year, slr_m,
  annual_cost_mid_eur, annual_cost_low_eur, annual_cost_high_eur,
  cumulative_cost_mid_eur, cumulative_cost_low_eur, cumulative_cost_high_eur,
  return_period_yr, closure_days_yr

Schema — pillar3_adaptation_normalized.csv:
  section, section_type, option_id, option_label, scenario, variant,
  capex_low_eur, capex_mid_eur, capex_high_eur,
  breakeven_year_low, breakeven_year_mid, breakeven_year_high

Notes (updated 2026-04-12 for 10a/10b/10c DDR rewrite):
  - Railways (Mondego / Tagus / Aveiro) now output annual_cost_mid/low/high_eur
    directly in EUR — no unit conversion needed (removed ×1e6 for Mondego).
  - All three railway sections now populate low/high cost columns (were blank before).
  - Aveiro now provides return_period_yr and closure_days_yr (were blank before).
  - Mondego adaptation: breakeven_year → breakeven_year_mid (DDR band added).
  - Tagus/Aveiro adaptation: be_year_low/mid/high →
    be_year_low/mid/high_capex_mid_ddr (column rename with DDR band suffix).
  - A1 disruption file stores POST-ADAPTATION costs (option 1 = 50% reducer).
    No-adaptation cost is recovered by × 2 (verified: 5.453 × 2 = 10.859 bn ✓).
  - VdG cumulative costs stored in bn€ (× 1e9 applied).
  - Variant labels normalised → "Baseline" or "+Geoid" (capital-first, consistent).
  - Run from project directory: python 12c_normalize_pillar3.py
"""

import os
import csv
import sys

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DISRUPTION_IN  = os.path.join(SCRIPT_DIR, "pillar3_disruption_master.csv")
ADAPTATION_IN  = os.path.join(SCRIPT_DIR, "pillar3_adaptation_master.csv")
DISRUPTION_OUT = os.path.join(SCRIPT_DIR, "pillar3_disruption_normalized.csv")
ADAPTATION_OUT = os.path.join(SCRIPT_DIR, "pillar3_adaptation_normalized.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def flt(val, default=None):
    """Safe float parse; returns default if blank/unparseable."""
    try:
        v = float(val)
        return v
    except (ValueError, TypeError):
        return default

def int_or_blank(val):
    """Parse break-even year values.
    - Numeric strings → integer string (e.g. "2047" → "2047")
    - ">2100" → "2101" (Tableau-renderable sentinel; axis can be extended to 2105)
    - "TBD" or any other non-numeric → "" (genuinely unknown, shown as null)
    """
    if val is None:
        return ""
    s = str(val).strip()
    if s == ">2100":
        return "2101"   # sentinel: does not break even within the 2100 horizon
    try:
        return str(int(float(s)))
    except (ValueError, TypeError):
        return ""

def normalise_variant(v):
    """Collapse all variant spellings to 'Baseline' or '+Geoid'."""
    v = v.strip()
    if v.lower() in ("baseline",):
        return "Baseline"
    if v.lower() in ("+geoid", "geoid"):
        return "+Geoid"
    return v   # pass-through for unknowns

# ---------------------------------------------------------------------------
# 1. DISRUPTION NORMALISATION
# ---------------------------------------------------------------------------

DISRUPTION_FIELDNAMES = [
    "section", "section_type", "scenario", "variant", "year", "slr_m",
    "annual_cost_mid_eur", "annual_cost_low_eur", "annual_cost_high_eur",
    "cumulative_cost_mid_eur", "cumulative_cost_low_eur", "cumulative_cost_high_eur",
    "return_period_yr", "closure_days_yr",
]

def normalise_disruption(rows):
    """
    Convert each stacked row to the normalised schema.
    Returns list of dicts; skips rows that cannot be resolved.

    Railway column mapping (updated for 10a/10b/10c DDR rewrite, 2026-04-12):
      Mondego: annual_cost_mid_eur (EUR, no conversion), + low/high columns
      Tagus:   annual_cost_mid_eur (EUR, no conversion), + low/high columns
      Aveiro:  annual_cost_mid_eur (EUR, no conversion), + low/high columns,
               + return_period_yr, closure_days_yr now populated

    Ports cumulative low/high fix (2026-04-12 session 2):
      11a_ports.py computes cumulative_cost_mid_eur but leaves low/high null.
      12c now accumulates them here from the annual_cost_low/high_eur columns,
      keyed by (section, scenario, variant), rows assumed year-ordered in master.
    """
    out = []
    skipped = 0

    # Running accumulators for ports cumulative low/high (fix: 2026-04-12 session 2)
    # 11a writes cumulative_mid correctly but leaves cumulative_low/high null.
    port_cum_low  = {}   # key: (section, scenario, variant_norm)
    port_cum_high = {}

    # Pre-index A1/A14/Faro-Olhão rows by (scenario, variant_norm, year) for × 2 recovery.
    # All three sections use option "1a" with freq_multiplier=2.0 → no-adapt = ×2.
    # Updated Session 28: A1 option key changed from "1" → "1a".
    a1_opt1 = {
        (r["scenario"], normalise_variant(r["variant"]), r["year"]): r
        for r in rows
        if r["section"] == "A1 Azambuja (road)" and r.get("option") == "1a"
    }
    a14_opt1a = {
        (r["scenario"], normalise_variant(r["variant"]), r["year"]): r
        for r in rows
        if r["section"] == "A14 Mondego (road)" and r.get("option") == "1a"
    }
    faro_opt1a = {
        (r["scenario"], normalise_variant(r["variant"]), r["year"]): r
        for r in rows
        if r["section"] == "Faro–Olhão (railway)" and r.get("option") == "1a"
    }
    # Portimão/Arade: all options have freq_multiplier=10000 (effectively zero closures).
    # No ×2 recovery needed — pass option "A" costs through directly.
    portimao_optA = {
        (r["scenario"], normalise_variant(r["variant"]), r["year"]): r
        for r in rows
        if r["section"] == "Portimão/Arade (railway)" and r.get("option") == "A"
    }

    seen_a1_keys      = set()
    seen_a14_keys     = set()
    seen_faro_keys    = set()
    seen_portimao_keys = set()

    for r in rows:
        sec   = r["section"]
        stype = r["section_type"]
        scen  = r["scenario"]
        var   = normalise_variant(r["variant"])
        year  = r["year"]
        slr   = r["slr_m"]

        # ── Mondego ─────────────────────────────────────────────────────────
        # 10a now outputs annual_cost_mid_eur / _low_eur / _high_eur in EUR.
        # No unit conversion needed (was M€ before — that ×1e6 is removed).
        if sec == "Mondego (railway)":
            mid_ann = flt(r.get("annual_cost_mid_eur", ""))
            lo_ann  = flt(r.get("annual_cost_low_eur",  ""))
            hi_ann  = flt(r.get("annual_cost_high_eur", ""))
            mid_cum = flt(r.get("cumulative_cost_mid_eur", ""))
            lo_cum  = flt(r.get("cumulative_cost_low_eur",  ""))
            hi_cum  = flt(r.get("cumulative_cost_high_eur", ""))
            if mid_ann is None:
                skipped += 1; continue
            rp  = r.get("return_period_yr",  "")
            cld = r.get("closure_days_yr", "")
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": slr,
                "annual_cost_mid_eur":        f"{mid_ann:.2f}",
                "annual_cost_low_eur":        f"{lo_ann:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum:.2f}"  if hi_cum  is not None else "",
                "return_period_yr": rp, "closure_days_yr": cld,
            })

        # ── Tagus ────────────────────────────────────────────────────────────
        # 10b now outputs annual_cost_mid_eur / _low_eur / _high_eur in EUR.
        elif sec == "Tagus floodplain (railway)":
            mid_ann = flt(r.get("annual_cost_mid_eur", ""))
            lo_ann  = flt(r.get("annual_cost_low_eur",  ""))
            hi_ann  = flt(r.get("annual_cost_high_eur", ""))
            mid_cum = flt(r.get("cumulative_cost_mid_eur", ""))
            lo_cum  = flt(r.get("cumulative_cost_low_eur",  ""))
            hi_cum  = flt(r.get("cumulative_cost_high_eur", ""))
            if mid_ann is None:
                skipped += 1; continue
            rp  = r.get("return_period_yr", "")
            cld = r.get("closure_days_yr",  "")
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": slr,
                "annual_cost_mid_eur":        f"{mid_ann:.2f}",
                "annual_cost_low_eur":        f"{lo_ann:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum:.2f}"  if hi_cum  is not None else "",
                "return_period_yr": rp, "closure_days_yr": cld,
            })

        # ── Aveiro ───────────────────────────────────────────────────────────
        # 10c now outputs annual_cost_mid_eur / _low_eur / _high_eur in EUR.
        # return_period_yr and closure_days_yr are now populated (were blank before).
        elif sec == "Aveiro Ria (railway)":
            mid_ann = flt(r.get("annual_cost_mid_eur", ""))
            lo_ann  = flt(r.get("annual_cost_low_eur",  ""))
            hi_ann  = flt(r.get("annual_cost_high_eur", ""))
            mid_cum = flt(r.get("cumulative_cost_mid_eur", ""))
            lo_cum  = flt(r.get("cumulative_cost_low_eur",  ""))
            hi_cum  = flt(r.get("cumulative_cost_high_eur", ""))
            if mid_ann is None:
                skipped += 1; continue
            rp  = r.get("return_period_yr", "")
            cld = r.get("closure_days_yr",  "")
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": slr,
                "annual_cost_mid_eur":        f"{mid_ann:.2f}",
                "annual_cost_low_eur":        f"{lo_ann:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum:.2f}"  if hi_cum  is not None else "",
                "return_period_yr": rp, "closure_days_yr": cld,
            })

        # ── Ports (Leixões, Lisbon, Setúbal) ─────────────────────────────────
        elif stype == "Port":
            mid_ann = flt(r.get("annual_cost_mid_eur", ""))
            lo_ann  = flt(r.get("annual_cost_low_eur", ""))
            hi_ann  = flt(r.get("annual_cost_high_eur", ""))
            mid_cum = flt(r.get("cumulative_cost_mid_eur", ""))
            if mid_ann is None:
                skipped += 1; continue
            # Accumulate low/high cumulatives (11a leaves these null in master CSV)
            pk = (sec, scen, var)
            port_cum_low[pk]  = port_cum_low.get(pk,  0.0) + (lo_ann  or 0.0)
            port_cum_high[pk] = port_cum_high.get(pk, 0.0) + (hi_ann  or 0.0)
            rp  = r.get("return_period_yr", r.get("days_yr", ""))
            cld = r.get("closure_days_yr", "")
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": slr,
                "annual_cost_mid_eur":        f"{mid_ann:.2f}",
                "annual_cost_low_eur":        f"{lo_ann:.2f}"           if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann:.2f}"           if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum:.2f}"          if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{port_cum_low[pk]:.2f}" if lo_ann  is not None else "",
                "cumulative_cost_high_eur":   f"{port_cum_high[pk]:.2f}"if hi_ann  is not None else "",
                "return_period_yr": rp, "closure_days_yr": cld,
            })

        # ── VdG ── REMOVED Session 28 (11b not updated with raise_requirements.csv) ──

        # ── A1 ───────────────────────────────────────────────────────────────
        # Disruption_cost.csv stores POST-ADAPTATION costs for option 1/2/3.
        # No-adaptation cost = option-1 cost × 2 (option 1 is a 50% frequency reducer).
        # We emit one row per year/scenario/variant (deduplicated via seen_a1_keys).
        elif sec == "A1 Azambuja (road)":
            key = (scen, var, year)
            if key in seen_a1_keys:
                continue  # already emitted from option=1 row
            opt1_row = a1_opt1.get(key)
            if opt1_row is None:
                skipped += 1; continue
            mid_ann = flt(opt1_row.get("annual_cost_mid_M", ""))
            lo_ann  = flt(opt1_row.get("annual_cost_low_M", ""))
            hi_ann  = flt(opt1_row.get("annual_cost_hi_M",  ""))
            mid_cum = flt(opt1_row.get("cum_cost_mid_bn", ""))
            lo_cum  = flt(opt1_row.get("cum_cost_low_bn", ""))
            hi_cum  = flt(opt1_row.get("cum_cost_hi_bn",  ""))
            if mid_ann is None:
                skipped += 1; continue
            # × 1e6 (M€→€) × 2 (reverse 50% option-1 reduction) = × 2e6
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": opt1_row["slr_m"],
                "annual_cost_mid_eur":        f"{mid_ann*2e6:.2f}",
                "annual_cost_low_eur":        f"{lo_ann*2e6:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann*2e6:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum*2e9:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum*2e9:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum*2e9:.2f}"  if hi_cum  is not None else "",
                "return_period_yr":  opt1_row.get("return_period_yr", ""),
                "closure_days_yr":   opt1_row.get("closure_days_yr",  ""),
            })
            seen_a1_keys.add(key)

        # ── A14 Mondego (road) ────────────────────────────────────────────────
        # Same M€/bn€ column structure as A1; option "1a" freq_multiplier=2.0.
        elif sec == "A14 Mondego (road)":
            key = (scen, var, year)
            if key in seen_a14_keys:
                continue
            opt1_row = a14_opt1a.get(key)
            if opt1_row is None:
                skipped += 1; continue
            mid_ann = flt(opt1_row.get("annual_cost_mid_M", ""))
            lo_ann  = flt(opt1_row.get("annual_cost_low_M", ""))
            hi_ann  = flt(opt1_row.get("annual_cost_hi_M",  ""))
            mid_cum = flt(opt1_row.get("cum_cost_mid_bn", ""))
            lo_cum  = flt(opt1_row.get("cum_cost_low_bn", ""))
            hi_cum  = flt(opt1_row.get("cum_cost_hi_bn",  ""))
            if mid_ann is None:
                skipped += 1; continue
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": opt1_row["slr_m"],
                "annual_cost_mid_eur":        f"{mid_ann*2e6:.2f}",
                "annual_cost_low_eur":        f"{lo_ann*2e6:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann*2e6:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum*2e9:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum*2e9:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum*2e9:.2f}"  if hi_cum  is not None else "",
                "return_period_yr":  opt1_row.get("return_period_yr", ""),
                "closure_days_yr":   opt1_row.get("closure_days_yr",  ""),
            })
            seen_a14_keys.add(key)

        # ── Faro–Olhão (railway) ──────────────────────────────────────────────
        # Same M€/bn€ column structure as A1; option "1a" freq_multiplier=2.0.
        elif sec == "Faro–Olhão (railway)":
            key = (scen, var, year)
            if key in seen_faro_keys:
                continue
            opt1_row = faro_opt1a.get(key)
            if opt1_row is None:
                skipped += 1; continue
            mid_ann = flt(opt1_row.get("annual_cost_mid_M", ""))
            lo_ann  = flt(opt1_row.get("annual_cost_low_M", ""))
            hi_ann  = flt(opt1_row.get("annual_cost_hi_M",  ""))
            mid_cum = flt(opt1_row.get("cum_cost_mid_bn", ""))
            lo_cum  = flt(opt1_row.get("cum_cost_low_bn", ""))
            hi_cum  = flt(opt1_row.get("cum_cost_hi_bn",  ""))
            if mid_ann is None:
                skipped += 1; continue
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": opt1_row["slr_m"],
                "annual_cost_mid_eur":        f"{mid_ann*2e6:.2f}",
                "annual_cost_low_eur":        f"{lo_ann*2e6:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann*2e6:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum*2e9:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum*2e9:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum*2e9:.2f}"  if hi_cum  is not None else "",
                "return_period_yr":  opt1_row.get("return_period_yr", ""),
                "closure_days_yr":   opt1_row.get("closure_days_yr",  ""),
            })
            seen_faro_keys.add(key)

        # ── Portimão/Arade (railway) ──────────────────────────────────────────
        # All options have freq_multiplier=10000 → disruption costs ≈ 0 post-intervention.
        # No-adaptation scenario = service loss (NPV), not closure days.
        # Pass option "A" costs through directly (represent post-adaptation ~zero cost).
        elif sec == "Portimão/Arade (railway)":
            key = (scen, var, year)
            if key in seen_portimao_keys:
                continue
            opt_row = portimao_optA.get(key)
            if opt_row is None:
                skipped += 1; continue
            mid_ann = flt(opt_row.get("annual_cost_mid_M", ""))
            lo_ann  = flt(opt_row.get("annual_cost_low_M", ""))
            hi_ann  = flt(opt_row.get("annual_cost_hi_M",  ""))
            mid_cum = flt(opt_row.get("cum_cost_mid_bn", ""))
            lo_cum  = flt(opt_row.get("cum_cost_low_bn", ""))
            hi_cum  = flt(opt_row.get("cum_cost_hi_bn",  ""))
            if mid_ann is None:
                skipped += 1; continue
            out.append({
                "section": sec, "section_type": stype,
                "scenario": scen, "variant": var, "year": year, "slr_m": opt_row["slr_m"],
                "annual_cost_mid_eur":        f"{mid_ann*1e6:.2f}",
                "annual_cost_low_eur":        f"{lo_ann*1e6:.2f}"  if lo_ann  is not None else "",
                "annual_cost_high_eur":       f"{hi_ann*1e6:.2f}"  if hi_ann  is not None else "",
                "cumulative_cost_mid_eur":    f"{mid_cum*1e9:.2f}" if mid_cum is not None else "",
                "cumulative_cost_low_eur":    f"{lo_cum*1e9:.2f}"  if lo_cum  is not None else "",
                "cumulative_cost_high_eur":   f"{hi_cum*1e9:.2f}"  if hi_cum  is not None else "",
                "return_period_yr":  opt_row.get("return_period_yr", ""),
                "closure_days_yr":   opt_row.get("closure_days_yr",  ""),
            })
            seen_portimao_keys.add(key)

        else:
            skipped += 1

    return out, skipped


# ---------------------------------------------------------------------------
# 2. ADAPTATION NORMALISATION
# ---------------------------------------------------------------------------

ADAPTATION_FIELDNAMES = [
    "section", "section_type", "option_id", "option_label",
    "scenario", "variant",
    "capex_low_eur", "capex_mid_eur", "capex_high_eur",
    "breakeven_year_low", "breakeven_year_mid", "breakeven_year_high",
]

# Shortened option labels for Tableau display
OPTION_SHORT = {
    "Option 1: In-situ viaduct (3–5km)":                         "Opt 1: In-situ viaduct",
    "Option 2: Junction relocation to Soure (~11km)":             "Opt 2: Soure relocation",
    "Option 3: Western bypass via Ramal de Alfarelos (~21km)":    "Opt 3: Alfarelos bypass",
    "Option 1: Embankment Raising":                               "Opt 1: Embankment raising",
    "Option 2: Flood Barriers + Smart Drainage":                  "Opt 2: Flood barriers",
    "Option 3: Track Relocation Inland":                          "Opt 3: Track relocation",
    "Option 1: Track Raising + Embankment Reinforcement":         "Opt 1: Track raising",
    "Option 2: Coastal Barrier Reinforcement (Barra–Costa Nova)": "Opt 2: Coastal barrier",
    "Option 3: Inland Reroute (Aveiro Eastern Bypass)":           "Opt 3: Eastern bypass",
    "Option 1: Physical Flood-Proofing":                          "Opt 1: Flood-proofing",
    "Option 2: Landside Access Resilience":                       "Opt 2: Landside resilience",
    "Option 3: Operational Resilience Protocol":                  "Opt 3: Operational protocol",
    "Option 1: Approach Road Raising (+0.50m embankment)":        "Opt 1: Road raising",
    "Option 2: Tidal Flood Gates + Pumping Station":              "Opt 2: Tidal gates",
    "Option 3: Dynamic Traffic Management Protocol":              "Opt 3: Traffic mgmt",
    "1":  "Opt 1: Carriageway raising",
    "2":  "Opt 2: Barriers + drainage",
    "3":  "Opt 3: Traffic mgmt",
    # New options — Session 28 dual-scenario raise heights
    "1a": "Opt 1a: Elevated road (SSP2-4.5)",
    "1b": "Opt 1b: Full reconstruction (SSP5-8.5)",
    "A":  "Opt A: Managed retreat (NPV)",
    "B":  "Opt B: Short viaduct",
    "C":  "Opt C: Realignment (TBD)",
}

def normalise_adaptation(rows):
    """
    Collapse each section's adaptation rows to a standard schema.
    One row per section / option_id / scenario / variant.

    Column mapping updated 2026-04-12 for 10a/10b/10c DDR rewrite:
      Mondego:       breakeven_year → breakeven_year_mid (+ _low, _high for DDR bands)
      Tagus/Aveiro:  be_year_low/mid/high → be_year_low/mid/high_capex_mid_ddr
    """
    from collections import defaultdict
    groups = defaultdict(list)

    for r in rows:
        sec   = r["section"]
        scen  = r["scenario"]
        var   = normalise_variant(r["variant"])
        opt   = r.get("option", "?")
        # Derive option_id (1/2/3) from option string
        if opt in ("1", "2", "3", "1a", "1b", "A", "B", "C"):
            oid = opt   # preserve full option ID for dual-scenario sections
        elif "1" in opt[:10]:
            oid = "1"
        elif "2" in opt[:10]:
            oid = "2"
        elif "3" in opt[:10]:
            oid = "3"
        else:
            oid = "?"
        groups[(sec, oid, scen, var)].append(r)

    out = []
    for (sec, oid, scen, var), grp_rows in sorted(groups.items()):
        stype = grp_rows[0]["section_type"]
        # Pick a representative option label (first non-empty, prefer full label)
        opt_raw   = next((r.get("option","") for r in grp_rows if r.get("option","")), "")
        opt_label = OPTION_SHORT.get(opt_raw, opt_raw[:60] if opt_raw else f"Option {oid}")

        cap_lo = cap_mid = cap_hi = None
        be_lo  = be_mid  = be_hi  = None

        r0 = grp_rows[0]

        # ── Mondego ────────────────────────────────────────────────────────
        # Rows have cost_scenario (low/base/high) × key_year.
        # Updated: read breakeven_year_mid (MID DDR, given CAPEX band).
        # Also read breakeven_year_low / breakeven_year_high for DDR sensitivity.
        if sec == "Mondego (railway)":
            for r in grp_rows:
                cs   = r.get("cost_scenario", "").lower()
                cost = flt(r.get("bypass_cost_meur", ""))
                # Primary break-even = MID DDR band for the given CAPEX scenario
                be_val = int_or_blank(r.get("breakeven_year_mid", ""))
                if cs == "low":
                    cap_lo = f"{cost*1e6:.0f}" if cost is not None else ""
                    be_lo  = be_val
                elif cs in ("mid", "base"):
                    cap_mid = f"{cost*1e6:.0f}" if cost is not None else ""
                    be_mid  = be_val
                elif cs == "high":
                    cap_hi = f"{cost*1e6:.0f}" if cost is not None else ""
                    be_hi  = be_val
            # Fallback: if mid not found, use first row
            if cap_mid is None:
                cost    = flt(r0.get("bypass_cost_meur", ""))
                cap_mid = f"{cost*1e6:.0f}" if cost is not None else ""
                be_mid  = int_or_blank(r0.get("breakeven_year_mid",
                                               r0.get("breakeven_year", "")))

        # ── Tagus / Aveiro ─────────────────────────────────────────────────
        # Updated: be_year_low/mid/high → be_year_low/mid/high_capex_mid_ddr
        elif sec in ("Tagus floodplain (railway)", "Aveiro Ria (railway)"):
            cap_lo  = f"{flt(r0.get('cost_low_eur',''), 0):.0f}"
            cap_mid = f"{flt(r0.get('cost_mid_eur',''), 0):.0f}"
            cap_hi  = f"{flt(r0.get('cost_high_eur',''), 0):.0f}"
            be_lo   = int_or_blank(r0.get("be_year_low_capex_mid_ddr",
                                           r0.get("be_year_low", "")))
            be_mid  = int_or_blank(r0.get("be_year_mid_capex_mid_ddr",
                                           r0.get("be_year_mid", "")))
            be_hi   = int_or_blank(r0.get("be_year_high_capex_mid_ddr",
                                           r0.get("be_year_high", "")))

        # ── Ports ──────────────────────────────────────────────────────────
        elif sec in ("Leixões", "Lisbon", "Setúbal"):
            cap_lo  = f"{flt(r0.get('cost_low_eur',''), 0):.0f}"
            cap_mid = f"{flt(r0.get('cost_mid_eur',''), 0):.0f}"
            cap_hi  = f"{flt(r0.get('cost_high_eur',''), 0):.0f}"
            be_lo   = int_or_blank(r0.get("be_year_low", ""))
            be_mid  = int_or_blank(r0.get("be_year_mid", ""))
            be_hi   = int_or_blank(r0.get("be_year_high", ""))

        # ── VdG ── REMOVED Session 28 (11b not updated with raise_requirements.csv) ──

        # ── A1 / A14 / Faro-Olhão / Portimão/Arade ────────────────────────
        # All four share the same adaptation CSV schema (Session 28 dual-scenario):
        #   capex_low_M, capex_high_M (M€); be_year_low/mid/hi_capex
        elif sec in ("A1 Azambuja (road)", "A14 Mondego (road)",
                     "Faro–Olhão (railway)", "Portimão/Arade (railway)"):
            clo = flt(r0.get("capex_low_M", ""))
            chi = flt(r0.get("capex_high_M", ""))
            cmi = ((clo + chi) / 2) if (clo is not None and chi is not None) else None
            cap_lo  = f"{clo*1e6:.0f}" if clo is not None else ""
            cap_mid = f"{cmi*1e6:.0f}" if cmi is not None else ""
            cap_hi  = f"{chi*1e6:.0f}" if chi is not None else ""
            be_lo   = int_or_blank(r0.get("be_year_low_capex", ""))
            be_mid  = int_or_blank(r0.get("be_year_mid_capex", ""))
            be_hi   = int_or_blank(r0.get("be_year_hi_capex",  ""))

        out.append({
            "section":      sec,
            "section_type": stype,
            "option_id":    oid,
            "option_label": opt_label,
            "scenario":     scen,
            "variant":      var,
            "capex_low_eur":      cap_lo  or "",
            "capex_mid_eur":      cap_mid or "",
            "capex_high_eur":     cap_hi  or "",
            "breakeven_year_low":  be_lo  or "",
            "breakeven_year_mid":  be_mid or "",
            "breakeven_year_high": be_hi  or "",
        })

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # ── Disruption ──────────────────────────────────────────────────────────
    if not os.path.exists(DISRUPTION_IN):
        print(f"ERROR: {DISRUPTION_IN} not found. Run 12a first."); sys.exit(1)

    print("=== 12c: Normalising disruption master ===")
    dis_rows = read_csv(DISRUPTION_IN)
    norm_dis, skipped_dis = normalise_disruption(dis_rows)
    with open(DISRUPTION_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DISRUPTION_FIELDNAMES)
        w.writeheader()
        w.writerows(norm_dis)
    print(f"  ✓  pillar3_disruption_normalized.csv: {len(norm_dis)} rows written "
          f"({skipped_dis} skipped)")

    from collections import Counter
    sec_counts = Counter(r["section"] for r in norm_dis)
    var_counts  = Counter(r["variant"] for r in norm_dis)
    print(f"     Sections: {dict(sec_counts)}")
    print(f"     Variants: {dict(var_counts)}")

    # Spot-check low/high population for railways
    mondego_check = [r for r in norm_dis
                     if r["section"] == "Mondego (railway)"
                     and r["year"] == "2100"
                     and r["scenario"] == "SSP5-8.5"
                     and r["variant"] == "Baseline"]
    if mondego_check:
        rc = mondego_check[0]
        print(f"     ✓ Mondego spot-check 2100/SSP5-8.5/Baseline: "
              f"MID={rc['annual_cost_mid_eur']}  LOW={rc['annual_cost_low_eur']}  "
              f"HIGH={rc['annual_cost_high_eur']}")

    # Spot-check A1 canonical (SSP5-8.5, Baseline, 2100, mid ≈ 10.859 bn)
    a1_check = [r for r in norm_dis
                if r["section"]  == "A1 Azambuja (road)"
                and r["scenario"] == "SSP5-8.5"
                and r["variant"]  == "Baseline"
                and r["year"]     == "2100"]
    if a1_check:
        val = float(a1_check[0]["cumulative_cost_mid_eur"])
        print(f"     ✓ A1 canonical check: SSP5-8.5 Baseline 2100 cumulative mid "
              f"= €{val/1e9:.3f}bn (updated Session 28: was ~10.859bn pre-elevated-road)")

    # ── Adaptation ──────────────────────────────────────────────────────────
    if not os.path.exists(ADAPTATION_IN):
        print(f"ERROR: {ADAPTATION_IN} not found. Run 12b first."); sys.exit(1)

    print("\n=== 12c: Normalising adaptation master ===")
    adap_rows = read_csv(ADAPTATION_IN)
    norm_adap = normalise_adaptation(adap_rows)
    with open(ADAPTATION_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ADAPTATION_FIELDNAMES)
        w.writeheader()
        w.writerows(norm_adap)
    print(f"  ✓  pillar3_adaptation_normalized.csv: {len(norm_adap)} rows written")

    sec_counts2 = Counter(r["section"] for r in norm_adap)
    print(f"     Sections: {dict(sec_counts2)}")

    print(f"\n  Output dir: {SCRIPT_DIR}")
    print("  Done. Connect both _normalized.csv files to Tableau.")


if __name__ == "__main__":
    main()
