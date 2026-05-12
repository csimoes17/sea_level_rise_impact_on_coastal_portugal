"""
11c_a1_motorway.py  –  Pillar 3: A1 Motorway (Lezíria do Tejo Section)
========================================================================
Analyses sea-level rise (SLR) disruption risk to Portugal's primary
north–south motorway (A1 / E80) where it crosses the Tagus alluvial
floodplain near Azambuja (Aveiras de Baixo area).

GEOGRAPHIC SCOPE — VERIFIED FROM DEM + OSM DATA
-------------------------------------------------
A DEM analysis of actual A1 road geometry (OSM node coordinates sampled
against the Copernicus GLO-30 DEM) identified the following vulnerable
sections (Stage 1 output — see Decision D15):

  Section 1 (main): 38.955°N → 39.027°N  |  ~8.0 km  |  2.4–4.9 m MSL
    → Aveiras de Baixo / Azambuja area, approximately A1 km 45–55
       from Lisbon (IC17 junction)
    → Absolute lowest point on the A1 in this corridor: 2.4 m MSL

  Section 2 (secondary): 39.042°N → 39.071°N  |  ~3.2 km  |  3.4–5.0 m
    → North of Azambuja, before road climbs back into limestone hills

  Section 3 (minor): 39.242°N → 39.243°N  |  ~0.1 km  |  4.4–4.7 m
    → Near Santarém interchange, brief flat crossing

  Combined low-elevation zone: approximately 12 km total across two
  main sections. Earlier estimate of "~35 km" was the distance between
  landmark towns, not the actual road surface length below 5 m MSL.

  NOTE: The ROAD_ELEV_M parameter (2.50 m) represents the carriageway
  CROWN elevation on the embankment. The DEM minimum of 2.4 m reflects
  the surrounding terrain at 30 m resolution; the road surface on a
  built embankment crown is consistent with the 2.50 m parameter used.

TWO-STAGE ANALYTICAL ARCHITECTURE
-----------------------------------
Stage 1 (Spatial — Pillars 1 & 2 + geographic verification):
  Copernicus GLO-30 DEM raster analysis identified this corridor as a
  zone of SLR exposure. OSM road geometry (portugal-251031.osm.pbf)
  was parsed to extract precise A1 node coordinates (ref='A 1',
  highway=motorway), which were then sampled against the DEM to
  determine the true extent and elevation of the vulnerable section.
  This corrected the initial estimate of 35 km to ~8–12 km. (D15)

Stage 2 (Parametric — this script): Applies the Moftakhari et al. (2017)
  compound flood model using parameters derived from Stage 1 outputs and
  the published literature. Parameters are hardcoded (not read from
  files) because they represent the researcher's calibrated transfer
  from spatial evidence to the parametric disruption model. (D14)

SECTION CHARACTERISTICS
-----------------------
Location   : A1 motorway, Aveiras de Baixo / Azambuja corridor
             (~km 45–55 from Lisbon, sections 1+2 above)
Mechanism  : Compound estuarine/fluvial — Tagus storm-surge backwater
             combined with high-flow Tagus river levels (same as 10b,
             Tagus railway, which parallels the A1 through this plain).
Elevation  : 2.50 m MSL at road carriageway crown (embankment).
             DEM minimum: 2.4 m (surrounding terrain at 30 m resolution).
Traffic    : ~40,000 TMDA (Tráfego Médio Diário Anual), 8% HGV —
             primary Lisbon–Porto freight corridor.
             Sources: IMT / ANSR 2022 road statistics (REF-28);
             INE May 2025 national traffic report (REF-29);
             Brisa Concessão 2024 annual report (REF-30).
Alternative: Emergency diversion via IC3/EN1 adds ~40 km and
             ~50 min per trip; manageable for passengers but
             problematic for sustained HGV volumes over closures.

CRITICAL THRESHOLD
------------------
Permanent inundation requires SLR ≥ 2.50 m — NOT reached by 2100 under
any IPCC AR6 scenario (max SSP5-8.5 + geoid = 1.15 m). Risk is purely
OPERATIONAL (increased flood frequency and closure duration), not
existential.

MODEL PARAMETERS
----------------
ROAD_ELEV_M         = 2.50   # m MSL — carriageway crown (embankment)
RETURN_PERIOD_BASE  = 20 yr  # RP₀ under present SLR conditions
                              # Higher than Tagus rail (10b, RP₀=10):
                              # road embankment 0.5 m higher + better
                              # drainage standard than railway
CLOSURE_DAYS_BASE   = 2.5    # days per event — shorter than rail
                              # (flexible traffic management, no
                              # signalling reset, contraflow possible)
DAILY_DISRUPTION    : low=€0.80M / mid=€1.40M / high=€2.30M per day
                              #
                              # ── VALUE-OF-TIME (VOT) DERIVATION ──────────
                              # TMDA      = 40,000 veh/day  (REF-28)
                              # HGV       = 8%  →  3,200 HGV/day
                              #             (REF-29 INE May 2025; REF-30 Brisa 2024)
                              # Passenger = 92% → 36,800 cars/day
                              #             avg 1.6 occ → 58,880 person-trips
                              # Detour    : IC3 / EN1, +40 km, +50 min (0.83 h)
                              #
                              # Component                          €k/day
                              # ──────────────────────────────────────────
                              # Passenger delay
                              #   58,880 × 0.83h × €8.13/h VOT*      397
                              # HGV time cost
                              #   3,200  × 0.83h × €35/h               93
                              # Extra fuel — cars
                              #   36,800 × 40 km × €0.07/km           103
                              # Extra fuel — HGVs
                              #   3,200  × 40 km × €0.45/km            58
                              # Fixed direct subtotal                  651
                              # * EU Handbook on External Costs
                              #   (PT short-run VOT 2021)
                              #
                              # Cargo disruption (Tagus corridor
                              # ~€200M/day freight GDP exposure):
                              #   Low : 0 %  →   €0k (conservative)
                              #   Mid : 0.20% →  €400k
                              #   High: 0.40% →  €800k
                              #
                              # Indirect system multiplier
                              # (Anas & Hiramatsu 2013 IO-model):
                              #   Low=1.20  /  Mid=1.35  /  High=1.60
                              #
                              # DERIVED VALUES (researcher-calibrated
                              # inputs for parametric disruption model):
                              #   Low : (651+   0)×1.20 = €781k → €0.80M
                              #   Mid : (651+ 400)×1.35 = €1,419k → €1.40M
                              #   High: (651+ 800)×1.60 = €2,322k → €2.30M

ADAPTATION OPTIONS (raise heights from raise_requirements.csv)
--------------------------------------------------------------
Required raise: SSP2-4.5 = +0.98 m (road embankment, <1.00 m threshold)
                SSP5-8.5 = +1.37 m (elevated road on reinforced structure — design)
Prior +0.50 m raise (EA SC080039/R2 minimum intervention) now superseded.

Option 1 | Elevated road / reinforced embankment (scenario-specific raise height)
          Unit cost: €15–25 M/km (±35%) — European elevated road benchmark.
          SSP2-4.5 lower bound: +0.98 m → reinforced embankment or elevated road.
          SSP5-8.5 design:      +1.37 m → elevated road on reinforced structure.
          Cost for both: €15–25 M/km × 12 km = €180–300 M (unit cost same for
          both scenarios at 12 km; structural depth differs, captured by ±35% band).
          Raises effective carriageway above all SLR scenarios to 2100.
          Type: frequency reducer (eliminates structural flood vulnerability).

Option 2 | Perimeter flood barriers + smart drainage
          Cost: computed from UK EA SC080039/R2, Table 1.7
          (permanent steel sheet piling £1,843/m, 2015 GBP,
          adjusted × 1.13 × 1.17). Both shoulders, full section length
          (2 × 12,000 m). Sluice/pump installation absorbed in ±25% band.
          Complementary to 10b Option 2 — a single Lezíria corridor
          programme protects BOTH the A1 and Linha do Norte railway.
          Type: frequency reducer (intercepts inundation).

Option 3 | Dynamic traffic management protocol (duration reducer)
          Cost: parametric — €500k/km European ITS/VMS deployment
          benchmark, ±30 % uncertainty, over 12 km section.
          Reduces mean closure duration by 50% (2.5 → 1.25 days).
          Does NOT reduce flood frequency — hydrology unchanged.
          Type: duration reducer only.

OUTPUTS
-------
a1_flood_frequency.csv        — 24 rows
a1_disruption_cost.csv        — 1,368 rows
a1_adaptation_comparison.csv  — 72 rows

REFERENCES
----------
REF-01 : Fox-Kemper et al. (2021) IPCC AR6 WG1 Ch.9 — SLR scenarios
REF-02 : Seeger & Minderhoud (2026) Nature 652, 667–674 — geoid offset +0.15 m EU Atlantic coast
REF-03 : Moftakhari et al. (2017) PNAS — compound flood model
REF-05 : Guerreiro, M., Fortunato, A. B., et al. (2015) RGCI 15(1), 65–80 — Tagus estuary hydrodynamics and SLR
REF-06 : Trigo et al. (2016) J. Hydrology 541, 597–610 — Tagus flood climatology
REF-28 : IMT / ANSR (2022) Portuguese road traffic statistics — A1 TMDA 40,572 at km 45–55
REF-29 : INE (May 2025) Transportes e Comunicações — national HGV share motorways 8 %
REF-30 : Brisa Concessão (2024) Annual Report — network-average HGV share 8 %
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

_RAISE = _read_raise("a1_tagus")
# SSP2-4.5 = +0.98 m → Road embankment raising (< 1.00 m threshold)
# SSP5-8.5 = +1.37 m → Elevated road on reinforced structure  [design/headline]

# ── SLR SCENARIOS (IPCC AR6 WG1 Ch.9 — REF-01) ───────────────────────────────
SLR_BASE = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2040: 0.13, 2050: 0.20,
                 2060: 0.24, 2070: 0.28, 2080: 0.32, 2090: 0.36, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2040: 0.20, 2050: 0.30,
                 2060: 0.36, 2070: 0.42, 2080: 0.48, 2090: 0.54, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2040: 0.27, 2050: 0.40,
                 2060: 0.52, 2070: 0.64, 2080: 0.76, 2090: 0.88, 2100: 1.00},
}
GEOID_OFFSET = 0.15    # Seeger & Minderhoud (2026) Nature 652, 667–674 — REF-02

SCENARIOS = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
VARIANTS  = ["baseline", "+geoid"]
YEARS     = list(range(2025, 2101))
KEY_YEARS = [2030, 2050, 2075, 2100]

# ── SECTION PARAMETERS (derived from Stage 1 DEM + OSM analysis) ─────────────
ROAD_ELEV_M         = 2.50    # m MSL — carriageway crown, Azambuja section
                               # DEM minimum 2.4 m (30 m terrain); crown = 2.5 m
RETURN_PERIOD_BASE  = 20.0    # yr — RP₀ under present SLR
CLOSURE_DAYS_BASE   = 2.50    # days per closure event
SENSITIVITY_K       = np.log(2) / 0.10   # ≈ 6.931 — Moftakhari 2017 REF-03

# ── DAILY DISRUPTION COST — VOT COMPUTATION ──────────────────────────────────
# All inputs are researcher-defined constants from cited sources.
# DAILY_DISRUPTION is computed by this script from those inputs.
#
# TRAFFIC INPUTS
# [IMT / ANSR 2022 (REF-28); INE May 2025 (REF-29); Brisa 2024 (REF-30)]
_TMDA             = 40_000      # vehicles/day — A1 TMDA at Azambuja section
_HGV_SHARE        = 0.08        # fraction — national motorway average
_CAR_OCCUPANCY    = 1.6         # persons/car (Portuguese average)
_DETOUR_KM        = 40.0        # km  — IC3/EN1 extra distance per vehicle
_DETOUR_H         = 50.0 / 60   # h   — 50 min extra travel time

# UNIT VALUE-OF-TIME RATES
# [EU Handbook on External Costs, Portuguese short-run VOT 2021]
_VOT_PASS_EUR_H   = 8.13        # €/h — passenger value of time
_VOT_HGV_EUR_H    = 35.00       # €/h — HGV driver/logistics value of time

# MARGINAL FUEL COSTS (incremental cost of detour km only)
_FUEL_CAR_EUR_KM  = 0.07        # €/km — marginal fuel, passenger car
_FUEL_HGV_EUR_KM  = 0.45        # €/km — marginal fuel, HGV

# FREIGHT CORRIDOR GDP EXPOSURE
# [researcher estimate — Tagus industrial corridor, consistent with
#  NUTS II Lisboa/Alentejo freight flows; REF-22 (INE regional GDP)]
_FREIGHT_GDP_D    = 200e6       # €/day — freight GDP at risk in corridor

# CARGO DISRUPTION RATE by tier (fraction of freight GDP disrupted per closure)
# Low: conservative (no cargo delay premium assumed; passengers only)
# Mid: 0.2% of corridor freight GDP — moderate supply-chain disruption
# High: 0.4% of corridor freight GDP — extended closure, multi-sector
_CARGO_RATE = {"low": 0.000, "mid": 0.002, "high": 0.004}

# INDIRECT SYSTEM MULTIPLIER by tier
# [Input-Output model, Anas & Hiramatsu 2013]
_INDIRECT_MULT = {"low": 1.20, "mid": 1.35, "high": 1.60}

# ── VOT COMPUTATION ───────────────────────────────────────────────────────────
_hgv_d          = _TMDA * _HGV_SHARE
_car_d          = _TMDA * (1 - _HGV_SHARE)
_persons_d      = _car_d * _CAR_OCCUPANCY

_delay_pass     = _persons_d * _DETOUR_H * _VOT_PASS_EUR_H
_delay_hgv      = _hgv_d    * _DETOUR_H * _VOT_HGV_EUR_H
_fuel_car       = _car_d    * _DETOUR_KM * _FUEL_CAR_EUR_KM
_fuel_hgv       = _hgv_d    * _DETOUR_KM * _FUEL_HGV_EUR_KM
_direct_fixed   = _delay_pass + _delay_hgv + _fuel_car + _fuel_hgv

DAILY_DISRUPTION = {
    t: (_direct_fixed + _CARGO_RATE[t] * _FREIGHT_GDP_D) * _INDIRECT_MULT[t]
    for t in ("low", "mid", "high")
}

# ── ADAPTATION CAPEX ──────────────────────────────────────────────────────────
# Section geometry (from Stage 1 DEM + OSM analysis, Decision D15)
_SECTION_LEN_M  = 12_000   # m  — combined vulnerable length (sections 1+2)
_SECTION_LEN_KM = _SECTION_LEN_M / 1_000   # 12 km
_PAVE_WIDTH_M   = 26.0     # m  — A1 full carriageway (2+2 lanes + shoulders)

# Raise heights from raise_requirements.csv
_RAISE_SSP2_M  = _RAISE["SSP2-4.5"]   # 0.98 m — road embankment raising
_RAISE_SSP5_M  = _RAISE["SSP5-8.5"]   # 1.37 m — elevated road on reinforced structure
_METHOD_DESIGN = _RAISE["method"]      # "Elevated road on reinforced structure"

# Option 1: Elevated road / reinforced embankment
# Both SLR scenarios use the same elevated road unit cost range (€15-25M/km ±35%).
# The cost difference between scenarios is captured within the uncertainty band
# (SSP2-4.5 at +0.98m may use reinforced embankment; SSP5-8.5 at +1.37m requires
# full elevated road deck — both yield €180-300M for 12km at this unit cost range).
_ELEV_ROAD_EUR_KM_LOW  = 15_000_000   # €/km — lower bound, reinforced embankment
_ELEV_ROAD_EUR_KM_HIGH = 25_000_000   # €/km — upper bound, full elevated deck ±35%
_OPT1_SSP2_LOW_M  = round(_ELEV_ROAD_EUR_KM_LOW  * _SECTION_LEN_KM / 1e6, 0)
_OPT1_SSP2_HIGH_M = round(_ELEV_ROAD_EUR_KM_HIGH * _SECTION_LEN_KM / 1e6, 0)
_OPT1_SSP5_LOW_M  = _OPT1_SSP2_LOW_M   # same unit cost, same length
_OPT1_SSP5_HIGH_M = _OPT1_SSP2_HIGH_M

# Option 2: sheet-pile perimeter barriers — both shoulders, full section
# EA SC080039/R2, Table 1.7: £1,843/m × 1.13 × 1.17 ≈ €2,436/m
_EA_SHEETPILE_GBP2015 = 1843.0
_spile_eur_m    = _EA_SHEETPILE_GBP2015 * 1.13 * 1.17  # ≈ €2,436/m
_opt2_len_m     = 2 * _SECTION_LEN_M
_opt2_mid_M     = _opt2_len_m * _spile_eur_m / 1e6
_OPT2_LOW_M     = round(_opt2_mid_M * 0.75, 1)
_OPT2_HIGH_M    = round(_opt2_mid_M * 1.25, 1)

# Option 3: ITS/VMS dynamic traffic management — parametric €/km
_ITS_EUR_PER_KM = 500_000   # €/km — A1-class motorway ITS/VMS systems
_opt3_mid_M     = _ITS_EUR_PER_KM * _SECTION_LEN_KM / 1e6
_OPT3_LOW_M     = round(_opt3_mid_M * 0.70, 1)
_OPT3_HIGH_M    = round(_opt3_mid_M * 1.30, 1)

# ── ADAPTATION OPTIONS ────────────────────────────────────────────────────────
# Option 1 has two sub-scenarios reflecting the SLR design range.
# Both use elevated road unit costs; structural depth differs (captured in ±35% band).
OPTIONS = {
    "1a": {"name": f"Elevated road — SSP2-4.5 lower bound (+{_RAISE_SSP2_M:.2f} m)",
           "capex_low_M": _OPT1_SSP2_LOW_M, "capex_high_M": _OPT1_SSP2_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    "1b": {"name": f"Elevated road — SSP5-8.5 design (+{_RAISE_SSP5_M:.2f} m)",
           "capex_low_M": _OPT1_SSP5_LOW_M, "capex_high_M": _OPT1_SSP5_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    2:    {"name": "Perimeter barriers + smart drainage",
           "capex_low_M": _OPT2_LOW_M, "capex_high_M": _OPT2_HIGH_M,
           "type": "frequency", "freq_multiplier": 1.8, "dur_multiplier": 1.0},
    3:    {"name": "Dynamic traffic management protocol",
           "capex_low_M": _OPT3_LOW_M,  "capex_high_M": _OPT3_HIGH_M,
           "type": "duration",  "freq_multiplier": 1.0, "dur_multiplier": 0.50},
}

# ── PRINT VOT COMPUTATION AUDIT ──────────────────────────────────────────────
# Printed at runtime so the derivation is visible and traceable.
def _print_vot_audit() -> None:
    print("── VOT COMPUTATION (A1 — Azambuja / Aveiras de Baixo) ────────────────")
    print(f"  TMDA = {_TMDA:,}  |  HGV = {_HGV_SHARE*100:.0f}%  |  "
          f"Detour +{_DETOUR_KM:.0f} km / +{_DETOUR_H*60:.0f} min")
    print(f"  Vehicles: {_hgv_d:,.0f} HGV/day, {_car_d:,.0f} cars/day "
          f"({_persons_d:,.0f} person-trips)")
    print(f"  Delay — passengers : €{_delay_pass/1e3:,.1f}k/day")
    print(f"  Delay — HGV        : €{_delay_hgv/1e3:,.1f}k/day")
    print(f"  Extra fuel — cars  : €{_fuel_car/1e3:,.1f}k/day")
    print(f"  Extra fuel — HGVs  : €{_fuel_hgv/1e3:,.1f}k/day")
    print(f"  Fixed direct total : €{_direct_fixed/1e3:,.1f}k/day")
    print(f"  Freight GDP exposure: €{_FREIGHT_GDP_D/1e6:.0f}M/day (Tagus corridor)")
    print()
    for t in ("low", "mid", "high"):
        cargo = _CARGO_RATE[t] * _FREIGHT_GDP_D
        total_direct = _direct_fixed + cargo
        print(f"  [{t:4s}]  cargo {_CARGO_RATE[t]*100:.2f}% = €{cargo/1e3:,.1f}k  |  "
              f"direct €{total_direct/1e3:,.1f}k  ×  {_INDIRECT_MULT[t]:.2f}  "
              f"=  €{DAILY_DISRUPTION[t]/1e6:.3f}M/day")
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
print("A1 MOTORWAY — AVEIRAS DE BAIXO / AZAMBUJA SECTION")
print("Pillar 3: Sea-Level Rise Network Disruption Analysis")
print("=" * 68)
print()
print("  Geographic scope (verified DEM + OSM, Decision D15):")
print("  Section 1: 38.955–39.027°N | ~8.0 km | 2.4–4.9 m MSL")
print("  Section 2: 39.042–39.071°N | ~3.2 km | 3.4–5.0 m MSL")
print("  Combined vulnerable length: ~12 km  (NOT 35 km — corrected)")
print("  Lowest point on carriageway: 2.4 m (DEM terrain); crown ~2.50 m")
print()
print(f"  Required raises (raise_requirements.csv — 00_raise_requirements.py):")
print(f"    SSP2-4.5 : +{_RAISE_SSP2_M:.2f} m  → Road embankment raising (< 1.00 m threshold)")
print(f"    SSP5-8.5 : +{_RAISE_SSP5_M:.2f} m  → {_METHOD_DESIGN}  [design/headline]")
print(f"    Prior +0.50 m raise (EA SC080039/R2 minimum) is now superseded.")
print(f"    Elevated road unit cost: €{_ELEV_ROAD_EUR_KM_LOW//1e6:.0f}–{_ELEV_ROAD_EUR_KM_HIGH//1e6:.0f}M/km × {_SECTION_LEN_KM:.0f}km = "
      f"€{_OPT1_SSP5_LOW_M:.0f}–{_OPT1_SSP5_HIGH_M:.0f}M (±35%)")
print()
print(f"── LAYER A: FLOOD FREQUENCY ──────────────────────────────────────────")
print(f"  Road elevation (carriageway crown): {ROAD_ELEV_M:.2f} m MSL")
print(f"  Baseline return period (RP₀):       {RETURN_PERIOD_BASE:.0f} yr")
print(f"  Closure days per event:             {CLOSURE_DAYS_BASE:.1f} days")
print(f"  Sensitivity k:                      {SENSITIVITY_K:.3f}  [Moftakhari 2017]")
print(f"  Geoid correction:                   +{GEOID_OFFSET:.2f} m  [REF-02 ⚠]")
print(f"  Max SLR+geoid by 2100 (SSP5-8.5):  {1.00 + GEOID_OFFSET:.2f} m")
print(f"  Road elevation threshold:           {ROAD_ELEV_M:.2f} m")
print(f"  ▸ Permanent inundation by 2100:     NO (margin = "
      f"{ROAD_ELEV_M - (1.00 + GEOID_OFFSET):.2f} m)")

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
csv_freq = OUT_DIR / "a1_flood_frequency.csv"
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
                    "annual_cost_low_M": round(days * DAILY_DISRUPTION["low"]  / 1e6, 4),
                    "annual_cost_mid_M": round(days * DAILY_DISRUPTION["mid"]  / 1e6, 4),
                    "annual_cost_hi_M":  round(days * DAILY_DISRUPTION["high"] / 1e6, 4),
                    "cum_cost_low_bn":  round(cumulative["low"]  / 1e9, 4),
                    "cum_cost_mid_bn":  round(cumulative["mid"]  / 1e9, 4),
                    "cum_cost_hi_bn":   round(cumulative["high"] / 1e9, 4),
                })

df_disrupt = pd.DataFrame(disrupt_rows)
csv_disrupt = OUT_DIR / "a1_disruption_cost.csv"
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
                      f"{cum['low']/1e9:>18.3f} "
                      f"{cum['mid']/1e9:>10.3f} "
                      f"{cum['high']/1e9:>10.3f}")
print(f"\n  ▸ Saved: {csv_disrupt.name}  ({len(df_disrupt)} rows)")


# ── LAYER C: ADAPTATION BREAK-EVEN ───────────────────────────────────────────
print("\n── LAYER C: ADAPTATION BREAK-EVEN ANALYSIS ───────────────────────────")
print()
for opt_id, opt in OPTIONS.items():
    print(f"  {opt_id}. {opt['name']:<38} "
          f"€{opt['capex_low_M']:.0f}–{opt['capex_high_M']:.0f} M  "
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
                    "cum_no_adapt_bn": round(c_no / 1e9, 4),
                    "cum_adapt_bn":    round(c_ad / 1e9, 4),
                    "savings_bn":      round((c_no - c_ad) / 1e9, 4),
                    "be_year_low_capex": be_low  if be_low  else ">2100",
                    "be_year_mid_capex": be_mid  if be_mid  else ">2100",
                    "be_year_hi_capex":  be_high if be_high else ">2100",
                })

df_adapt = pd.DataFrame(adapt_rows)
csv_adapt = OUT_DIR / "a1_adaptation_comparison.csv"
df_adapt.to_csv(csv_adapt, index=False)

print()
print(f"\n  Break-even years (mid disruption cost):")
print()
print(f"  {'Option':<38} {'Scenario':<12} {'Variant':<10} "
      f"{'BE low':>8} {'BE mid':>8} {'BE high':>9}")
print("  " + "-" * 90)
for opt_id in OPTIONS:
    for scenario in ["SSP2-4.5", "SSP5-8.5"]:
        for variant in VARIANTS:
            sub = df_adapt[(df_adapt.option == opt_id) &
                           (df_adapt.scenario == scenario) &
                           (df_adapt.variant  == variant) &
                           (df_adapt.key_year == 2100)]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  {opt_id}. {OPTIONS[opt_id]['name']:<36} "
                  f"{scenario:<12} {variant:<10} "
                  f"{str(r['be_year_low_capex']):>8} "
                  f"{str(r['be_year_mid_capex']):>8} "
                  f"{str(r['be_year_hi_capex']):>9}")
print(f"\n  ▸ Saved: {csv_adapt.name}  ({len(df_adapt)} rows)")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("SECTION SUMMARY — A1 MOTORWAY (AVEIRAS DE BAIXO / AZAMBUJA)")
print("=" * 68)
print()
print("  Vulnerable section (DEM + OSM verified, Decision D15):")
print("    Section 1: 38.955–39.027°N, ~8.0 km, 2.4–4.9 m MSL")
print("    Section 2: 39.042–39.071°N, ~3.2 km, 3.4–5.0 m MSL")
print("    Total: ~12 km  |  Lowest carriageway point: 2.4 m (DEM terrain)")
print(f"  Compound flood mechanism   : Tagus estuarine/fluvial backwater")
print(f"  Baseline return period     : {RETURN_PERIOD_BASE:.0f} yr")
print(f"  Permanent inundation       : NOT reached by 2100 (all scenarios)")
print()
print("  Cumulative disruption cost (NO adaptation, mid estimate):")
for scenario in SCENARIOS:
    for variant in VARIANTS:
        cum = sum(closure_days_per_year(slr_for(scenario, variant, y))
                  * DAILY_DISRUPTION["mid"] for y in YEARS)
        print(f"    {scenario:<12} {variant:<10}  →  €{cum/1e9:.3f} bn by 2100")
print()
print("  ★ Revised section length: ~12 km (not 35 km as initially stated).")
print("    The A1 runs through limestone hills for most of the Carregado–")
print("    Santarém corridor; only the Aveiras/Azambuja stretch descends")
print("    to floodplain level. See Decision D15.")
print()
print("  ★ Option 1 now correctly costed at elevated road unit costs")
print(f"    (€{_ELEV_ROAD_EUR_KM_LOW//1e6:.0f}–{_ELEV_ROAD_EUR_KM_HIGH//1e6:.0f}M/km × {_SECTION_LEN_KM:.0f}km = "
      f"€{_OPT1_SSP5_LOW_M:.0f}–{_OPT1_SSP5_HIGH_M:.0f}M). Prior +0.50m embankment estimate superseded.")
print(f"    SSP2-4.5 (+{_RAISE_SSP2_M:.2f}m): road embankment / elevated road — €{_OPT1_SSP2_LOW_M:.0f}–{_OPT1_SSP2_HIGH_M:.0f}M")
print(f"    SSP5-8.5 (+{_RAISE_SSP5_M:.2f}m): elevated road on structure   — €{_OPT1_SSP5_LOW_M:.0f}–{_OPT1_SSP5_HIGH_M:.0f}M")
print()
print("  ★ Option 2 + Tagus railway Option 2 (10b) are complementary:")
print("    A1 and Linha do Norte run in near-parallel through this plain.")
print("    A single Lezíria corridor flood-barrier programme protects")
print("    BOTH assets at shared programme cost — key Ch.5 finding.")
print()
print("  ★ Option 3 breaks even earliest but is a duration reducer only.")
print("    Recommended as interim measure pending structural investment.")
print()
print(f"  Outputs: {OUT_DIR}")
print(f"    {csv_freq.name}   ({len(df_freq)} rows)")
print(f"    {csv_disrupt.name}  ({len(df_disrupt)} rows)")
print(f"    {csv_adapt.name}  ({len(df_adapt)} rows)")
print()
print("  Sources: REF-01 (IPCC AR6), REF-02 (Seeger & Minderhoud 2026), REF-03 (Moftakhari),")
print("           REF-05 (Guerreiro et al. 2015), REF-06 (Trigo et al. 2016), REF-28 (IMT ⚠).")
