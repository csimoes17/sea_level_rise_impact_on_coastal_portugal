# ANALYSIS LOG — Sea Level Rise Impact Analysis · Coastal Portugal
**MBA Data Science Capstone**
*Chronological record of methodological decisions, analytical pivots, and key findings that shaped the project. Each entry includes: what was decided, why, any source that justifies it, and what it changed. This document feeds directly into Chapter 3 (Methodology justification) and Chapter 6 (Discussion / Limitations).*

---

## DECISION 001 — Choice of SLR Scenarios
**When:** Project inception
**Decision:** Use IPCC AR6 SSP1-2.6, SSP2-4.5, SSP5-8.5 as the three SLR scenarios, with anchor values at 2050 and 2100 and linear interpolation for intermediate years.
**Rationale:** IPCC AR6 (2021) is the current scientific consensus. Three scenarios provide a low/mid/high envelope covering the plausible range of 21st-century outcomes. SSP5-8.5 represents the worst-case physically plausible trajectory and is standard in infrastructure risk assessment.
**Alternative considered:** Using regional Portuguese tide gauge projections only. Rejected: IPCC AR6 provides globally consistent, peer-reviewed median projections; local projections are not yet published at the same level of certainty for Portugal specifically.
**Source:** REF-01 (Fox-Kemper et al., 2021)
**Dissertation feed:** Chapter 3.2

---

## DECISION 002 — Static Bathtub Inundation Model (not dynamic)
**When:** Project inception (Pillars 1 & 2)
**Decision:** Use a static bathtub model — a pixel is flooded if its elevation ≤ SLR threshold.
**Rationale:** For regional-scale screening across coastal Portugal, dynamic models (ADCIRC, Delft3D, etc.) are computationally prohibitive and require storm surge hindcast data not available at this resolution. The bathtub model is the standard approach for first-order exposure assessment and is well-documented in the peer-reviewed literature.
**Limitation acknowledged:** The bathtub model overestimates inundation in disconnected low-lying areas (pixels not hydraulically connected to the sea are flagged as flooded if elevation ≤ SLR). It also ignores wave action, storm surge, and drainage. This is explicitly flagged in the dissertation limitations.
**Source:** REF-04 (Poulter & Halpin, 2008 — candidate citation)
**Dissertation feed:** Chapter 3.2, Chapter 6 (limitations)

---

## DECISION 003 — Geoid Correction (+0.15m)
**When:** After Pillar 1 initial results; applied retroactively to all analyses
**Decision:** Apply a +0.15m geoid correction to all SLR scenarios to produce a "geoid variant" alongside the baseline, creating two parallel tracks for every result.
**Rationale:** Standard IPCC AR6 projections are relative to a global mean sea level baseline, but the observed relative sea level change at a given coastline depends on vertical land movement and regional geoid variations. Seeger & Minderhoud (2026) identify a systematic underestimation of relative SLR for the EU Atlantic coast. Rather than replacing the IPCC values, we present both variants to quantify the sensitivity of results to this correction.
**Impact:** Geoid correction amplifies exposure most dramatically in near-term/low scenarios — SSP1-2.6 2030 shows +279% infrastructure cost amplification — because the +0.15m offset pushes areas just below the baseline flood threshold into the flood zone. Effect diminishes in late high-emission scenarios.
**Critical note:** REF-02 (Seeger & Minderhoud 2026) must be verified before submission. If the specific paper cannot be confirmed, the geoid variant must be re-sourced or reframed as a general sensitivity analysis.
**Source:** REF-02 ⚠ (needs verification)
**Dissertation feed:** Chapter 3.2 (methodology), Chapter 4 (results — both variants presented throughout), Chapter 6 (sensitivity caveat)

---

## DECISION 004 — Compound Flood Model for Pillar 3
**When:** Before writing first Pillar 3 script (10a_mondego_bypass.py)
**Decision:** For Pillar 3 (network disruption), replace the static bathtub approach with a compound flood model. The return period of a flood event decreases exponentially as SLR accumulates.
**Formula adopted:** `RP(SLR) = RP₀ × exp(−k × SLR)`, where k = ln(2)/0.10 ≈ 6.93
**Rationale:** The bathtub model is appropriate for estimating *which areas* flood at a given SLR level (Pillars 1 & 2). But for infrastructure disruption, what matters is *how often* a flood event occurs — and that frequency increases non-linearly with SLR as events that were rare become routine. Moftakhari et al. (2017) established that a 10cm SLR approximately doubles the frequency of a given flood event in compound estuarine/coastal settings. k = ln(2)/0.10 directly encodes this relationship.
**Impact:** This model drives all Pillar 3 frequency calculations. Higher SLR → much shorter return periods → rapidly escalating annual disruption costs → earlier break-even for adaptation options.
**Source:** REF-03 (Moftakhari et al., 2017)
**Dissertation feed:** Chapter 3.3 (Pillar 3 methodology), Chapter 4.3

---

## DECISION 005 — Closure Days Cap at 365
**When:** During 10a_mondego_bypass.py development
**Decision:** Cap annual closure days at 365 in the disruption model.
**Rationale:** The exponential compound flood formula can mathematically produce closure days exceeding 365/year at extreme SLR values. Physically, a section cannot be closed more than 365 days/year. The cap is applied conservatively — it actually underestimates disruption costs at extreme SLR (SSP5-8.5 +geoid late century) because it treats the section as continuously closed rather than permanently abandoned.
**Note for dissertation:** Where the cap is reached (flagged as "⚠ CAP" in script outputs), the infrastructure section should be considered effectively non-functional — a qualitative finding that transcends the quantitative model.
**Dissertation feed:** Chapter 3.3 (model boundary), Chapter 4.3 (interpretation of cap-reached rows)

---

## DECISION 006 — Infrastructure Unit Costs (Pillar 2)
**When:** Before 06b_osm_infrastructure.py
**Decision:** Apply fixed unit replacement costs: buildings €800/m², roads €1.5M/km, railways €3.0M/km, utilities €0.5M/km.
**Rationale:** OpenStreetMap provides asset geometry (footprints, lengths) but not valuation. Replacement cost unit rates are derived from Portuguese construction industry benchmarks. These are conservative estimates — actual replacement costs in coastal zones (with access constraints and protective design requirements) would be higher.
**Limitation:** Unit costs do not vary spatially (a coastal road in a remote area uses the same rate as an urban arterial). This is a deliberate simplification consistent with the screening-level nature of the study.
**Dissertation feed:** Chapter 3.3, Chapter 6 (limitations)

---

## DECISION 007 — Port Disruption: CDDR Framework (not cargo value)
**When:** Before writing 11a_ports.py
**Trigger:** User correctly challenged the assumption that port disruption cost = daily cargo value. Most cargo is delayed, not lost — it arrives eventually on the next vessel. Only perishable goods are permanently lost.
**Decision:** Adopt a Composite Daily Disruption Rate (CDDR) framework:
```
CDDR = Inventory Carrying Cost (ICC)
     + JIT supply chain premium
     + Perishable cargo loss
     + Rerouting cost
     ≈ 3–7% of delayed cargo value per week of closure
```
**Evidence:** The 2021 Suez Canal blockage (Ever Given) delayed ~€26.5bn of cargo for ~6 days and caused an estimated €127–147bn in supply chain disruption — approximately 3–7% of delayed cargo value per week. This is the strongest real-world validation of the CDDR range.
**Why not total cargo value:** The daily cargo value at a major port (Lisbon: ~€68M/day) would produce absurdly high disruption costs and has no empirical grounding — most shippers reroute or wait, incurring incremental costs, not total cargo loss.
**Sources:** REF-10 (Tran et al., 2025), REF-10 (Suez Canal study), REF-11 (maritime blockage model), REF-12 (IMF PortWatch)
**Dissertation feed:** Chapter 3.3 (port disruption methodology), Chapter 6 (CDDR range sensitivity)

---

## DECISION 008 — Savings-Based Break-Even for Ports (not 100% elimination)
**When:** During 11a_ports.py design
**Decision:** Port adaptation break-even uses a savings-based approach — each option avoids a *fraction* of disruption cost, and break-even is reached when cumulative avoided costs equal the investment.
**Contrast:** Railway scripts (10a–10c) assumed adaptation eliminates 100% of disruption above the protection threshold. This is defensible for a physical bypass (which completely reroutes the line away from the flood zone) but not for port adaptations (which reduce but cannot eliminate flood risk).
**Mechanics:**
- Option 1 (Physical Flood-Proofing): +0.40m SLR buffer → reduces flood frequency
- Option 2 (Landside Access Resilience): +0.30m SLR buffer → reduces flood frequency
- Option 3 (Operational Protocol): −50% closure duration per event → does NOT reduce frequency
**Dissertation feed:** Chapter 3.3 (adaptation methodology distinction), Chapter 5 (break-even results)

---

## DECISION 009 — Option 3 as Duration Reducer (not frequency reducer)
**When:** During 11a_ports.py design
**Decision:** Model Option 3 (Operational Resilience Protocol) as reducing closure days per event by 50%, structurally separate from Options 1 & 2 which reduce the probability of events occurring.
**Rationale:** An operational protocol (pre-positioning resources, pre-alerting key shippers like AutoEuropa, establishing emergency logistics corridors) cannot prevent a storm surge from occurring or reduce its physical magnitude. It can reduce the time the port remains closed after each event — through faster response, pre-positioned pumping equipment, pre-cleared alternative routings. These are fundamentally different mechanisms.
**Impact on results:** Option 3 has the lowest cost and fastest break-even across all three ports — precisely because it costs the least to implement and yields savings from day 1, without requiring construction lead time.
**Dissertation feed:** Chapter 3.3, Chapter 5 (adaptation comparison)

---

## DECISION 010 — Sines Excluded from Port Analysis
**When:** During 11a_ports.py scoping
**Decision:** Port of Sines not included in the disruption analysis.
**Rationale:** Sines quay elevations are 5–7m, with modern construction designed to international standards. Maximum SLR+geoid in the study (SSP5-8.5 +geoid, 2100) = 1.15m — well below Sines' quay level. There is no compound flood exposure within the century that would trigger meaningful disruption costs.
**Strategic note (for dissertation):** Under high-emission scenarios, Sines becomes *more* strategically valuable as the de facto overflow port when Lisbon and Setúbal face increasing disruption frequency. This is a positive adaptation finding.
**Dissertation feed:** Chapter 4.3 (Sines rationale), Chapter 6 (strategic implications)

---

## DECISION 011 — Vasco da Gama Bridge: South Approach Only
**When:** Before writing 11b_vasco_da_gama.py
**Decision:** Analyse only the south approach (Alcochete side, A12). Exclude north approach.
**Rationale:** The north approach is carried on elevated viaduct structure throughout, with the road deck well above flood level. Modelling it would be technically misleading. The south approach descends to grade through the Reserva Natural do Estuário do Tejo — tidal marshland at ~1.5m elevation — and is genuinely vulnerable.
**Dissertation feed:** Chapter 4.3 (scope justification)

---

## DECISION 012 — Aveiro Barrier Breach as Non-Incremental Threshold
**When:** During 10c_aveiro_ria.py design
**Decision:** Model the Barra–Costa Nova barrier breach as a binary threshold event at 0.60m SLR (conservative) and 0.80m (optimistic), not as a gradual process.
**Rationale:** The Barra–Costa Nova barrier is the only physical separation between the Atlantic Ocean and the Ria de Aveiro lagoon. Its breach is not a gradual process — it is a threshold event that, once triggered, fundamentally and irreversibly changes the lagoon's tidal dynamics. The 0.60–0.80m range reflects geomorphological uncertainty in breach timing, not a continuous sensitivity.
**Impact:** Creates a step-change discontinuity in Zone B disruption costs — a methodological feature that must be explicitly disclosed in the dissertation.
**Sources:** REF-07 (Lopes et al., 2011), REF-08 (Fortunato et al., 2013)
**Dissertation feed:** Chapter 3.3, Chapter 4.3, Chapter 6 (non-linearity and thresholds)

---

## DECISION 013 — No NPV Discounting in Pillar 3 Cumulative Costs
**When:** During Pillar 3 development
**Decision:** All cumulative disruption costs and break-even calculations are reported in nominal terms (no discounting).
**Rationale:** Discounting future climate costs at standard social rates (3.5%) systematically undervalues impacts occurring after 2075 — a recognised limitation of CBA in climate economics (Stern, 2007; Weitzman, 2007). Presenting nominal cumulative costs avoids this distortion and is more transparent. The 3.5% discount rate is retained for adaptation option appraisal only if explicitly requested.
**Dissertation feed:** Chapter 3.3, Chapter 6 (discounting debate)

---

## PIVOT LOG — Key Moments Where Analysis Direction Changed

| # | When | What changed | Why |
|---|------|-------------|-----|
| P1 | After Pillar 1 first run | Added geoid correction variant to all analyses | Results showed large sensitivity to the +0.15m offset; presenting only baseline would understate uncertainty |
| P2 | Before Pillar 3 | Switched from bathtub to compound flood model | Bathtub model answers "what floods"; Pillar 3 needs "how often" — different question, different model |
| P3 | Before 11a_ports.py | Replaced cargo value metric with CDDR | Daily cargo value produces economically indefensible results; CDDR grounded in Suez Canal evidence |
| P4 | Before 11a_ports.py | Switched to savings-based break-even | Railway 100%-elimination assumption inappropriate for port options that reduce but don't eliminate risk |
| P5 | Before 11b_vasco_da_gama.py | Excluded north approach | Elevated viaduct — modelling it would be misleading |
