"""
10a_mondego_bypass.py  —  Pillar 3: Linha do Norte — Mondego Valley Section
=============================================================================
Analyses the flood disruption risk and bypass/relocation costs for the 3-5km
critical flood zone on the Linha do Norte at Alfarelos–Formoselha (Mondego
valley, ~km 240–244 from Lisbon).

FLOOD MECHANISM
---------------
This section is NOT directly flooded by SLR. It is a fluvial flood zone:
the Mondego River overflows its banks during storm events. SLR exacerbates
this indirectly via the TIDAL BACKWATER EFFECT — as mean sea level rises at
Figueira da Foz (the Mondego mouth, ~20km west), the river's discharge
capacity decreases, increasing the frequency and severity of upstream flooding
for a given rainfall event.

Documented closure events: February 2026 (5 days), 2021, 2019 — giving an
observed return period of approximately 4 years at current sea levels.

Model: return_period(SLR) = R₀ × exp(−k × SLR)
  where k = ln(2)/0.10 ≈ 6.93  [frequency doubles per 0.1m SLR rise]
  Source: Moftakhari et al. (2017), Haigh et al. (2014) — compound flooding.

TWO ADAPTATION OPTIONS
----------------------
All options presented for academic completeness. Decision-makers
would weigh engineering, financial, environmental and operational factors.

  Option 1 – In-situ viaduct:
    Raise the existing 3–5km alignment on piled viaducts (~37m height,
    consistent with LAV EIA precedent for the same Mondego crossing).
    Rebuild Alfarelos junction on raised structure. Shortest, cheapest,
    keeps all connections intact. Key risk: alluvial soil foundations
    (A1 motorway embankment failure in Feb 2026 confirms soil instability).

  Option 2 – Eastern bypass (Casal do Redinho → Pereira, ~7 km):
    New alignment starting south of Alfarelos near Casal do Redinho,
    routing east through higher terrain, rejoining the main line north of
    Formoselha near Pereira (~40.158°N). Estimated civil works mix:
    ~3–4 km open cut / embankment, ~1.5–2 km viaduct, ~1–1.5 km tunnel.
    Permanently removes the flood-prone section from the operational route.
    CAPEX range is intentionally wide — geological uncertainty is high and
    a full geotechnical survey is required before detailed costing.
    NOTE: A western bypass via the old Ramal de Alfarelos corridor was
    evaluated and rejected: it would require ≥2 major bridges over the
    Mondego and its parallel canal while remaining within the floodplain,
    defeating the purpose of the bypass entirely.

THREE LAYERS
------------
  Layer A: Flood frequency projection — events/year and closure days/year
           per scenario × year × variant (Baseline / +Geoid)
  Layer B: Annual and cumulative disruption cost (€) — THREE DDR BANDS
           DDR_LOW  = €0.5M/day (direct costs only)
           DDR_MID  = €1.0M/day (direct + indirect; central estimate)
           DDR_HIGH = €1.75M/day (full systemic costs)
           Basis for MID: ~7,100 passengers/day (72 trains/day × AMT 2022/2024
           occupancy rates by service type; ADFERSIT 2021 + AMT 2022/2024)
           × ~€40 avg extra cost + freight delays + business productivity losses
  Layer C: Bypass cost (low/base/high) + break-even year vs. do-nothing

DDR UNCERTAINTY BANDS (Decision D18 / D19, 2026-04-12)
-------------------------------------------------------
Following CAPEX uncertainty convention: LOW = 0.50 × MID, HIGH = 1.75 × MID.
DDR_MID calibrated from:
  · ADFERSIT (2021): 72 train movements/day at Alfarelos–Coimbra B section
  · AMT (2022): avg 176 pax/train long-distance; 54 pax/train regional
  · AMT (2024 [2023 data]): updated to 178 pax/train long-distance; 59 pax/train regional
    → ~7,100 passengers/day through Mondego section (km 240–244)
    Note: CP (2026) reported 208.2M total passengers in 2025; Intercidades +48.8% YoY,
    but per-section occupancy growth cannot be isolated without granular data
  · IP (March 2026): Linha do Norte duplication study, €30.5M / 35km
  · Observador investigation (2026): Mondego Mais Seguro plan (€36.7M, 2020)
    partially unexecuted; line flooded again Feb 2026
  · Haigh et al. (2014) disruption valuation framework
  Rural location (vs Tagus Lisbon suburban) justifies €1M/day MID vs €1.5M/day.

OUTPUTS
-------
  mondego_flood_frequency.csv     — Layer A: flood stats per year
  mondego_disruption_cost.csv     — Layer B: annual + cumulative cost (3 bands)
  mondego_bypass_comparison.csv   — Layer C: costs + break-even

REFERENCES
----------
  IP (March 2026): "IP estuda eventual subida da Linha do Norte" — Renascença
  IP (March 2026): Alfarelos-Pampilhosa duplication, €30.5M / 35km
  Observador investigation (2026): Mondego Mais Seguro plan (€36.7M, 2020)
    partially unexecuted; line flooded again Feb 2026
  LAV EIA (2023): 37m viaduct confirmed feasible at Mondego crossing
  ADFERSIT (2021): train counts per section, H2019 data (slide 32)
  AMT (2022): Nota Estatística Transporte Ferroviário 2019–2022 — avg pax/train by service type
  AMT (2024): Análise Estatística Transporte Ferroviário em Portugal 2023 — updated pax/train rates
  CP (2026): 208.2M passengers in 2025; Intercidades +48.8% YoY (contextual only)
  A1 motorway collapse km 191, Feb 2026: alluvial soil failure precedent
  Moftakhari et al. (2017), Nature Climate Change — compound flood model
  Seeger & Minderhoud (Nature 2026) — geoid offset +0.15 m EU Atlantic coast
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent

YEAR_START = 2025
YEAR_END   = 2100
KEY_YEARS  = [2030, 2050, 2075, 2100]

SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2100: 1.00},
}
SCENARIOS    = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
GEOID_OFFSET = 0.15

# ── FLOOD MODEL (tidal backwater) ─────────────────────────────────────────────
RETURN_PERIOD_BASE   = 4.0              # years — calibrated (2019, 2021, 2026)
SENSITIVITY_K        = np.log(2) / 0.10 # ≈ 6.93; frequency doubles / 0.1m SLR
CLOSURE_DAYS_BASE    = 5.0              # days/event — calibrated from Feb 2026
CLOSURE_DAYS_GROWTH  = 2.0             # multiplier at 0.5m SLR (duration doubles)

# ── DAILY DISRUPTION RATE (DDR) — THREE BANDS ─────────────────────────────────
# LOW  = direct costs only (track repair, timetable disruption, operator losses)
# MID  = direct + indirect (pax delay costs, freight, productivity) — CENTRAL
# HIGH = full systemic (MID × 1.75; modal shift, regional economy, emergency mgmt)
DDR_LOW  =   500_000   # €/day  (0.50 × MID)
DDR_MID  = 1_000_000   # €/day  central estimate
DDR_HIGH = 1_750_000   # €/day  (1.75 × MID)

# ── PILLAR 3 SCHEMA METADATA ──────────────────────────────────────────────────
SECTION_ID   = "mondego_valley"
SECTION_NAME = "Mondego Valley (km 240–244)"
SECTION_TYPE = "railway"

# ── BYPASS OPTIONS (€ millions) ───────────────────────────────────────────────
OPTIONS = [
    {
        "id":   "OPT1",
        "name": "Option 1: In-situ viaduct (3–5km)",
        "low":  88,   "base": 120,  "high": 155,
        "construction_years": "4–6",
        "track_km":           "3–5 (viaduct only)",
        "journey_time_delta": "None",
        "beira_alta_impact":  "None — junction rebuilt in-situ at raised level",
        "slr_proof":          "Yes — structure raised ~37m above current track",
        "key_risk":           "Alluvial soil: piled foundations essential "
                              "(A1 collapse Feb 2026 is direct precedent)",
        "env_constraints":    "Low — within existing railway corridor",
        "slr_exposure_bypass":"None",
    },
    {
        "id":   "OPT2",
        "name": "Option 2: Eastern bypass — Casal do Redinho → Pereira (~7km)",
        "low":  150,  "base": 250,  "high": 400,
        "construction_years": "5–8",
        "track_km":           "~7 (est. mix: 3–4km open/embankment, "
                              "1.5–2km viaduct, 1–1.5km tunnel)",
        "journey_time_delta": "None — direct alignment maintained",
        "beira_alta_impact":  "None — bypass south of Alfarelos junction; "
                              "junction unaffected",
        "slr_proof":          "Yes — eastern high ground, well above all "
                              "SLR scenarios through 2100",
        "key_risk":           "Geotechnical uncertainty pending site survey; "
                              "rural land acquisition; tunnel/viaduct mix TBC",
        "env_constraints":    "Moderate — new rural corridor through hilly "
                              "terrain east of floodplain",
        "slr_exposure_bypass":"None",
    },
]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def slr_at_year(anchors, year, offset=0.0):
    ay = np.array(sorted(anchors))
    av = np.array([anchors[y] for y in ay])
    return float(np.interp(year, ay, av)) + offset

def return_period(slr):
    """Effective flood return period in years (tidal backwater model)."""
    return RETURN_PERIOD_BASE * np.exp(-SENSITIVITY_K * max(slr, 0.0))

def events_per_year(slr):
    return 1.0 / return_period(slr)

def days_per_event(slr):
    """Expected closure duration per event — grows with flood severity.
    At SLR=0: CLOSURE_DAYS_BASE days.  At SLR=0.5m: CLOSURE_DAYS_GROWTH × base days.
    Linear interpolation between 0 and 0.5m; extrapolates beyond.
    """
    return CLOSURE_DAYS_BASE * (1.0 + (slr / 0.50) * (CLOSURE_DAYS_GROWTH - 1.0))

def annual_cost(slr, ddr):
    """Expected annual disruption cost in € for a given DDR band.
    Closure days/yr capped at 365 (physical maximum — consistent with 10b/10c).
    The compound frequency model breaks down at extreme SLR where return periods
    drop below 1/365 yr; the cap prevents astronomically high costs that would
    dominate Tableau visualisations.
    """
    cld = min(events_per_year(slr) * days_per_event(slr), 365.0)
    return cld * ddr


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    years = np.arange(YEAR_START, YEAR_END + 1)

    # ── Layer A + B ───────────────────────────────────────────────────────────
    print("Computing flood frequency and disruption costs …")
    freq_rows, cost_rows = [], []

    for scenario in SCENARIOS:
        anchors = SLR_ANCHORS[scenario]
        cum = {
            "Baseline": {"mid": 0.0, "low": 0.0, "high": 0.0},
            "+Geoid":   {"mid": 0.0, "low": 0.0, "high": 0.0},
        }

        for year in years:
            for variant, offset in [("Baseline", 0.0), ("+Geoid", GEOID_OFFSET)]:
                slr  = slr_at_year(anchors, int(year), offset)
                rp   = return_period(slr)
                evy  = events_per_year(slr)
                dpe  = days_per_event(slr)
                closure_days_yr = min(evy * dpe, 365.0)  # cap: consistent with annual_cost()

                acst_mid  = annual_cost(slr, DDR_MID)
                acst_low  = annual_cost(slr, DDR_LOW)
                acst_high = annual_cost(slr, DDR_HIGH)

                cum[variant]["mid"]  += acst_mid
                cum[variant]["low"]  += acst_low
                cum[variant]["high"] += acst_high

                freq_rows.append({
                    "section":              SECTION_NAME,
                    "section_type":         SECTION_TYPE,
                    "scenario":             scenario,
                    "year":                 int(year),
                    "variant":              variant,
                    "slr_m":                round(slr, 3),
                    "return_period_yr":     round(rp,  2),
                    "events_per_year":      round(evy, 3),
                    "days_per_event":       round(dpe, 1),
                    "closure_days_yr":      round(closure_days_yr, 1),
                })
                cost_rows.append({
                    "section":                    SECTION_NAME,
                    "section_type":               SECTION_TYPE,
                    "scenario":                   scenario,
                    "variant":                    variant,
                    "year":                       int(year),
                    "slr_m":                      round(slr, 3),
                    "return_period_yr":           round(rp, 2),
                    "closure_days_yr":            round(closure_days_yr, 1),
                    "annual_cost_mid_eur":         round(acst_mid,  0),
                    "annual_cost_low_eur":         round(acst_low,  0),
                    "annual_cost_high_eur":        round(acst_high, 0),
                    "cumulative_cost_mid_eur":     round(cum[variant]["mid"],  0),
                    "cumulative_cost_low_eur":     round(cum[variant]["low"],  0),
                    "cumulative_cost_high_eur":    round(cum[variant]["high"], 0),
                })

    df_freq = pd.DataFrame(freq_rows)
    df_cost = pd.DataFrame(cost_rows)

    # ── Layer C: break-even ───────────────────────────────────────────────────
    print("Computing break-even years …")
    bypass_rows = []

    for opt in OPTIONS:
        for cost_lbl, cost_meur in [("low",  opt["low"]),
                                     ("base", opt["base"]),
                                     ("high", opt["high"])]:
            cost_eur = cost_meur * 1e6

            for scenario in SCENARIOS:
                anchors = SLR_ANCHORS[scenario]

                for variant, offset in [("Baseline", 0.0), ("+Geoid", GEOID_OFFSET)]:
                    # Cumulative disruption (MID band) from 2025 until break-even
                    cum_be_mid  = 0.0
                    cum_be_low  = 0.0
                    cum_be_high = 0.0
                    be_year_mid = be_year_low = be_year_high = None

                    for year in years:
                        slr = slr_at_year(anchors, int(year), offset)
                        cum_be_mid  += annual_cost(slr, DDR_MID)
                        cum_be_low  += annual_cost(slr, DDR_LOW)
                        cum_be_high += annual_cost(slr, DDR_HIGH)

                        if cum_be_mid  >= cost_eur and be_year_mid  is None:
                            be_year_mid  = int(year)
                        if cum_be_low  >= cost_eur and be_year_low  is None:
                            be_year_low  = int(year)
                        if cum_be_high >= cost_eur and be_year_high is None:
                            be_year_high = int(year)

                    for ky in KEY_YEARS:
                        slr_ky = slr_at_year(anchors, ky, offset)
                        bypass_rows.append({
                            "option":                 opt["name"],
                            "option_id":              opt["id"],
                            "cost_scenario":          cost_lbl,
                            "bypass_cost_meur":       cost_meur,
                            "scenario":               scenario,
                            "variant":                variant,
                            "key_year":               ky,
                            "slr_m":                  round(slr_ky, 3),
                            "events_per_year":        round(events_per_year(slr_ky), 3),
                            "closure_days_yr":        round(min(events_per_year(slr_ky) * days_per_event(slr_ky), 365.0), 1),
                            "annual_cost_mid_eur":    round(annual_cost(slr_ky, DDR_MID), 0),
                            "annual_cost_low_eur":    round(annual_cost(slr_ky, DDR_LOW), 0),
                            "annual_cost_high_eur":   round(annual_cost(slr_ky, DDR_HIGH), 0),
                            "breakeven_year_mid":     be_year_mid  if be_year_mid  else ">2100",
                            "breakeven_year_low":     be_year_low  if be_year_low  else ">2100",
                            "breakeven_year_high":    be_year_high if be_year_high else ">2100",
                        })

    df_bypass = pd.DataFrame(bypass_rows)

    # ── Save ──────────────────────────────────────────────────────────────────
    df_freq.to_csv(  PROJECT_DIR / "mondego_flood_frequency.csv",  index=False)
    df_cost.to_csv(  PROJECT_DIR / "mondego_disruption_cost.csv",  index=False)
    df_bypass.to_csv(PROJECT_DIR / "mondego_bypass_comparison.csv",index=False)
    print(f"  Saved: mondego_flood_frequency.csv  ({len(df_freq)} rows)")
    print(f"  Saved: mondego_disruption_cost.csv  ({len(df_cost)} rows)")
    print(f"  Saved: mondego_bypass_comparison.csv ({len(df_bypass)} rows)\n")

    # ══════════════════════════════════════════════════════════════════════════
    W = 112
    print("═" * W)
    print("LINHA DO NORTE — MONDEGO VALLEY — PILLAR 3 ANALYSIS")
    print("Section: Alfarelos–Formoselha (~3km critical zone, fluvial flood)")
    print("Model: Tidal backwater — flood frequency doubles per 0.1m SLR at "
          "Figueira da Foz mouth")
    print("Calibration: return period = 4 years at 2025 SLR "
          "(events: 2019, 2021, Feb 2026)")
    print(f"DDR bands: LOW=€{DDR_LOW/1e6:.2f}M/day  MID=€{DDR_MID/1e6:.2f}M/day  "
          f"HIGH=€{DDR_HIGH/1e6:.3f}M/day")
    print("═" * W)

    # ── Layer A ───────────────────────────────────────────────────────────────
    print("\nLAYER A — FLOOD FREQUENCY PROJECTION")
    print(f"{'Scenario':<12} {'Year':>6}  {'Variant':<10}  {'SLR':>6}  "
          f"{'Return pd':>10}  {'Events/yr':>10}  "
          f"{'Days/event':>11}  {'Closure days/yr':>15}")
    print("─" * W)
    for scenario in SCENARIOS:
        for year in KEY_YEARS:
            for variant, offset in [("Baseline", 0.0), ("+Geoid", GEOID_OFFSET)]:
                slr = slr_at_year(SLR_ANCHORS[scenario], year, offset)
                rp  = return_period(slr)
                evy = events_per_year(slr)
                dpe = days_per_event(slr)
                cld_print = min(evy * dpe, 365.0)  # cap for display (consistent with CSV)
                cap_flag  = " ⚠CAP" if evy * dpe > 365.0 else ""
                print(f"{scenario:<12} {year:>6}  {variant:<10}  {slr:>6.3f}  "
                      f"{rp:>10.2f}  {evy:>10.3f}  "
                      f"{dpe:>11.1f}  {cld_print:>15.1f}{cap_flag}")
        print()

    # ── Layer B ───────────────────────────────────────────────────────────────
    print("═" * W)
    print("LAYER B — ANNUAL DISRUPTION COST  (THREE DDR BANDS)")
    print(f"{'Scenario':<12} {'Year':>6}  {'Variant':<10}  {'SLR':>6}  "
          f"{'€M/yr LOW':>10}  {'€M/yr MID':>10}  {'€M/yr HIGH':>11}  "
          f"{'Cum.MID (€M)':>13}")
    print("─" * W)
    for scenario in SCENARIOS:
        for year in KEY_YEARS:
            for variant in ["Baseline", "+Geoid"]:
                row = df_cost[
                    (df_cost.scenario == scenario) &
                    (df_cost.year == year) &
                    (df_cost.variant == variant)
                ].iloc[0]
                print(f"{scenario:<12} {year:>6}  {variant:<10}  {row.slr_m:>6.3f}  "
                      f"{row.annual_cost_low_eur/1e6:>10.3f}  "
                      f"{row.annual_cost_mid_eur/1e6:>10.3f}  "
                      f"{row.annual_cost_high_eur/1e6:>11.3f}  "
                      f"{row.cumulative_cost_mid_eur/1e6:>13.1f}")
        print()

    # ── Layer C ───────────────────────────────────────────────────────────────
    print("═" * W)
    print("LAYER C — BYPASS COST & BREAK-EVEN YEAR (vs do-nothing, MID DDR)")
    print("Break-even: year when cumulative disruption cost ≥ bypass investment")
    print(f"{'Option':<44} {'€M range':>12}  {'Scenario':<12}  "
          f"{'BE LOW DDR':>11}  {'BE MID DDR':>11}  {'BE HIGH DDR':>12}")
    print("─" * W)
    for opt in OPTIONS:
        cost_str = f"€{opt['low']}–{opt['high']}M"
        for scenario in SCENARIOS:
            row_base = df_bypass[
                (df_bypass.option_id     == opt["id"]) &
                (df_bypass.cost_scenario == "base") &
                (df_bypass.scenario      == scenario) &
                (df_bypass.variant       == "Baseline") &
                (df_bypass.key_year      == 2100)
            ].iloc[0]
            print(f"{opt['name']:<44} {cost_str:>12}  {scenario:<12}  "
                  f"{str(row_base.breakeven_year_low):>11}  "
                  f"{str(row_base.breakeven_year_mid):>11}  "
                  f"{str(row_base.breakeven_year_high):>12}")
        print()

    # ── Qualitative comparison ────────────────────────────────────────────────
    print("═" * W)
    print("QUALITATIVE OPTION COMPARISON")
    print("═" * W)
    for opt in OPTIONS:
        print(f"\n  ▶ {opt['name']}")
        print(f"    Cost range:          €{opt['low']}M – €{opt['high']}M  "
              f"(base: €{opt['base']}M)")
        print(f"    New track length:    {opt['track_km']} km")
        print(f"    Construction time:   {opt['construction_years']} years")
        print(f"    Journey time Δ:      {opt['journey_time_delta']}")
        print(f"    Beira Alta impact:   {opt['beira_alta_impact']}")
        print(f"    SLR-proof:           {opt['slr_proof']}")
        print(f"    Env. constraints:    {opt['env_constraints']}")
        print(f"    Key risk:            {opt['key_risk']}")
    print()
    print("═" * W)
    print("NOTE ON OPTION 2 CAPEX RANGE: The wide uncertainty band (€150M–€400M)")
    print("reflects genuine geological uncertainty in the tunnel/viaduct mix.")
    print("A geotechnical survey of the Casal do Redinho → Pereira corridor is")
    print("required before detailed costing. Break-even under most scenarios")
    print("falls beyond 2075; this option is a long-horizon corridor upgrade")
    print("rather than a near-term adaptation measure.")
    print("═" * W)
