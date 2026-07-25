"""
11d_a14_mondego.py  –  Pillar 3: A14 / IP3 Motorway (Mondego Lezíria Section)
===============================================================================
Analyses sea-level rise (SLR) disruption risk to the A14 / IP3 motorway
where it crosses the Mondego alluvial floodplain (lezíria) between the
A17/IP3 junction near Maiorca and the plain east of the Mondego bridge.

GEOGRAPHIC SCOPE — VERIFIED FROM EU-DEM + OSM DATA
----------------------------------------------------
A DEM analysis of actual A14/IP3 road geometry (OSM way geometry sampled
against the EU-DEM 25m, EGM2008) identified the following vulnerable
section (Stage 1 output — see elev_a14_mondego_plain.py):

  Section    : A14/IP3 Mondego lezíria crossing
  West end   : A17/IP3 junction near Maiorca   lat=40.145  lon=-8.750
  East end   : East of Mondego bridge          lat=40.172  lon=-8.720
  Bbox used  : S=40.138, W=-8.758, N=40.178, E=-8.712
  OSM source : relation/7301317  (ref='A 14;IP 3')

  Sample points    : 438 (at 25 m intervals, post-bbox clip)
  Road length est. : ~11 km
  Minimum elev.    : 1.63 m MSL  (lat=40.170696, lon=-8.722700)
  Mean elev.       : 8.78 m MSL  (section includes elevated approaches)
  Points < 5 m     : 237 / 438  (54.1% of section)

  NOTE: ROAD_ELEV_M (2.38 m) represents the carriageway CROWN on the
  embankment. EU-DEM credible minimum is 1.63 m (terrain floor at 25 m
  resolution); the road crown on the embankment = 1.63 + 0.75 m = 2.38 m.

TWO-STAGE ANALYTICAL ARCHITECTURE
-----------------------------------
Stage 1 (Spatial — Pillars 1 & 2 + geographic verification):
  EU-DEM 25m (EGM2008) sampled against OSM A14/IP3 way geometry inside
  a tight geographic bbox. Direct way query (no route relation — globally
  duplicated ref numbers make relation queries unreliable for roads).
  438 sample points extracted post-bbox clip; lowest credible point
  1.63 m MSL, road crown ~2.38 m. (see elev_a14_mondego_plain.py)

Stage 2 (Parametric — this script): Applies the Moftakhari et al. (2017)
  compound flood model using parameters derived from Stage 1 outputs and
  published literature. Parameters are hardcoded (not read from files)
  because they represent the researcher's calibrated transfer from spatial
  evidence to the parametric disruption model. (D14)

SECTION CHARACTERISTICS
-----------------------
Location   : A14/IP3 motorway, Mondego lezíria crossing
             A17/IP3 junction (Maiorca) → east of Mondego bridge
             Ereira/Maiorca corridor, Figueira da Foz municipality
Mechanism  : Compound fluvial + SLR — Mondego River peak flows
             combined with rising sea levels reducing the river's
             tidal drainage capacity at the estuary mouth.
             Same mechanism as the Mondego railway bypass (10a).
Elevation  : 2.38 m MSL at road carriageway crown (embankment).
             EU-DEM credible minimum: 1.63 m (terrain floor, 25 m res.).
             A14 crown (~2.38 m) < Mondego railway (~4.1 m):
             A14 is lower and floods first in the same corridor.
Traffic    : ~11,000 TMDA (Tráfego Médio Diário Anual), 8% HGV —
             regional connector linking A17 (Aveiro / Figueira da Foz
             coast) with the A1 / Coimbra axis.
             Sources: IMT regional traffic counts (REF-25);
             INE May 2025 national traffic report (REF-29);
             Brisa Concessão 2024 annual report (REF-30).
Alternative: Diversion via EN111 / A17 north adds ~25 km and
             ~35 min per trip; manageable for passengers but
             problematic for HGV volumes over extended closures.
Events     : Documented Mondego lezíria flood events affecting road
             and rail infrastructure: 2019, 2021, February 2026.
             2026 event: A14 closed Maiorca–Montemor-o-Velho for
             36 days total (flood phase ~4 days; remainder road
             inspection and safety certification prior to reopening).
             This is the exact study section. (REF-24, REF-31, REF-32)

CRITICAL THRESHOLD
------------------
Permanent inundation requires SLR ≥ 2.38 m — NOT reached by 2100 under
any IPCC AR6 scenario (max SSP5-8.5 + geoid = 1.15 m). Risk is purely
OPERATIONAL (increased flood frequency and closure duration), not
existential.

MODEL PARAMETERS
----------------
ROAD_ELEV_M         = 2.38   # m MSL — carriageway crown (embankment)
RETURN_PERIOD_BASE  = 5 yr   # RP₀ under present conditions:
                              #  • Crown at 2.38 m — lowest of all
                              #    road sections studied
                              #  • Mondego documented events: 2019,
                              #    2021, 2026 (high-frequency system)
                              #  • More frequent than A1 (20 yr,
                              #    2.50 m, Tagus) and Tagus railway
                              #    (10 yr); A14 crown is 0.12 m lower
                              #    than A1 and Mondego floods faster
                              #  • Conservative relative to raw event
                              #    frequency (not all Mondego floods
                              #    close the A14)
CLOSURE_DAYS_BASE   = 4.0    # days per event — empirically grounded
                              #  in the February 2026 A14 closure
                              #  (Maiorca–Montemor-o-Velho, this study
                              #  section). Total closure 36 days; the
                              #  physical flood/drainage phase lasting
                              #  ~4 days for the peak-flow event. The
                              #  remaining 32 days reflect structural
                              #  inspection and safety certification
                              #  prior to reopening — not modelled as
                              #  recurrent operational closure. 4 days
                              #  is therefore conservative relative to
                              #  the 2026 centennial event, and
                              #  consistent with the 2001 Mondego event
                              #  (TR=439yr, "several days" of closure).
                              #  Sources: REF-24 (ANEPC), REF-31, REF-32.
DAILY_DISRUPTION    : low=€0.18M / mid=€0.31M / high=€0.55M per day
                              #
                              # ── VALUE-OF-TIME (VOT) DERIVATION ──────────
                              # TMDA      = 11,000 veh/day  (REF-25)
                              # HGV       = 8%  →  880 HGV/day
                              #             (REF-29 INE May 2025; REF-30 Brisa 2024)
                              # Passenger = 92% → 10,120 cars/day
                              #             avg 1.6 occ → 16,192 person-trips
                              # Detour    : EN111 / A17 north, +25 km, +35 min (0.58 h)
                              #
                              # Component                          €k/day
                              # ──────────────────────────────────────────
                              # Passenger delay
                              #   16,192 × 0.58h × €8.13/h VOT*       76
                              # HGV time cost
                              #      880 × 0.58h × €35/h               18
                              # Extra fuel — cars
                              #   10,120 × 25 km × €0.07/km            18
                              # Extra fuel — HGVs
                              #      880 × 25 km × €0.45/km            10
                              # Fixed direct subtotal                  122
                              # * EU Handbook on External Costs
                              #   (PT short-run VOT 2021)
                              #
                              # Cargo disruption (Mondego corridor
                              # ~€20M/day freight GDP exposure):
                              #   Low : 0.14% →  €28k
                              #   Mid : 0.55% → €110k
                              #   High: 1.10% → €222k
                              #
                              # Indirect system multiplier
                              # (Anas & Hiramatsu 2013 IO-model):
                              #   Low=1.20  /  Mid=1.35  /  High=1.60
                              #
                              # DERIVED VALUES (researcher-calibrated
                              # inputs for parametric disruption model):
                              #   Low : (122+  28)×1.20 = €180k → €0.18M
                              #   Mid : (122+ 110)×1.35 = €313k → €0.31M
                              #   High: (122+ 222)×1.60 = €550k → €0.55M

ADAPTATION OPTIONS (raise heights from raise_requirements.csv)
--------------------------------------------------------------
Required raise: SSP2-4.5 = +1.75 m (elevated road on reinforced structure)
                SSP5-8.5 = +2.14 m (full structural reconstruction — design)
Prior +0.50 m raise (EA SC080039/R2 minimum) massively underestimates the
required intervention. All SLR scenarios require structural-scale investment.

Option 1 | Structural road reconstruction (scenario-specific raise height)
          SSP2-4.5 lower bound (+1.75 m): elevated road on reinforced structure.
            Unit cost: €15–25 M/km × 11 km = €165–275 M (±35%).
          SSP5-8.5 design (+2.14 m): full structural reconstruction.
            Unit cost: €25–40 M/km × 11 km = €275–440 M (±35%).
          Prior estimate (+0.50 m embankment, EA SC080039/R2) superseded.
          Type: frequency reducer (raises carriageway above all flood levels).

Option 2 | Embankment flood protection + drainage improvement
          Cost: computed from UK EA SC080039/R2, Table 1.7
          (permanent steel sheet piling £1,843/m, 2015 GBP,
          adjusted × 1.13 × 1.17). Both shoulders, full section length
          (2 × 11,000 m). Sluice/pump installation absorbed in ±25% band.
          Complementary to Mondego railway (10a) — A14 and Linha do Norte
          run through the same lezíria corridor. A shared Mondego corridor
          programme could protect BOTH assets at shared programme cost.
          Type: frequency reducer (intercepts inundation).

Option 3 | Dynamic traffic management protocol (duration reducer)
          Cost: parametric — €350k/km European ITS/VMS deployment
          benchmark, ±30 % uncertainty, over 11 km section.
          Reduces mean closure duration by 50% (4.0 → 2.0 days).
          Does NOT reduce flood frequency — hydrology unchanged.
          Type: duration reducer only.

OUTPUTS
-------
a14_flood_frequency.csv        — 24 rows
a14_disruption_cost.csv        — 1,368 rows
a14_adaptation_comparison.csv  — 72 rows

REFERENCES
----------
REF-01 : Fox-Kemper et al. (2021) IPCC AR6 WG1 Ch.9 — SLR scenarios
REF-02 : Seeger & Minderhoud (2026) Nature 652, 667–674 — geoid +0.15 m
REF-03 : Moftakhari et al. (2017) PNAS — compound flood model
REF-20 : OpenStreetMap contributors (2024) — road geometry, way/7301317
REF-24 : ANEPC / ANPC civil protection reports — Mondego flood events 2019, 2021, 2026
REF-25 : IMT regional traffic counts — A14/IP3 TMDA ~11,000 (Mondego section)
REF-29 : INE (May 2025) Transportes e Comunicações — national HGV share motorways 8 %
REF-30 : Brisa Concessão (2024) Annual Report — network-average HGV share 8 %
REF-31 : 24horas / Diário de Coimbra (February 2026) — A14 closure Maiorca–Montemor-o-Velho
REF-32 : Observador (February 2026) — A14 flood impact and road reopening timeline
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

_RAISE = _read_raise("a14_mondego")
# SSP2-4.5 = +1.75 m → Elevated road on reinforced structure (1.00-2.00 m range)
# SSP5-8.5 = +2.14 m → Full structural reconstruction  [design/headline]
# ALL scenarios require structural-scale interventions (> 1.00 m threshold).
# Prior +0.50 m raise (EA SC080039/R2 minimum) massively underestimates required raise.

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

# ── SECTION PARAMETERS (derived from Stage 1 EU-DEM + OSM analysis) ──────────
ROAD_ELEV_M         = 2.38    # m MSL — carriageway crown, Mondego lezíria
                               # EU-DEM credible min 1.63 m + 0.75 m embankment
RETURN_PERIOD_BASE  = 5.0     # yr — RP₀ under present SLR
CLOSURE_DAYS_BASE   = 4.00    # days per closure event — empirically grounded
                               # in the February 2026 A14 closure (36 days
                               # total; physical flood phase ~4 days; remainder
                               # structural inspection/certification). 4 days
                               # is conservative vs the 2026 centennial event.
                               # Sources: REF-24 (ANEPC), REF-31, REF-32.
SENSITIVITY_K       = np.log(2) / 0.10   # ≈ 6.931 — Moftakhari 2017 REF-03

# ── DAILY DISRUPTION COST — VOT COMPUTATION ──────────────────────────────────
# All inputs are researcher-defined constants from cited sources.
# DAILY_DISRUPTION is computed by this script from those inputs.
#
# TRAFFIC INPUTS
# [IMT regional counts (REF-25); INE May 2025 (REF-29); Brisa 2024 (REF-30)]
_TMDA             = 11_000      # vehicles/day — A14/IP3 TMDA, Mondego section
_HGV_SHARE        = 0.08        # fraction — national motorway average
_CAR_OCCUPANCY    = 1.6         # persons/car (Portuguese average)
_DETOUR_KM        = 25.0        # km  — EN111/A17 north extra distance
_DETOUR_H         = 35.0 / 60   # h   — 35 min extra travel time

# UNIT VALUE-OF-TIME RATES
# [EU Handbook on External Costs, Portuguese short-run VOT 2021]
_VOT_PASS_EUR_H   = 8.13        # €/h — passenger value of time
_VOT_HGV_EUR_H    = 35.00       # €/h — HGV driver/logistics value of time

# MARGINAL FUEL COSTS (incremental cost of detour km only)
_FUEL_CAR_EUR_KM  = 0.07        # €/km — marginal fuel, passenger car
_FUEL_HGV_EUR_KM  = 0.45        # €/km — marginal fuel, HGV

# FREIGHT CORRIDOR GDP EXPOSURE
# [researcher estimate — Mondego/Coimbra corridor, consistent with
#  regional freight flows; REF-22 (INE regional GDP)]
_FREIGHT_GDP_D    = 20e6        # €/day — freight GDP at risk in corridor

# CARGO DISRUPTION RATE by tier (fraction of freight GDP disrupted per closure)
# Low: 0.14% — minimal supply-chain disruption (regional, short closure)
# Mid: 0.55% — moderate disruption (industrial and agricultural freight)
# High: 1.11% — extended closure, multi-sector cascade
_CARGO_RATE = {"low": 0.0014, "mid": 0.0055, "high": 0.0111}

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
# Section geometry (from Stage 1 EU-DEM + OSM analysis, elev_a14_mondego_plain.py)
_SECTION_LEN_M  = 11_000   # m  — A14 vulnerable lezíria section
_SECTION_LEN_KM = _SECTION_LEN_M / 1_000   # 11 km
_PAVE_WIDTH_M   = 12.0     # m  — A14/IP3: 2-lane motorway (narrower than A1)

# Raise heights from raise_requirements.csv
_RAISE_SSP2_M  = _RAISE["SSP2-4.5"]   # 1.75 m — elevated road on reinforced structure
_RAISE_SSP5_M  = _RAISE["SSP5-8.5"]   # 2.14 m — full structural reconstruction
_METHOD_DESIGN = _RAISE["method"]      # "Full structural reconstruction"

# Option 1a: SSP2-4.5 lower bound — elevated road on reinforced structure
# Unit cost: €15–25 M/km (± 35% — same range as 11c elevated road)
_ELEV_ROAD_EUR_KM_LOW  = 15_000_000   # €/km
_ELEV_ROAD_EUR_KM_HIGH = 25_000_000   # €/km
_OPT1A_LOW_M  = round(_ELEV_ROAD_EUR_KM_LOW  * _SECTION_LEN_KM / 1e6, 0)
_OPT1A_HIGH_M = round(_ELEV_ROAD_EUR_KM_HIGH * _SECTION_LEN_KM / 1e6, 0)

# Option 1b: SSP5-8.5 design — full structural reconstruction
# Unit cost: €25–40 M/km (± 35% — major infrastructure rebuild at 2.14 m raise)
_FULL_RECON_EUR_KM_LOW  = 25_000_000   # €/km
_FULL_RECON_EUR_KM_HIGH = 40_000_000   # €/km
_OPT1B_LOW_M  = round(_FULL_RECON_EUR_KM_LOW  * _SECTION_LEN_KM / 1e6, 0)
_OPT1B_HIGH_M = round(_FULL_RECON_EUR_KM_HIGH * _SECTION_LEN_KM / 1e6, 0)

# Option 2: sheet-pile perimeter barriers — both shoulders, full section
# EA SC080039/R2, Table 1.7: £1,843/m × 1.13 × 1.17 ≈ €2,436/m
_EA_SHEETPILE_GBP2015 = 1843.0
_spile_eur_m    = _EA_SHEETPILE_GBP2015 * 1.13 * 1.17  # ≈ €2,436/m
_opt2_len_m     = 2 * _SECTION_LEN_M
_opt2_mid_M     = _opt2_len_m * _spile_eur_m / 1e6
_OPT2_LOW_M     = round(_opt2_mid_M * 0.75, 1)
_OPT2_HIGH_M    = round(_opt2_mid_M * 1.25, 1)

# Option 3: ITS/VMS dynamic traffic management — parametric €/km
_ITS_EUR_PER_KM = 350_000   # €/km — regional motorway ITS/VMS systems
_opt3_mid_M     = _ITS_EUR_PER_KM * _SECTION_LEN_KM / 1e6
_OPT3_LOW_M     = round(_opt3_mid_M * 0.70, 1)
_OPT3_HIGH_M    = round(_opt3_mid_M * 1.30, 1)

# ── ADAPTATION OPTIONS ────────────────────────────────────────────────────────
# Option 1 has two sub-scenarios: SSP2-4.5 (elevated road) and SSP5-8.5 (full reconstruction).
# Both massively exceed the prior +0.50 m embankment estimate.
OPTIONS = {
    "1a": {"name": f"Elevated road — SSP2-4.5 lower bound (+{_RAISE_SSP2_M:.2f} m)",
           "capex_low_M": _OPT1A_LOW_M, "capex_high_M": _OPT1A_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    "1b": {"name": f"Full reconstruction — SSP5-8.5 design (+{_RAISE_SSP5_M:.2f} m)",
           "capex_low_M": _OPT1B_LOW_M, "capex_high_M": _OPT1B_HIGH_M,
           "type": "frequency", "freq_multiplier": 2.0, "dur_multiplier": 1.0},
    2:    {"name": "Embankment flood protection + drainage",
           "capex_low_M": _OPT2_LOW_M, "capex_high_M": _OPT2_HIGH_M,
           "type": "frequency", "freq_multiplier": 1.8, "dur_multiplier": 1.0},
    3:    {"name": "Dynamic traffic management protocol",
           "capex_low_M": _OPT3_LOW_M,  "capex_high_M": _OPT3_HIGH_M,
           "type": "duration",  "freq_multiplier": 1.0, "dur_multiplier": 0.50},
}

# ── PRINT VOT COMPUTATION AUDIT ──────────────────────────────────────────────
# Printed at runtime so the derivation is visible and traceable.
def _print_vot_audit() -> None:
    print("── VOT COMPUTATION (A14/IP3 — Mondego lezíria) ───────────────────────")
    print(f"  TMDA = {_TMDA:,}  |  HGV = {_HGV_SHARE*100:.0f}%  |  "
          f"Detour +{_DETOUR_KM:.0f} km / +{_DETOUR_H*60:.0f} min")
    print(f"  Vehicles: {_hgv_d:,.0f} HGV/day, {_car_d:,.0f} cars/day "
          f"({_persons_d:,.0f} person-trips)")
    print(f"  Delay — passengers : €{_delay_pass/1e3:,.1f}k/day")
    print(f"  Delay — HGV        : €{_delay_hgv/1e3:,.1f}k/day")
    print(f"  Extra fuel — cars  : €{_fuel_car/1e3:,.1f}k/day")
    print(f"  Extra fuel — HGVs  : €{_fuel_hgv/1e3:,.1f}k/day")
    print(f"  Fixed direct total : €{_direct_fixed/1e3:,.1f}k/day")
    print(f"  Freight GDP exposure: €{_FREIGHT_GDP_D/1e6:.0f}M/day (Mondego corridor)")
    print()
    for t in ("low", "mid", "high"):
        cargo = _CARGO_RATE[t] * _FREIGHT_GDP_D
        total_direct = _direct_fixed + cargo
        print(f"  [{t:4s}]  cargo {_CARGO_RATE[t]*100:.3f}% = €{cargo/1e3:,.1f}k  |  "
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
print("A14 / IP3 — MONDEGO LEZÍRIA SECTION")
print("Pillar 3: Sea-Level Rise Network Disruption Analysis")
print("=" * 68)
print()
print("  Geographic scope (verified EU-DEM 25m + OSM, elev_a14_mondego_plain.py):")
print("  Section: A17/IP3 jct (Maiorca) → east of Mondego bridge")
print("  Bbox   : S=40.138, W=-8.758, N=40.178, E=-8.712")
print("  Length : ~11 km  (438 sample points × 25 m)")
print("  Lowest point  : 1.63 m MSL  (lat=40.170696, lon=-8.722700)")
print("  54.1% of section below 5 m MSL")
print("  Road crown    : ~2.38 m MSL  (DEM floor 1.63 m + 0.75 m embankment)")
print("  A14 crown (~2.38 m) < Mondego railway (~4.1 m) — A14 floods first")
print()
print(f"── LAYER A: FLOOD FREQUENCY ──────────────────────────────────────────")
print(f"  Raise requirements (from raise_requirements.csv):")
print(f"    SSP2-4.5 lower bound : +{_RAISE_SSP2_M:.2f} m → Elevated road on reinforced structure")
print(f"    SSP5-8.5 design      : +{_RAISE_SSP5_M:.2f} m → Full structural reconstruction")
print(f"    Unit cost (SSP2-4.5) : €{_ELEV_ROAD_EUR_KM_LOW//1_000_000}–"
      f"{_ELEV_ROAD_EUR_KM_HIGH//1_000_000} M/km × {_SECTION_LEN_KM:.0f} km "
      f"= €{_OPT1A_LOW_M:.0f}–{_OPT1A_HIGH_M:.0f} M (±35%)")
print(f"    Unit cost (SSP5-8.5) : €{_FULL_RECON_EUR_KM_LOW//1_000_000}–"
      f"{_FULL_RECON_EUR_KM_HIGH//1_000_000} M/km × {_SECTION_LEN_KM:.0f} km "
      f"= €{_OPT1B_LOW_M:.0f}–{_OPT1B_HIGH_M:.0f} M (±35%)")
print(f"    Prior +0.50 m embankment (EA SC080039/R2): SUPERSEDED — structural intervention required")
print()
print(f"  Road elevation (carriageway crown): {ROAD_ELEV_M:.2f} m MSL")
print(f"  Baseline return period (RP₀):       {RETURN_PERIOD_BASE:.0f} yr")
print(f"  Closure days per event:             {CLOSURE_DAYS_BASE:.1f} days")
print(f"  Sensitivity k:                      {SENSITIVITY_K:.3f}  [Moftakhari 2017]")
print(f"  Geoid correction:                   +{GEOID_OFFSET:.2f} m  [REF-02]")
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
csv_freq = OUT_DIR / "a14_flood_frequency.csv"
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
csv_disrupt = OUT_DIR / "a14_disruption_cost.csv"
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
    print(f"  {opt_id}. {opt['name']:<40} "
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
csv_adapt = OUT_DIR / "a14_adaptation_comparison.csv"
df_adapt.to_csv(csv_adapt, index=False)

print()
print(f"\n  Break-even years (mid disruption cost):")
print()
print(f"  {'Option':<40} {'Scenario':<12} {'Variant':<10} "
      f"{'BE low':>8} {'BE mid':>8} {'BE high':>9}")
print("  " + "-" * 92)
for opt_id in OPTIONS:
    for scenario in ["SSP2-4.5", "SSP5-8.5"]:
        for variant in VARIANTS:
            sub = df_adapt[(df_adapt.option == opt_id) &
                           (df_adapt.scenario == scenario) &
                           (df_adapt.variant  == variant) &
                           (df_adapt.key_year == 2100)]
            if sub.empty: continue
            r = sub.iloc[0]
            print(f"  {opt_id}. {OPTIONS[opt_id]['name']:<38} "
                  f"{scenario:<12} {variant:<10} "
                  f"{str(r['be_year_low_capex']):>8} "
                  f"{str(r['be_year_mid_capex']):>8} "
                  f"{str(r['be_year_hi_capex']):>9}")
print(f"\n  ▸ Saved: {csv_adapt.name}  ({len(df_adapt)} rows)")


# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 68)
print("SECTION SUMMARY — A14 / IP3 (MONDEGO LEZÍRIA)")
print("=" * 68)
print()
print("  Vulnerable section (EU-DEM 25m + OSM verified):")
print("    A17/IP3 jct (Maiorca) → east of Mondego bridge")
print("    ~11 km  |  438 sample points  |  54.1% below 5 m MSL")
print("    Lowest carriageway point: 1.63 m (EU-DEM terrain)")
print("    Road crown estimate:      2.38 m MSL  (+0.75 m embankment)")
print(f"  Compound flood mechanism   : Mondego fluvial + SLR")
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
print("  ★ A14 crown (~2.38 m) < Mondego railway (~4.1 m):")
print("    A14 is the lower infrastructure in the same lezíria corridor.")
print("    It floods first and with greater depth than the adjacent railway.")
print("    A shared Mondego corridor flood-protection programme (A14 + 10a)")
print("    would protect both assets at reduced combined programme cost.")
print()
print("  ★ RP₀=5 yr reflects documented Mondego flood frequency (2019, 2021,")
print("    2026) at a threshold (2.38 m) well below the railway level (4.1 m).")
print("    Not all Mondego flood events will close the A14 — 5 yr is")
print("    conservative relative to the raw event record.")
print()
print("  ★ CLOSURE_DAYS_BASE = 4 days: grounded in the February 2026 A14")
print("    closure (Maiorca–Montemor-o-Velho, this study section). Total")
print("    closure: 36 days. Physical flood/drainage phase: ~4 days.")
print("    Remainder: structural inspection + safety certification before")
print("    reopening (not modelled as recurrent operational closure).")
print("    Sources: REF-24 (ANEPC), REF-31 (24horas/Diário de Coimbra),")
print("    REF-32 (Observador). 2001 Mondego event (TR=439yr): 'several")
print("    days' — consistent with 4-day baseline. (REF-24)")
print()
print("  ★ Option 3 (traffic management) breaks even earliest but is a")
print("    duration reducer only. Recommended as an interim measure.")
print("    Option 2 creates synergy with Mondego railway (10a) if delivered")
print("    as a unified Mondego lezíria corridor programme.")
print()
print(f"  Adaptation capex (scenario-specific, from raise_requirements.csv):")
print(f"    Opt1a (elevated road, SSP2-4.5 +{_RAISE_SSP2_M:.2f} m): "
      f"€{_OPT1A_LOW_M:.0f}–{_OPT1A_HIGH_M:.0f} M  "
      f"(€{_ELEV_ROAD_EUR_KM_LOW//1_000_000}–{_ELEV_ROAD_EUR_KM_HIGH//1_000_000} M/km "
      f"× {_SECTION_LEN_KM:.0f} km ±35%)")
print(f"    Opt1b (full reconstruction, SSP5-8.5 +{_RAISE_SSP5_M:.2f} m): "
      f"€{_OPT1B_LOW_M:.0f}–{_OPT1B_HIGH_M:.0f} M  "
      f"(€{_FULL_RECON_EUR_KM_LOW//1_000_000}–{_FULL_RECON_EUR_KM_HIGH//1_000_000} M/km "
      f"× {_SECTION_LEN_KM:.0f} km ±35%)")
print(f"    Opt2 (sheet-pile barriers): "
      f"€{_OPT2_LOW_M:.1f}–{_OPT2_HIGH_M:.1f} M  "
      f"(len={_opt2_len_m:,} m × €{_spile_eur_m:.0f}/m ±25%)")
print(f"    Opt3 (ITS/VMS mgmt): "
      f"€{_OPT3_LOW_M:.1f}–{_OPT3_HIGH_M:.1f} M  "
      f"(€{_ITS_EUR_PER_KM//1000}k/km × {_SECTION_LEN_M//1000} km ±30%)")
print()
print(f"  Outputs: {OUT_DIR}")
print(f"    {csv_freq.name}   ({len(df_freq)} rows)")
print(f"    {csv_disrupt.name}  ({len(df_disrupt)} rows)")
print(f"    {csv_adapt.name}  ({len(df_adapt)} rows)")
print()
print("  Sources: REF-01 (IPCC AR6), REF-02 (Seeger & Minderhoud 2026),")
print("           REF-03 (Moftakhari 2017), REF-20 (OSM / way 7301317),")
print("           REF-24 (ANEPC), REF-25 (IMT), REF-29 (INE), REF-30 (Brisa),")
print("           REF-31–32 (A14 2026 closure press sources).")
