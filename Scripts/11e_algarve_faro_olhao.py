"""
11e_algarve_faro_olhao.py  –  Pillar 3: Linha do Algarve (Faro–Olhão Section)
===============================================================================
Analyses sea-level rise (SLR) disruption risk to the Linha do Algarve
where it crosses the Ria Formosa backbarrier lagoon between Faro station
and Olhão station — the lowest-lying section of the Portuguese southern
railway network.

GEOGRAPHIC SCOPE — VERIFIED FROM EU-DEM + OSM DATA
----------------------------------------------------
A DEM analysis of actual track geometry (OSM relation 349295 sampled
against EU-DEM 25m, EGM2008) identified the following vulnerable section
(Stage 1 output — see elev_algarve_faro_olhao.py):

  Section     : Linha do Algarve — Faro station → Olhão station
  OSM relation: 349295 (Linha do Algarve)
  Bbox used   : lat [36.99, 37.038]  lon [-7.945, -7.80]
  Run date    : 2026-05-12

  Sample points      : 264 (at 50 m intervals)
  Track length est.  : 13.2 km (section sampled)
  Minimum elev.      : 2.341 m MSL  (lat=37.015467, lon=-7.937635)
  Mean elev. (section): 7.130 m MSL (includes higher approaches)
  Mean elev. (at risk): 4.125 m MSL (87 pts in Ria Formosa Crossing zone)
  Points < 5 m       : 98 / 264  (37.1% of section)
  Track at risk      : 4.9 km  (below 5 m MSL)

  Flood zones:
    Faro–Ria Formosa Crossing   : 87 pts, 4.35 km, min 2.341 m, mean 4.125 m
    Olhão Station Approaches    : 11 pts, 0.55 km, min 3.838 m, mean 4.375 m

  NOTE: TRACK_ELEV_M (2.341 m) is the EU-DEM terrain floor at 25 m
  resolution. The actual rail formation (ballast + sleepers + rail)
  sits approximately +0.30–0.40 m above terrain. The DEM value is
  therefore a conservative lower bound; the true rail crown may be
  ~2.6–2.7 m. 2.341 m is used as the threshold for the compound
  flood model (conservative).

FLOOD MECHANISM
---------------
Compound event: Atlantic storm surge + lagoonal backing through the Ria
Formosa inlet system. The Ria Formosa is a multi-inlet backbarrier lagoon
(Natura 2000). Its eastern end (Faro–Olhão) is semi-enclosed; surge energy
propagates through the inlets and backs up against the rail embankment from
the landward side as well as the seaward side. This mechanism is distinct
from open-coast surge (no wave run-up) but is compounded by SLR raising
mean lagoonal water levels. Under SLR, the frequency and depth of lagoonal
inundation of the embankment increases non-linearly.

CRITICAL THRESHOLD
------------------
Permanent inundation of the minimum section (2.341 m) requires SLR ≥ 2.341 m
— not reached by 2100 under any IPCC AR6 scenario (max SSP5-8.5 + geoid =
1.15 m). Risk is operational (flood frequency increase), not existential.

IMPORTANT PARAMETERS — ⚠ RESEARCHER ESTIMATES
-----------------------------------------------
TRACK_ELEV_M        = 2.341 m  (EU-DEM floor, verified)
RETURN_PERIOD_BASE  = 20 yr    ⚠ researcher estimate pending hydrological
                               calibration against Ria Formosa/Faro tide
                               gauge records (REF-42 flagged for verification).
                               Rationale: MHWS at Faro ≈ +1.5 m MSL; 1-in-20yr
                               surge ≈ +0.85 m → combined ≈ 2.35 m, marginal
                               exceedance of 2.341 m threshold.
CLOSURE_DAYS_BASE   = 3.0 days ⚠ researcher estimate; typical Portuguese
                               railway flood reinstatement (ballast inspection,
                               track geometry check, safety sign-off).
                               No documented Algarve line closure data found;
                               comparable to short embankment flood events.

ECONOMIC MODULE — RIDERSHIP × RAIL VOT × TIME PENALTY
------------------------------------------------------
The Linha do Algarve is a passenger-only regional service (CP Algarve).
No freight component. Daily disruption cost = passenger delay × rail VOT
× indirect (tourism) multiplier.

DAILY DISRUPTION:
  low  : €0.011 M/day  (1,500 pax × 0.60 h × €10.5/h × 1.15)
  mid  : €0.020 M/day  (2,500 pax × 0.60 h × €10.5/h × 1.30)
  high : €0.049 M/day  (5,000 pax × 0.60 h × €10.5/h × 1.55)

ADAPTATION OPTIONS
------------------
Option 1 | Track/embankment raising (scenario-specific raise height)
          Raise heights from raise_requirements.csv (00_raise_requirements.py).
          Formula: MHWS(1.80) + surge_100yr(0.50) + SLR_2100 + freeboard(0.30)
                   − terrain_floor(2.341 m EU-DEM).
          SSP2-4.5 lower bound: +0.689 m → vol = 6 × 0.689 × 4,900 ≈ 20,256 m³
          SSP5-8.5 design:      +1.079 m → vol = 6 × 1.079 × 4,900 ≈ 31,722 m³
          EA SC080039/R2 Table 1.4: £594/m³ (2015 GBP) × 1.13 × 1.17.
          ⚠ NOTA BENE: The Ria Formosa crossing is a Natura 2000 / SPA site.
          Any embankment raising requires Avaliação de Impacte Ambiental (AIA)
          and Article 6 Habitats Directive assessment. Permitting costs and
          mitigation measures are additional and outside this cost model.
          Type: frequency reducer.

Option 2 | Flood protection barriers (sheet piling, both shoulders)
          EA SC080039/R2 Table 1.7: £1,843/m × 1.13 × 1.17. Both sides,
          full at-risk section (2 × 4,900 m). Same Natura 2000 caveat as Opt1.
          Type: frequency reducer.

Option 3 | Service resilience protocol (duration reducer only)
          Pre-contracted bus replacement fleet + real-time flood monitoring
          at the Ria Formosa crossing. European ITS/monitoring benchmark.
          Reduces mean closure duration by 50% (3.0 → 1.5 days).
          Does NOT reduce flood frequency — lagoonal hydrology unchanged.
          Type: duration reducer only.

OUTPUTS
-------
  algarve_faro_olhao_flood_frequency.csv      — 24 rows
  algarve_faro_olhao_disruption_cost.csv      — 1,368 rows
  algarve_faro_olhao_adaptation_comparison.csv — 72 rows

REFERENCES
----------
REF-01 : Fox-Kemper et al. (2021) IPCC AR6 WG1 Ch.9 — SLR scenarios
REF-02 : Seeger & Minderhoud (2026) Nature 652, 667–674 — geoid +0.15 m
REF-03 : Moftakhari et al. (2017) PNAS — compound flood model
REF-20 : OpenStreetMap contributors — relation 349295 (Linha do Algarve)
REF-40 : CP (Comboios de Portugal) Relatório e Contas 2023 — ⚠ verify
         Algarve line annual ridership (~3.2–3.5 M passengers/year)
REF-41 : European Commission (2019) EU Handbook on External Costs —
         ⚠ verify Table 3.3: rail passenger short-run VOT, Portugal
REF-42 : ⚠ FLAGGED FOR VERIFICATION — hydrological source for Ria Formosa
         surge frequency / Faro tide gauge RP analysis to calibrate RP₀=20 yr
"""

import csv as _csv
import numpy as np
import pandas as pd
from pathlib import Path

# ── OUTPUT DIRECTORY ──────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── RAISE HEIGHTS FROM MASTER CSV (00_raise_requirements.py) ─────────────────
def _read_raise(section_id: str) -> dict:
    """Read scenario raise heights from raise_requirements.csv."""
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

_RAISE = _read_raise("faro_olhao")

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
TRACK_ELEV_M        = 2.341   # m MSL — EU-DEM terrain floor (conservative)
                               # True rail crown ≈ +0.30-0.40 m above terrain
RETURN_PERIOD_BASE  = 20.0    # yr — RP₀ ⚠ researcher estimate
                               # Rationale: MHWS Faro ≈ +1.5 m MSL;
                               # 1-in-20yr surge ≈ +0.85 m at Faro;
                               # combined ≈ 2.35 m → marginal exceedance
                               # of 2.341 m threshold. Pending REF-42.
CLOSURE_DAYS_BASE   = 3.0     # days per closure event ⚠ researcher estimate
                               # Typical railway flood reinstatement: ballast
                               # inspection, track geometry check, safety sign-off.
SENSITIVITY_K       = np.log(2) / 0.10   # ≈ 6.931 — Moftakhari 2017 REF-03

# ── DAILY DISRUPTION COST — RIDERSHIP × RAIL VOT COMPUTATION ─────────────────
# Linha do Algarve is a passenger-only regional service. No freight component.
# DAILY_DISRUPTION computed from declared input constants. (D24 methodology)
#
# RIDERSHIP INPUTS
# [CP Relatório e Contas 2023 — REF-40 ⚠]
# Algarve line total: ~3.2–3.5 M passengers/year
# Faro–Olhão section share: ~15–20% of total (high-frequency, short section)
# Annual average with seasonal uplift (summer peak × 3–5× winter):
_DAILY_PAX = {"low": 1_500, "mid": 2_500, "high": 5_000}
              # low  = off-season / conservative annual share
              # mid  = weighted annual average (summer-loaded)
              # high = peak summer day / upper bound

# RAIL VALUE-OF-TIME
# [EU Handbook on External Costs 2019, Table 3.3, PT — REF-41 ⚠]
# Rail passenger short-run VOT: ~€8-10/h (2016 prices) → 2025 adjusted ×1.25
_VOT_RAIL_EUR_H   = 10.5      # €/h — rail passenger VOT, 2025 prices

# TIME PENALTY — bus replacement service vs direct train
# Faro–Olhão by train: ~12 min. Bus replacement: ~50 min (slower, stops, wait).
# Time penalty per disrupted passenger journey: ~38 min ≈ 0.60 h
_TIME_PENALTY_H   = 0.60      # h/passenger — additional journey time

# TOURISM (INDIRECT) MULTIPLIER
# The Algarve is highly tourism-dependent. Service disruption reduces tourist
# activity beyond direct passenger delay. Analogous to Anas & Hiramatsu (2013)
# IO multiplier used for roads, adapted for tourism-weighted rail context.
_TOURISM_MULT = {"low": 1.15, "mid": 1.30, "high": 1.55}

# ── VOT COMPUTATION ───────────────────────────────────────────────────────────
DAILY_DISRUPTION = {
    t: _DAILY_PAX[t] * _TIME_PENALTY_H * _VOT_RAIL_EUR_H * _TOURISM_MULT[t]
    for t in ("low", "mid", "high")
}

# ── ADAPTATION CAPEX (UK EA SC080039/R2, 2015 prices, railway geometry) ──────
# Same source and adjustment factors as 11c/11d.
_EA_EMBANK_GBP2015    = 594.0      # £/m³  — Table 1.4, >15,000 m³ band
_EA_SHEETPILE_GBP2015 = 1843.0     # £/m   — Table 1.7
_EA_TO_PT2025         = 1.13
_GBP_TO_EUR           = 1.17

_embank_eur_m3  = _EA_EMBANK_GBP2015    * _EA_TO_PT2025 * _GBP_TO_EUR
_spile_eur_m    = _EA_SHEETPILE_GBP2015 * _EA_TO_PT2025 * _GBP_TO_EUR

# Section geometry (from Stage 1 elev_algarve_faro_olhao.py)
_AT_RISK_LEN_M  = 4_900    # m — track at risk (< 5 m MSL), 98 pts × 50 m
_FORMATION_W_M  = 6.0      # m — single-track railway formation width

# Raise heights from raise_requirements.csv (00_raise_requirements.py).
# Formula: MHWS(1.80) + surge_100yr(0.50) + SLR_2100 + freeboard(0.30)
#          − terrain_floor(2.341 m EU-DEM).
# SSP2-4.5 = lower bound / minimum adequate investment scenario.
# SSP5-8.5 = design/headline scenario.
_RAISE_SSP2_M   = _RAISE["SSP2-4.5"]   # 0.689 m
_RAISE_SSP5_M   = _RAISE["SSP5-8.5"]   # 1.079 m
_METHOD_DESIGN  = _RAISE["method"]      # "Elevated embankment (reinforced)"

# Option 1a: embankment raising — SSP2-4.5 lower bound
_opt1a_vol_m3 = _FORMATION_W_M * _RAISE_SSP2_M * _AT_RISK_LEN_M
_opt1a_mid_M  = _opt1a_vol_m3 * _embank_eur_m3 / 1e6
_OPT1A_LOW_M  = round(_opt1a_mid_M * 0.75, 1)
_OPT1A_HIGH_M = round(_opt1a_mid_M * 1.25, 1)

# Option 1b: embankment raising — SSP5-8.5 design scenario
_opt1b_vol_m3 = _FORMATION_W_M * _RAISE_SSP5_M * _AT_RISK_LEN_M
_opt1b_mid_M  = _opt1b_vol_m3 * _embank_eur_m3 / 1e6
_OPT1B_LOW_M  = round(_opt1b_mid_M * 0.75, 1)
_OPT1B_HIGH_M = round(_opt1b_mid_M * 1.25, 1)

# Option 2: sheet piling both shoulders
_opt2_len_m   = 2 * _AT_RISK_LEN_M
_opt2_mid_M   = _opt2_len_m * _spile_eur_m / 1e6
_OPT2_LOW_M   = round(_opt2_mid_M * 0.75, 1)
_OPT2_HIGH_M  = round(_opt2_mid_M * 1.25, 1)

# Option 3: service resilience protocol (bus replacement + flood monitoring)
_RESILIENCE_EUR_KM = 200_000   # €/km — pre-contracted bus + real-time monitoring
_opt3_mid_M   = _RESILIENCE_EUR_KM * _AT_RISK_LEN_M / 1_000 / 1e6
_OPT3_LOW_M   = round(_opt3_mid_M * 0.70, 1)
_OPT3_HIGH_M  = round(_opt3_mid_M * 1.30, 1)

# ── ADAPTATION OPTIONS ────────────────────────────────────────────────────────
# Option 1 now has two CAPEX variants (one per SLR design scenario).
# Flood-frequency reduction effectiveness (freq_multiplier) is the same
# for both: the embankment raise doubles the effective return period
# regardless of exact raise height within the embankment range.
OPTIONS = {
    "1a": {"name": f"Embankment raising — SSP2-4.5 lower bound (+{_RAISE_SSP2_M:.2f} m)",
           "capex_low_M": _OPT1A_LOW_M, "capex_high_M": _OPT1A_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    "1b": {"name": f"Embankment raising — SSP5-8.5 design (+{_RAISE_SSP5_M:.2f} m)",
           "capex_low_M": _OPT1B_LOW_M, "capex_high_M": _OPT1B_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    2:    {"name": "Flood protection barriers (sheet piling)",
           "capex_low_M": _OPT2_LOW_M, "capex_high_M": _OPT2_HIGH_M,
           "type": "frequency", "freq_multiplier": 1.8, "dur_multiplier": 1.0},
    3:    {"name": "Service resilience protocol",
           "capex_low_M": _OPT3_LOW_M,  "capex_high_M": _OPT3_HIGH_M,
           "type": "duration",  "freq_multiplier": 1.0, "dur_multiplier": 0.50},
}

# ── PRINT VOT COMPUTATION AUDIT ──────────────────────────────────────────────
def _print_vot_audit() -> None:
    print("── RIDERSHIP × VOT COMPUTATION (Linha do Algarve — Faro–Olhão) ───────")
    print(f"  Faro–Olhão section  |  4.9 km at risk  |  OSM relation 349295")
    print(f"  Rail VOT = €{_VOT_RAIL_EUR_H}/h  |  Time penalty = {_TIME_PENALTY_H:.2f} h/pax")
    print(f"  (Bus replacement Faro–Olhão adds ~38 min vs direct train)")
    print()
    for t in ("low", "mid", "high"):
        print(f"  [{t:4s}]  {_DAILY_PAX[t]:,} pax/day  ×  {_TIME_PENALTY_H:.2f}h  ×  "
              f"€{_VOT_RAIL_EUR_H}/h  ×  {_TOURISM_MULT[t]:.2f} (tourism mult)"
              f"  =  €{DAILY_DISRUPTION[t]/1e6:.3f}M/day")
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
print("LINHA DO ALGARVE — FARO–OLHÃO SECTION (Ria Formosa Crossing)")
print("Pillar 3: Sea-Level Rise Network Disruption Analysis")
print("=" * 68)
print()
print("  Geographic scope (verified EU-DEM 25m + OSM relation 349295):")
print("  Section : Faro station → Olhão station")
print("  Bbox    : lat [36.99, 37.038]  lon [-7.945, -7.80]")
print("  Length  : 13.2 km sampled  |  4.9 km at risk (< 5 m MSL)")
print("  Min elev: 2.341 m MSL  (lat=37.015467, lon=-7.937635)")
print("  37.1% of section below 5 m MSL")
print("  At-risk section mean: 4.125 m MSL (Ria Formosa Crossing zone)")
print()
print(f"── LAYER A: FLOOD FREQUENCY ──────────────────────────────────────────")
print(f"  Track elevation (EU-DEM floor): {TRACK_ELEV_M:.3f} m MSL  ⚠ conservative")
print(f"  Baseline return period (RP₀):   {RETURN_PERIOD_BASE:.0f} yr  ⚠ researcher estimate")
print(f"  Closure days per event:         {CLOSURE_DAYS_BASE:.1f} days  ⚠ researcher estimate")
print(f"  Sensitivity k:                  {SENSITIVITY_K:.3f}  [Moftakhari 2017]")
print(f"  Geoid correction:               +{GEOID_OFFSET:.2f} m  [REF-02]")
print(f"  Max SLR+geoid by 2100 (SSP5-8.5): {1.00 + GEOID_OFFSET:.2f} m")
print(f"  Track elevation threshold:      {TRACK_ELEV_M:.3f} m")
print(f"  ▸ Permanent inundation by 2100: NO (margin = "
      f"{TRACK_ELEV_M - (1.00 + GEOID_OFFSET):.3f} m)")

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
csv_freq = OUT_DIR / "algarve_faro_olhao_flood_frequency.csv"
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
csv_disrupt = OUT_DIR / "algarve_faro_olhao_disruption_cost.csv"
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


# ── LAYER C: ADAPTATION BREAK-EVEN ───────────────────────────────────────────
print("\n── LAYER C: ADAPTATION BREAK-EVEN ANALYSIS ───────────────────────────")
print()
for opt_id, opt in OPTIONS.items():
    print(f"  {opt_id}. {opt['name']:<45} "
          f"€{opt['capex_low_M']:.1f}–{opt['capex_high_M']:.1f} M  "
          f"[{opt['type']}]")

adapt_rows = []
for scenario in SCENARIOS:
    for variant in VARIANTS:
        for opt_id, opt in OPTIONS.items():
            capex_low  = opt["capex_low_M"]  * 1e6
            capex_mid  = (opt["capex_low_M"] + opt["capex_high_M"]) / 2 * 1e6
            capex_high = opt["capex_high_M"] * 1e6
            be_low = be_mid = be_high = None
            _cum_no = 0.0; cum_ad = 0.0

            for year in YEARS:
                slr        = slr_for(scenario, variant, year)
                days_no    = closure_days_per_year(slr)
                days_ad    = closure_days_per_year(slr, opt["freq_multiplier"],
                                                   opt["dur_multiplier"])
                _cum_no   += days_no * DAILY_DISRUPTION["mid"]
                cum_ad    += days_ad * DAILY_DISRUPTION["mid"]
                savings    = _cum_no - cum_ad
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
                    "scenario": scenario, "variant": variant,
                    "option": opt_id, "option_name": opt["name"],
                    "capex_low_M": opt["capex_low_M"],
                    "capex_high_M": opt["capex_high_M"],
                    "key_year": key_yr,
                    "cum_no_adapt_bn":   round(c_no / 1e9, 4),
                    "cum_adapt_bn":      round(c_ad / 1e9, 4),
                    "savings_bn":        round((c_no - c_ad) / 1e9, 4),
                    "be_year_low_capex": be_low  if be_low  else ">2100",
                    "be_year_mid_capex": be_mid  if be_mid  else ">2100",
                    "be_year_hi_capex":  be_high if be_high else ">2100",
                })

df_adapt = pd.DataFrame(adapt_rows)
csv_adapt = OUT_DIR / "algarve_faro_olhao_adaptation_comparison.csv"
df_adapt.to_csv(csv_adapt, index=False)

print()
print(f"\n  Break-even years (mid disruption cost):")
print()
print(f"  {'Option':<45} {'Scenario':<12} {'Variant':<10} "
      f"{'BE low':>8} {'BE mid':>8} {'BE high':>9}")
print("  " + "-" * 97)
for opt_id in OPTIONS:
    for scenario in ["SSP2-4.5", "SSP5-8.5"]:
        for variant in VARIANTS:
            sub = df_adapt[(df_adapt.option == opt_id) &
                           (df_adapt.scenario == scenario) &
                           (df_adapt.variant  == variant) &
                           (df_adapt.key_year == 2100)]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  {opt_id}. {OPTIONS[opt_id]['name']:<43} "
                  f"{scenario:<12} {variant:<10} "
                  f"{str(r['be_year_low_capex']):>8} "
                  f"{str(r['be_year_mid_capex']):>8} "
                  f"{str(r['be_year_hi_capex']):>9}")
print(f"\n  ▸ Saved: {csv_adapt.name}  ({len(df_adapt)} rows)")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("SECTION SUMMARY — LINHA DO ALGARVE (FARO–OLHÃO)")
print("=" * 68)
print()
print("  Vulnerable section (EU-DEM 25m + OSM relation 349295 verified):")
print("    Faro station → Olhão station (Ria Formosa crossing)")
print("    13.2 km sampled  |  4.9 km at risk (37.1% of section)")
print("    Min elev: 2.341 m MSL  |  Mean (at-risk): 4.125 m MSL")
print(f"  Flood mechanism  : Atlantic surge + lagoonal backing (Ria Formosa)")
print(f"  Baseline RP₀     : {RETURN_PERIOD_BASE:.0f} yr  ⚠ researcher estimate — needs REF-42")
print(f"  Permanent inundation: NOT reached by 2100 (all scenarios)")
print()
print("  Cumulative disruption cost (NO adaptation, mid estimate):")
for scenario in SCENARIOS:
    for variant in VARIANTS:
        cum = sum(closure_days_per_year(slr_for(scenario, variant, y))
                  * DAILY_DISRUPTION["mid"] for y in YEARS)
        print(f"    {scenario:<12} {variant:<10}  →  €{cum/1e9:.4f} bn by 2100")
print()
print("  ★ RP₀ = 20 yr is a researcher estimate based on MHWS + surge")
print("    statistics at Faro. Must be verified against tide gauge records")
print("    and published Ria Formosa flood frequency studies. (REF-42)")
print()
print("  ★ CLOSURE_DAYS_BASE = 3 days is a researcher estimate. No documented")
print("    Algarve line flood closure events found in the literature.")
print("    Must be verified against CP operational records or ANSR reports.")
print()
print("  ★ Option 1 and Option 2 are subject to Natura 2000 AIA permitting.")
print("    The Ria Formosa crossing is a Special Area of Conservation.")
print("    Environmental permitting and mitigation costs are NOT included.")
print()
print(f"  Adaptation capex (EA SC080039/R2, railway geometry 6 m × {_AT_RISK_LEN_M} m):")
print(f"    Opt1a (SSP2-4.5 +{_RAISE_SSP2_M:.3f}m): "
      f"€{_OPT1A_LOW_M:.1f}–{_OPT1A_HIGH_M:.1f} M  "
      f"(vol={_opt1a_vol_m3:,.0f} m³ × €{_embank_eur_m3:.0f}/m³ ±25%)")
print(f"    Opt1b (SSP5-8.5 +{_RAISE_SSP5_M:.3f}m): "
      f"€{_OPT1B_LOW_M:.1f}–{_OPT1B_HIGH_M:.1f} M  "
      f"(vol={_opt1b_vol_m3:,.0f} m³ × €{_embank_eur_m3:.0f}/m³ ±25%)")
print(f"    Opt2 (sheet piling):  "
      f"€{_OPT2_LOW_M:.1f}–{_OPT2_HIGH_M:.1f} M  "
      f"(len={_opt2_len_m:,} m × €{_spile_eur_m:.0f}/m ±25%)")
print(f"    Opt3 (service resil): "
      f"€{_OPT3_LOW_M:.1f}–{_OPT3_HIGH_M:.1f} M  "
      f"(€{_RESILIENCE_EUR_KM//1000}k/km × {_AT_RISK_LEN_M//1000:.1f} km ±30%)")
print()
print(f"  Outputs: {OUT_DIR}")
print(f"    {csv_freq.name}   ({len(df_freq)} rows)")
print(f"    {csv_disrupt.name}  ({len(df_disrupt)} rows)")
print(f"    {csv_adapt.name}  ({len(df_adapt)} rows)")
print()
print("  Sources: REF-01 (IPCC AR6), REF-02 (Seeger & Minderhoud 2026),")
print("           REF-03 (Moftakhari 2017), REF-20 (OSM relation 349295),")
print("           REF-40 ⚠ (CP 2023), REF-41 ⚠ (EU Handbook VOT),")
print("           REF-42 ⚠ (Ria Formosa flood frequency — TO BE CONFIRMED).")
