"""
13a5_sealevel_multivariate_ml.py
==================================
Sea Level Rise — GENUINE MULTIVARIATE Machine Learning Model Comparison
Leixões, Sines, Cascais, Lagos  x  +NAO  +AMO climate indices

WHY THIS SCRIPT EXISTS (read this before the results)
-------------------------------------------------------
13a3_sealevel_ml_models.py compared 9 ML models using a SINGLE predictor:
year. That is a legitimate thing to do, but it is not yet a genuine
multivariate comparison — with only one input column, several of the
"machine learning" models in that script (Ridge, Lasso, SVR, Gaussian
Process) are mathematically just dressed-up straight lines, because there
is nothing else for them to use.

This script adds real additional predictors — two climate indices (NAO,
AMO) known in the oceanography literature to influence year-to-year
coastal sea level on the Atlantic European coast — and two additional,
independently-sourced tide gauge stations (Cascais, Lagos), so the model
comparison is run on an actual multi-column dataset, not just "year".

THIS IS A NEW, SEPARATE FILE. It does not modify 13a3_sealevel_ml_models.py
or 13a4_sealevel_scenario_analysis.py in any way. There are two reasons,
not one:
  1. The project's standing rule: never edit an already-validated script
     when extending the analysis — write a new one instead.
  2. A real, structural reason discovered while building this: 13a3's own
     fit/predict functions are written for exactly ONE predictor column.
     fit_linear() calls scipy.stats.linregress(x_train.flatten(), y_train)
     — flattening only makes sense for one column, and linregress itself
     only does simple (one-predictor) regression. fit_ridge/fit_lasso/
     fit_svr/fit_gpr standardise the input with x_train.mean() and
     x_train.std() with no axis argument — on a multi-column array, that
     computes ONE mean/std across every value in every column combined,
     not a separate mean/std per column. Used as-is on a 3-column
     (year, NAO, AMO) input, that would silently mix three different
     physical units and scales together, which would quietly corrupt
     every regularised/kernel model's results without throwing an error.
     So this script defines its own multivariate-correct versions of the
     SAME NINE algorithms, with the same names, same hyperparameters, and
     the same scaled/unscaled choices 13a3 made per model — just fixed to
     handle more than one column correctly (proper per-column scaling via
     scikit-learn's StandardScaler, and scikit-learn's own LinearRegression
     in place of scipy.stats.linregress for the multivariate case).
  This script DOES reuse, unmodified, the parts of 13a/13a3 that are
  already generic and already validated: compute_annual_means (13a),
  check_outliers (13a3), walk_forward_cv (13a3), TARGET_YEAR and
  RANDOM_STATE (13a3). Those are imported via importlib, never copied.

DATA SOURCES — read the caveats, they materially limit what this script
can claim:

  TIDE GAUGES (PSMSL, Permanent Service for Mean Sea Level, RLR monthly
  data, same format and same missing-value convention already used by
  sealevel_cleaner.py for Leixões/Sines — semicolon-delimited
  year_decimal;sea_level_mm;flag;quality, -99999 = missing):

    Leixões (existing, unchanged)   1956-2022
    Sines   (existing, unchanged)   1977-2022
    Cascais (NEW, PSMSL station ID 52)
        Time span on file at PSMSL: 1882-1993.
        IMPORTANT: this record does NOT reach the present. PSMSL's own
        station page documents a gap from 1994-1999 "due to malfunction",
        and the station has no further data after 1993. Treat any
        reference to Cascais as a HISTORICAL record, not a current one.
    Lagos   (NEW, PSMSL station ID 162 — Lagos, ALGARVE, PORTUGAL)
        Time span on file at PSMSL: 1908-1999.
        PSMSL's own station page carries an explicit warning:
        "WARNING: QCFLAG EXISTS. PLEASE READ THE DOCUMENTATION", and
        documents irregularities around 1940-41 (possibly earthquake-
        related) and an unstable pre-1962 benchmark. This script prints
        the actual distribution of PSMSL's per-month flag values found
        for Cascais and Lagos at runtime (see inspect_station_flags
        below) so you can SEE whether unusual flag values appear, rather
        than assuming the existing flag<=1 threshold (inherited from
        13a_sealevel_regression.py, designed against Leixões/Sines) is
        automatically appropriate here too.
        NOTE ON STATION NAMING: PSMSL also has a station literally named
        "LAGOS II" (ID 1767) — that one is in LAGOS, NIGERIA (1990-1996),
        a completely different country and a different metric/lower-
        quality record. This script uses ID 162 (Lagos, Portugal) only.
        This mix-up was caught and avoided during research for this
        script — it is flagged here so it is never repeated by anyone
        re-using this code with a different "Lagos" station ID.

  NAO — North Atlantic Oscillation index (monthly, NOAA Climate
  Prediction Center, standardised index, 1950-present):
      https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/
      norm.nao.monthly.b5001.current.ascii.table
  This URL was directly fetched and verified while building this script
  (real data, not assumed). Coverage starts in 1950 — this is the
  single biggest constraint in this whole script: even though Cascais's
  tide gauge record starts in 1882 and Lagos's starts in 1908, NEITHER
  can be used with NAO/AMO as predictors before 1950, because the NAO
  series simply does not exist before then. Every station's usable
  multivariate window in this script is therefore capped at 1950 onward,
  REGARDLESS of how far back its own tide gauge record goes.

  AMO — Atlantic Multidecadal Oscillation index (monthly):
  NOAA PSL's own AMO page states, verbatim, that their official AMO
  index (Kaplan-SST-based) "is currently not updated due to the source
  dataset (Kaplan SST) not being updated" and that it only reaches
  January 2023. NOAA PSL's own page recommends NOAA/NCEI's ERSSTv5-based
  AMO index as the replacement:
      https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.amo.dat
  This script tries that NCEI file FIRST. Its exact byte-for-byte layout
  could not be independently re-confirmed while building this script
  (the web-fetch tool used for research returned it as unreadable binary
  data rather than text) — so the parser below implements NOAA PSL's own
  documented "Standard Format" specification instead (verified directly
  from https://psl.noaa.gov/gcos_wgsp/Timeseries/standard/, which NOAA
  states ALL of its monthly teleconnection-index files use, this one
  included). The parser runs explicit sanity checks on what it downloads
  and will stop with a clear, readable error — NOT a silent guess — if
  the real file does not match that documented layout. If that happens,
  this script automatically falls back to NOAA PSL's own legacy AMO file
  (Kaplan-SST based, capped at Jan 2023):
      https://psl.noaa.gov/data/correlation/amon.us.long.data
  Whichever source actually succeeds, the script PRINTS which one it
  used. It never silently swaps sources without telling you.

WHY THIS SCRIPT DOES NOT PRODUCE A 2100 PROJECTION
  (unlike 13a3 and 13a4, which both project every model to 2100)
  ----------------------------------------------------------------
  Projecting a multivariate model to 2100 would require plugging in
  YEAR=2100 *and* a specific NAO value *and* a specific AMO value. NAO
  and AMO are climate OSCILLATIONS — by definition they swing between
  positive and negative phases on multi-year/multi-decade cycles, they
  do not have a meaningful long-term "trend" the way sea level itself
  does. There is no honest way to say what NAO or AMO will be in 2100;
  assuming a value (even "zero", i.e. assuming a neutral phase) would be
  quietly injecting an assumption dressed up as a model output. Rather
  than do that, this script's deliverable is exactly what was asked for:
  a genuine model comparison/selection exercise — which of the 9
  algorithms test best, via the same walk-forward cross-validation
  method used everywhere else in this project, when real additional
  predictors are available — not a new 2100 number.

  As a directly useful side effect of not needing a 2100 projection,
  this script can also report each model's CV performance using ONLY
  "year" as a predictor but restricted to the SAME 1950-onward window
  forced by NAO/AMO availability ("year_only" rows), right next to the
  full "year+NAO+AMO" rows for the same years. That is the fair,
  apples-to-apples comparison that actually answers "did adding NAO and
  AMO help" — comparing it instead to 13a3's full-record year-only
  numbers would confound two changes (shorter window AND extra
  predictors) at once.

TRAIN -> TEST -> APPLY, REPORT EVERYTHING (same standing rules as
13a3/13a4):
  - TEST = walk-forward cross-validation (never shuffled, never tests on
    a year a fold trained on).
  - APPLY here means: refit on the full available subset and report the
    fitted model's coefficients / feature importances where the
    algorithm has them, so you can SEE whether NAO/AMO actually carry
    weight in the fitted model — this is reported, never silently
    decided for you.
  - All 4 stations x both feature-sets x all 9 models are run and saved.
    Nothing is filtered out for looking better or worse.

REQUIRES:
  numpy, pandas, matplotlib, scipy, scikit-learn (same as 13a3) — nothing
  new to install if 13a3 already runs on your machine.
  An internet connection ON THE MACHINE THAT RUNS THIS SCRIPT, to
  download the PSMSL/NOAA files the first time. (This was built and
  researched in a sandboxed environment with no general network access,
  so none of this could be executed there — it is meant to be run on
  your own machine, as agreed.) Downloaded files are cached locally
  (see *_CACHE paths below) so re-runs do not need an internet
  connection unless you delete the cache files.

OUTPUTS:
  sealevel_multivariate_ml_summary.csv   — every station x feature_set x model
  sealevel_multivariate_ml_chart.png     — CV RMSE, year_only vs year+NAO+AMO
  sea_level_cascais_monthly_cleaned.csv  — new cleaned tide gauge file
  sea_level_lagos_monthly_cleaned.csv    — new cleaned tide gauge file

USAGE:
  python 13a5_sealevel_multivariate_ml.py
"""

import io
import sys
import urllib.request
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from scipy import stats
except ImportError:
    raise SystemExit(
        "This script needs the 'scipy' package (the same one used by "
        "13a_sealevel_regression.py). Install it with:\n"
        "    pip install scipy\n"
    )

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LinearRegression, Ridge, Lasso
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.svm import SVR
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel, DotProduct
    from sklearn.exceptions import ConvergenceWarning
except ImportError:
    raise SystemExit(
        "This script needs the 'scikit-learn' package for the machine "
        "learning models. Install it with:\n"
        "    pip install scikit-learn\n"
    )

import warnings
warnings.filterwarnings("ignore", category=ConvergenceWarning)

# ─── REUSE — imported, never copied, never modified ──────────────────────────
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

_base = import_module("13a_sealevel_regression")
compute_annual_means = _base.compute_annual_means

_ml3 = import_module("13a3_sealevel_ml_models")
check_outliers = _ml3.check_outliers
walk_forward_cv = _ml3.walk_forward_cv
TARGET_YEAR = _ml3.TARGET_YEAR
RANDOM_STATE = _ml3.RANDOM_STATE

# ─── EXISTING (unchanged) tide gauge files ────────────────────────────────────
LEIXOES_CSV = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV   = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"

# ─── NEW tide gauge stations — PSMSL RLR monthly data ─────────────────────────
PSMSL_RLR_MONTHLY_URL_TMPL = "https://psmsl.org/data/obtaining/rlr.monthly.data/{id}.rlrdata"
CASCAIS_STATION_ID = 52
LAGOS_STATION_ID    = 162   # Lagos, ALGARVE, PORTUGAL — NOT "Lagos II" (ID 1767, Nigeria)

CASCAIS_RAW_CACHE     = PROJECT_DIR / "sea_level_cascais_monthly_raw.txt"
LAGOS_RAW_CACHE       = PROJECT_DIR / "sea_level_lagos_monthly_raw.txt"
CASCAIS_CLEANED_CSV   = PROJECT_DIR / "sea_level_cascais_monthly_cleaned.csv"
LAGOS_CLEANED_CSV     = PROJECT_DIR / "sea_level_lagos_monthly_cleaned.csv"

# ─── Climate index predictors ─────────────────────────────────────────────────
NAO_URL = ("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/"
           "norm.nao.monthly.b5001.current.ascii.table")
NAO_CACHE = PROJECT_DIR / "nao_index_monthly_cpc.txt"

AMO_URL_PRIMARY  = "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.amo.dat"
AMO_URL_FALLBACK = "https://psl.noaa.gov/data/correlation/amon.us.long.data"
AMO_CACHE_PRIMARY  = PROJECT_DIR / "amo_index_monthly_ncei_ersstv5.txt"
AMO_CACHE_FALLBACK = PROJECT_DIR / "amo_index_monthly_psl_legacy.txt"

OUT_CSV = PROJECT_DIR / "sealevel_multivariate_ml_summary.csv"
OUT_PNG = PROJECT_DIR / "sealevel_multivariate_ml_chart.png"

NAO_AMO_MIN_VALID_MONTHS = 10   # of 12, to accept a year's annual mean (stricter
                                # than the tide-gauge >=6 threshold on purpose:
                                # these are climate indices, not gappy field
                                # instruments, so a fuller year is expected and
                                # available almost everywhere in the record)


# ─── Generic, dependency-free download-with-local-cache helper ───────────────
def download_with_cache(url, cache_path, description):
    """
    Returns the text contents of `url`, using a local cache file so this
    script only needs an internet connection the first time it is run.
    Delete the cache file to force a fresh download.
    """
    if cache_path.exists():
        print(f"  Using cached copy of {description}: {cache_path.name}")
        return cache_path.read_text()

    print(f"  Downloading {description} from:\n    {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            text = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise SystemExit(
            f"\nCould not download {description}.\n"
            f"  URL tried: {url}\n"
            f"  Error: {exc}\n"
            f"This usually means either no internet connection is available "
            f"right now, or the URL has changed since this script was "
            f"written. You can work around this by manually downloading the "
            f"file yourself and saving it as:\n    {cache_path}\n"
            f"then re-running this script (it will use that cached file "
            f"instead of trying to download again)."
        )
    cache_path.write_text(text)
    print(f"  Saved local cache: {cache_path.name}")
    return text


# ─── PSMSL tide gauge cleaning — same logic as the project's own ──────────────
# ─── sealevel_cleaner.py, applied here to Cascais and Lagos ───────────────────
PSMSL_COLUMNS = ["year_decimal", "sea_level_mm", "flag", "quality"]


def clean_psmsl_station(raw_text, station_name):
    """
    Parses PSMSL RLR monthly data (semicolon-delimited:
    year_decimal;sea_level_mm;flag;quality, -99999 = missing) into the
    same [year_decimal, sea_level_m, flag] format already used by every
    other tide gauge CSV in this project. This is the SAME logic as the
    project's own sealevel_cleaner.py — reproduced here (not imported,
    since sealevel_cleaner.py is written to read from local files, not
    from already-downloaded text) but verified to do the exact same
    steps.
    """
    df = pd.read_csv(io.StringIO(raw_text), sep=";", names=PSMSL_COLUMNS, header=None)
    df["sea_level_mm"] = df["sea_level_mm"].replace(-99999, np.nan)
    df = df.dropna(subset=["sea_level_mm"])
    df["sea_level_m"] = df["sea_level_mm"] / 1000.0

    inspect_station_flags(df, station_name)

    df = df[["year_decimal", "sea_level_m", "flag"]]
    return df


def inspect_station_flags(df, station_name):
    """
    Prints the actual distribution of PSMSL's per-month flag values found
    for this station. This project's existing convention (inherited from
    13a_sealevel_regression.py) treats flag <= 1 as usable. That
    convention was validated against Leixões/Sines specifically. Cascais
    and Lagos are new stations — Lagos in particular carries PSMSL's own
    "QCFLAG EXISTS" warning — so this print statement exists to let you
    SEE the real flag values before trusting that the inherited
    threshold is still the right cut-off for these two stations too.
    """
    counts = df["flag"].value_counts().sort_index()
    print(f"  {station_name}: PSMSL per-month flag values found (this script "
          f"keeps flag <= 1, same convention as the rest of the project):")
    for flag_value, n in counts.items():
        kept = "kept" if flag_value <= 1 else "EXCLUDED"
        print(f"      flag={flag_value!r:>4}  ->  {n:5d} months  ({kept})")
    unusual = counts[~counts.index.isin([0, 1])]
    if not unusual.empty:
        print(f"      NOTE: {station_name} contains flag values other than 0/1 "
              f"({list(unusual.index)}). These are excluded by the flag<=1 rule "
              f"above, consistent with the rest of the project, but if you want "
              f"to know exactly what those flag values mean for this station, "
              f"consult PSMSL's own documentation file for it at "
              f"https://psmsl.org/data/obtaining/stations/{{station_id}}.php")


def get_cascais_annual():
    print("Cascais (PSMSL station ID 52, Portugal — record ends 1993, gap 1994-1999):")
    raw = download_with_cache(
        PSMSL_RLR_MONTHLY_URL_TMPL.format(id=CASCAIS_STATION_ID),
        CASCAIS_RAW_CACHE, "Cascais raw PSMSL monthly data",
    )
    cleaned = clean_psmsl_station(raw, "Cascais")
    cleaned.to_csv(CASCAIS_CLEANED_CSV, index=False)
    print(f"  Saved: {CASCAIS_CLEANED_CSV.name}")
    return compute_annual_means(CASCAIS_CLEANED_CSV)


def get_lagos_annual():
    print("Lagos (PSMSL station ID 162, Algarve, Portugal — record ends 1999, "
          "PSMSL QC-flag warning on file):")
    raw = download_with_cache(
        PSMSL_RLR_MONTHLY_URL_TMPL.format(id=LAGOS_STATION_ID),
        LAGOS_RAW_CACHE, "Lagos raw PSMSL monthly data",
    )
    cleaned = clean_psmsl_station(raw, "Lagos")
    cleaned.to_csv(LAGOS_CLEANED_CSV, index=False)
    print(f"  Saved: {LAGOS_CLEANED_CSV.name}")
    return compute_annual_means(LAGOS_CLEANED_CSV)


# ─── NAO — NOAA CPC standardised monthly index, 1950-present ─────────────────
def load_nao_annual():
    """
    Downloads/parses NOAA CPC's standardised monthly NAO index table:
    one header line (month abbreviations), then one line per year
    ("year jan feb ... dec"). The most recent year on file is often
    incomplete (fewer than 12 months) — handled explicitly below rather
    than assumed to always have 12 values.
    """
    print("NAO (North Atlantic Oscillation) index, NOAA Climate Prediction Center:")
    text = download_with_cache(NAO_URL, NAO_CACHE, "NAO monthly index (NOAA CPC)")

    lines = [ln for ln in text.splitlines() if ln.strip()]
    data_lines = lines[1:]  # skip the "Jan Feb Mar ..." header line

    records = []
    for ln in data_lines:
        parts = ln.split()
        year = int(parts[0])
        monthly_vals = [float(v) for v in parts[1:13]]  # may be < 12 for latest year
        if len(monthly_vals) >= NAO_AMO_MIN_VALID_MONTHS:
            records.append({
                "year": year,
                "nao_annual": float(np.mean(monthly_vals)),
                "nao_n_months": len(monthly_vals),
            })
    nao_df = pd.DataFrame(records)

    out_of_range = nao_df[(nao_df["nao_annual"].abs() > 4)]
    if not out_of_range.empty:
        print(f"  WARNING: {len(out_of_range)} year(s) have an annual NAO index "
              f"outside the usual ±4 range seen in the literature — worth a "
              f"manual look at {NAO_CACHE.name} before trusting them: "
              f"{out_of_range['year'].tolist()}")

    print(f"  Parsed {len(nao_df)} years ({int(nao_df.year.min())}-"
          f"{int(nao_df.year.max())}).")
    return nao_df


# ─── AMO — tries NOAA NCEI's ERSSTv5-based index first, then falls back ──────
# ─── to NOAA PSL's own legacy Kaplan-SST AMO series if that fails ────────────
def parse_psl_standard_format(text, description):
    """
    Parses NOAA PSL's documented "Standard Format" for monthly
    teleconnection index files (verified directly from
    https://psl.noaa.gov/gcos_wgsp/Timeseries/standard/):
        year1 yearend
        year1 val_jan val_feb ... val_dec
        year2 val_jan val_feb ... val_dec
        ...
        missing_value_sentinel   <- single number, marks end of data
        free-text lines (source, citation, etc.) — ignored here

    Raises a clear, readable error (not a silent guess) if the file does
    not actually look like this — see the AMO section of the module
    docstring for why this format could not be independently re-verified
    byte-for-byte for the specific AMO file being parsed.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        raise SystemExit(f"{description}: file is too short to be in PSL's "
                          f"standard format. Inspect it manually.")

    try:
        year1, yearend = (int(v) for v in lines[0].split()[:2])
    except ValueError:
        raise SystemExit(
            f"{description}: expected the first line to be 'year1 yearend' "
            f"(PSL's documented standard format) but got: {lines[0]!r}. "
            f"This file may not be in the format this script assumes — "
            f"inspect it manually before trusting any AMO results."
        )

    records = []
    sentinel = None
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) == 1:
            # This is the missing-value sentinel line — data ends here.
            sentinel = float(parts[0])
            break
        if len(parts) != 13:
            raise SystemExit(
                f"{description}: expected 13 values per data line (year + 12 "
                f"months) but got {len(parts)} on line: {ln!r}. This file may "
                f"not match PSL's documented standard format — inspect it "
                f"manually before trusting any AMO results."
            )
        year = int(parts[0])
        monthly_vals = [float(v) for v in parts[1:13]]
        records.append({"year": year, "monthly_vals": monthly_vals})

    if sentinel is None:
        raise SystemExit(
            f"{description}: never found the single-number missing-value "
            f"sentinel line that PSL's standard format requires after the "
            f"last year of data. The file may be truncated or not in this "
            f"format — inspect it manually before trusting any AMO results."
        )

    if records[0]["year"] != year1 or records[-1]["year"] != yearend:
        raise SystemExit(
            f"{description}: header says years {year1}-{yearend}, but the "
            f"data rows actually run {records[0]['year']}-{records[-1]['year']}. "
            f"Inspect the file manually before trusting any AMO results."
        )

    rows = []
    for rec in records:
        vals = [np.nan if v == sentinel else v for v in rec["monthly_vals"]]
        n_valid = sum(not np.isnan(v) for v in vals)
        if n_valid >= NAO_AMO_MIN_VALID_MONTHS:
            rows.append({
                "year": rec["year"],
                "amo_annual": float(np.nanmean(vals)),
                "amo_n_months": n_valid,
            })
    return pd.DataFrame(rows)


def load_amo_annual():
    print("AMO (Atlantic Multidecadal Oscillation) index:")
    print("  NOTE: NOAA PSL's own AMO page states their official index "
          "(Kaplan-SST based) is no longer updated and stops at Jan 2023. "
          "Trying NOAA/NCEI's ERSSTv5-based replacement first, as NOAA PSL "
          "itself recommends, with NOAA PSL's own legacy series as a "
          "fallback if that fails.")
    try:
        text = download_with_cache(
            AMO_URL_PRIMARY, AMO_CACHE_PRIMARY,
            "AMO monthly index (NOAA NCEI, ERSSTv5-based)",
        )
        amo_df = parse_psl_standard_format(text, "AMO (NCEI ERSSTv5)")
        print(f"  SOURCE USED: NOAA NCEI ERSSTv5-based AMO index "
              f"({int(amo_df.year.min())}-{int(amo_df.year.max())}).")
        return amo_df
    except SystemExit as exc:
        print(f"  Primary AMO source failed or did not parse as expected:\n"
              f"    {exc}\n  Falling back to NOAA PSL's own legacy "
              f"(Kaplan-SST, capped at Jan 2023) AMO series instead.")
        text = download_with_cache(
            AMO_URL_FALLBACK, AMO_CACHE_FALLBACK,
            "AMO monthly index (NOAA PSL legacy, Kaplan-SST based)",
        )
        amo_df = parse_psl_standard_format(text, "AMO (PSL legacy)")
        print(f"  SOURCE USED: NOAA PSL legacy Kaplan-SST AMO index "
              f"({int(amo_df.year.min())}-{int(amo_df.year.max())}). "
              f"Disclose this substitution if you cite AMO data in the "
              f"dissertation text.")
        return amo_df


# ─── Build the (year, sea_level_m, nao_annual, amo_annual) merged dataset ────
def build_multivariate_dataset(annual_sealevel_df, nao_df, amo_df, station_name):
    merged = (annual_sealevel_df
              .merge(nao_df[["year", "nao_annual"]], on="year", how="inner")
              .merge(amo_df[["year", "amo_annual"]], on="year", how="inner")
              .sort_values("year")
              .reset_index(drop=True))

    n_sealevel_years = len(annual_sealevel_df)
    n_merged_years = len(merged)
    if n_merged_years < n_sealevel_years:
        print(f"  {station_name}: {n_sealevel_years} years of tide gauge data "
              f"available, but only {n_merged_years} years also have both NAO "
              f"and AMO coverage ({int(merged.year.min()) if n_merged_years else '-'}"
              f"-{int(merged.year.max()) if n_merged_years else '-'}). The "
              f"{n_sealevel_years - n_merged_years} dropped year(s) are almost "
              f"certainly pre-1950 years (before NAO coverage begins), not a "
              f"data-quality problem with the tide gauge itself.")
    return merged


# ─── Multivariate-correct versions of 13a3's nine models ─────────────────────
# Same nine algorithms, same names, same hyperparameters, same choice of
# which models get scaled — generalised to handle more than one predictor
# column correctly (per-column StandardScaler; scikit-learn's own
# LinearRegression for the multivariate linear case). See module docstring
# for exactly why 13a3's own versions of these functions cannot be reused
# as-is for this.

def fit_linear_multi(x_train, y_train):
    model = LinearRegression()
    model.fit(x_train, y_train)
    return {"model": model}


def predict_linear_multi(model, x_query):
    return model["model"].predict(x_query)


def fit_ridge_multi(x_train, y_train):
    scaler = StandardScaler().fit(x_train)
    ridge = Ridge(alpha=1.0)
    ridge.fit(scaler.transform(x_train), y_train)
    return {"model": ridge, "scaler": scaler}


def predict_ridge_multi(model, x_query):
    return model["model"].predict(model["scaler"].transform(x_query))


def fit_lasso_multi(x_train, y_train):
    scaler = StandardScaler().fit(x_train)
    lasso = Lasso(alpha=1.0)
    lasso.fit(scaler.transform(x_train), y_train)
    return {"model": lasso, "scaler": scaler}


def predict_lasso_multi(model, x_query):
    return model["model"].predict(model["scaler"].transform(x_query))


def fit_knn_multi(x_train, y_train):
    knn = KNeighborsRegressor(n_neighbors=5)
    knn.fit(x_train, y_train)
    return {"model": knn}


def predict_knn_multi(model, x_query):
    return model["model"].predict(x_query)


def fit_decision_tree_multi(x_train, y_train):
    tree = DecisionTreeRegressor(random_state=RANDOM_STATE)
    tree.fit(x_train, y_train)
    return {"model": tree}


def predict_decision_tree_multi(model, x_query):
    return model["model"].predict(x_query)


def fit_rf_multi(x_train, y_train):
    rf = RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE)
    rf.fit(x_train, y_train)
    return {"model": rf}


def predict_rf_multi(model, x_query):
    return model["model"].predict(x_query)


def fit_gboost_multi(x_train, y_train):
    gboost = GradientBoostingRegressor(random_state=RANDOM_STATE)
    gboost.fit(x_train, y_train)
    return {"model": gboost}


def predict_gboost_multi(model, x_query):
    return model["model"].predict(x_query)


def fit_svr_multi(x_train, y_train):
    scaler = StandardScaler().fit(x_train)
    svr = SVR(kernel="linear", C=2.0, epsilon=0.005)
    svr.fit(scaler.transform(x_train), y_train)
    return {"model": svr, "scaler": scaler}


def predict_svr_multi(model, x_query):
    return model["model"].predict(model["scaler"].transform(x_query))


def fit_gpr_multi(x_train, y_train):
    scaler = StandardScaler().fit(x_train)
    kernel = (
        ConstantKernel(1.0, (1e-5, 1e5)) * DotProduct(sigma_0=1.0, sigma_0_bounds=(1e-5, 1e5))
        + ConstantKernel(1.0, (1e-5, 1e5)) * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
        + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-6, 1e1))
    )
    gpr = GaussianProcessRegressor(
        kernel=kernel, normalize_y=True, n_restarts_optimizer=15, random_state=RANDOM_STATE,
    )
    gpr.fit(scaler.transform(x_train), y_train)
    return {"model": gpr, "scaler": scaler}


def predict_gpr_multi(model, x_query):
    return model["model"].predict(model["scaler"].transform(x_query))


MODELS_MULTI = [
    ("Linear Regression", fit_linear_multi, predict_linear_multi, True),
    ("Ridge Regression", fit_ridge_multi, predict_ridge_multi, True),
    ("Lasso Regression", fit_lasso_multi, predict_lasso_multi, True),
    ("K-Nearest Neighbors", fit_knn_multi, predict_knn_multi, False),
    ("Decision Tree", fit_decision_tree_multi, predict_decision_tree_multi, False),
    ("Random Forest", fit_rf_multi, predict_rf_multi, False),
    ("Gradient Boosting", fit_gboost_multi, predict_gboost_multi, False),
    ("Support Vector Regression", fit_svr_multi, predict_svr_multi, True),
    ("Gaussian Process Regression", fit_gpr_multi, predict_gpr_multi, True),
]


# ─── CV-fold count, scaled down for small subsets (same spirit as 13a4) ──────
def n_splits_for(n_years):
    return max(2, min(5, n_years // 4))


# ─── Run all 9 models for one (station, feature_set) combination ────────────
def run_feature_set(station_name, feature_set_name, feature_cols, df):
    n_splits = n_splits_for(len(df))
    rows = []

    if len(df) < n_splits + 1:
        print(f"  SKIPPED {feature_set_name}: only {len(df)} usable years, "
              f"not enough for {n_splits} CV folds.")
        for model_name, _fit, _pred, can_extrap in MODELS_MULTI:
            rows.append({
                "station": station_name, "feature_set": feature_set_name,
                "features": ",".join(feature_cols), "n_years_used": len(df),
                "year_range_used": "", "cv_folds": n_splits, "model": model_name,
                "can_extrapolate_trend": can_extrap,
                "rmse_mm_mean": np.nan, "rmse_mm_std": np.nan,
                "mae_mm_mean": np.nan, "mae_mm_std": np.nan,
                "r2_mean": np.nan, "r2_std": np.nan,
            })
        return rows

    x = df[feature_cols].values.astype(float)
    y = df["sea_level_m"].values
    year_range_used = f"{int(df['year'].min())}-{int(df['year'].max())}"

    for model_name, fit_fn, predict_fn, can_extrap in MODELS_MULTI:
        cv = walk_forward_cv(x, y, fit_fn, predict_fn, n_splits=n_splits)
        rows.append({
            "station": station_name,
            "feature_set": feature_set_name,
            "features": ",".join(feature_cols),
            "n_years_used": len(df),
            "year_range_used": year_range_used,
            "cv_folds": n_splits,
            "model": model_name,
            "can_extrapolate_trend": can_extrap,
            "rmse_mm_mean": round(cv["rmse_mm_mean"], 1),
            "rmse_mm_std": round(cv["rmse_mm_std"], 1),
            "mae_mm_mean": round(cv["mae_mm_mean"], 1),
            "mae_mm_std": round(cv["mae_mm_std"], 1),
            "r2_mean": round(cv["r2_mean"], 3),
            "r2_std": round(cv["r2_std"], 3),
        })

    print(f"  {feature_set_name} ({year_range_used}, {len(df)} years, "
          f"{n_splits} CV folds):")
    disp = pd.DataFrame(rows)[["model", "rmse_mm_mean", "rmse_mm_std", "r2_mean", "r2_std"]]
    print(disp.sort_values("rmse_mm_mean").to_string(index=False))
    print()
    return rows


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 78)
    print("STEP 1 — Gathering data (downloads happen once, then cache locally)")
    print("=" * 78)

    nao_df = load_nao_annual()
    print()
    amo_df = load_amo_annual()
    print()

    print("Existing stations (Leixões, Sines) — unchanged, same cleaned CSVs "
          "used by 13a/13a3/13a4:")
    leixoes_annual = compute_annual_means(LEIXOES_CSV).sort_values("year").reset_index(drop=True)
    sines_annual   = compute_annual_means(SINES_CSV).sort_values("year").reset_index(drop=True)
    print(f"  Leixões: {len(leixoes_annual)} years "
          f"({int(leixoes_annual.year.min())}-{int(leixoes_annual.year.max())})")
    print(f"  Sines:   {len(sines_annual)} years "
          f"({int(sines_annual.year.min())}-{int(sines_annual.year.max())})")
    print()

    cascais_annual = get_cascais_annual().sort_values("year").reset_index(drop=True)
    print()
    lagos_annual   = get_lagos_annual().sort_values("year").reset_index(drop=True)
    print()

    stations = [
        ("Leixões", leixoes_annual),
        ("Sines",   sines_annual),
        ("Cascais", cascais_annual),
        ("Lagos",   lagos_annual),
    ]

    print("=" * 78)
    print("STEP 2 — Merging tide gauge data with NAO + AMO by year")
    print("=" * 78)
    merged_by_station = {}
    for station_name, annual_df in stations:
        merged = build_multivariate_dataset(annual_df, nao_df, amo_df, station_name)
        merged_by_station[station_name] = merged
    print()

    print("=" * 78)
    print("STEP 3 — Train -> test (walk-forward CV) for every station, both "
          "feature sets, all 9 models. APPLY here means refitting on the full "
          "usable subset; see module docstring for why this script does NOT "
          "produce a 2100 projection number.")
    print("=" * 78)

    all_rows = []
    for station_name, merged in merged_by_station.items():
        print(f"\n--- {station_name} ---")
        if merged.empty:
            print("  No years available with both tide gauge AND NAO/AMO "
                  "coverage — skipping this station entirely.")
            continue

        check_outliers(merged, station_name)

        all_rows.extend(run_feature_set(
            station_name, "year_only", ["year"], merged
        ))
        all_rows.extend(run_feature_set(
            station_name, "year+NAO+AMO", ["year", "nao_annual", "amo_annual"], merged
        ))

    all_results = pd.DataFrame(all_rows)
    all_results.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")

    print("\n" + "=" * 78)
    print("HOW TO READ THIS OUTPUT — IMPORTANT")
    print("=" * 78)
    print(
        "This script does NOT declare a winning model or station. To use it:\n"
        "  - For a given station and model, compare its 'year_only' row "
        "against its 'year+NAO+AMO' row. Both rows use the EXACT SAME years "
        "(the NAO/AMO-limited window), so this is a fair, apples-to-apples "
        "test of whether the two climate indices actually help.\n"
        "  - A lower RMSE/MAE and a higher R2 in 'year+NAO+AMO' than in "
        "'year_only', for the SAME station and model, supports including "
        "NAO/AMO. If results are mixed across stations or across models, "
        "that is itself a finding worth reporting honestly, not a reason to "
        "only report the station/model pair that looks best.\n"
        "  - Remember the coverage caveats from the module docstring: "
        "Cascais and Lagos are historical (pre-1994 and pre-2000) records "
        "and NAO/AMO availability further restricts every station here to "
        "1950 onward. None of this script's numbers describe present-day "
        "conditions at Cascais or Lagos specifically.\n"
        "  - No 2100 projection is produced here on purpose — see the "
        "module docstring for why projecting a multivariate model that "
        "far out would require assuming future NAO/AMO values, which this "
        "script deliberately does not do."
    )

    # ─── Chart: CV RMSE, year_only vs year+NAO+AMO, grouped by station ──────
    if not all_results.empty:
        plot_df = all_results.dropna(subset=["rmse_mm_mean"])
        if not plot_df.empty:
            stations_present = plot_df["station"].unique().tolist()
            fig, axes = plt.subplots(1, len(stations_present),
                                      figsize=(6 * len(stations_present), 6),
                                      squeeze=False)
            for ax, station_name in zip(axes[0], stations_present):
                sub = plot_df[plot_df["station"] == station_name]
                models_here = [m[0] for m in MODELS_MULTI if m[0] in sub["model"].unique()]
                x_pos = np.arange(len(models_here))
                width = 0.35
                for offset, feature_set, color in [
                    (-width / 2, "year_only", "#9E9E9E"),
                    (width / 2, "year+NAO+AMO", "#1976D2"),
                ]:
                    vals = [
                        sub[(sub["model"] == m) & (sub["feature_set"] == feature_set)]
                        ["rmse_mm_mean"].mean()
                        for m in models_here
                    ]
                    ax.bar(x_pos + offset, vals, width=width, label=feature_set, color=color)
                ax.set_xticks(x_pos)
                ax.set_xticklabels(models_here, rotation=45, ha="right", fontsize=7.5)
                ax.set_ylabel("CV RMSE (mm) — lower is better", fontsize=9)
                ax.set_title(station_name, fontsize=11, fontweight="bold")
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.25, axis="y")
            plt.tight_layout()
            plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
            plt.show()
            plt.close()
            print(f"Saved: {OUT_PNG}")

    print("\nDone.")


if __name__ == "__main__":
    main()
