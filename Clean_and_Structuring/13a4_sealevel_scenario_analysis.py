"""
13a4_sealevel_scenario_analysis.py
====================================
Sea Level Rise — Model Selection Scenario / Robustness Analysis
Leixões and Sines

WHY THIS SCRIPT EXISTS
-----------------------
13a3_sealevel_ml_models.py cross-validated 9 machine learning regression
models on the FULL historical record for each station and found that every
single model's walk-forward cross-validated R² came out negative. Rather
than guessing why, or quietly trying different versions of the data until
something looks better (which would be indefensible if presented as "the"
result without saying so — that is the textbook definition of data
dredging / p-hacking), this script runs the SAME 9 models, with the SAME
walk-forward cross-validation method, across several different,
independently-justified data scenarios, and reports ALL of them side by
side. The point is transparency: show what changes, what doesn't, and why
— so that if you end up favouring one scenario in the dissertation, you can
point to this side-by-side comparison as the reason, rather than it looking
like a number was picked because it was convenient.

SCENARIOS TESTED (and why each one is a legitimate thing to check, not an
arbitrary tweak chosen to chase a better-looking number):

  1. full_record       - every year on file. This is the baseline, and
                          should reproduce 13a3's own numbers, so this
                          script's results stay traceable back to that one.

  2. no_outliers        - the same data, with any year flagged by 13a3's
                          own outlier check removed. NOTE: this only
                          changes anything for Leixões (year 1961). Sines
                          has no flagged year, so this scenario is
                          IDENTICAL to full_record for Sines — included
                          anyway, for completeness and so that fact is
                          visible rather than silently skipped.

  3. recent_period      - restricted to year >= 1993. This is NOT a new
                          cutoff invented for this analysis — it is the
                          exact same cutoff already used months ago in
                          13a_sealevel_regression.py, for an unrelated
                          reason (1993 is commonly used in sea-level
                          literature as the start of the satellite-
                          altimetry era). Reusing an existing, externally
                          motivated cutoff avoids the appearance of
                          picking a period specifically to flatter today's
                          results.

  4. short_term_recent  - the most recent 15 years of data on file at each
                          station. Included because it was asked for, but
                          flagged with a real caution below: fewer points
                          means noisier cross-validation scores, AND a
                          trend fit on only 15 years is a far shakier basis
                          for extrapolating 80 years forward to 2100 than a
                          trend fit on 50+ years. A "better-looking" score
                          here is not automatically a more trustworthy one.

  5. fold_count_check   - the same FULL record as scenario 1, but
                          cross-validated with fewer folds than 13a3 used.
                          This checks whether 13a3's negative-R² finding
                          was an artifact of specifically choosing 5 folds,
                          or holds up regardless of how many folds are
                          used.

The number of cross-validation folds is not fixed at 5 for every scenario.
It scales down automatically for smaller data subsets (see
n_splits_for() below), so a 15-year window is never forced through the
same 5-fold split as a 50-year record — that would leave only 2-3 years
per test fold, which is not a meaningful test of anything.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO:
  - It does not pick a "winning" scenario for you. That decision belongs
    in the dissertation text, with reasoning written out — not buried
    inside a script.
  - It does not modify 13a3_sealevel_ml_models.py in any way. It imports
    that file's own model definitions and cross-validation function
    (rather than re-writing copies of them here), so the two scripts can
    never silently drift out of sync with each other.
  - It does not change the train -> test -> apply order used everywhere
    else in this project: every scenario's 2100 projection still only
    happens after that scenario's own cross-validated test step.

REQUIRES: numpy, pandas, scipy, scikit-learn — all already required by
13a3_sealevel_ml_models.py (nothing new to install if that script already
ran successfully on your machine).

OUTPUTS:
  sealevel_scenario_analysis_summary.csv — station x scenario x model,
  every metric, for you to inspect, sort, and compare yourself.

USAGE:
  python 13a4_sealevel_scenario_analysis.py
"""

from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse 13a3's own model definitions and CV function rather than copying
# them — guarantees this script can never silently disagree with 13a3 about
# what each model is or how cross-validation is performed. If scikit-learn
# or scipy are missing, 13a3's own import guards will raise a clear error.
_ml = import_module("13a3_sealevel_ml_models")
MODELS = _ml.MODELS
walk_forward_cv = _ml.walk_forward_cv
check_outliers = _ml.check_outliers
compute_annual_means = _ml.compute_annual_means
TARGET_YEAR = _ml.TARGET_YEAR

# ─── PATHS ──────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
LEIXOES_CSV = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV   = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV     = PROJECT_DIR / "sealevel_scenario_analysis_summary.csv"

RECENT_PERIOD_START_YEAR = 1993   # reuses 13a_sealevel_regression.py's own cutoff
SHORT_TERM_WINDOW_YEARS  = 15


# ─── Pick a sample-size-appropriate number of CV folds ─────────────────────
def n_splits_for(n_years):
    """
    Scales the number of walk-forward CV folds down for smaller data
    subsets, so a short window is never forced through the same 5-fold
    split used for a 50-year record (which would leave only 2-3 years per
    test fold — not a meaningful test). Capped at 5 so the full_record
    scenario always matches 13a3's own choice exactly.
    """
    return max(2, min(5, n_years // 4))


# ─── Build the list of scenarios for one station ───────────────────────────
def make_scenarios(annual_full, station_name):
    """
    Returns a list of (scenario_name, annual_subset, n_splits, note)
    tuples for one station, all derived from its already-cleaned full
    annual dataframe (same compute_annual_means used everywhere else in
    this project).
    """
    scenarios = []

    # 1. full_record
    scenarios.append((
        "full_record",
        annual_full.copy(),
        n_splits_for(len(annual_full)),
        "Every year on file (same data as 13a3_sealevel_ml_models.py).",
    ))

    # 2. no_outliers
    flagged_years = check_outliers(annual_full, station_name)
    annual_no_outliers = annual_full[~annual_full["year"].isin(flagged_years)].copy()
    if flagged_years:
        note = (f"Year(s) {flagged_years} removed (flagged by 13a3's own "
                f"outlier check, >3 standard deviations from a simple trend line).")
    else:
        note = ("No year was flagged by the outlier check for this station, so "
                 "this scenario is IDENTICAL to full_record here.")
    scenarios.append((
        "no_outliers", annual_no_outliers, n_splits_for(len(annual_no_outliers)), note
    ))

    # 3. recent_period
    annual_recent = annual_full[annual_full["year"] >= RECENT_PERIOD_START_YEAR].copy()
    scenarios.append((
        "recent_period",
        annual_recent,
        n_splits_for(len(annual_recent)),
        f"Restricted to year >= {RECENT_PERIOD_START_YEAR} — the same cutoff "
        f"already used in 13a_sealevel_regression.py, not a new one chosen here.",
    ))

    # 4. short_term_recent
    last_year = int(annual_full["year"].max())
    cutoff = last_year - SHORT_TERM_WINDOW_YEARS + 1
    annual_short = annual_full[annual_full["year"] >= cutoff].copy()
    scenarios.append((
        "short_term_recent",
        annual_short,
        n_splits_for(len(annual_short)),
        f"Most recent {SHORT_TERM_WINDOW_YEARS} years only ({cutoff}-{last_year}). "
        f"CAUTION: a trend fit on this few years is a much weaker basis for an "
        f"80-year extrapolation to 2100 than the full record — included because "
        f"it was requested, not because it is the most defensible scenario.",
    ))

    # 5. fold_count_check — same data as full_record, fewer CV folds
    baseline_splits = n_splits_for(len(annual_full))
    alt_splits = max(2, baseline_splits - 2)
    scenarios.append((
        "fold_count_check",
        annual_full.copy(),
        alt_splits,
        f"Same data as full_record, but {alt_splits} CV folds instead of "
        f"{baseline_splits}, to check whether the fold count itself changes "
        f"the conclusion (not a different dataset at all).",
    ))

    return scenarios


# ─── Run all 9 models on one (station, scenario) data subset ───────────────
def run_scenario(station_name, scenario_name, scenario_note, annual_subset, n_splits):
    """
    Runs every model's walk-forward CV (TEST) followed by a full-subset
    refit and 2100 projection (APPLY) — same train -> test -> apply order
    used everywhere else in this project, just applied to a different
    slice of the data each time.
    """
    rows = []

    if len(annual_subset) < n_splits + 1:
        for model_name, _note, _fit_fn, _predict_fn, can_extrap in MODELS:
            rows.append({
                "station": station_name, "scenario": scenario_name,
                "scenario_note": scenario_note, "n_years_used": len(annual_subset),
                "year_range_used": "", "cv_folds": n_splits, "model": model_name,
                "can_extrapolate_trend": can_extrap,
                "rmse_mm_mean": np.nan, "rmse_mm_std": np.nan,
                "mae_mm_mean": np.nan, "mae_mm_std": np.nan,
                "r2_mean": np.nan, "r2_std": np.nan,
                "prediction_2100_m": np.nan, "change_vs_last_observed_mm": np.nan,
            })
        return rows

    x = annual_subset["year"].values.reshape(-1, 1).astype(float)
    y = annual_subset["sea_level_m"].values
    last_year_used = int(annual_subset["year"].max())
    last_observed_used = float(
        annual_subset.loc[annual_subset["year"] == last_year_used, "sea_level_m"].values[0]
    )
    year_range_used = f"{int(annual_subset['year'].min())}-{last_year_used}"

    for model_name, _note, fit_fn, predict_fn, can_extrap in MODELS:
        # STEP 1+2 — TEST via walk-forward cross-validation, this scenario's data only
        cv = walk_forward_cv(x, y, fit_fn, predict_fn, n_splits=n_splits)

        # STEP 3 — APPLY: refit on this scenario's full subset, then project to 2100
        model_full = fit_fn(x, y)
        pred_2100 = float(predict_fn(model_full, np.array([[float(TARGET_YEAR)]]))[0])
        change_mm = (pred_2100 - last_observed_used) * 1000

        rows.append({
            "station": station_name,
            "scenario": scenario_name,
            "scenario_note": scenario_note,
            "n_years_used": len(annual_subset),
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
            "prediction_2100_m": round(pred_2100, 3),
            "change_vs_last_observed_mm": round(change_mm, 1),
        })

    return rows


# ─── MAIN ───────────────────────────────────────────────────────────────────
def main():
    print("Running 9 models across 5 data scenarios, for both stations...")
    print("(This re-runs walk-forward CV many times over — it may take a")
    print(" little longer than 13a3_sealevel_ml_models.py did.)\n")

    all_rows = []

    for station_name, csv_path in [("Leixões", LEIXOES_CSV), ("Sines", SINES_CSV)]:
        print("=" * 78)
        print(station_name)
        print("=" * 78)

        annual_full = compute_annual_means(csv_path).sort_values("year").reset_index(drop=True)
        scenarios = make_scenarios(annual_full, station_name)

        for scenario_name, annual_subset, n_splits, note in scenarios:
            print(f"\n--- Scenario: {scenario_name} ---")
            print(f"  {note}")
            if len(annual_subset) >= n_splits + 1:
                print(f"  Years used: {len(annual_subset)} "
                      f"({int(annual_subset['year'].min())}-{int(annual_subset['year'].max())}), "
                      f"{n_splits} CV folds")
            else:
                print(f"  SKIPPED actual fitting: only {len(annual_subset)} years available, "
                      f"not enough for {n_splits} CV folds.")

            rows = run_scenario(station_name, scenario_name, note, annual_subset, n_splits)
            all_rows.extend(rows)

            scenario_df = pd.DataFrame(rows)
            display_cols = ["model", "rmse_mm_mean", "rmse_mm_std", "r2_mean", "r2_std",
                             "prediction_2100_m", "change_vs_last_observed_mm"]
            print(scenario_df[display_cols].sort_values("rmse_mm_mean").to_string(index=False))
        print()

    all_results = pd.DataFrame(all_rows)
    all_results.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")

    print("\n" + "=" * 78)
    print("HOW TO READ THIS OUTPUT — IMPORTANT")
    print("=" * 78)
    print(
        "This script does NOT declare a winning scenario or model. To use it:\n"
        "  - Pick one model and one station, then compare its R2/RMSE across the\n"
        "    five scenario rows. If a model only looks good in ONE narrow scenario\n"
        "    (especially short_term_recent) and looks poor in full_record and\n"
        "    recent_period, that is a sign of fitting to a convenient window, not\n"
        "    a genuinely better model.\n"
        "  - A model whose score holds up reasonably consistently across MULTIPLE\n"
        "    scenarios — not just the one that looks best — is the more defensible\n"
        "    one to discuss as your selected model.\n"
        "  - If every scenario still gives negative R2 for every model, that is\n"
        "    itself a finding: it says the limitation is the single predictor\n"
        "    (year alone) and the data's natural noise, not which slice of data\n"
        "    or how many CV folds were used."
    )


if __name__ == "__main__":
    main()
