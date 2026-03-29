# ANALYTICAL PIPELINE — Sea Level Rise Impact Analysis · Coastal Portugal
**MBA Data Science Capstone**
*This document is the formal record of the analytical sequence. It maps every script to the research question it answers, its inputs and outputs, and the dissertation section it feeds. Read this alongside ANALYSIS_LOG.md (decisions) and REFERENCES.md (sources).*

---

## OVERARCHING METHODOLOGY

**Primary framework:** IPCC AR6 Risk Assessment Framework
> Risk = f(Hazard, Exposure, Vulnerability) → evaluated across adaptation pathways

**Secondary framework (computational pipeline):** Reproducible research principles
> Each stage has defined inputs, a documented process, and versioned outputs. Results are traceable to parameters.

**SLR scenarios:** IPCC AR6 SSP1-2.6 / SSP2-4.5 / SSP5-8.5 (REF-01)
**Geoid variant:** +0.15m correction for EU Atlantic coast (REF-02)
**Time horizons:** 2030, 2050, 2075, 2100
**Inundation model:** Static bathtub (REF-04)
**Compound flood model:** RP(SLR) = RP₀ × exp(−k × SLR), k ≈ 6.93 (REF-03)

---

## STAGE 0 — DATA ACQUISITION & PREPARATION
*Dissertation section: Chapter 3.1 — Data Sources*

### Step 0.1 — Sea Level Trend Analysis
**Scripts:** `meansealeveltrend_estimation.py`, `meansealeveltrend_estimation_from1993.py`
**Research question:** What is the observed SLR trend at Portuguese tide gauges, and does it align with IPCC AR6 projections?
**Input:** Tide gauge records (Cascais and/or other Portuguese stations)
**Output:** Trend estimates (mm/yr), baseline validation against IPCC AR6
**Dissertation feed:** Chapter 3.1 — validates use of IPCC AR6 projections as the study's SLR scenario basis
**References:** REF-01

---

### Step 0.2 — Sea Level Data Cleaning
**Script:** `sealevel_cleaner.py`
**Research question:** Are the tide gauge records quality-sufficient for trend analysis?
**Input:** Raw tide gauge data
**Output:** Cleaned time series for trend estimation
**Dissertation feed:** Chapter 3.1 — data quality note

---

### Step 0.3 — DEM Acquisition & Merging
**Script:** `04_merge_dem.py`
*[Logical step 3; filename reflects merge operation on pre-downloaded tiles]*
**Research question:** What is the terrain elevation across coastal Portugal at sufficient resolution for flood modelling?
**Input:** Copernicus GLO-30 DEM tiles (30m resolution, EPSG:4326) (REF-19)
**Output:** `dem_portugal_merged.tif` — single merged DEM covering the study area
**Dissertation feed:** Chapter 3.2 — DEM specification, resolution justification, EPSG:4326 choice
**References:** REF-19

---

## STAGE 1 — FLOOD ZONE GENERATION (BATHTUB MODEL)
*Dissertation section: Chapter 3.2 — Inundation Methodology*
*IPCC framework role: HAZARD definition*

### Step 1.1 — Static Inundation Masks
**Script:** `05_flood_exposure.py`
**Research question:** Which land pixels are inundated under each SLR scenario and year?
**Input:** `dem_portugal_merged.tif`, SLR scenario values (REF-01)
**Output:**
- `dem_flood_{year}_{scenario}.tif` — 24 binary GeoTIFF flood masks (8 years × 3 scenarios)
- `flood_scenario_summary.csv` — flooded pixels and area (km²) per scenario/year
**Method:** Pixel floods when `0 < elevation ≤ SLR`. Ocean pixels (elevation = 0) excluded.
**Dissertation feed:** Chapter 3.2 — bathtub model description, equation, limitation statement
**References:** REF-04 (bathtub model), REF-01 (SLR values)

---

### Step 1.2 — Flood Animation
**Script:** `09_flood_animation.py`
**Research question:** How does the inundation extent evolve visually across scenarios and decades?
**Input:** Flood masks from Step 1.1
**Output:** Animation MP4s — one per scenario
**Dissertation feed:** Chapter 4 figures / supplementary material

---

## STAGE 2 — PILLAR 1: GDP AT RISK
*Dissertation section: Chapter 4.1*
*IPCC framework role: EXPOSURE — economic flow*

### Step 2.1 — GDP Spatial Allocation
**Script:** `06a_economic_gdp.py`
**Research question:** How is GDP spatially distributed across coastal Portugal?
**Input:** NUTS3 GDP data (REF: INE — to be added), population/land use proxies
**Output:** `gdp_grid.tif` — GDP allocated to 30m raster cells
**Method:** Proportional allocation within NUTS3 boundaries
**Dissertation feed:** Chapter 3.3 — GDP gridding methodology and assumptions
**References:** INE regional GDP data (to be added to REFERENCES.md)

---

### Step 2.2 — GDP Flood Exposure
**Script:** `05_flood_exposure.py` (GDP overlay component)
*(Note: GDP exposure is computed within the same script as the flood masks or a sub-module — verify)*
**Research question:** What annual GDP is exposed to inundation under each scenario?
**Input:** `gdp_grid.tif`, flood masks from Step 1.1
**Output:** `gdp_exposure_summary.csv`
**Key results (SSP5-8.5, 2100):**
- Baseline: 340 km² / €5.302bn exposed
- +Geoid: 396 km² / €6.350bn exposed (+20%)
**Dissertation feed:** Chapter 4.1 — GDP at risk headline results

---

### Step 2.3 — Geoid Sensitivity (GDP)
**Script:** `09b_geoid_sensitivity.py`
**Research question:** How much does the +0.15m geoid correction amplify GDP exposure, particularly in near-term scenarios?
**Input:** `gdp_grid.tif`, flood masks at baseline and +geoid SLR values
**Output:** `geoid_sensitivity_summary.csv`, `geoid_sensitivity_area.csv`, `geoid_sensitivity_gdp.csv`
**Key finding:** Geoid amplification is largest in early years (SSP1-2.6 2100: +74%). Effect diminishes in later high-emission scenarios as large areas flood regardless.
**Dissertation feed:** Chapter 4.1 — geoid sensitivity analysis; Chapter 5 — why early adaptation matters
**References:** REF-02

---

### Step 2.4 — Tableau Export (Pillar 1)
**Script:** `07_export_tableau.py` (Pillar 1 component)
**Output:** `06_geoid_sensitivity_tableau.csv` — 24 rows (3 scenarios × 4 years × 2 variants)
**Dissertation feed:** Tableau Dashboard 2 — GDP at risk

---

## STAGE 3 — PILLAR 2: INFRASTRUCTURE REPLACEMENT COST
*Dissertation section: Chapter 4.2*
*IPCC framework role: EXPOSURE — physical asset stock*

### Step 3.1 — Infrastructure Inventory (OSM)
**Script:** `06b_osm_infrastructure.py`
**Research question:** What is the spatial inventory and replacement value of infrastructure assets in coastal Portugal?
**Input:** OpenStreetMap data extract (REF-20)
**Output:** `infrastructure_inventory.csv` — buildings, roads, railways, utilities with coordinates and replacement cost estimates
**Unit costs applied:**
- Buildings: €800/m²
- Roads: €1.5M/km
- Railways: €3.0M/km
- Utilities: €0.5M/km
**Dissertation feed:** Chapter 3.3 — infrastructure data source, unit cost assumptions and justification
**References:** REF-20

---

### Step 3.2 — Infrastructure Flood Exposure
**Script:** `06b_sensitivity.py` *(or 07_infra_exposure.py — verify exact filename)*
**Research question:** What is the total replacement cost of infrastructure exposed under each scenario?
**Input:** `infrastructure_inventory.csv`, flood masks from Step 1.1
**Output:** `infra_exposure_summary.csv`
**Dissertation feed:** Chapter 4.2 — infrastructure cost results

---

### Step 3.3 — Geoid Sensitivity (Infrastructure)
**Script:** `09c_geoid_sensitivity_infra.py`
**Research question:** How does the +0.15m geoid correction affect infrastructure exposure estimates?
**Input:** `infrastructure_inventory.csv`, baseline and +geoid flood masks
**Output:** `infra_geoid_sensitivity_summary.csv`, `infra_geoid_sensitivity_detail.csv`
**Key results (SSP5-8.5, 2100):**
- Baseline: €82.84bn | +Geoid: €95.10bn (+14.8%)
- Buildings dominate (99% of total cost)
- Geoid amplification largest in early years: SSP1-2.6 2030 = +279%
**Dissertation feed:** Chapter 4.2 — geoid sensitivity; Chapter 5 — near-term investment urgency argument
**References:** REF-02, REF-20

---

### Step 3.4 — Tableau Export (Pillar 2)
**Script:** `07_export_tableau.py` (Pillar 2 component)
**Output:** `07_infra_geoid_tableau.csv` — 24 rows × 19 columns
**Dissertation feed:** Tableau Dashboard 3 — Infrastructure replacement cost

---

## STAGE 4 — PILLAR 3: CRITICAL INFRASTRUCTURE DISRUPTION
*Dissertation section: Chapter 4.3*
*IPCC framework role: VULNERABILITY + RISK + ADAPTATION*

### Pillar 3 Methodology (applied to all Step 4.x scripts)

**Compound flood model** (REF-03):
```
RP(SLR) = RP₀ × exp(−k × SLR)     k = ln(2)/0.10 ≈ 6.93
```
*Interpretation: flood return period halves for every 10cm of SLR*

**Disruption cost model:**
```
closure_days/yr = (1/RP) × CLOSURE_DAYS_BASE × (1 + SLR/0.50)   [cap: 365]
annual_disruption_cost = closure_days/yr × DAILY_DISRUPTION_RATE
```

**Break-even analysis:**
```
Year when cumulative(avoided disruption cost) ≥ adaptation investment
```

**Three adaptation options tested per section:**
- Option 1: Physical hardening (raises effective flood threshold)
- Option 2: Alternative routing / structural barrier (avoids or deflects inundation)
- Option 3: Operational resilience protocol (reduces closure duration per event, −50%)

---

### Step 4.1 — Mondego Valley Section (Linha do Norte, km ~250–265)
**Script:** `10a_mondego_bypass.py`
**Infrastructure type:** Railway (Linha do Norte)
**Flood mechanism:** Fluvial/tidal backwater (Mondego River, not direct SLR)
**Parameters:** Elev ~1.0m | RP₀=4yr | Closure=5 days | Disruption=€1.0M/day
**Outputs:** `mondego_flood_frequency.csv`, `mondego_disruption_cost.csv`, `mondego_bypass_comparison.csv`
**Key findings:**
- Cumulative disruption 2100: €43.6bn (baseline) / €136.9bn (+geoid)
- Best break-even: Option 1 viaduct, 2034 (+geoid, mid)
- Option 3 (western bypass) is circular — route exposed to SLR at Figueira da Foz
**Dissertation feed:** Chapter 4.3 — Mondego section analysis
**References:** REF-03 (compound flood model)

---

### Step 4.2 — Tagus Floodplain Section (Linha do Norte, km 37–47)
**Script:** `10b_tagus_floodplain.py`
**Infrastructure type:** Railway (Linha do Norte)
**Flood mechanism:** Compound estuarine/fluvial
**Parameters:** Elev 2.0m | RP₀=10yr | Closure=4 days | Disruption=€1.5M/day
**Outputs:** `tagus_flood_frequency.csv` (24 rows), `tagus_disruption_cost.csv` (456 rows), `tagus_bypass_comparison.csv` (18 rows)
**Key findings:**
- No permanent inundation by 2100 (max SLR 1.15m < 2.0m track elevation)
- Cumulative disruption 2100: €13.4bn (baseline) / €20.1bn (+geoid)
- Best break-even: Option 2 barriers, 2033 (+geoid, mid)
**Dissertation feed:** Chapter 4.3 — Tagus section analysis
**References:** REF-03, REF-05, REF-06

---

### Step 4.3 — Ria de Aveiro / Ovar Section (Linha do Norte, km 251–275)
**Script:** `10c_aveiro_ria.py`
**Infrastructure type:** Railway (Linha do Norte)
**Flood mechanism:** Multi-source (direct SLR + tidal lagoon + barrier breach)
**Parameters:** Two sub-zones (A: elev 1.2m, RP₀=7yr; B: elev 0.7m, RP₀=3yr)
**Outputs:** `aveiro_flood_frequency.csv` (48 rows), `aveiro_disruption_cost.csv` (456 rows), `aveiro_bypass_comparison.csv` (18 rows), `aveiro_breach_thresholds.csv` (6 rows)
**Key findings:**
- Zone B: only section in study with permanent track inundation before 2100
  (SSP5-8.5 baseline: 2075 | +geoid: 2063)
- Cumulative disruption 2100 (A+B): €25.0bn (baseline) / €33.8bn (+geoid)
- Earliest break-even of all railway sections: 2030 (+geoid, Option 1)
- Option 2 (barrier) is a system-level intervention — rail is 15–20% of total cost; co-benefits include Aveiro city flood protection and 80k residents
**Dissertation feed:** Chapter 4.3 — Aveiro section analysis
**References:** REF-03, REF-07, REF-08

---

### Step 4.4 — Major Commercial Ports (Leixões, Lisbon, Setúbal)
**Script:** `11a_ports.py`
**Infrastructure type:** Port infrastructure (road/quay access)
**Flood mechanism:** Atlantic compound (Leixões) | Tagus estuarine (Lisbon) | Sado estuarine (Setúbal)
**Disruption methodology:** Composite Daily Disruption Rate (CDDR) — see ANALYSIS_LOG.md §4
**Outputs:** `ports_flood_frequency.csv` (72 rows), `ports_disruption_cost.csv` (1,368 rows), `ports_adaptation_comparison.csv` (54 rows)
**Key findings:**
- No permanent inundation (lowest quay: 2.5m Setúbal > max SLR+geoid 1.15m)
- Cumulative disruption 2100 (3 ports, mid-CDDR):
  - Baseline: €55.44bn | +Geoid: €96.15bn
- Lisbon: highest single-asset disruption (€27.28bn / €43.11bn)
- Setúbal: highest JIT concentration (45%) — AutoEuropa dependency
- Option 3 (Operational Protocol): cheapest, fastest payback across all ports
**Dissertation feed:** Chapter 4.3 — ports analysis
**References:** REF-03, REF-09, REF-10, REF-11, REF-12, REF-14, REF-15, REF-16, REF-17, REF-18

---

### Step 4.5 — Vasco da Gama Bridge South Approach ⏳ PENDING
**Script:** `11b_vasco_da_gama.py` *(to be written)*
**Infrastructure type:** Road bridge approach (A12 south, Alcochete side)
**Flood mechanism:** Direct tidal inundation of low-lying approach road through Tagus Natural Reserve
**Rationale for inclusion:** North approach excluded — elevated viaduct structure throughout; south approach runs at ~1.5m elevation through tidal marshland
**Planned outputs:** TBD
**Dissertation feed:** Chapter 4.3 — road infrastructure exposure

---

### Step 4.6 — A1 Motorway, Lezíria do Tejo Section ⏳ PENDING
**Script:** `11c_a1_motorway.py` *(to be written)*
**Infrastructure type:** Motorway (primary north-south road artery)
**Flood mechanism:** Fluvial/estuarine — Tagus floodplain near Santarém/Vila Franca de Xira
**Dissertation feed:** Chapter 4.3 — motorway network disruption

---

## STAGE 5 — TABLEAU DASHBOARDS ⏳ PENDING
*Dissertation section: Chapter 4 figures (embedded) + Appendix*

| Dashboard | Data source | Status |
|---|---|---|
| 1: Flood area map (animated by year/scenario) | Flood GeoTIFFs from Step 1.1 | ⏳ |
| 2: GDP at risk — scenario + geoid sensitivity | `06_geoid_sensitivity_tableau.csv` | ⏳ |
| 3: Infrastructure replacement cost | `07_infra_geoid_tableau.csv` | ⏳ |
| 4: Linha do Norte disruption (3 sections) | Mondego/Tagus/Aveiro CSVs | ⏳ |
| 5: Break-even analysis — all assets | All bypass_comparison CSVs | ⏳ |

---

## STAGE 6 — DISSERTATION ⏳ PENDING

| Chapter | Feeds from |
|---|---|
| 1: Introduction & research questions | — |
| 2: Literature review | REFERENCES.md |
| 3: Data & methodology | Steps 0–1, ANALYSIS_LOG.md |
| 4: Results (Pillars 1–3) | Steps 2–4 |
| 5: Adaptation cost-benefit | Step 4 break-even tables |
| 6: Discussion & conclusions | ANALYSIS_LOG.md (limitations), cross-section comparison |

---

## OUTPUT FILE REGISTRY

| File | Produced by | Stage | Rows |
|------|-------------|-------|------|
| `flood_scenario_summary.csv` | `05_flood_exposure.py` | 1.1 | 24 |
| `gdp_exposure_summary.csv` | `06a_economic_gdp.py` | 2.2 | — |
| `geoid_sensitivity_summary.csv` | `09b_geoid_sensitivity.py` | 2.3 | 12 |
| `geoid_sensitivity_detail.csv` | `09b_geoid_sensitivity.py` | 2.3 | 24 |
| `infrastructure_inventory.csv` | `06b_osm_infrastructure.py` | 3.1 | — |
| `infra_exposure_summary.csv` | `06b_sensitivity.py` | 3.2 | — |
| `infra_geoid_sensitivity_summary.csv` | `09c_geoid_sensitivity_infra.py` | 3.3 | 12 |
| `infra_geoid_sensitivity_detail.csv` | `09c_geoid_sensitivity_infra.py` | 3.3 | 24 |
| `06_geoid_sensitivity_tableau.csv` | `07_export_tableau.py` | 2.4 | 24 |
| `07_infra_geoid_tableau.csv` | `07_export_tableau.py` | 3.4 | 24 |
| `mondego_flood_frequency.csv` | `10a_mondego_bypass.py` | 4.1 | — |
| `mondego_disruption_cost.csv` | `10a_mondego_bypass.py` | 4.1 | — |
| `mondego_bypass_comparison.csv` | `10a_mondego_bypass.py` | 4.1 | — |
| `tagus_flood_frequency.csv` | `10b_tagus_floodplain.py` | 4.2 | 24 |
| `tagus_disruption_cost.csv` | `10b_tagus_floodplain.py` | 4.2 | 456 |
| `tagus_bypass_comparison.csv` | `10b_tagus_floodplain.py` | 4.2 | 18 |
| `aveiro_flood_frequency.csv` | `10c_aveiro_ria.py` | 4.3 | 48 |
| `aveiro_disruption_cost.csv` | `10c_aveiro_ria.py` | 4.3 | 456 |
| `aveiro_bypass_comparison.csv` | `10c_aveiro_ria.py` | 4.3 | 18 |
| `aveiro_breach_thresholds.csv` | `10c_aveiro_ria.py` | 4.3 | 6 |
| `ports_flood_frequency.csv` | `11a_ports.py` | 4.4 | 72 |
| `ports_disruption_cost.csv` | `11a_ports.py` | 4.4 | 1,368 |
| `ports_adaptation_comparison.csv` | `11a_ports.py` | 4.4 | 54 |
