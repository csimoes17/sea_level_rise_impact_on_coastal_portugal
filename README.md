# Sea Level Rise Impact on Coastal Portugal

MBA in Data Science capstone project analyzing the projected impact of sea
level rise on coastal Portugal — combining climate projections, elevation
and flood-exposure modeling, infrastructure and economic risk analysis, and
statistical/ML forecasting of observed sea level trends.

**Status:** Submitted for academic review. Content may change based on
instructor feedback.

The full written report (methodology, results, and discussion) is available
in this repo as `Sea Level Rise Impact on Coastal Portugal_en.docx` (English)
and `_pt.docx` (Portuguese).

## Repository structure

```
Data Sources/    Raw and reference datasets used throughout the pipeline
Scripts/         Python pipeline, numbered in processing order
*.docx           Written report, submitted for evaluation (EN / PT)
*.pptx           Project presentation
```

## Data Sources

- Tide gauge sea level records (Cascais, Lagos, Leixões, Sines)
- Copernicus DEM elevation raster (`COP DEM 1.tif`)
- National administrative boundaries (`nuts3_wgs84.geojson`)
- Regional GDP / economic data (`pordata.xlsx`)

Two source files used in the original analysis are not included here due to
GitHub's 100MB file size limit: a second Copernicus DEM tile (`COP DEM 2.tif`)
and the national cadastral boundary dataset (`Continente_CAOP2024_1.gpkg`).

## Scripts

The pipeline runs roughly in numeric order:

- `00`–`07` — data preparation: requirements, DEM merging, flood exposure
  modeling, economic (GDP) and infrastructure (OSM) exposure layers, geoid
  sensitivity, Tableau export
- `09`–`10` — flood animations and regional case studies (ports, Tagus/A1
  corridor, Mondego/A14, Vasco da Gama bridge, Aveiro ria)
- `11` — further regional case studies (motorway network, Algarve — Faro/
  Olhão and Portimão/Arade)
- `12` — consolidation of adaptation and disruption-cost pillars
- `13` — statistical and machine learning modeling of sea level trends,
  scenario analysis, and coastal risk clustering

## Note on project history

This repository's commit history reflects the project's actual working
timeline (November 2025 – July 2026), reconstructed from the original file
modification dates. The current file structure shown above reflects the
version submitted for evaluation; earlier exploratory work and intermediate
outputs remain visible in the commit history. This structure will be updated
if the project is revised following instructor feedback.
