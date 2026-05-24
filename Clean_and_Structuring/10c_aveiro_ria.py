#!/usr/bin/env python3
"""
10c_aveiro_ria.py  —  Pillar 3 · Linha do Norte · Ria de Aveiro / Cacia–Estarreja Section

SCOPE CORRECTION (2026-05-24):
  Previously modelled Zone A (Ovar–Estarreja Causeway, km 251–260, 9 km, hardcoded 1.2 m MSL).
  EU-DEM field check (OpenTopoData API, 2026-05-10) confirmed Zone A minimum elevation
  ~6.4 m MSL near Estarreja — NOT vulnerable to SLR before 2100; excluded from analysis.

  This script now models the CORRECT at-risk section:
  Cacia–Estarreja (Ria de Aveiro Lagoon Fringe), km 265–275, ~10 km.
  EU-DEM terrain minimum: −0.40 m MSL (OpenTopoData, 2026-05-10, track corridor).
  Estimated mean track elevation: ~0.3 m MSL (embankment above terrain minimum;
  field verification recommended).

Critical section : km 265–275 from Lisboa Santa Apolónia
                   (Cacia → Estarreja), crossing the southern Ria de Aveiro lagoon fringe
Length           : ~10 km
Track elevation  : ~0.3 m MSL (estimated; EU-DEM terrain min −0.40 m; embankment above terrain)

Flood mechanism  : MULTI-SOURCE — most complex section on the line
                   · Direct SLR: Ria de Aveiro is a semi-enclosed coastal lagoon open to the
                     Atlantic at Barra inlet. Rising sea level raises lagoon baseline directly.
                   · Tidal amplification: Spring tides inside the Ria reach ~1.5–2.0 m MSL.
                   · Storm surge: Atlantic fetch provides extra 0.3–0.5 m during NW storms.
                   · Barrier overwash: The sandy barrier (Barra–Costa Nova) that separates the
                     Ria from the Atlantic is itself at risk of SLR-induced overwash/breaching,
                     which would fundamentally alter lagoon hydrodynamics and create a new
                     persistent flood regime (non-incremental, threshold event).
                   · River backwater: Rivers Vouga and Antuã discharge into the Ria; SLR reduces
                     their tidal gradient → more frequent fluvial backwater floods in low areas.

This section differs fundamentally from Mondego and Tagus sections because:
                   · The barrier breaching risk introduces a BINARY THRESHOLD: before breach =
                     compound frequency model; after breach = near-permanent inundation of much
                     of the Ria margins including the rail corridor.
                   · The Cacia–Estarreja section has terrain already below sea level (−0.40 m
                     minimum) — the LOWEST elevation of any critical rail section studied.
                     Permanent inundation is possible well before 2100 under SSP5-8.5 +geoid.
                   · This section is also in the BATHTUB MODEL domain (unlike Mondego which is
                     purely fluvial). The Ria acts as a direct SLR receptor; the compound model
                     supplements the bathtub model rather than replacing it.

Three adaptation options (raise heights from raise_requirements.csv):
  Required raise: SSP2-4.5 = +3.43 m, SSP5-8.5 = +3.82 m → Managed retreat / line
  discontinuation under standard method thresholds (raise > 2.50 m). A very high viaduct
  is technically possible as an extreme intervention but exceeds standard cost frameworks.
  Option 1 — Extreme viaduct on current alignment (10 km)           €150–250 M
              [Unit cost €15–25 M/km × 10 km ±30%; greater raise than Zone A equivalent]
  Option 2 — Coastal barrier reinforcement (Barra–Costa Nova)       €80–140 M
              [Address root cause: protect the Ria system, not just the track]
  Option 3 — Inland reroute (Aveiro eastern bypass)                 €280–480 M
              [Move the track east of the Ria entirely]

Note on Option 2: Addresses system-level vulnerability — protects Aveiro city,
aquaculture (EUR 120M+ sector), and ~80k residents. Rail cost is a co-benefit share.

DDR UNCERTAINTY BANDS (Decision D18 / D21, 2026-04-12)
-------------------------------------------------------
Three Daily Disruption Rate bands:
  DDR_LOW  = €0.60M/day  (0.50 × MID — direct costs only)
  DDR_MID  = €1.20M/day  (central estimate — raised from €1.0M original)
  DDR_HIGH = €2.10M/day  (1.75 × MID — full systemic costs)

DDR_MID raised from €1.0M to €1.2M (vs Mondego €1.0M) justified by:
  · ADFERSIT (2021): 66 train movements/day at Cacia–Estarreja corridor (H2019 data;
    same Aveiro–Ovar trunk corridor in which km 265–275 falls)
  · AMT (2022): avg 117 pax/train Porto suburban; 176 long-distance; 54 regional
  · AMT (2024 [2023 data]): updated to 119 pax/train Porto suburban; 178 long-distance; 59 regional
    → ~8,800 passengers/day (CONSERVATIVE lower bound — see note below)
    vs ~7,100/day for Mondego (+~24% passenger exposure)
  NOTE: ADFERSIT 2021 H2019 baseline predates subsequent expansions of the CP Urbanos
    Aveiro suburban service (Porto–Aveiro corridor). Actual daily ridership — driven
    primarily by Porto commuter traffic — is likely higher than this estimate.
    No more granular post-2019 section-level data was available at time of writing.
  · Cacia–Estarreja section has higher regional tourism + aquaculture freight value
  · Aveiro city (>78k population) served by this section — larger indirect impact
    vs Mondego's predominantly inter-urban pass-through function
  · Sources: ADFERSIT (2021); AMT (2022, 2024); CP timetables (Dec 2025);
    Haigh et al. (2014) disruption valuation

BARRIER BREACH MODEL
---------------------
When SLR ≥ BARRIER_BREACH_LOW (0.60 m), the Barra–Costa Nova barrier is assumed
to fail. Sub-zone B closure_days is then set to 365 days/year (permanent closure),
regardless of the compound frequency model result.
  · This is a BINARY CAP, not a multiplier — the np.where logic sets days to 365
    exactly when breached, not a proportional increase
  · Two thresholds define a range: conservative (0.60 m) and optimistic (0.80 m)
  · Sub-zone B Layer A uses BARRIER_BREACH_LOW (conservative) for cost calculation
  · Combined annual cost = annual_A + annual_B (NOT capped — zones are independent)

References:
  Lopes et al. (2011) "Ria de Aveiro future evolution under climate change scenarios", J. Coastal Res.
  Fortunato et al. (2013) "Inundation of the Aveiro lagoon under storm conditions", Nat. Hazards.
  Moftakhari et al. (2017) compound flood framework, PNAS.
  IPCC AR6 WG1 Ch. 9 — Sea-level projections for European Atlantic coast.
  Seeger & Minderhoud (Nature 2026) — geoid offset +0.15 m EU Atlantic coast.
"""

import csv as _csv
import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent

# ── Raise heights from master CSV (00_raise_requirements.py) ──────────────────
def _read_raise(section_id: str) -> dict:
    path = PROJECT_DIR / "raise_requirements.csv"
    with open(path, newline="", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            if row["section_id"] == section_id:
                return {
                    "SSP2-4.5":   float(row["raise_SSP2_4_5"]),
                    "SSP5-8.5":   float(row["raise_SSP5_8_5"]),
                    "SSP5+geoid": float(row["raise_SSP5_geoid"]),
                    "method":     row["design_method"],
                }
    raise ValueError(f"Section '{section_id}' not found in raise_requirements.csv.")

_RAISE = _read_raise("aveiro_cacia_estarreja")
# SSP2-4.5 = +3.43 m → Managed retreat / line discontinuation
# SSP5-8.5 = +3.82 m → Managed retreat / line discontinuation  [design/headline]
# SSP5+geoid = +4.15 m → Managed retreat / line discontinuation
# All exceed 2.50 m threshold — standard embankment or viaduct are NOT viable;
# extreme viaduct (Option 1) treated as engineering outlier; bypass or managed retreat
# are the primary recommended responses.

# ── SLR Constants (IPCC AR6) ───────────────────────────────────────────────────
SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
GEOID_OFFSET = 0.15   # metres — Seeger & Minderhoud (Nature 2026)
YEARS        = np.arange(2025, 2101)

# ── Section Parameters — Cacia–Estarreja (sole section in scope) ──────────────
# SCOPE CORRECTION (2026-05-24): Zone A (Ovar–Estarreja, km 251–260) found at
# ~6.4 m MSL minimum (EU-DEM, 2026-05-10) — NOT vulnerable; excluded.
# Cacia–Estarreja (km 265–275) is the correct at-risk section.
SECTION_DISPLAY_NAME  = "Cacia–Estarreja (Ria de Aveiro Lagoon Fringe, km 265–275)"
SECTION_LENGTH_KM     = 10.0
SECTION_ELEVATION_M   = 0.3    # estimated mean track elevation, m MSL
                                # EU-DEM terrain minimum −0.40 m (OpenTopoData, 2026-05-10)
                                # track on embankment estimated ~0.3 m; field verification recommended
SECTION_RP_BASE       = 3.0    # years — estimated current return period for closure
                                # lower than Zone A's 7.0 yr, reflecting lower elevation
                                # and more direct lagoon exposure; barrier breach dominates
                                # after SLR 0.60 m
SECTION_CLOSURE_DAYS  = 5.0    # days/event — deeper inundation → longer drainage time

# ── Barrier breach constants ───────────────────────────────────────────────────
# Barra–Costa Nova sandy barrier failure thresholds (SLR values that trigger breach)
BARRIER_BREACH_LOW  = 0.60   # m — conservative threshold; used in cost calculation
BARRIER_BREACH_HIGH = 0.80   # m — optimistic threshold; used for sensitivity display

# ── Shared model parameters ────────────────────────────────────────────────────
SENSITIVITY_K        = np.log(2) / 0.10  # ≈ 6.93 — same across all sections

# ── PILLAR 3 SCHEMA METADATA ──────────────────────────────────────────────────
SECTION_ID   = "aveiro_cacia_estarreja"
SECTION_NAME = "Ria de Aveiro — Cacia–Estarreja (km 265–275)"
SECTION_TYPE = "railway"

# ── DAILY DISRUPTION RATE (DDR) — THREE BANDS ─────────────────────────────────
# LOW  = direct costs only (track repair, timetable disruption, operator losses)
# MID  = direct + indirect (pax delay costs, freight, productivity) — CENTRAL
# HIGH = full systemic (MID × 1.75; modal shift, regional economy, emergency mgmt)
DDR_LOW  =   600_000   # €/day  (0.50 × MID)
DDR_MID  = 1_200_000   # €/day  central estimate (~8,800 pax/day conservative; ADFERSIT 2021 × AMT 2022/2024)
DDR_HIGH = 2_100_000   # €/day  (1.75 × MID)

# ── Adaptation Options (Cacia–Estarreja) ────────────────────────────────────────────
# Required raises from raise_requirements.csv:
#   SSP2-4.5: +3.43 m → Managed retreat / line discontinuation (> 2.50 m threshold)
#   SSP5-8.5: +3.82 m → Managed retreat / line discontinuation (> 2.50 m threshold)
# All scenarios exceed the 2.50 m threshold — managed retreat is the standard method.
# Option 1 (extreme viaduct) is included as a technically possible but exceptional intervention.
OPTIONS = {
    "Option 1: Extreme Viaduct on Current Alignment (10 km)": {
        "desc_short": (
            f"Extreme viaduct on current alignment — SSP5-8.5 design raise +{_RAISE['SSP5-8.5']:.2f} m; "
            f"SSP2-4.5 lower bound +{_RAISE['SSP2-4.5']:.2f} m"
        ),
        "description": (
            "Replace the 10 km at-risk Cacia–Estarreja section with an extreme elevated "
            "viaduct on the current alignment, deck level set to clear all SLR scenarios "
            "to 2100. Required raise: +3.43 m (SSP2-4.5) to +3.82 m (SSP5-8.5) — both "
            "exceed the 2.50 m managed-retreat threshold under standard method classification. "
            "A viaduct of this height is technically achievable but constitutes an extreme "
            "intervention: terrain is already below sea level (−0.40 m minimum), requiring "
            "deep pile foundations into waterlogged lagoon sediments. Unit cost: "
            "€15–25 M/km × 10 km (±30%), higher than standard viaduct unit costs due to "
            "foundation complexity. This option exceeds the standard cost framework and should "
            "be compared against Option 3 (bypass) on a lifecycle basis."
        ),
        "cost_low_eur":  150_000_000,
        "cost_high_eur": 250_000_000,
        "permanent": True,
    },
    "Option 2: Coastal Barrier Reinforcement (Barra–Costa Nova)": {
        "desc_short": "Reinforce the Barra–Costa Nova barrier + inlet management",
        "description": (
            "Reinforce and raise the Barra–Costa Nova sandy barrier (the natural 'lid' of "
            "the Ria de Aveiro) against SLR-induced overwash and breaching. Interventions "
            "include: beach nourishment, dune restoration and armoring, inlet morphology "
            "management, and possible hard-engineering protection at the Barra inlet. "
            "SYSTEM-LEVEL APPROACH: Unlike Options 1 and 3, this protects the entire Ria "
            "de Aveiro system — Aveiro city infrastructure, the EUR 120M+ aquaculture/salt "
            "industry, coastal biodiversity, and ~80,000 residents in lagoon municipalities. "
            "Rail protection is a co-benefit of a broader coastal defence programme. "
            "Rail-attributable cost: ~15-20% share of total barrier programme "
            "(estimated EUR 400-700M total). Rail share: EUR 60-140M. Potentially eligible "
            "for EU Cohesion Fund co-financing. "
            "RISK: If barrier reinforcement is insufficient and breach still occurs, "
            "Option 1 would still be needed as a fallback measure."
        ),
        "cost_low_eur":  80_000_000,
        "cost_high_eur": 140_000_000,
        "permanent": False,
    },
    "Option 3: Inland Reroute (Aveiro Eastern Bypass)": {
        "desc_short": "New ~30 km alignment east of the Ria, via Albergaria-a-Velha",
        "description": (
            "Construct a new ~30 km double-track alignment bypassing the Ria de Aveiro "
            "entirely, routed east through Albergaria-a-Velha on higher ground (20-80 m "
            "elevation). Connects at Ovar (north) and Aveiro (south), completely replacing "
            "the 24 km lagoon corridor. "
            "STRATEGIC UPSIDE: Reduces Lisboa-Porto travel time by ~5-8 minutes (straighter "
            "geometry); serves Albergaria-a-Velha, a town currently without rail access. "
            "CONSTRAINT: Crosses the Vouga River valley and several stream gorges — "
            "multiple viaducts required. The 30 km length at ~EUR 16M/km is the largest "
            "investment of any adaptation option in this study. "
            "OBSERVATION: This reroute mirrors the concept behind the planned new high-speed "
            "rail corridor Porto-Lisboa, which would also bypass the coastal Linha do Norte. "
            "Under high emissions, building climate-resilient new infrastructure rather than "
            "adapting vulnerable existing infrastructure becomes the dominant strategy."
        ),
        "cost_low_eur":  280_000_000,
        "cost_high_eur": 480_000_000,
        "permanent": True,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
def interp_slr(anchors: dict, years: np.ndarray) -> np.ndarray:
    anchor_yrs  = sorted(anchors.keys())
    anchor_vals = [anchors[y] for y in anchor_yrs]
    return np.interp(years, anchor_yrs, anchor_vals)


def build_slr_dict(offset: float = 0.0) -> dict:
    return {
        scen: interp_slr(
            {yr: (v + offset if yr > 2020 else v) for yr, v in anchors.items()},
            YEARS,
        )
        for scen, anchors in SLR_ANCHORS.items()
    }


def layer_a_zone(slr_arr: np.ndarray, rp_base: float, closure_days_base: float,
                 barrier_breach_threshold: float = None) -> tuple:
    """
    Layer A: Compound flood frequency for a single sub-zone.

    closure_days/yr = (1/RP) × closure_days_base × (1 + SLR/0.50)
    The (1 + SLR/0.50) multiplier captures that deeper floods take longer to recede.

    barrier_breach_threshold: if set, closure_days is CAPPED to 365 when SLR >= threshold.
    This is a BINARY CAP (np.where), not a multiplier — the entire day count jumps to 365.

    Returns: (closure_days_per_year, return_period_years, barrier_breached_mask)
    """
    rp           = rp_base * np.exp(-SENSITIVITY_K * slr_arr)
    closures_yr  = 1.0 / rp
    closure_days = closures_yr * closure_days_base * (1.0 + slr_arr / 0.50)
    closure_days = np.minimum(closure_days, 365.0)

    breached = np.zeros(len(slr_arr), dtype=bool)
    if barrier_breach_threshold is not None:
        breached = slr_arr >= barrier_breach_threshold
        closure_days = np.where(breached, 365.0, closure_days)  # HARD CAP, not multiply

    return closure_days, rp, breached


def layer_b(closure_days_arr: np.ndarray, ddr: float) -> np.ndarray:
    """Annual disruption cost for a given DDR band."""
    return closure_days_arr * ddr


def cumulative_cost(annual_arr: np.ndarray) -> np.ndarray:
    return np.cumsum(annual_arr)


def break_even_year(cum_arr: np.ndarray, invest_eur: float):
    idx = np.searchsorted(cum_arr, invest_eur)
    return int(YEARS[idx]) if idx < len(YEARS) else None


# ─────────────────────────────────────────────────────────────────────────────
def main():
    slr_base  = build_slr_dict(offset=0.0)
    slr_geoid = build_slr_dict(offset=GEOID_OFFSET)

    KEY_YEARS = [2030, 2050, 2075, 2100]

    # ═══════════════════════════════════════════════════════════════════════════
    print("\n" + "═" * 76)
    print("  PILLAR 3 — LINHA DO NORTE · RIA DE AVEIRO / CACIA–ESTARREJA SECTION")
    print("═" * 76)
    print()
    print(f"  SCOPE CORRECTION (2026-05-24):")
    print(f"    Zone A (Ovar–Estarreja, km 251–260): EU-DEM minimum ~6.4 m MSL — NOT vulnerable; EXCLUDED.")
    print(f"    Cacia–Estarreja (km 265–275): EU-DEM terrain min −0.40 m MSL — this is the correct at-risk section.")
    print()
    print(f"  Section in scope    : Cacia–Estarreja — km 265–275, {SECTION_LENGTH_KM:.0f} km")
    print(f"  Flood mechanism     : Direct SLR + tidal amplification + storm surge + barrier breach (binary)")
    print(f"  Barrier breach      : ACTIVE — BARRIER_BREACH_LOW={BARRIER_BREACH_LOW:.2f} m (conservative)")
    print(f"                        BARRIER_BREACH_HIGH={BARRIER_BREACH_HIGH:.2f} m (optimistic/sensitivity)")
    print(f"  DDR bands           : LOW=€{DDR_LOW/1e6:.3f}M/day  MID=€{DDR_MID/1e6:.3f}M/day  "
          f"HIGH=€{DDR_HIGH/1e6:.4f}M/day")
    print()
    print(f"  {SECTION_DISPLAY_NAME}")
    print(f"    Length: {SECTION_LENGTH_KM:.0f} km | Est. track elevation: {SECTION_ELEVATION_M:.1f} m MSL "
          f"(EU-DEM terrain min −0.40 m; embankment estimate)")
    print(f"    Base RP: {SECTION_RP_BASE:.0f} yr | Closure: {SECTION_CLOSURE_DAYS:.1f} days/event")
    print(f"    Direct permanent inundation: POSSIBLE before 2100 — terrain already below 0 m MSL.")
    print(f"    Barrier breach (Barra–Costa Nova): caps closure to 365 days/yr when SLR ≥ {BARRIER_BREACH_LOW:.2f} m")
    print()
    print(f"  Required raises (raise_requirements.csv — 00_raise_requirements.py):")
    print(f"    SSP2-4.5 : +{_RAISE['SSP2-4.5']:.2f} m  → {_RAISE['method']}")
    print(f"    SSP5-8.5 : +{_RAISE['SSP5-8.5']:.2f} m  → {_RAISE['method']}  [design/headline]")
    print(f"    All exceed 2.50 m threshold — managed retreat is the standard method.")
    print(f"    Extreme viaduct (Option 1) treated as exceptional engineering intervention.")
    print()

    # ─── Layer A ──────────────────────────────────────────────────────────────
    rows_freq = []
    print(f"  {'═'*72}")
    print(f"  LAYER A — Flood Frequency · {SECTION_DISPLAY_NAME}")
    print(f"  Barrier breach ACTIVE: closure_days → 365 when SLR ≥ {BARRIER_BREACH_LOW:.2f} m (BARRIER_BREACH_LOW)")
    print(f"  Model: RP = {SECTION_RP_BASE:.0f} yr × exp(−{SENSITIVITY_K:.2f}×SLR)  |  "
          f"Closure = (1/RP) × {SECTION_CLOSURE_DAYS:.1f} × (1+SLR/0.50)  |  cap 365")
    print("  " + "─" * 72)
    hdr = (f"  {'Scenario':<12} {'Variant':<12} {'Year':>6}  "
           f"{'SLR (m)':>8}  {'RP (yr)':>9}  {'Days/yr':>8}  {'Flag':>16}")
    print(hdr)
    print("  " + "─" * 72)
    for scen in SLR_ANCHORS:
        for label, slr_d in [("Baseline", slr_base), ("+Geoid", slr_geoid)]:
            sarr = slr_d[scen]
            days_arr, rp_arr, breached = layer_a_zone(
                sarr, SECTION_RP_BASE, SECTION_CLOSURE_DAYS,
                barrier_breach_threshold=BARRIER_BREACH_LOW)
            for ky in KEY_YEARS:
                i = ky - YEARS[0]
                if breached[i]:
                    flag_str = "⚠ BREACH+CAP"
                elif days_arr[i] >= 364.9:
                    flag_str = "⚠ CAP"
                else:
                    flag_str = ""
                print(f"  {scen:<12} {label:<12} {ky:>6}  "
                      f"{sarr[i]:>8.3f}  {rp_arr[i]:>9.2f}  {days_arr[i]:>8.1f}  "
                      f"{flag_str:>16}")
                rows_freq.append({
                    "section":          SECTION_NAME,
                    "section_type":     SECTION_TYPE,
                    "zone":             "Cacia-Estarreja",
                    "scenario":         scen,
                    "variant":          label,
                    "year":             ky,
                    "slr_m":            round(float(sarr[i]), 3),
                    "return_period_yr": round(float(rp_arr[i]), 3),
                    "closure_days_yr":  round(float(days_arr[i]), 1),
                    "barrier_breached": bool(breached[i]),
                    "at_cap":           bool(days_arr[i] >= 364.9),
                })
        print()

    # ─── Layer B ──────────────────────────────────────────────────────────────
    print("  " + "═" * 72)
    print(f"  LAYER B — Cumulative Disruption Cost: {SECTION_DISPLAY_NAME}")
    print(f"  Barrier breach ACTIVE: see BREACH+CAP flags above.")
    print(f"  DDR_LOW=€{DDR_LOW/1e6:.3f}M/day  DDR_MID=€{DDR_MID/1e6:.3f}M/day  "
          f"DDR_HIGH=€{DDR_HIGH/1e6:.4f}M/day")
    print("  (Nominal, no discounting)")
    print("  " + "─" * 72)
    hdr2 = (f"  {'Scenario':<12} {'Variant':<12}  "
            f"{'2030 MID (€bn)':>14}  {'2050 MID (€bn)':>14}  "
            f"{'2075 MID (€bn)':>14}  {'2100 MID (€bn)':>14}")
    print(hdr2)
    print("  " + "─" * 72)

    _cum_combined = {}
    rows_ts = []

    for scen in SLR_ANCHORS:
        for label, slr_d in [("Baseline", slr_base), ("+Geoid", slr_geoid)]:
            sarr = slr_d[scen]

            days_a, rp_a, breached = layer_a_zone(
                sarr, SECTION_RP_BASE, SECTION_CLOSURE_DAYS,
                barrier_breach_threshold=BARRIER_BREACH_LOW)

            annual_mid  = layer_b(days_a, DDR_MID)
            annual_low  = layer_b(days_a, DDR_LOW)
            annual_high = layer_b(days_a, DDR_HIGH)

            cum_mid  = cumulative_cost(annual_mid)
            cum_low  = cumulative_cost(annual_low)
            cum_high = cumulative_cost(annual_high)

            _cum_combined[(scen, label)] = {
                "mid": cum_mid, "low": cum_low, "high": cum_high
            }

            vals_mid = {ky: cum_mid[ky - YEARS[0]] for ky in KEY_YEARS}
            print(f"  {scen:<12} {label:<12}  "
                  f"{vals_mid[2030]/1e9:>14.3f}  {vals_mid[2050]/1e9:>14.3f}  "
                  f"{vals_mid[2075]/1e9:>14.3f}  {vals_mid[2100]/1e9:>14.3f}")

            for i, yr in enumerate(YEARS):
                rows_ts.append({
                    "section":                  SECTION_NAME,
                    "section_type":             SECTION_TYPE,
                    "scenario":                 scen,
                    "variant":                  label,
                    "year":                     int(yr),
                    "slr_m":                    round(float(sarr[i]), 4),
                    "return_period_yr":         round(float(rp_a[i]), 4),
                    "closure_days_yr":          round(float(days_a[i]), 3),
                    "barrier_breached":         bool(breached[i]),
                    "annual_cost_mid_eur":      round(float(annual_mid[i]),  0),
                    "annual_cost_low_eur":      round(float(annual_low[i]),  0),
                    "annual_cost_high_eur":     round(float(annual_high[i]), 0),
                    "cumulative_cost_mid_eur":  round(float(cum_mid[i]),  0),
                    "cumulative_cost_low_eur":  round(float(cum_low[i]),  0),
                    "cumulative_cost_high_eur": round(float(cum_high[i]), 0),
                })
        print()

    # ─── Layer C ─────────────────────────────────────────────────────────────
    print("  " + "═" * 72)
    print("  LAYER C — Adaptation Options · Break-Even Analysis")
    print("  (Cacia–Estarreja cumulative disruption cost vs option investment)")
    print("  Break-even shown for LOW / MID / HIGH DDR bands (mid CAPEX)")
    print("  " + "─" * 72)

    rows_be = []
    for opt_name, opt in OPTIONS.items():
        cost_mid_capex = (opt["cost_low_eur"] + opt["cost_high_eur"]) / 2.0
        print(f"\n  ● {opt_name}")
        print(f"    {opt['desc_short']}")
        print(f"    Cost: €{opt['cost_low_eur']/1e6:.0f}M – "
              f"€{opt['cost_high_eur']/1e6:.0f}M  (mid: €{cost_mid_capex/1e6:.0f}M)")
        if opt.get("permanent"):
            print(f"    ★  Permanent solution — eliminates flood risk for full section.")
        if "Barrier" in opt_name:
            print(f"    ℹ  System-level: rail cost share ~15–20% of total barrier programme.")
        print()
        print(f"    {'Scenario':<12} {'Variant':<12}  "
              f"{'Low BE (MID DDR)':>16}  {'Mid BE (MID DDR)':>16}  {'High BE (MID DDR)':>17}")
        print(f"    {'─' * 65}")

        for scen in SLR_ANCHORS:
            for label in ["Baseline", "+Geoid"]:
                store = _cum_combined[(scen, label)]
                be_low  = break_even_year(store["mid"], opt["cost_low_eur"])
                be_mid  = break_even_year(store["mid"], cost_mid_capex)
                be_high = break_even_year(store["mid"], opt["cost_high_eur"])
                be_low_ddr  = break_even_year(store["low"],  cost_mid_capex)
                be_high_ddr = break_even_year(store["high"], cost_mid_capex)
                fmt = lambda y: str(y) if y else ">2100"
                print(f"    {scen:<12} {label:<12}  "
                      f"{fmt(be_low):>16}  {fmt(be_mid):>16}  {fmt(be_high):>17}")
                rows_be.append({
                    "option":                     opt_name,
                    "scenario":                   scen,
                    "variant":                    label,
                    "cost_low_eur":               opt["cost_low_eur"],
                    "cost_mid_eur":               cost_mid_capex,
                    "cost_high_eur":              opt["cost_high_eur"],
                    "be_year_low_capex_mid_ddr":  be_low,
                    "be_year_mid_capex_mid_ddr":  be_mid,
                    "be_year_high_capex_mid_ddr": be_high,
                    "be_year_mid_capex_low_ddr":  be_low_ddr,
                    "be_year_mid_capex_high_ddr": be_high_ddr,
                })
        print()

    # ─── Option descriptions ──────────────────────────────────────────────────
    print("  " + "═" * 72)
    print("  OPTION DESCRIPTIONS")
    print("  " + "─" * 72)
    for opt_name, opt in OPTIONS.items():
        print(f"\n  ▶ {opt_name}")
        words = opt["description"].split()
        line = "    "
        for w in words:
            if len(line) + len(w) + 1 > 74:
                print(line)
                line = "    " + w + " "
            else:
                line += w + " "
        if line.strip():
            print(line)

    # ─── Key insights ─────────────────────────────────────────────────────────
    print()
    print("  " + "═" * 72)
    print("  KEY INSIGHTS — RIA DE AVEIRO vs MONDEGO AND TAGUS SECTIONS")
    print("  " + "─" * 72)
    print()
    print("  1. MOST COMPLEX SECTION IN THE STUDY. Three concurrent flood mechanisms")
    print("     (direct SLR, tidal amplification, barrier breach) interact non-linearly.")
    print("     The Cacia–Estarreja section is the only section in this study where")
    print("     terrain is already below sea level (EU-DEM minimum −0.40 m MSL),")
    print("     making it the most immediately vulnerable asset in the entire analysis.")
    print()
    print("  2. SCOPE CORRECTION: ZONE A (OVAR–ESTARREJA) EXCLUDED. EU-DEM field check")
    print("     (2026-05-10) confirmed Zone A minimum elevation ~6.4 m MSL near Estarreja —")
    print("     far above any SLR projection to 2100. Previously modelled at 1.2 m MSL")
    print("     (unverified hardcoded assumption). Cacia–Estarreja (km 265–275) is the")
    print("     correct at-risk section and is now the sole section analysed in 10c.")
    print()
    print("  3. STANDARD ADAPTATION METHODS ARE NOT VIABLE. The required raise (+3.43 m")
    print("     under SSP2-4.5, +3.82 m under SSP5-8.5) exceeds the 2.50 m managed-")
    print("     retreat threshold under all scenarios. An extreme viaduct (Option 1) is")
    print("     technically possible but constitutes an exceptional intervention requiring")
    print("     deep pile foundations in below-sea-level waterlogged sediments.")
    print()
    print("  4. OPTION 2 IS UNIQUELY POSITIONED. It is the only option that addresses")
    print("     the root cause (lagoon system integrity) rather than the symptom (track")
    print("     flooding). It also protects Aveiro city, aquaculture, and 80k residents.")
    print("     The rail-attributable cost share (€80–140M) is comparable to Option 1,")
    print("     making the system-level co-benefits effectively 'free' for rail planning.")
    print()
    print("  5. OPTION 3 (BYPASS) MIRRORS THE HIGH-SPEED RAIL ARGUMENT. Under high")
    print("     emissions, the case for building a new climate-resilient corridor east")
    print("     of the Ria converges with the long-standing transport policy case for")
    print("     a Porto–Lisboa high-speed line bypassing the coastal corridor entirely.")
    print()
    print("  6. BARRIER BREACH IS NOW ACTIVE IN THE MODEL. When SLR reaches 0.60 m")
    print("     (conservative threshold), the Barra–Costa Nova barrier is assumed to")
    print("     fail, setting closure_days to 365/year (permanent closure). This binary")
    print("     threshold is reached ~2055–2070 under SSP5-8.5 +geoid, and ~2080–2100")
    print("     under SSP2-4.5. The barrier breach is the dominant risk driver for this")
    print("     section, not the incremental compound flood frequency model.")
    print()

    # ─── Save ─────────────────────────────────────────────────────────────────
    df_freq = pd.DataFrame(rows_freq)
    df_ts   = pd.DataFrame(rows_ts)
    df_be   = pd.DataFrame(rows_be)

    df_freq.to_csv(PROJECT_DIR / "aveiro_flood_frequency.csv",   index=False)
    df_ts.to_csv  (PROJECT_DIR / "aveiro_disruption_cost.csv",    index=False)
    df_be.to_csv  (PROJECT_DIR / "aveiro_bypass_comparison.csv",  index=False)

    print(f"  Outputs saved to: {PROJECT_DIR}")
    print(f"    aveiro_flood_frequency.csv    ({len(df_freq)} rows — key-year summary, Cacia–Estarreja)")
    print(f"    aveiro_disruption_cost.csv    ({len(df_ts)} rows — full annual time series, 3 DDR bands, barrier breach active)")
    print(f"    aveiro_bypass_comparison.csv  ({len(df_be)} rows — break-even by option/scenario)")
    print()

if __name__ == "__main__":
    main()
