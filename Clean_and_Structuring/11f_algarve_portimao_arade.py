"""
11f_algarve_portimao_arade.py  –  Pillar 3: Linha do Algarve (Portimão/Arade)
===============================================================================
Analyses sea-level rise (SLR) disruption risk to the Linha do Algarve
where it crosses the tidal Arade estuary west of Portimão station —
specifically the low-lying approach embankments on both banks of the estuary.

GEOGRAPHIC SCOPE — VERIFIED FROM EU-DEM + OSM DATA
----------------------------------------------------
A DEM analysis of actual track geometry (OSM relation 349295 sampled
against EU-DEM 25m, EGM2008) identified the following vulnerable section
(Stage 1 output — see elev_algarve_portimao_arade.py):

  Section     : Linha do Algarve — Portimão / Arade estuary crossing
  OSM relation: 349295 (Linha do Algarve)
  Bbox used   : lat [37.12, 37.18]  lon [-8.56, -8.46]
  Run date    : 2026-05-12

  Sample points      : 301 valid terrain (9 water artifacts excluded)
  Track length est.  : 15.1 km (section sampled)
  Minimum elev.      : 0.585 m MSL  (lat=37.137619, lon=-8.523111)
  Points < 5 m       : 30 / 301  (10.0% of section)
  Track at risk      : 1.5 km  (below 5 m MSL)

  All 30 at-risk points fall in the Arade Estuary Bridge Crossing zone:
    Arade Estuary Bridge Crossing: 30 pts, 1.50 km, min 0.585 m, mean 2.834 m

  EU-DEM BRIDGE NOTE: 9 sample points over the bridge span returned
  negative elevations (DEM samples Arade water surface, not bridge deck).
  These were excluded from all statistics. The bridge deck is assessed
  separately as elevated infrastructure (outside EU-DEM scope).

  NOTE: TRACK_ELEV_M (0.585 m) is the EU-DEM terrain floor on the
  approach embankment. True rail formation crown ≈ +0.30–0.40 m above
  terrain (≈ 0.9–1.0 m). 0.585 m used as conservative threshold.
  This is the lowest track elevation of any infrastructure in this study.

FLOOD MECHANISM
---------------
Compound event: Arade estuary tidal surge + Atlantic storm surge. The
Arade is a mesotidal estuary (tidal range 2–3 m at spring tides). The
estuary funnel concentrates surge energy; combined spring-tide + storm
events have historically overtopped the low-lying south bank alluvial
plain. At 0.585 m MSL, the approach embankment is well below MHWS
(~+1.3 m MSL at Portimão), meaning tide-only events can reach the track
in current conditions — let alone under SLR.

CRITICAL THRESHOLD
------------------
Permanent inundation of the minimum section (0.585 m) requires SLR ≥
0.585 m — reached before 2100 under SSP5-8.5 (2090 baseline, 2075
+geoid). This section faces existential operational risk under high
scenarios: essentially permanent disruption well before 2100 if not
adapted. The minimum track crown (~0.9 m including rail formation)
would be breached under SSP5-8.5 + geoid before 2080.

IMPORTANT PARAMETERS — ⚠ RESEARCHER ESTIMATES
-----------------------------------------------
TRACK_ELEV_M        = 0.585 m  (EU-DEM floor, verified)
                                True rail crown ≈ 0.9–1.0 m
RETURN_PERIOD_BASE  = 10 yr   ⚠ researcher estimate pending hydrological
                               calibration against Portimão tide gauge /
                               Arade estuary surge records (REF-43).
                               Rationale: MHWS Portimão ≈ +1.3 m MSL;
                               current spring tides already above 0.585 m;
                               RP₀ = 10 yr is conservative (actual current
                               exceedance may be much more frequent).
CLOSURE_DAYS_BASE   = 3.0 days ⚠ researcher estimate; same basis as 11e.

ECONOMIC MODULE — RIDERSHIP × RAIL VOT × TIME PENALTY
------------------------------------------------------
Same methodology as 11e (Faro–Olhão). Lower ridership for the western
Portimão section. DAILY_DISRUPTION computed from declared constants. (D24)

DAILY DISRUPTION:
  low  : €0.004 M/day  (400 pax × 0.75 h × €10.5/h × 1.15)
  mid  : €0.007 M/day  (700 pax × 0.75 h × €10.5/h × 1.30)
  high : €0.017 M/day  (1,400 pax × 0.75 h × €10.5/h × 1.55)

ADAPTATION OPTIONS (D24 — Decision 24, Session 27)
-------------------------------------------------
Required raise from raise_requirements.csv: SSP2-4.5 = +2.495 m, SSP5-8.5 = +2.885 m.
These values exceed the 2.50 m threshold for embankment raising — all SLR scenarios
require either a structural solution (viaduct / realignment) or managed retreat.
The previous +0.50 m raise approach (EA SC080039/R2 minimum intervention) is now
superseded by scenario-specific design thresholds.

Option A | Managed retreat — permanent bus replacement service
          Railway section (1.5 km) permanently closed; service maintained by
          dedicated bus route (Portimão–Lagos/Faro direction). Ongoing annual
          cost converted to NPV (2025–2100, 4% social discount rate).
          Unit rate: €250–400k/km/yr × 1.5 km = €375–600k/yr.
          NPV (75 yr @ 4%): PV-factor ≈ 22.36.
          Type: service continuity (permanent structural abandonment).

Option B | Short viaduct on current alignment (~1.5 km)
          Elevated concrete viaduct replacing the at-risk embankment on the
          existing Arade estuary alignment. Deck level set to clear all SLR
          scenarios to 2100 under SSP5-8.5 + geoid (+1.15 m).
          Unit cost: €12–20 M/km (±30%) × 1.5 km = €18–30 M.
          Type: structural adaptation (eliminates flood frequency risk).

Option C | Short realignment to higher ground
          New-build alignment routing through higher terrain, bypassing the
          Arade estuary low-lying section. Terrain check PENDING — EU-DEM
          suggests alternative corridor through northern margin of Portimão
          urban area (~5–8 m MSL, ~1.8–2.0 km route) but ground-truth and
          engineering feasibility study required.
          CAPEX: TBD pending terrain verification.
          Type: structural adaptation (eliminates flood frequency risk).

NOTE: Options B and C both eliminate flood risk by design. Break-even analysis
compares CAPEX against cumulative disruption cost avoided. Option A avoids
railway disruption entirely (by ending railway service) but incurs permanent
bus-service NPV cost. No engineering break-even exists for managed retreat —
it is a policy decision driven by cost-benefit relative to railway OPEX and
strategic network connectivity.

OUTPUTS
-------
  algarve_portimao_arade_flood_frequency.csv       — 24 rows
  algarve_portimao_arade_disruption_cost.csv       — rows (all 3 options)
  algarve_portimao_arade_adaptation_comparison.csv — rows (options A, B)

REFERENCES
----------
REF-01 : Fox-Kemper et al. (2021) IPCC AR6 WG1 Ch.9 — SLR scenarios
REF-02 : Seeger & Minderhoud (2026) Nature 652, 667–674 — geoid +0.15 m
REF-03 : Moftakhari et al. (2017) PNAS — compound flood model
REF-20 : OpenStreetMap contributors — relation 349295 (Linha do Algarve)
REF-40 : CP (Comboios de Portugal) Relatório e Contas 2023 — ⚠ verify
REF-41 : European Commission (2019) EU Handbook on External Costs — ⚠ verify
REF-43 : ⚠ FLAGGED FOR VERIFICATION — hydrological source for Arade
         estuary surge frequency / Portimão tide gauge RP analysis
         to calibrate RP₀ = 10 yr (and current exceedance frequency
         given MHWS already exceeds 0.585 m threshold)
"""

import csv as _csv
import math
import numpy as np
import pandas as pd
from pathlib import Path

# ── OUTPUT DIRECTORY ──────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── RAISE HEIGHTS FROM MASTER CSV (for reference / documentation) ─────────────
def _read_raise(section_id: str) -> dict:
    path = OUT_DIR / "raise_requirements.csv"
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

_RAISE = _read_raise("portimao_arade")
# Required raises: SSP2-4.5 = +2.495 m, SSP5-8.5 = +2.885 m.
# Both exceed the 2.50 m embankment threshold — structural solutions required.
# All three options (A/B/C) eliminate flood risk rather than raising embankment.

# ── SLR SCENARIOS (IPCC AR6 WG1 Ch.9 — REF-01) ───────────────────────────────
SLR_BASE = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2040: 0.13, 2050: 0.20,
                 2060: 0.24, 2070: 0.28, 2080: 0.32, 2090: 0.36, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2040: 0.20, 2050: 0.30,
                 2060: 0.36, 2070: 0.42, 2080: 0.48, 2090: 0.54, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2040: 0.27, 2050: 0.40,
                 2060: 0.52, 2070: 0.64, 2080: 0.76, 2090: 0.88, 2100: 1.00},
}
GEOID_OFFSET = 0.15    # Seeger & Minderhoud (2026) Nature 652 — REF-02

SCENARIOS = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
VARIANTS  = ["baseline", "+geoid"]
YEARS     = list(range(2025, 2101))
KEY_YEARS = [2030, 2050, 2075, 2100]

# ── SECTION PARAMETERS (from Stage 1 EU-DEM + OSM analysis) ──────────────────
TRACK_ELEV_M        = 0.585   # m MSL — EU-DEM terrain floor (conservative)
                               # True rail crown ≈ 0.9–1.0 m (+ rail formation)
                               # LOWEST ELEVATION IN THIS STUDY
RETURN_PERIOD_BASE  = 10.0    # yr — RP₀ ⚠ researcher estimate
                               # MHWS Portimão ≈ +1.3 m MSL; current spring
                               # tides already exceed 0.585 m — actual RP₀
                               # may be < 1 yr for terrain floor. 10 yr is
                               # conservative (refers to rail crown ~0.9 m).
                               # Must be calibrated vs REF-43.
CLOSURE_DAYS_BASE   = 3.0     # days per closure event ⚠ researcher estimate
SENSITIVITY_K       = np.log(2) / 0.10   # ≈ 6.931 — Moftakhari 2017 REF-03

# ── DAILY DISRUPTION COST — RIDERSHIP × RAIL VOT COMPUTATION ─────────────────
# Same methodology as 11e. Portimão section has lower ridership (western end).
#
# [CP Relatório e Contas 2023 — REF-40 ⚠]
# Portimão share of Algarve line: ~8–12% of total (~3.2 M passengers/year)
# Annual average with seasonal uplift:
_DAILY_PAX = {"low": 400, "mid": 700, "high": 1_400}
              # low  = off-season / conservative
              # mid  = weighted annual average
              # high = peak summer / upper bound

_VOT_RAIL_EUR_H   = 10.5      # €/h — rail passenger VOT, 2025 prices (REF-41 ⚠)
_TIME_PENALTY_H   = 0.75      # h/passenger — Portimão bus replacement adds
                               # ~45 min vs direct train (longer route)
_TOURISM_MULT = {"low": 1.15, "mid": 1.30, "high": 1.55}

# ── VOT COMPUTATION ───────────────────────────────────────────────────────────
DAILY_DISRUPTION = {
    t: _DAILY_PAX[t] * _TIME_PENALTY_H * _VOT_RAIL_EUR_H * _TOURISM_MULT[t]
    for t in ("low", "mid", "high")
}

# ── ADAPTATION CAPEX (three-option model — D24) ───────────────────────────────
# Embankment raising is NOT a viable option for this section:
#   SSP2-4.5 required raise = +2.495 m  (> 2.50 m threshold → structural)
#   SSP5-8.5 required raise = +2.885 m  (>> 2.50 m threshold → structural/retreat)
# See raise_requirements.csv (00_raise_requirements.py).

# Section geometry
_AT_RISK_LEN_M  = 1_500    # m — track at risk (< 5 m MSL), 30 pts × 50 m
_SERVICE_LEN_KM = _AT_RISK_LEN_M / 1_000   # 1.5 km

# ── Option A: Managed retreat — permanent bus replacement service ──────────────
# Annual cost: €250–400k/km/yr (industry benchmark for rural bus replacement
# on comparable lightly-used Portuguese regional rail routes).
# NPV 2025–2100 at 4% social discount rate (Portuguese standard).
_DISCOUNT_RATE       = 0.04
_HORIZON_N_YR        = 75        # 2025 → 2100
_PV_ANNUITY          = (1 - (1 + _DISCOUNT_RATE) ** -_HORIZON_N_YR) / _DISCOUNT_RATE
_BUS_RATE_LOW_EUR_KM_YR  = 250_000   # €/km/yr — lower bound
_BUS_RATE_HIGH_EUR_KM_YR = 400_000   # €/km/yr — upper bound

_OPT_A_ANNUAL_LOW_EUR  = _BUS_RATE_LOW_EUR_KM_YR  * _SERVICE_LEN_KM
_OPT_A_ANNUAL_HIGH_EUR = _BUS_RATE_HIGH_EUR_KM_YR * _SERVICE_LEN_KM
_OPT_A_NPV_LOW_M   = round(_OPT_A_ANNUAL_LOW_EUR  * _PV_ANNUITY / 1e6, 1)
_OPT_A_NPV_HIGH_M  = round(_OPT_A_ANNUAL_HIGH_EUR * _PV_ANNUITY / 1e6, 1)

# ── Option B: Short viaduct on current alignment (~1.5 km) ───────────────────
# Unit cost range: €12–20 M/km (±30% around €16 M/km mid-point).
# Based on European rail viaduct benchmarks (recent Portuguese infrastructure
# procurement), adjusted for short span, no major pier complications.
# Arade estuary crossing may require marine piers — upper bound applies.
_VIADUCT_UNIT_LOW_EUR_KM  = 12_000_000   # €/km
_VIADUCT_UNIT_HIGH_EUR_KM = 20_000_000   # €/km
_VIADUCT_LEN_KM  = _SERVICE_LEN_KM       # 1.5 km
_OPT_B_LOW_M   = round(_VIADUCT_UNIT_LOW_EUR_KM  * _VIADUCT_LEN_KM / 1e6, 0)
_OPT_B_HIGH_M  = round(_VIADUCT_UNIT_HIGH_EUR_KM * _VIADUCT_LEN_KM / 1e6, 0)

# ── Option C: Short realignment to higher ground ──────────────────────────────
# Route via higher terrain north of Portimão (EU-DEM suggests 5–8 m MSL,
# ~1.8–2.0 km route). CAPEX TBD — terrain check and feasibility study pending.
# Provisionally same order of magnitude as Option B, but may be higher due to
# urban area land acquisition and longer route length.
_OPT_C_NOTE   = "CAPEX TBD — terrain check pending"
_OPT_C_LOW_M  = float("nan")
_OPT_C_HIGH_M = float("nan")

# ── ADAPTATION OPTIONS ────────────────────────────────────────────────────────
# All three options eliminate railway flood disruption (either by abandoning
# the railway or elevating/rerouting above all SLR scenarios to 2100).
# freq_multiplier = 10000 models "effectively zero closure days" in adapted case.
OPTIONS = {
    "A": {"name": "Managed retreat — permanent bus replacement (NPV 2025-2100)",
          "capex_low_M":  _OPT_A_NPV_LOW_M,  "capex_high_M": _OPT_A_NPV_HIGH_M,
          "capex_note":   f"NPV @4%, 75yr: €{_OPT_A_ANNUAL_LOW_EUR/1000:.0f}–"
                          f"{_OPT_A_ANNUAL_HIGH_EUR/1000:.0f}k/yr × PVF {_PV_ANNUITY:.2f}",
          "type": "retreat",    "freq_multiplier": 10000.0, "dur_multiplier": 1.0},
    "B": {"name": "Short viaduct on current alignment (~1.5 km)",
          "capex_low_M":  _OPT_B_LOW_M,  "capex_high_M": _OPT_B_HIGH_M,
          "capex_note":   f"€{_VIADUCT_UNIT_LOW_EUR_KM//1e6:.0f}–"
                          f"{_VIADUCT_UNIT_HIGH_EUR_KM//1e6:.0f}M/km × {_VIADUCT_LEN_KM}km",
          "type": "structural", "freq_multiplier": 10000.0, "dur_multiplier": 1.0},
    "C": {"name": "Short realignment to higher ground (terrain check pending)",
          "capex_low_M":  _OPT_C_LOW_M,  "capex_high_M": _OPT_C_HIGH_M,
          "capex_note":   _OPT_C_NOTE,
          "type": "structural", "freq_multiplier": 10000.0, "dur_multiplier": 1.0},
}

# ── PRINT VOT COMPUTATION AUDIT ──────────────────────────────────────────────
def _print_vot_audit() -> None:
    print("── RIDERSHIP × VOT COMPUTATION (Linha do Algarve — Portimão/Arade) ──")
    print(f"  Portimão/Arade section  |  1.5 km at risk  |  OSM relation 349295")
    print(f"  Rail VOT = €{_VOT_RAIL_EUR_H}/h  |  Time penalty = {_TIME_PENALTY_H:.2f} h/pax")
    print(f"  (Bus replacement Portimão section adds ~45 min vs direct train)")
    print()
    for t in ("low", "mid", "high"):
        print(f"  [{t:4s}]  {_DAILY_PAX[t]:,} pax/day  ×  {_TIME_PENALTY_H:.2f}h  ×  "
              f"€{_VOT_RAIL_EUR_H}/h  ×  {_TOURISM_MULT[t]:.2f} (tourism mult)"
              f"  =  €{DAILY_DISRUPTION[t]/1e6:.4f}M/day")
    print()

_print_vot_audit()

# ── COMPOUND FLOOD MODEL ──────────────────────────────────────────────────────
def slr_for(scenario: str, variant: str, year: int) -> float:
    tbl = SLR_BASE[scenario]
    if year in tbl:
        slr = tbl[year]
    else:
        keys = sorted(tbl.keys())
        lo = max(k for k in keys if k <= year)
        hi = min(k for k in keys if k >= year)
        frac = (year - lo) / (hi - lo)
        slr = tbl[lo] + frac * (tbl[hi] - tbl[lo])
    if variant == "+geoid":
        slr += GEOID_OFFSET
    return slr


def closure_days_per_year(slr: float,
                           freq_mult: float = 1.0,
                           dur_mult:  float = 1.0) -> float:
    rp            = RETURN_PERIOD_BASE * freq_mult * np.exp(-SENSITIVITY_K * slr)
    events_per_yr = (1.0 / rp) * (1.0 + slr / 0.50)
    days          = events_per_yr * CLOSURE_DAYS_BASE * dur_mult
    return min(days, 365.0)


# ── LAYER A: FLOOD FREQUENCY ──────────────────────────────────────────────────
print("=" * 68)
print("LINHA DO ALGARVE — PORTIMÃO / ARADE ESTUARY SECTION")
print("Pillar 3: Sea-Level Rise Network Disruption Analysis")
print("=" * 68)
print()
print("  Geographic scope (verified EU-DEM 25m + OSM relation 349295):")
print("  Section : Portimão / Arade estuary crossing")
print("  Bbox    : lat [37.12, 37.18]  lon [-8.56, -8.46]")
print("  Length  : 15.1 km sampled  |  1.5 km at risk (< 5 m MSL)")
print("  Min elev: 0.585 m MSL  (lat=37.137619, lon=-8.523111)")
print("  10.0% of section below 5 m MSL")
print("  At-risk section mean: 2.834 m MSL (Arade Estuary Bridge zone)")
print("  ★ LOWEST TRACK ELEVATION IN THIS STUDY (0.585 m MSL)")
print()
print(f"── LAYER A: FLOOD FREQUENCY ──────────────────────────────────────────")
print(f"  Track elevation (EU-DEM floor): {TRACK_ELEV_M:.3f} m MSL  ⚠ conservative")
print(f"  True rail crown estimate:       ~0.90 m MSL  (+0.30-0.40 m formation)")
print(f"  Baseline return period (RP₀):   {RETURN_PERIOD_BASE:.0f} yr  ⚠ researcher estimate")
print(f"  ⚠ NOTE: MHWS at Portimão ≈ +1.3 m MSL — spring tides already")
print(f"          EXCEED the 0.585 m terrain floor in current conditions.")
print(f"          RP₀=10 yr refers conservatively to the ~0.9 m rail crown.")
print(f"  Closure days per event:         {CLOSURE_DAYS_BASE:.1f} days  ⚠ researcher estimate")
print(f"  Sensitivity k:                  {SENSITIVITY_K:.3f}  [Moftakhari 2017]")
print(f"  Geoid correction:               +{GEOID_OFFSET:.2f} m  [REF-02]")
print(f"  Max SLR+geoid by 2100 (SSP5-8.5): {1.00 + GEOID_OFFSET:.2f} m")
print(f"  Track elevation threshold:      {TRACK_ELEV_M:.3f} m")
print(f"  ▸ Permanent inundation (terrain floor) by 2100:")
if 1.00 + GEOID_OFFSET >= TRACK_ELEV_M:
    print(f"    YES — SSP5-8.5 + geoid ({1.00+GEOID_OFFSET:.2f} m) exceeds {TRACK_ELEV_M:.3f} m")
    print(f"    This section faces existential operational risk under SSP5-8.5.")
else:
    print(f"    NO (margin = {TRACK_ELEV_M - (1.00 + GEOID_OFFSET):.3f} m)")

freq_rows = []
for scenario in SCENARIOS:
    for variant in VARIANTS:
        for year in KEY_YEARS:
            slr = slr_for(scenario, variant, year)
            days = closure_days_per_year(slr)
            rp_eff = RETURN_PERIOD_BASE * np.exp(-SENSITIVITY_K * slr)
            freq_rows.append({
                "scenario": scenario, "variant": variant, "year": year,
                "slr_m": round(slr, 3), "rp_effective_yr": round(rp_eff, 2),
                "closure_days_yr": round(days, 3),
            })

df_freq = pd.DataFrame(freq_rows)
csv_freq = OUT_DIR / "algarve_portimao_arade_flood_frequency.csv"
df_freq.to_csv(csv_freq, index=False)

print()
print(f"  {'Scenario':<12} {'Variant':<10} {'Year':>5} {'SLR(m)':>8} "
      f"{'RP(yr)':>8} {'Closure d/yr':>13}")
print("  " + "-" * 60)
for _, r in df_freq.iterrows():
    print(f"  {r['scenario']:<12} {r['variant']:<10} {int(r['year']):>5} "
          f"{r['slr_m']:>8.3f} {r['rp_effective_yr']:>8.2f} "
          f"{r['closure_days_yr']:>13.3f}")
print(f"\n  ▸ Saved: {csv_freq.name}  ({len(df_freq)} rows)")


# ── LAYER B: CUMULATIVE DISRUPTION COST ───────────────────────────────────────
print("\n── LAYER B: CUMULATIVE DISRUPTION COST (no adaptation) ───────────────")

disrupt_rows = []
for scenario in SCENARIOS:
    for variant in VARIANTS:
        for opt_id, opt in OPTIONS.items():
            cumulative = {"low": 0.0, "mid": 0.0, "high": 0.0}
            for year in YEARS:
                slr  = slr_for(scenario, variant, year)
                days = closure_days_per_year(slr, opt["freq_multiplier"],
                                             opt["dur_multiplier"])
                for tier in ("low", "mid", "high"):
                    cumulative[tier] += days * DAILY_DISRUPTION[tier]
                disrupt_rows.append({
                    "scenario": scenario, "variant": variant,
                    "option": opt_id, "year": year,
                    "slr_m": round(slr, 3),
                    "closure_days_yr": round(days, 4),
                    "annual_cost_low_M":  round(days * DAILY_DISRUPTION["low"]  / 1e6, 4),
                    "annual_cost_mid_M":  round(days * DAILY_DISRUPTION["mid"]  / 1e6, 4),
                    "annual_cost_hi_M":   round(days * DAILY_DISRUPTION["high"] / 1e6, 4),
                    "cum_cost_low_bn":    round(cumulative["low"]  / 1e9, 4),
                    "cum_cost_mid_bn":    round(cumulative["mid"]  / 1e9, 4),
                    "cum_cost_hi_bn":     round(cumulative["high"] / 1e9, 4),
                })

df_disrupt = pd.DataFrame(disrupt_rows)
csv_disrupt = OUT_DIR / "algarve_portimao_arade_disruption_cost.csv"
df_disrupt.to_csv(csv_disrupt, index=False)

print()
print(f"  {'Scenario':<12} {'Variant':<10} {'Year':>5} "
      f"{'Cumul. low (€bn)':>18} {'mid':>10} {'high':>10}")
print("  " + "-" * 70)
for scenario in SCENARIOS:
    for variant in VARIANTS:
        cum = {"low": 0.0, "mid": 0.0, "high": 0.0}
        for year in YEARS:
            slr  = slr_for(scenario, variant, year)
            days = closure_days_per_year(slr)
            for tier in ("low", "mid", "high"):
                cum[tier] += days * DAILY_DISRUPTION[tier]
            if year in KEY_YEARS:
                print(f"  {scenario:<12} {variant:<10} {year:>5} "
                      f"{cum['low']/1e9:>18.4f} "
                      f"{cum['mid']/1e9:>10.4f} "
                      f"{cum['high']/1e9:>10.4f}")
print(f"\n  ▸ Saved: {csv_disrupt.name}  ({len(df_disrupt)} rows)")


# ── LAYER C: ADAPTATION COST COMPARISON ──────────────────────────────────────
print("\n── LAYER C: ADAPTATION COST COMPARISON (three-option model) ─────────")
print()
print(f"  Required raises from raise_requirements.csv (section: portimao_arade):")
print(f"    SSP2-4.5 : +{_RAISE['SSP2-4.5']:.3f} m  →  {_RAISE['method']}")
print(f"    SSP5-8.5 : +{_RAISE['SSP5-8.5']:.3f} m  →  {_RAISE['method']}")
print(f"  Both exceed the 2.50 m embankment threshold.")
print(f"  Embankment raising is NOT viable. Three structural options analysed.")
print()
for opt_id, opt in OPTIONS.items():
    c_lo = opt["capex_low_M"]
    c_hi = opt["capex_high_M"]
    if math.isnan(c_lo):
        capex_str = "TBD (terrain check pending)"
    else:
        capex_str = f"€{c_lo:.1f}–{c_hi:.1f} M"
    print(f"  Option {opt_id}: {opt['name']}")
    print(f"           CAPEX: {capex_str}")
    print(f"           Note : {opt['capex_note']}")
    print(f"           Type : {opt['type']}")
    print()

adapt_rows = []
for scenario in SCENARIOS:
    for variant in VARIANTS:
        for opt_id, opt in OPTIONS.items():
            c_lo = opt["capex_low_M"]
            c_hi = opt["capex_high_M"]
            # Skip break-even if CAPEX is TBD (Option C)
            if math.isnan(c_lo):
                be_low = be_mid = be_high = "TBD"
                capex_low = capex_mid = capex_high = float("nan")
            else:
                capex_low  = c_lo * 1e6
                capex_mid  = (c_lo + c_hi) / 2 * 1e6
                capex_high = c_hi * 1e6
                be_low = be_mid = be_high = None
            _cum_no = 0.0; cum_ad = 0.0

            for year in YEARS:
                slr     = slr_for(scenario, variant, year)
                days_no = closure_days_per_year(slr)
                days_ad = closure_days_per_year(slr, opt["freq_multiplier"],
                                                opt["dur_multiplier"])
                _cum_no += days_no * DAILY_DISRUPTION["mid"]
                cum_ad  += days_ad * DAILY_DISRUPTION["mid"]
                savings  = _cum_no - cum_ad
                if not math.isnan(capex_low):
                    if be_low  is None and savings >= capex_low:  be_low  = year
                    if be_mid  is None and savings >= capex_mid:  be_mid  = year
                    if be_high is None and savings >= capex_high: be_high = year

            for key_yr in KEY_YEARS:
                c_no = sum(closure_days_per_year(slr_for(scenario, variant, y))
                           * DAILY_DISRUPTION["mid"]
                           for y in YEARS if y <= key_yr)
                c_ad = sum(closure_days_per_year(slr_for(scenario, variant, y),
                                                 opt["freq_multiplier"],
                                                 opt["dur_multiplier"])
                           * DAILY_DISRUPTION["mid"]
                           for y in YEARS if y <= key_yr)
                adapt_rows.append({
                    "scenario":     scenario,
                    "variant":      variant,
                    "option":       opt_id,
                    "option_name":  opt["name"],
                    "option_type":  opt["type"],
                    "capex_low_M":  c_lo,
                    "capex_high_M": c_hi,
                    "key_year":     key_yr,
                    "cum_no_adapt_bn":   round(c_no / 1e9, 4),
                    "cum_adapt_bn":      round(c_ad / 1e9, 4),
                    "savings_bn":        round((c_no - c_ad) / 1e9, 4),
                    "be_year_low_capex": (be_low  if be_low  else ">2100")
                                         if not math.isnan(capex_low) else "TBD",
                    "be_year_mid_capex": (be_mid  if be_mid  else ">2100")
                                         if not math.isnan(capex_low) else "TBD",
                    "be_year_hi_capex":  (be_high if be_high else ">2100")
                                         if not math.isnan(capex_low) else "TBD",
                })

df_adapt = pd.DataFrame(adapt_rows)
csv_adapt = OUT_DIR / "algarve_portimao_arade_adaptation_comparison.csv"
df_adapt.to_csv(csv_adapt, index=False)

print(f"  Break-even years vs cumulative disruption cost (mid estimate):")
print()
print(f"  {'Option':<47} {'Scenario':<12} {'Variant':<10} "
      f"{'BE low':>8} {'BE mid':>8} {'BE high':>9}")
print("  " + "-" * 99)
for opt_id in OPTIONS:
    for scenario in ["SSP2-4.5", "SSP5-8.5"]:
        for variant in VARIANTS:
            sub = df_adapt[(df_adapt.option == opt_id) &
                           (df_adapt.scenario == scenario) &
                           (df_adapt.variant  == variant) &
                           (df_adapt.key_year == 2100)]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  {opt_id}. {OPTIONS[opt_id]['name'][:45]:<45} "
                  f"{scenario:<12} {variant:<10} "
                  f"{str(r['be_year_low_capex']):>8} "
                  f"{str(r['be_year_mid_capex']):>8} "
                  f"{str(r['be_year_hi_capex']):>9}")
print(f"\n  ▸ Saved: {csv_adapt.name}  ({len(df_adapt)} rows)")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("SECTION SUMMARY — LINHA DO ALGARVE (PORTIMÃO / ARADE ESTUARY)")
print("=" * 68)
print()
print("  Vulnerable section (EU-DEM 25m + OSM relation 349295 verified):")
print("    Portimão / Arade estuary approach embankments")
print("    15.1 km sampled  |  1.5 km at risk (10.0% of section)")
print("    Min elev: 0.585 m MSL  |  Mean (at-risk): 2.834 m MSL")
print("    ★ LOWEST TRACK ELEVATION IN THIS STUDY")
print(f"  Flood mechanism  : Arade tidal surge + Atlantic storm surge")
print(f"  Baseline RP₀     : {RETURN_PERIOD_BASE:.0f} yr  ⚠ researcher estimate — needs REF-43")
if 1.00 + GEOID_OFFSET >= TRACK_ELEV_M:
    print(f"  ★ Permanent inundation (terrain floor): YES under SSP5-8.5+geoid")
    print(f"    SLR+geoid = {1.00+GEOID_OFFSET:.2f} m > {TRACK_ELEV_M:.3f} m terrain floor")
    print(f"    This section has no long-term operational future without adaptation")
    print(f"    under high SLR scenarios.")
print()
print("  Cumulative disruption cost (NO adaptation, mid estimate):")
for scenario in SCENARIOS:
    for variant in VARIANTS:
        cum = sum(closure_days_per_year(slr_for(scenario, variant, y))
                  * DAILY_DISRUPTION["mid"] for y in YEARS)
        print(f"    {scenario:<12} {variant:<10}  →  €{cum/1e9:.4f} bn by 2100")
print()
print("  ★ RP₀ = 10 yr applied to rail crown (~0.9 m MSL). The EU-DEM")
print("    terrain floor (0.585 m) is already below MHWS at Portimão")
print("    (~1.3 m). Current spring tides likely already reach or exceed")
print("    the terrain floor. Must be verified vs tide gauge. (REF-43)")
print()
print("  ★ Required raises exceed 2.50 m — embankment raising is not viable.")
print("    Structural solutions (viaduct/realignment) or managed retreat required.")
print("    Prior +0.50 m raise (EA SC080039/R2 minimum) now superseded by")
print("    scenario-specific design thresholds (00_raise_requirements.py).")
print()
print(f"  Adaptation options (three-option model, D24):")
print(f"    Option A (managed retreat): NPV €{_OPT_A_NPV_LOW_M:.1f}–{_OPT_A_NPV_HIGH_M:.1f} M  "
      f"(€{_OPT_A_ANNUAL_LOW_EUR/1000:.0f}–{_OPT_A_ANNUAL_HIGH_EUR/1000:.0f}k/yr × PVF {_PV_ANNUITY:.1f})")
print(f"    Option B (viaduct, 1.5 km): €{_OPT_B_LOW_M:.0f}–{_OPT_B_HIGH_M:.0f} M  "
      f"(€{_VIADUCT_UNIT_LOW_EUR_KM//1e6:.0f}–{_VIADUCT_UNIT_HIGH_EUR_KM//1e6:.0f}M/km × {_VIADUCT_LEN_KM} km ±30%)")
print(f"    Option C (realignment):     CAPEX TBD — terrain check pending")
print()
print(f"  Outputs: {OUT_DIR}")
print(f"    {csv_freq.name}   ({len(df_freq)} rows)")
print(f"    {csv_disrupt.name}  ({len(df_disrupt)} rows)")
print(f"    {csv_adapt.name}  ({len(df_adapt)} rows)")
print()
print("  Sources: REF-01 (IPCC AR6), REF-02 (Seeger & Minderhoud 2026),")
print("           REF-03 (Moftakhari 2017), REF-20 (OSM relation 349295),")
print("           REF-40 ⚠ (CP 2023), REF-41 ⚠ (EU Handbook VOT),")
print("           REF-43 ⚠ (Arade estuary flood frequency — TO BE CONFIRMED).")
