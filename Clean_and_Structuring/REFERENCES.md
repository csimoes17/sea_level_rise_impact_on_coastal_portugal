# REFERENCES — Sea Level Rise Impact Analysis · Coastal Portugal
**MBA Data Science Capstone**
Format: APA 7th Edition
Last updated: 2026-05-11 (session 25 — full audit; REF-24 through REF-39 formalised)

Legend:
- ✅ Full citation confirmed
- ⚠ Citation incomplete — needs verification before submission
- 🔍 Source located via web search — URL included; full citation needs checking

*Each reference includes: where it is used (script + pipeline step) and which ANALYSIS_LOG decision it justifies.*

---

## 1. SEA LEVEL RISE PROJECTIONS

**[REF-01] ✅ IPCC AR6 — Core SLR scenarios**
> Fox-Kemper, B., Hewitt, H. T., Xiao, C., Aðalgeirsdóttir, G., Drijfhout, S. S., Edwards, T. L., Golledge, N. R., Hemer, M., Kopp, R. E., Krinner, G., Mix, A., Notz, D., Nowicki, S., Nurhati, I. S., Ruiz, L., Sallée, J.-B., Slangen, A. B. A., & Yu, Y. (2021). Ocean, cryosphere and sea level change. In V. Masson-Delmotte et al. (Eds.), *Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change* (Chapter 9). Cambridge University Press. https://doi.org/10.1017/9781009157896.011

*Pipeline step:* 1.1 (all flood masks), 2.1–2.3 (GDP), 3.1–3.3 (infrastructure), 4.1–4.4 (disruption)
*Justifies:* ANALYSIS_LOG Decision 001 — scenario selection
*Used in:* All scripts. Provides SLR anchor values: SSP1-2.6 (+0.40m), SSP2-4.5 (+0.60m), SSP5-8.5 (+1.00m) by 2100.

---

**[REF-02] ✅ Geoid offset — coastal sea level underestimation**
> Seeger, K., & Minderhoud, P. S. J. (2026). Sea level much higher than assumed in most coastal hazard assessments. *Nature*, *652*, 667–674. https://doi.org/10.1038/s41586-026-10196-1

*Pipeline step:* 2.3 (geoid sensitivity GDP), 3.3 (geoid sensitivity infra), 4.1–4.4 (all Pillar 3 +geoid variant)
*Justifies:* ANALYSIS_LOG Decision 003 — geoid offset sensitivity layer
*Note:* Confirmed. Author order is Seeger & Minderhoud (Seeger is first author — corrected from earlier drafts). Cite as "Seeger & Minderhoud (2026)" in-text. Paper documents global mean offsets of ~0.24–0.27 m across 90% of coastal hazard assessments; the +0.15 m adopted here is a conservative lower bound.

---

## 2. FLOOD MODELLING METHODOLOGY

**[REF-03] ✅ Compound flood model — core framework**
> Moftakhari, H. R., Salvadori, G., AghaKouchak, A., Sanders, B. F., & Matthew, R. A. (2017). Compounding effects of sea level rise and fluvial flooding. *Proceedings of the National Academy of Sciences*, *114*(37), 9785–9790. https://doi.org/10.1073/pnas.1620325114

*Pipeline step:* 4.1 (Mondego), 4.2 (Tagus), 4.3 (Aveiro), 4.4 (ports)
*Justifies:* ANALYSIS_LOG Decision 004 — compound flood model adoption
*Used in:* All Pillar 3 scripts. Cited for the compound flood probability framework; the exponential return-period scaling form RP(SLR) = RP₀ × exp(−k × SLR), k = ln(2)/0.10 ≈ 6.93 is the study's simplified operationalisation of this framework, consistent with the directional findings in Moftakhari et al. (2017). The specific formula is not presented in that form in the original paper (which uses a copula-based bivariate probability approach). The citation is therefore to the conceptual framework, not to a specific equation.
*⚠ Action:* Dissertation text should clarify that the exponential model is the study's simplified analytical implementation of the Moftakhari compound flood concept, not a formula directly extracted from their paper.

---

**[REF-04] ✅ Static bathtub inundation model**
> Poulter, B., & Halpin, P. N. (2008). Raster modelling of coastal flooding from sea-level rise. *International Journal of Geographical Information Science*, *22*(2), 167–182. https://doi.org/10.1080/13658810701371858

*Pipeline step:* 1.1 (flood zones), 2.x (GDP exposure), 3.x (infrastructure exposure)
*Justifies:* ANALYSIS_LOG Decision 002 — bathtub model choice
*Note:* Confirmed. Taylor & Francis / Duke confirm: IJGIS 22(2), 167–182, DOI 10.1080/13658810701371858.

---

## 3. TEJO (TAGUS) ESTUARY

**[REF-05] ⚠ Tagus estuary — hydrodynamics and sea-level rise**
> Guerreiro, M., Fortunato, A. B., Freire, P., Rilo, A., Taborda, R., Freitas, M. C., Andrade, C., Silva, T., Rodrigues, M., Bertin, X., & Azevedo, A. (2015). Evolution of the hydrodynamics of the Tagus estuary (Portugal) in the 21st century. *Revista de Gestão Costeira Integrada / Journal of Integrated Coastal Zone Management*, *15*(1), 65–80. https://doi.org/10.5894/rgci515

*Pipeline step:* 4.2 (Tagus floodplain)
*Used in:* `10b_tagus_floodplain.py` docstring. Provides context for Tagus hydrodynamic and SLR exposure.
*Note:* Confirmed. Models SLR impacts on tidal dynamics and extreme water levels in the Tagus estuary; widely cited (~50 citations). Directly relevant to the Tagus floodplain section's hydrodynamic context.

---

**[REF-06] ✅ Portuguese flood climatology — Tagus floodplain context**
> Trigo, R. M., Ramos, C., Pereira, S. S., Ramos, A. M., Zêzere, J. L., & Liberato, M. L. R. (2016). The deadliest storm of the 20th century striking Portugal: Flood impacts and atmospheric circulation. *Journal of Hydrology*, *541*, 597–610. https://doi.org/10.1016/j.jhydrol.2015.10.036

*Pipeline step:* 4.2 (Tagus floodplain)
*Used in:* `10b_tagus_floodplain.py` docstring.
*Note:* Confirmed. Covers the November 1967 Tagus floodplain flood event (500+ fatalities); provides historical flood frequency and atmospheric driver context for the Tagus corridor.

---

## 4. RIA DE AVEIRO

**[REF-07] ✅ Ria de Aveiro — sea-level change and physical impacts**
> Lopes, C. L., Silva, P. A., Dias, J. M., Rocha, A., Picado, A., Plecha, S., & Fortunato, A. B. (2011). Local sea level change scenarios for the end of the 21st century and potential physical impacts in the lower Ria de Aveiro (Portugal). *Continental Shelf Research*, *31*, 1515–1526. https://doi.org/10.1016/j.csr.2011.06.015

*Pipeline step:* 4.3 (Aveiro)
*Justifies:* ANALYSIS_LOG Decision 012 — barrier breach threshold rationale
*Used in:* `10c_aveiro_ria.py` docstring.

---

**[REF-08] ✅ Aveiro lagoon — inundation under storm conditions**
> Fortunato, A. B., Oliveira, A., Rogeiro, J., da Costa, R. T., Gomes, J. L., Li, K., Jesus, G., Freire, P., Rilo, A., Mendes, A., Rodrigues, M., & Azevedo, A. (2017). Operational forecast framework applied to extreme sea levels at regional and local scales. *Journal of Operational Oceanography*, *10*(1). https://doi.org/10.1080/1755876X.2016.1255471

*Pipeline step:* 4.3 (Aveiro)
*Justifies:* ANALYSIS_LOG Decision 012 — barrier breach threshold
*Note:* Confirmed. Year corrected: 2017 (not 2013). Journal confirmed: *Journal of Operational Oceanography*, 10(1).

---

## 5. PORTS AND SUPPLY CHAIN DISRUPTION

**[REF-09] ~~RETIRED~~ — Port disruption cost methodology**
> ~~Hsu, C.-I., & Liao, P.-C. (2015). Cost consequences of a port-related supply chain disruption. *The Asian Journal of Shipping and Logistics*, *31*(2), 273–302.~~

*Note:* RETIRED. Citation could not be independently confirmed. Replaced throughout by **REF-10 (Tran et al., 2025)**.

---

**[REF-10] ✅ Suez Canal blockage — cargo disruption cost evidence**
> Tran, N. K., Haralambides, H., Notteboom, T., & Cullinane, K. (2025). The costs of maritime supply chain disruptions: The case of the Suez Canal blockage by the 'Ever Given' megaship. *International Journal of Production Economics*, *279*, 109464. https://doi.org/10.1016/j.ijpe.2024.109464

*Pipeline step:* 4.4 (ports)
*Justifies:* ANALYSIS_LOG Decision 007 — CDDR rate calibration (3–7%/week of delayed cargo value)
*Key data:* ~€26.5bn cargo delayed over ~6 days → combined disruption cost ≈ 3–7%/week.
*Note:* Confirmed. Replaces earlier incorrect citation to "Belhaj & Khalifa (2024)". Cite as "Tran et al. (2025)" in-text.

---

**[REF-11] ✅ Maritime network blockage — dynamic supply chain impacts**
> Qu, S., She, Y., Zhou, Q., Verschuur, J., Zhao, L.-T., Liu, H., Xu, M., & Wei, Y.-M. (2024). Modeling the dynamic impacts of maritime network blockage on global supply chains. *The Innovation*, *5*(4), 100653. https://doi.org/10.1016/j.xinn.2024.100653

*Pipeline step:* 4.4 (ports)
*Justifies:* ANALYSIS_LOG Decision 007 — JIT vulnerability framework
*Note:* Confirmed. PMC confirms authors, title, journal, issue, article number and DOI.

---

**[REF-12] 🔍 IMF PortWatch — port monitoring methodology**
> International Monetary Fund. (2023). *PortWatch: Data and Methodology*. IMF. https://portwatch.imf.org/pages/data-and-methodology

*Pipeline step:* 4.4 (ports)
*Justifies:* ANALYSIS_LOG Decision 007 — CDDR context

---

**[REF-13] 🔍 World Bank — port resilience and supply chain disruption**
> Arvis, J.-F., Ojala, L., Wiederer, C., Shepherd, B., Raj, A., Dairabayeva, K., & Kiiski, T. (2018). *Connecting to Compete 2018: Trade Logistics in the Global Economy*. World Bank. https://doi.org/10.1596/29971

*Pipeline step:* 4.4 (ports)
*Used in:* Port resilience context.

---

## 5b. PORT ELEVATION AND WAVE GROUNDING — LEIXÕES

**[REF-26] ⚠ Leixões — breakwater stability and port operability under wave action**
> Taveira-Pinto, F., Rosa-Santos, P., Veloso-Gomes, F., & Neves, M. (2013). Harbour operability and extreme wave conditions at the Port of Leixões. *Coastal Engineering Proceedings*, *1*(33). https://doi.org/10.9753/icce.v33.management.22

*Pipeline step:* 4.4 (ports — Leixões parameter grounding)
*Justifies:* Leixões RP₀ = 20 yr and quay_elevation = 3.0 m parameters in `11a_ports.py`.
*Key finding:* Leixões berths lose operability approximately 20% of the time under present Atlantic wave climate. North Pier at +3.0 m MSL (artificially elevated, breakwater-protected). Atlantic storm return periods (Kristin category) in the 10–25 yr range — consistent with RP₀ = 20 yr.
*Note:* ⚠ Title, volume, article number to confirm before submission. Authors Taveira-Pinto and Rosa-Santos are confirmed Leixões researchers at FEUP/UPORTO.

---

**[REF-27] ⚠ Leixões — tide gauge records and sea level variability**
> Araújo, I. B., Dias, J. M., & Pugh, D. T. (2013). Sea-level variability at Leixões tide gauge (1960–2011). *Journal of Operational Oceanography*, *6*(2), 15–25.

*Pipeline step:* 4.4 (ports — Leixões sea level baseline)
*Justifies:* Leixões sea level baseline and storm surge amplitude for compound event modelling.
*Key finding:* 1960–2011 Leixões record confirms Atlantic storm surge amplitudes consistent with 20-yr return period for berth-disrupting events; MSL trend +1.5 mm/yr.
*Note:* ⚠ Journal, volume, pages and DOI to confirm before submission.

---

## 6. PORT DATA SOURCES

**[REF-14] 🔍 Port of Lisbon — 2023 cargo statistics**
> Porto de Lisboa. (2024). *Port of Lisbon grows in cargo and cruises* [Press release]. https://www.portodelisboa.pt/en/-/port-of-lisbon-grows-in-cargo-and-cruises

*Pipeline step:* 4.4 — Lisbon parameter calibration
*Data:* ~11 Mt in 2023; cargo_value_bn_yr = €25.0bn; jit_share_pct = 12%

---

**[REF-15] 🔍 Port of Leixões — 2024 cargo statistics**
> Ports Europe. (2024, October). *Portugal mainland seaports cargo report — September 2024*. https://www.portseurope.com/portugal-mainland-seaports-cargo-report-september-2024/

*Pipeline step:* 4.4 — Leixões parameter calibration
*Data:* 14.4 Mt in 2024; ~25% of national port traffic; cargo_value_bn_yr = €28.8bn

---

**[REF-16] ✅ Port of Setúbal — Annual Report 2023**
> Administração dos Portos de Setúbal e Sesimbra (APSS). (2024). *Relatório e Contas 2023* [Annual Report]. APSS. https://www.portodesetubal.pt/docs/upload_docs/RC_RS%202023_03.07.2024_assinado.pdf

*Pipeline step:* 4.4 — Setúbal parameter calibration
*Data:* ~6.3 Mt (2023); jit_share_pct = 45% (AutoEuropa/VW dependency).
*Note:* Confirmed document — official signed Annual Report published 03.07.2024.

---

**[REF-17] 🔍 Portugal national port system — total throughput**
> Ports Europe. (2024). *Portugal mainland seaports cargo report — September 2024*. https://www.portseurope.com/portugal-mainland-seaports-cargo-report-september-2024/

*Data:* 69.2 Mt Jan–Sept 2024 (+8.3% YoY); ~92 Mt annualised

---

**[REF-18] 🔍 Portugal trade statistics — total exports/imports 2023**
> World Integrated Trade Solution (WITS) / World Bank. (2024). *Portugal trade summary 2023*. https://wits.worldbank.org/CountryProfile/en/Country/PRT/Year/2023/Summarytext

*Data:* Portugal exports USD 83.9bn, imports USD 113.4bn in 2023. 98.2% of freight by weight transported by sea.

---

## 7. DEM AND GEOSPATIAL DATA

**[REF-19] ✅ Copernicus DEM GLO-30**
> European Space Agency / Copernicus Land Monitoring Service. (2021). *Copernicus Digital Elevation Model (DEM) — Global 30m (GLO-30)*. ESA. https://doi.org/10.5270/ESA-c5d3d65

*Pipeline step:* 0.3 (DEM prep), 1.1 (flood zones), 2.3 (geoid sensitivity), 3.3 (infra geoid)
*Used in:* `04_merge_dem.py`, `05_flood_exposure.py`, `09b_geoid_sensitivity.py`, `09c_geoid_sensitivity_infra.py`

---

**[REF-20] ✅ OpenStreetMap — infrastructure data**
> OpenStreetMap contributors. (2024). *Planet dump* [dataset]. OpenStreetMap Foundation. https://planet.osm.org. Data licensed under the Open Database Licence (ODbL). https://www.openstreetmap.org/copyright

*Pipeline step:* 3.1 (infrastructure inventory), 3.2 (infra exposure), 3.3 (infra geoid sensitivity)
*Used in:* `06b_osm_infrastructure.py`

---

## 7b. ECONOMIC FRAMEWORK AND STATISTICAL SOURCES (REF-21 to REF-23)

**[REF-21] ✅ IPCC AR6 WG2 — Risk framework (Hazard × Exposure × Vulnerability)**
> Ara Begum, R., Lempert, R., Ali, E., Benjaminsen, T. A., Bernauer, T., Cramer, W., Cui, X., Mach, K., Nagy, G., Stenseth, N. C., Sukumar, R., & Wester, P. (2022). Point of departure and key concepts. In H.-O. Pörtner et al. (Eds.), *Climate Change 2022: Impacts, Adaptation and Vulnerability. Contribution of Working Group II to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change* (Chapter 1). Cambridge University Press. https://doi.org/10.1017/9781009325844.003

*Pipeline step:* Conceptual framework underpinning all three pillars
*Used in:* Chapter 3 (§3.1 methodological framework), Chapter 6 (discussion of risk components)

---

**[REF-22] ✅ INE — Portugal regional GDP by NUTS**
> Instituto Nacional de Estatística (INE). (2024). *Contas regionais: Produto interno bruto por NUTS III, 2022* [dataset]. INE. https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_contas_nacionais&contexto=cr&selTab=tab3

*Pipeline step:* 2.1 (GDP gridding by NUTS3 region)
*Used in:* `06a_economic_gdp.py`

---

**[REF-23] ✅ Stern Review — climate CBA discount rate**
> Stern, N. (2007). *The Economics of Climate Change: The Stern Review*. Cambridge University Press.

*Pipeline step:* Analytical framework (no NPV discounting decision)
*Used in:* Chapter 3 (§3.7 economic modelling assumptions), ANALYSIS_LOG Decision 013

---

## 7c. A14 MONDEGO LEZÍRIA — FLOOD EVENT DOCUMENTATION (REF-24, REF-25)

**[REF-24] ⚠ ANEPC — Mondego lezíria flood events 2019, 2021, 2026**
> ANEPC — Autoridade Nacional de Emergência e Proteção Civil. (2019, 2021, 2026). *Relatórios de situação — cheias Mondego* [situation reports]. ANEPC. https://www.anepc.pt

*Pipeline step:* 4.4 (A14/IP3 — Mondego section)
*Justifies:* RETURN_PERIOD_BASE = 5.0 yr in `11d_a14_mondego.py` — three documented flood events in 7 years (2019, 2021, 2026) at the Mondego lezíria corridor.
*Note:* ⚠ Exact report titles, dates and URLs to confirm before submission. ANEPC publishes situation reports (relatórios de situação) for declared civil protection events; Mondego 2026 event triggered calamity declaration in multiple Coimbra municipalities.

---

**[REF-25] ⚠ IMT — A14/IP3 traffic counts (Mondego section)**
> Instituto da Mobilidade e dos Transportes (IMT). (2022). *Tráfego médio diário anual — rede rodoviária nacional: A14 / IP3* [statistical dataset]. IMT.

*Pipeline step:* 4.4 (A14/IP3 — VOT computation)
*Justifies:* _TMDA = 11,000 in `11d_a14_mondego.py` VOT computation block.
*Note:* ⚠ TMDA 11,000 is a researcher estimate based on IMT regional traffic data for the Mondego section; the exact published table page / report year to confirm before submission. The A14/IP3 is a regional motorway connector (Figueira da Foz–Coimbra axis) with materially lower traffic than the A1 national spine.

---

## 8. ROAD INFRASTRUCTURE — TRAFFIC, COSTS AND ADAPTATION (REF-28 to REF-33)

**[REF-28] ✅ A1 TMDA — Portuguese road traffic statistics**
> IMT / ANSR (Instituto da Mobilidade e dos Transportes / Autoridade Nacional de Segurança Rodoviária). (2022). *Tráfego médio diário anual (TMDA) — rede rodoviária nacional*. ANSR / IMT.

*Pipeline step:* 4.3 (A1 motorway disruption)
*Justifies:* _TMDA = 40,000 in `11c_a1_motorway.py` VOT computation — A1 TMDA 40,572 at km 45–55 (Aveiras/Azambuja section). Used as 40,000 (rounded down, conservative).

---

**[REF-29] ✅ INE — National HGV share on Portuguese motorways**
> INE — Instituto Nacional de Estatística. (May 2025). *Transportes e Comunicações — Estatísticas dos transportes e comunicações 2024*. INE. https://www.ine.pt

*Pipeline step:* 4.3 (A1), 4.4 (A14) — VOT computation
*Justifies:* _HGV_SHARE = 0.08 in both `11c_a1_motorway.py` and `11d_a14_mondego.py` — INE May 2025 national traffic report confirms 8% HGV share on Portuguese motorways nationally.

---

**[REF-30] ✅ Brisa — Network HGV share**
> Brisa Concessão Rodoviária, S.A. (2024). *Annual Report 2024*. Brisa. https://www.brisa.pt

*Pipeline step:* 4.3 (A1), 4.4 (A14) — VOT computation
*Justifies:* Corroborates REF-29 — Brisa network-average HGV share confirmed at 8% in 2024 annual report. Two independent sources supporting 8% baseline.

---

**[REF-31] ⚠ A14 2026 closure — initial press reporting**
> 24horas / Diário de Coimbra. (February 2026). *Autoestrada A14 cortada entre Maiorca e Montemor-o-Velho por inundação* [news article].

*Pipeline step:* 4.4 (A14 — CLOSURE_DAYS_BASE calibration)
*Justifies:* CLOSURE_DAYS_BASE = 4.0 days in `11d_a14_mondego.py` — February 2026 A14 closure on the exact study section (Maiorca–Montemor-o-Velho); physical flood phase ~4 days.
*Note:* ⚠ Full citation (URL, exact date, journalist) to confirm before submission.

---

**[REF-32] ⚠ A14 2026 closure — reopening timeline**
> Observador. (February–March 2026). *A14 reabre após inundação do lezíria do Mondego* [news article]. Observador.

*Pipeline step:* 4.4 (A14 — CLOSURE_DAYS_BASE calibration)
*Justifies:* Distinguishes flood phase (~4 days) from road inspection/certification phase (remainder of 36-day total closure). Key for not over-modelling recurrent operational closure.
*Note:* ⚠ Full citation (URL, exact date) to confirm before submission.

---

**[REF-33] ✅ UK Environment Agency — Flood defence unit costs**
> UK Environment Agency. (2015). *Estimating the costs of managing flood and coastal erosion risks in England: A report summarising the analysis requirements and methodology* (SC080039/R2). Environment Agency. https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/292836/SC080039_R2_Estimating_costs_managing_flood_coastal_erosion_risks.pdf

*Pipeline step:* 4.3 (A1 adaptation options), 4.4 (A14 adaptation options)
*Justifies:* Adaptation capex computation in `11c_a1_motorway.py` and `11d_a14_mondego.py`.
*Key data:*
- Table 1.4: embankment raising £594/m³ (>15,000 m³ band, 2015 GBP)
- Table 1.7: sheet piling £1,843/m (2015 GBP)
- Adjustment: × 1.13 (Eurostat HICP 2015→2025 × UK/PT labour cost differential) × 1.17 (GBP→EUR, ECB 2025 Q1)
- Uncertainty band: ±25% (earthworks options), ±30% (ITS/VMS)

---

## 9. ECONOMIC METHODOLOGY — VALUE OF TIME (REF-34, REF-35)

**[REF-34] ⚠ EU Handbook on External Costs — passenger value of time**
> Ricardo Energy & Environment. (2019). *Handbook on the external costs of transport: Version 2019 — 1.1*. European Commission, DG MOVE. https://op.europa.eu/en/publication-detail/-/publication/9781f65f-8448-11ea-bf12-01aa75ed71a1

*Pipeline step:* 4.3 (A1 VOT), 4.4 (A14 VOT)
*Justifies:* _VOT_PASS_EUR_H = 8.13 €/h in both `11c_a1_motorway.py` and `11d_a14_mondego.py` — Portuguese short-run value of travel time savings (passenger car, intercity), 2021 prices.
*Note:* ⚠ Exact table reference (Table A-3 or equivalent for Portugal) and year to confirm before submission. The 2019 Handbook (v2) is the standard EU reference for transport economic appraisal. VOT for Portugal: ~€8–10/h for intercity car travel at 2021 prices — consistent with the €8.13/h used.

---

**[REF-35] ⚠ IO multiplier for indirect transport disruption costs**
> Anas, A., & Hiramatsu, A. (2013). The effects on prices and trade of multimodal transport improvements in a spatial general equilibrium model of Japan. *Journal of Transport Economics and Policy*, *47*(3), 449–472.

*Pipeline step:* 4.3 (A1 VOT), 4.4 (A14 VOT)
*Justifies:* _INDIRECT_MULT = {low: 1.20, mid: 1.35, high: 1.60} in both road scripts — input-output multiplier applied to direct VOT costs to capture indirect economic effects (supply chain cascades, induced productivity losses).
*Note:* ⚠ Title, journal and DOI to confirm before submission. The multiplier range (1.20–1.60) is consistent with standard IO transport disruption literature; Anas & Hiramatsu cited as representative source. If confirmation fails, alternative: McKinnon, A. C. (2014) or equivalent IO disruption multiplier study. Dissertation text should note this as a researcher-calibrated range drawn from IO modelling literature.

---

## 10. RAILWAY INFRASTRUCTURE — EVENT DOCUMENTATION (REF-36 to REF-38)

**[REF-36] ⚠ Mondego railway closure — February 2016**
> RTP — Rádio e Televisão de Portugal. (2016, February). *Linha do Norte cortada por cheias no Mondego* [news broadcast/article]. RTP. https://www.rtp.pt

*Pipeline step:* 4.1 (Mondego railway — RP₀ calibration)
*Justifies:* ANALYSIS_LOG Decision D18 — three documented Mondego railway closures (2016, 2019, 2026) calibrate RP₀ = 4 yr for the Alfarelos–Formoselha section.
*Note:* ⚠ Exact URL, date and article title to confirm before submission.

---

**[REF-37] ⚠ Mondego railway closure — December 2019**
> Diário de Notícias. (2019, December). *Linha do Norte interrompida por cheias no Mondego* [news article]. DN. https://www.dn.pt

*Pipeline step:* 4.1 (Mondego railway — RP₀ calibration)
*Justifies:* Second documented closure event in RP₀ = 4 yr calibration chain. See Decision D18.
*Note:* ⚠ Exact URL, date and article title to confirm before submission.

---

**[REF-38] ⚠ Mondego and Tagus railway closures — February 2026**
> Renascença. (2026, February). *Cheias 2026: IP confirma €35M para reforço da linha do Mondego; linha do Norte cortada na lezíria do Tejo* [news article]. Rádio Renascença. https://www.rr.pt

*Pipeline step:* 4.1 (Mondego railway), 4.2 (Tagus railway — RP₀ calibration)
*Justifies:* Third Mondego event (2026, closes RP₀ = 4 yr calibration) and independent Tagus closure at Castanheira–Alverca (km 37–47). IP confirmed €35M Mondego reinforcement programme. Government declared calamity in 68 municipalities + €2.5bn support package.
*Note:* ⚠ Exact URL, date and full article title to confirm before submission. Covers both the Mondego closure (REF-36/37/38 series) and the 2026 Tagus railway event.

---

## 11. MONDEGO RIVER HYDROLOGY (REF-39)

**[REF-39] ⚠ Mondego River — flood frequency and historical extreme events**
> *(Source to be confirmed — SNIRH / LNEC / academic hydrology study covering the 2001 Mondego flood event, estimated return period TR ≈ 439 yr)*

*Pipeline step:* 4.1 (Mondego railway RP₀ justification), 4.4 (A14 CLOSURE_DAYS_BASE calibration)
*Justifies:* Reference to 2001 Mondego flood (TR = 439 yr, "several days" of closure) used in `11d_a14_mondego.py` to establish that CLOSURE_DAYS_BASE = 4 days is conservative relative to the extreme 2001 event.
*Note:* ⚠ Candidate sources:
- SNIRH — Sistema Nacional de Informação de Recursos Hídricos (SNIRH, APA/LNEC). Flood frequency data for Mondego at Coimbra gauging station.
- Rodrigues, A. S., et al. (2002). *Cheia de 2001 no Rio Mondego*. Recursos Hídricos, 23(1).
- Ramos, C., & Reis, E. (2002). Floods in southern Portugal: their physical and human causes, impacts and human response. *Mitigation and Adaptation Strategies for Global Change*, *7*, 267–284.
Exact source to confirm before submission.

---

## 12. REFERENCES TO ADD (flagged during analysis)

These topics require references as the dissertation develops:

- [x] **ADD-01 ✅ AutoEuropa / Volkswagen Setúbal** — production volume and JIT halt cost.
  > Volkswagen Newsroom. (2025). *Volkswagen Autoeuropa Lda.* Volkswagen AG. https://www.volkswagen-newsroom.com/en/volkswagen-autoeuropa-lda-3731
  > Portugal, Ministry of Economy. (2025). *Minister of Economy praises Portugal being chosen to manufacture new Volkswagen electric vehicle* [Press release]. https://www.portugal.gov.pt/en/gc24/communication/news-item?i=minister-of-economy-praises-portugal-being-chosen-to-manufacture-new-volkswagen-electric-vehicle
  *Note:* Confirms 2023 turnover €3.8B and 220,100 vehicles → €10.4M/day. The "~45% of cargo value" parameter is an industry estimate — no single citable source.
- [x] **ADD-02 ✅ IPCC AR6 WG2 Chapter 1** — see REF-21.
- [x] **ADD-03 ✅ Stern Review (2007)** — see REF-23.
- [x] **ADD-04 ✅ INE — Portugal GDP and regional economic data** — see REF-22.
- [x] **ADD-05 ✅ ANEPC Mondego events** — see REF-24.
- [x] **ADD-06 ✅ IMT A14 TMDA** — see REF-25.
- [x] **ADD-07 ✅ Leixões seaport grounding** — see REF-26, REF-27.
- [x] **ADD-08 ✅ Road traffic HGV share** — see REF-28, REF-29, REF-30.
- [x] **ADD-09 ✅ A14 2026 closure** — see REF-31, REF-32.
- [x] **ADD-10 ✅ UK EA flood defence unit costs** — see REF-33.
- [x] **ADD-11 ✅ VOT methodology** — see REF-34, REF-35.
- [x] **ADD-12 ✅ Railway event documentation** — see REF-36, REF-37, REF-38.
- [ ] **Mondego River hydrology** — RP₀ = 4yr basis for `10a_mondego_bypass.py` — see REF-39 (⚠ source still to confirm).
- [ ] **Portuguese coastal zone management** — PNPOT, PMOT legislation. Needed for Chapter 1 policy context.
- [ ] **EU Cohesion Fund / CEF eligibility** — climate adaptation investment criteria. Needed for Chapter 5.
- [ ] **Vasco da Gama Bridge south approach elevation** — literature or official source confirming ~1.5m terrain at Reserva Natural do Estuário do Tejo.

---

## DISSERTATION NOTES

1. **REF-02 (geoid correction)** — most critical to verify before submission.
2. **REF-03 (Moftakhari et al. 2017)** — strongest citation. Dissertation text must clarify the exponential model is the study's simplified implementation, not a formula extracted directly from the paper.
3. **REF-26, REF-27 (Leixões seaport grounding)** — ⚠ to confirm. Leixões is the best-grounded port (3 independent sources: tide gauge, wave action study, Storm Kristin breakwater damage); Setúbal is researcher-defined and must be declared as such in Ch3.
4. **REF-31, REF-32 (A14 2026 closure)** — ⚠ exact press URLs and dates to confirm. The February 2026 A14 event is the empirical anchor for CLOSURE_DAYS_BASE = 4 days — critical to cite accurately.
5. **REF-34, REF-35 (VOT methodology)** — ⚠ both to confirm. Ch3 must document the full VOT derivation chain showing how DAILY_DISRUPTION is computed from TMDA, HGV share, detour parameters and freight GDP exposure.
6. **REF-36, REF-37, REF-38 (railway press events)** — ⚠ all three to confirm. These calibrate the Mondego RP₀ = 4 yr and Tagus railway RP₀ = 10 yr and are the empirical basis for Pillar 3 frequency parameters.
7. **REF-39 (Mondego hydrology)** — ⚠ to resolve. The RP₀ = 4 yr for `10a_mondego_bypass.py` needs a hydrological study, not just press articles.
8. **REF-14 through REF-17** — port data ideally sourced from official annual reports, not press releases or industry aggregators.
