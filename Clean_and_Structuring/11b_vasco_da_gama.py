"""
11b_vasco_da_gama.py  —  Pillar 3 · Vasco da Gama Bridge South Approach
=========================================================================
Sea Level Rise Impact Analysis · Coastal Portugal
MBA Data Science Capstone

SCOPE
-----
This script analyses the SLR disruption risk to the Vasco da Gama Bridge
south approach road (A12 / IP1), where the motorway descends from the bridge
deck to ground level and traverses the Reserva Natural do Estuário do Tejo
— tidal marshland on the Tagus south bank near Alcochete.

SCOPE RATIONALE (ANALYSIS_LOG Decision D11)
    The bridge deck itself (~10–12m above water) is not at risk.
    The north approach is carried on elevated viaduct throughout — no
    ground-level flood exposure. Only the south approach is vulnerable:
    it sits at ~1.5m elevation through tidal marshland.
    Source: literature-based estimate; Reserva Natural do Estuário do Tejo
    terrain elevation well-documented as 0–2m in the accessible areas.

FLOOD MECHANISM
    Direct tidal/estuarine inundation: Tagus south bank compound flood
    (same mechanism as 10b_tagus_floodplain.py but at lower elevation).
    Compound flood model: RP(SLR) = RP₀ × exp(−k × SLR)
    Source: Moftakhari et al. (2017) PNAS — REF-03

DISRUPTION METRIC
    Road closure → traffic forced to divert via 25 de Abril Bridge (A2/A5),
    adding ~35–40km and ~30–45min per vehicle in congestion.
    Daily disruption cost components:
      - Vehicle time cost (AADT ~90,000 vehicles/day; cars 85%, trucks 15%)
      - Fuel cost of extra distance
      - Freight JIT delay premium for time-sensitive cargo
      - Congestion externality on 25 de Abril Bridge (already near capacity)
    Range: €0.5M (low) / €1.0M (mid) / €2.0M (high) per closure day.
    Conservative relative to port CDDR values — road closures are shorter
    and diversion routes exist (unlike rail, where no alternative exists).

ADAPTATION OPTIONS
    Option 1: Approach road raising (+0.50m embankment hardening)
              Permanently raises road surface above higher flood threshold.
              Eliminates flood events below new effective elevation.
    Option 2: Tidal flood gates + pumping station
              Active flood defence at the lowest point of the approach.
              Provides effective SLR buffer of +0.40m.
    Option 3: Dynamic traffic management protocol
              Pre-emptive diversion (via VMS, app alerts) before road
              floods. Reduces closure duration by 50% — does NOT reduce
              flood frequency (same mechanism as Option 3 in 11a_ports.py).

OUTPUTS
    vdg_flood_frequency.csv        — key-year flood frequency table
    vdg_disruption_cost.csv        — full annual time series 2024–2100
    vdg_adaptation_comparison.csv  — break-even by option/scenario/variant

PIPELINE POSITION: Step 4.5 (PIPELINE.md)
DECISIONS: D11 (scope), D04 (compound flood), D05 (365-day cap),
           D09 (Option 3 as duration reducer), D13 (no NPV discounting)
REFERENCES: REF-01 (SLR), REF-02 (geoid), REF-03 (compound flood)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── OUTPUT DIRECTORY ──────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── SLR SCENARIOS (IPCC AR6, REF-01) ─────────────────────────────────────────
SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2075: 0.30, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2075: 0.45, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2075: 0.70, 2100: 1.00},
}
GEOID_OFFSET = 0.15          # REF-02 — EU Atlantic coast correction

# ── SECTION PARAMETERS ────────────────────────────────────────────────────────
SECTION_NAME    = "Vasco da Gama Bridge · South Approach (Alcochete, A12)"
MECHANISM       = "Direct tidal/estuarine inundation — Tagus south bank compound flood"
APPROACH_ELEV_M = 1.50       # metres; literature estimate, Tagus Natural Reserve terrain
RETURN_PERIOD_BASE  = 8.0    # years; lower than Tagus railway (2.0m) given lower elevation
CLOSURE_DAYS_BASE   = 2.0    # days/event; roads reopen faster than railways

# Daily disruption cost — traffic diversion via 25 de Abril Bridge
# Low:  direct vehicle + freight costs only
# Mid:  + congestion externality on 25 de Abril (already near capacity)
# High: + JIT premium for time-sensitive freight, productivity loss
DAILY_DISRUPTION_LOW  =   500_000   # €/day
DAILY_DISRUPTION_MID  = 1_000_000   # €/day
DAILY_DISRUPTION_HIGH = 2_000_000   # €/day

# Compound flood sensitivity (Moftakhari et al. 2017, REF-03)
SENSITIVITY_K = np.log(2) / 0.10    # ≈ 6.93 — RP halves per 10cm SLR

# ── ADAPTATION OPTIONS ────────────────────────────────────────────────────────
ADAPT_OPTIONS = {
    "Option 1: Approach Road Raising (+0.50m embankment)": {
        "type"      : "slr_buffer",
        "buffer_m"  : 0.50,
        "cost_low"  : 15_000_000,
        "cost_mid"  : 22_000_000,
        "cost_high" : 30_000_000,
        "note"      : "Raises road surface ~0.50m; armoured embankment + drainage upgrade",
    },
    "Option 2: Tidal Flood Gates + Pumping Station": {
        "type"      : "slr_buffer",
        "buffer_m"  : 0.40,
        "cost_low"  : 28_000_000,
        "cost_mid"  : 42_000_000,
        "cost_high" : 60_000_000,
        "note"      : "Active tidal gate at lowest approach point; effective SLR buffer +0.40m",
    },
    "Option 3: Dynamic Traffic Management Protocol": {
        "type"              : "duration_reduction",
        "duration_factor"   : 0.50,    # −50% closure days per event
        "cost_low"          : 3_000_000,
        "cost_mid"          : 8_000_000,
        "cost_high"         : 15_000_000,
        "note"      : "Pre-emptive VMS/app diversion before road floods; does NOT reduce "
                      "flood frequency — reduces closure duration per event by 50%",
    },
}

# ── SIMULATION YEARS ─────────────────────────────────────────────────────────
YEARS = list(range(2024, 2101))
KEY_YEARS = [2030, 2050, 2075, 2100]

# ── HELPER: interpolate SLR ───────────────────────────────────────────────────
def slr_at_year(scenario: str, year: int, geoid: bool = False) -> float:
    anchors = SLR_ANCHORS[scenario]
    keys = sorted(anchors.keys())
    if year <= keys[0]:
        val = anchors[keys[0]]
    elif year >= keys[-1]:
        val = anchors[keys[-1]]
    else:
        for i in range(len(keys) - 1):
            if keys[i] <= year <= keys[i + 1]:
                t = (year - keys[i]) / (keys[i + 1] - keys[i])
                val = anchors[keys[i]] + t * (anchors[keys[i + 1]] - anchors[keys[i]])
                break
    return val + (GEOID_OFFSET if geoid else 0.0)

# ── HELPER: closure days per year ────────────────────────────────────────────
def closure_days(slr: float) -> float:
    rp = RETURN_PERIOD_BASE * np.exp(-SENSITIVITY_K * slr)
    events_per_yr = (1.0 / rp) * (1.0 + slr / 0.50)
    days = events_per_yr * CLOSURE_DAYS_BASE
    return min(days, 365.0)

# ── HELPER: permanent inundation check ───────────────────────────────────────
def is_permanent(slr: float) -> bool:
    return slr >= APPROACH_ELEV_M

# ── LAYER A — FLOOD FREQUENCY ─────────────────────────────────────────────────
def layer_a() -> pd.DataFrame:
    rows = []
    for scenario in SLR_ANCHORS:
        for geoid in [False, True]:
            for yr in KEY_YEARS:
                slr = slr_at_year(scenario, yr, geoid)
                rp  = RETURN_PERIOD_BASE * np.exp(-SENSITIVITY_K * slr)
                days = closure_days(slr)
                perm = is_permanent(slr)
                rows.append({
                    "scenario"  : scenario,
                    "variant"   : "+Geoid" if geoid else "Baseline",
                    "year"      : yr,
                    "slr_m"     : round(slr, 3),
                    "rp_yr"     : round(rp, 2),
                    "days_yr"   : round(days, 1),
                    "permanent" : perm,
                    "flag"      : "⚠ PERMANENT" if perm else ("⚠ CAP" if days >= 365.0 else ""),
                })
    return pd.DataFrame(rows)

# ── LAYER B — CUMULATIVE DISRUPTION COST ─────────────────────────────────────
def layer_b() -> pd.DataFrame:
    rows = []
    for scenario in SLR_ANCHORS:
        for geoid in [False, True]:
            cumul_low = cumul_mid = cumul_high = 0.0
            for yr in YEARS:
                slr  = slr_at_year(scenario, yr, geoid)
                perm = is_permanent(slr)
                if perm:
                    # Permanently inundated — treated as continuously closed
                    days = 365.0
                else:
                    days = closure_days(slr)
                annual_low  = days * DAILY_DISRUPTION_LOW
                annual_mid  = days * DAILY_DISRUPTION_MID
                annual_high = days * DAILY_DISRUPTION_HIGH
                cumul_low  += annual_low
                cumul_mid  += annual_mid
                cumul_high += annual_high
                if yr in KEY_YEARS:
                    rows.append({
                        "scenario"       : scenario,
                        "variant"        : "+Geoid" if geoid else "Baseline",
                        "year"           : yr,
                        "slr_m"          : round(slr, 3),
                        "annual_low_eur" : round(annual_low),
                        "annual_mid_eur" : round(annual_mid),
                        "annual_high_eur": round(annual_high),
                        "cumul_low_bn"   : round(cumul_low  / 1e9, 3),
                        "cumul_mid_bn"   : round(cumul_mid  / 1e9, 3),
                        "cumul_high_bn"  : round(cumul_high / 1e9, 3),
                        "permanent"      : perm,
                    })
    return pd.DataFrame(rows)

# ── LAYER C — ADAPTATION BREAK-EVEN ──────────────────────────────────────────
def layer_c() -> pd.DataFrame:
    rows = []
    for opt_name, opt in ADAPT_OPTIONS.items():
        for scenario in SLR_ANCHORS:
            for geoid in [False, True]:
                for cost_label, invest in [
                    ("Low",  opt["cost_low"]),
                    ("Mid",  opt["cost_mid"]),
                    ("High", opt["cost_high"]),
                ]:
                    cumul_no_adapt  = 0.0
                    cumul_with_adapt = 0.0
                    cumul_savings   = 0.0
                    be_year = None

                    for yr in YEARS:
                        slr  = slr_at_year(scenario, yr, geoid)
                        perm = is_permanent(slr)

                        # --- baseline disruption (no adaptation) ---
                        days_base = 365.0 if perm else closure_days(slr)
                        annual_base = days_base * DAILY_DISRUPTION_MID

                        # --- disruption WITH adaptation ---
                        if opt["type"] == "slr_buffer":
                            # Physically raises effective threshold
                            effective_elev = APPROACH_ELEV_M + opt["buffer_m"]
                            slr_eff = slr - opt["buffer_m"]   # effective SLR seen by road
                            slr_eff = max(slr_eff, 0.0)
                            if slr >= effective_elev:
                                days_adapt = 365.0
                            elif slr_eff <= 0:
                                days_adapt = 0.0
                            else:
                                days_adapt = closure_days(slr_eff)
                            annual_adapt = days_adapt * DAILY_DISRUPTION_MID

                        elif opt["type"] == "duration_reduction":
                            # Reduces closure duration per event; doesn't change frequency
                            days_adapt = days_base * (1.0 - opt["duration_factor"])
                            annual_adapt = days_adapt * DAILY_DISRUPTION_MID

                        annual_saving = annual_base - annual_adapt
                        cumul_savings += annual_saving

                        if be_year is None and cumul_savings >= invest:
                            be_year = yr

                    rows.append({
                        "option"    : opt_name,
                        "option_type": opt["type"],
                        "scenario"  : scenario,
                        "variant"   : "+Geoid" if geoid else "Baseline",
                        "cost_case" : cost_label,
                        "invest_eur": invest,
                        "breakeven_year": be_year if be_year else ">2100",
                        "note"      : opt["note"],
                    })
    return pd.DataFrame(rows)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    W = 78
    print("═" * W)
    print(f"  PILLAR 3 — {SECTION_NAME}")
    print("═" * W)
    print(f"  Mechanism  : {MECHANISM}")
    print(f"  Road elev  : {APPROACH_ELEV_M:.1f} m (literature estimate — tidal marshland)")
    print(f"  RP base    : {RETURN_PERIOD_BASE:.0f} yr")
    print(f"  Closure    : {CLOSURE_DAYS_BASE:.1f} days/event")
    print(f"  CDDR       : Low €{DAILY_DISRUPTION_LOW/1e6:.1f}M  "
          f"Mid €{DAILY_DISRUPTION_MID/1e6:.1f}M  "
          f"High €{DAILY_DISRUPTION_HIGH/1e6:.1f}M per closure day")

    # ── Check permanent inundation risk ──────────────────────────────────────
    print()
    print("  PERMANENT INUNDATION CHECK")
    print(f"  {'─'*60}")
    perm_found = False
    for scenario in SLR_ANCHORS:
        for geoid in [False, True]:
            slr_2100 = slr_at_year(scenario, 2100, geoid)
            if slr_2100 >= APPROACH_ELEV_M:
                label = f"{scenario} {'(+Geoid)' if geoid else '(Baseline)'}"
                print(f"  ⚠  {label}: SLR {slr_2100:.2f}m ≥ {APPROACH_ELEV_M:.1f}m "
                      f"→ PERMANENT INUNDATION by 2100")
                perm_found = True
    if not perm_found:
        max_slr = slr_at_year("SSP5-8.5", 2100, True)
        print(f"  Max SLR+Geoid by 2100 = {max_slr:.2f}m  "
              f"{'≥' if max_slr >= APPROACH_ELEV_M else '<'}  "
              f"approach elevation {APPROACH_ELEV_M:.1f}m")
        if max_slr >= APPROACH_ELEV_M:
            print(f"  ⚠  SSP5-8.5 +Geoid reaches permanent inundation before 2100")
            perm_found = True

    # ── Layer A ───────────────────────────────────────────────────────────────
    df_freq = layer_a()
    print()
    print("  LAYER A — Flood Frequency")
    print(f"  Model: RP = {RETURN_PERIOD_BASE:.0f} yr × exp(−6.93×SLR)  |  "
          f"Closure = (1/RP) × {CLOSURE_DAYS_BASE:.1f} × (1+SLR/0.50)  |  cap 365")
    print(f"  {'─'*70}")
    print(f"  {'Scenario':<12} {'Variant':<10} {'Year':>5}  {'SLR (m)':>8}  "
          f"{'RP (yr)':>8}  {'Days/yr':>8}  {'':>12}")
    print(f"  {'─'*70}")
    for _, r in df_freq.iterrows():
        print(f"  {r.scenario:<12} {r.variant:<10} {r.year:>5}  {r.slr_m:>8.3f}  "
              f"{r.rp_yr:>8.2f}  {r.days_yr:>8.1f}  {r.flag:>12}")

    # ── Layer B ───────────────────────────────────────────────────────────────
    df_cost = layer_b()
    print()
    print("  LAYER B — Cumulative Disruption Cost (mid CDDR = "
          f"€{DAILY_DISRUPTION_MID/1e6:.1f}M/day, nominal)")
    print(f"  {'─'*70}")
    print(f"  {'Scenario':<12} {'Variant':<10} {'2030':>12} {'2050':>12} "
          f"{'2075':>12} {'2100':>12}")
    print(f"  {'─'*70}")
    for scenario in SLR_ANCHORS:
        for variant in ["Baseline", "+Geoid"]:
            sub = df_cost[(df_cost.scenario == scenario) & (df_cost.variant == variant)]
            vals = {int(r.year): r.cumul_mid_bn for _, r in sub.iterrows()}
            print(f"  {scenario:<12} {variant:<10} "
                  f"{vals.get(2030, 0):>11.3f}bn  {vals.get(2050, 0):>11.3f}bn  "
                  f"{vals.get(2075, 0):>11.3f}bn  {vals.get(2100, 0):>11.3f}bn")

    # ── Layer C ───────────────────────────────────────────────────────────────
    df_be = layer_c()
    print()
    print("  LAYER C — Adaptation Options · Break-Even Analysis")
    print("  (Year when cumulative avoided disruption cost ≥ adaptation investment)")
    print("  Note: Options 1 & 2 raise effective flood threshold (SLR buffer).")
    print("        Option 3 reduces closure duration (−50% days/event).")
    print(f"  {'─'*70}")

    for opt_name in ADAPT_OPTIONS:
        opt = ADAPT_OPTIONS[opt_name]
        sub = df_be[df_be.option == opt_name]
        print()
        print(f"  ● {opt_name}")
        print(f"    Cost : €{opt['cost_low']/1e6:.0f}M – €{opt['cost_high']/1e6:.0f}M  "
              f"(mid: €{opt['cost_mid']/1e6:.0f}M)")
        if opt["type"] == "slr_buffer":
            print(f"    Effective SLR buffer: +{opt['buffer_m']:.2f} m")
        else:
            print(f"    Closure day reduction: {opt['duration_factor']*100:.0f}% fewer days/event")
        print(f"    {'Scenario':<12} {'Variant':<10} {'Low BE':>10} {'Mid BE':>10} {'High BE':>10}")
        print(f"    {'─'*56}")
        for scenario in SLR_ANCHORS:
            for variant in ["Baseline", "+Geoid"]:
                row = sub[(sub.scenario == scenario) & (sub.variant == variant)]
                be_vals = {}
                for _, r in row.iterrows():
                    be_vals[r.cost_case] = str(r.breakeven_year)
                print(f"    {scenario:<12} {variant:<10} "
                      f"{be_vals.get('Low','?'):>10} "
                      f"{be_vals.get('Mid','?'):>10} "
                      f"{be_vals.get('High','?'):>10}")

    # ── Key Insights ──────────────────────────────────────────────────────────
    print()
    print("═" * W)
    print("  KEY INSIGHTS")
    print(f"  {'─'*76}")

    slr_585_base = slr_at_year("SSP5-8.5", 2100, False)
    slr_585_geo  = slr_at_year("SSP5-8.5", 2100, True)
    perm_585_base = slr_585_base >= APPROACH_ELEV_M
    perm_585_geo  = slr_585_geo  >= APPROACH_ELEV_M

    sub_585 = df_cost[(df_cost.scenario == "SSP5-8.5") & (df_cost.year == 2100)]
    cum_base = sub_585[sub_585.variant == "Baseline"].cumul_mid_bn.values[0]
    cum_geo  = sub_585[sub_585.variant == "+Geoid"].cumul_mid_bn.values[0]

    print(f"  1. SOUTH APPROACH ELEVATION RISK (elev ~{APPROACH_ELEV_M:.1f}m):")
    if perm_585_geo:
        print(f"     SSP5-8.5 +Geoid (SLR {slr_585_geo:.2f}m) reaches PERMANENT INUNDATION.")
        print(f"     SSP5-8.5 Baseline (SLR {slr_585_base:.2f}m): "
              f"{'permanent' if perm_585_base else 'no permanent inundation'}.")
    else:
        print(f"     No permanent inundation under any scenario by 2100.")
        print(f"     Max SLR+Geoid = {slr_585_geo:.2f}m < {APPROACH_ELEV_M:.1f}m approach elevation.")
        print(f"     Risk is compound flood frequency escalation only.")

    print()
    print(f"  2. CUMULATIVE DISRUPTION (SSP5-8.5, mid CDDR, by 2100):")
    print(f"     Baseline  : €{cum_base:.3f}bn")
    print(f"     +Geoid    : €{cum_geo:.3f}bn  "
          f"(+{((cum_geo/cum_base)-1)*100:.0f}% vs baseline)")

    print()
    print(f"  3. OPTION 3 (Dynamic Traffic Management) IS THE ENTRY-POINT MEASURE.")
    print(f"     Lowest cost (€3–15M), immediate deployment, no construction required.")
    print(f"     Pre-emptive VMS + app-based diversion before road floods reduces")
    print(f"     effective closure duration — and does so from year 1.")

    print()
    print(f"  4. OPTION 1 (Road Raising) IS THE DEFINITIVE LONG-TERM SOLUTION.")
    print(f"     +0.50m embankment hardening eliminates risk up to {APPROACH_ELEV_M+0.50:.1f}m SLR.")
    print(f"     Cost of €15–30M is low relative to cumulative disruption avoided.")
    print(f"     Should be sequenced as: Option 3 now → Option 1 within 5–10 years.")

    print()
    print(f"  5. STRATEGIC CONTEXT: 25 DE ABRIL BRIDGE CONGESTION RISK.")
    print(f"     When the VdG south approach floods, all diverted traffic concentrates")
    print(f"     on the 25 de Abril Bridge — which operates at near-capacity.")
    print(f"     Disruption cost estimates (mid/high) may understate systemic congestion")
    print(f"     effects. This is a conservative model.")
    print("═" * W)

    # ── Save outputs ──────────────────────────────────────────────────────────
    freq_path = OUT_DIR / "vdg_flood_frequency.csv"
    cost_path = OUT_DIR / "vdg_disruption_cost.csv"
    be_path   = OUT_DIR / "vdg_adaptation_comparison.csv"

    # Full annual time series for disruption cost
    full_rows = []
    for scenario in SLR_ANCHORS:
        for geoid in [False, True]:
            cumul_low = cumul_mid = cumul_high = 0.0
            for yr in YEARS:
                slr  = slr_at_year(scenario, yr, geoid)
                perm = is_permanent(slr)
                days = 365.0 if perm else closure_days(slr)
                annual_low  = days * DAILY_DISRUPTION_LOW
                annual_mid  = days * DAILY_DISRUPTION_MID
                annual_high = days * DAILY_DISRUPTION_HIGH
                cumul_low  += annual_low
                cumul_mid  += annual_mid
                cumul_high += annual_high
                full_rows.append({
                    "scenario"       : scenario,
                    "variant"        : "+Geoid" if geoid else "Baseline",
                    "year"           : yr,
                    "slr_m"          : round(slr, 3),
                    "days_yr"        : round(days, 2),
                    "annual_low_eur" : round(annual_low),
                    "annual_mid_eur" : round(annual_mid),
                    "annual_high_eur": round(annual_high),
                    "cumul_low_bn"   : round(cumul_low  / 1e9, 4),
                    "cumul_mid_bn"   : round(cumul_mid  / 1e9, 4),
                    "cumul_high_bn"  : round(cumul_high / 1e9, 4),
                    "permanent"      : perm,
                })
    df_full = pd.DataFrame(full_rows)

    df_freq.to_csv(freq_path, index=False)
    df_full.to_csv(cost_path, index=False)
    df_be.to_csv(be_path, index=False)

    print()
    print(f"  Outputs saved to: {OUT_DIR}")
    print(f"    vdg_flood_frequency.csv       ({len(df_freq)} rows — key-year table)")
    print(f"    vdg_disruption_cost.csv       ({len(df_full)} rows — full annual series)")
    print(f"    vdg_adaptation_comparison.csv ({len(df_be)} rows — break-even by option)")
