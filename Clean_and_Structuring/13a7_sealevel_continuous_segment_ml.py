"""
13a7_sealevel_continuous_segment_ml.py
=======================================
Sea Level Rise — 9 ML Models, Continuous Post-Gap Segments Only
Leixões and Sines

WHAT THIS SCRIPT DOES (plain language)
----------------------------------------
Both Leixões and Sines tide gauge stations have significant, documented gaps
in their monthly data records:

  Leixões: gaps 1986–1994 (9 years) and 1996–2001 (6 years)
  Sines:   gaps 1988–1990 (3 years) and 1993–1996 (4 years)

Previous scripts in this series (13a3 and 13a6) trained models on all
available data, which meant the training data came from multiple non-
consecutive intervals separated by these gaps. While the models themselves
are not broken by this (each model sees year/sea-level pairs regardless of
whether those years are consecutive), it is a methodological weakness:
the training data does not represent a single continuous, unbroken record.

This script addresses that weakness directly. For each station, it identifies
the most recent continuous post-gap segment and restricts ALL training,
testing, and projection to data within that segment only.

  Leixões — continuous segment: 2002–2022
    TRAIN : years ≤ 2017  (approximately 76% of segment data points)
    TEST  : years ≥ 2018  (approximately 24% of segment data points)
    APPLY : refit on full segment (2002–2022), project to 2100

  Sines — continuous segment: 1997–2022
    TRAIN : years ≤ 2017  (approximately 81% of segment data points)
    TEST  : years ≥ 2018  (approximately 19% of segment data points)
    APPLY : refit on full segment (1997–2022), project to 2100

Both stations share the same test window (2018–2022), making their results
directly comparable. The segment boundaries were fixed before running any
model — they are defined by the documented gap structure of each station's
record, not by which boundary produces favourable results.

HOW THIS DIFFERS FROM EARLIER SCRIPTS IN THIS PROJECT
------------------------------------------------------
  13a3 — walk-forward cross-validation on the FULL historical record
          (all available annual means, including data from across the
          documented gap periods)

  13a6 — single chronological train/test split on the FULL historical
          record (same data as 13a3, just split differently)

  13a7 — single chronological train/test split on the CONTINUOUS SEGMENT
          ONLY (gap periods completely excluded from every model step)

The gain is methodological clarity: the training set is a single unbroken
run of annual observations, which is a cleaner and more defensible basis
for the train → test → apply sequence. The cost is fewer training
observations (16–21 years instead of 36–50+), which means the models have
less information about the long-term trend.

TRAIN → TEST → APPLY ORDER
---------------------------
This is the same three-step sequence used in every other script in this
project. For this script:

  STEP 1 — TRAIN  : fit each of the 9 models on the training portion of
                     the continuous segment (years ≤ 2017 at each station)
  STEP 2 — TEST   : use that TRAIN model (and only that model) to predict
                     sea level for 2018–2022. Compute RMSE, MAE, and R²
                     from those predictions vs. the actual observed values.
                     These are the reported test metrics.
  STEP 3 — APPLY  : refit each model on the FULL continuous segment (train
                     + test combined), then project forward to TARGET_YEAR
                     (2100). This always comes last; the 2100 number is
                     never produced by the train-only model.

The test metrics (Step 2) are never used to train anything. The 2100
projection (Step 3) uses a richer model (trained on more data) than the
one tested in Step 2, which is correct: the test step evaluates
methodology; the apply step maximises the quality of the final output.

A NOTE ON EXPECTED RESULTS
---------------------------
Using a clean continuous segment does not eliminate the fundamental noise-
to-signal challenge identified in 13a3 and 13a6. Interannual sea level
variability (~40 mm) is substantially larger than the annual trend signal
(~2 mm/year), so predicting any specific year's sea level accurately is
genuinely difficult regardless of which data is used for training.

What changes with this approach is the methodological argument: any result
obtained here comes from models trained on continuous, uninterrupted data.
That is a stronger position to defend than one based on data from multiple
non-consecutive intervals.

A NOTE ON THE 2100 PROJECTION
------------------------------
The APPLY step in this script refits on 16–21 years of data (the
continuous segment), which is a shorter record than the full historical
datasets used in 13a3 (50 / 39 years) and 13a6 (same). The 2100
projection here therefore rests on a shorter trend baseline and carries
more uncertainty than in those earlier scripts. It is included for
completeness and comparison — not as the primary result.

OUTPUTS
-------
  sealevel_continuous_segment_summary.csv   — 9 models × 2 stations,
                                              test metrics + 2100 projection
  sealevel_continuous_segment_chart.png     — full historical record shown
                                              as background context; the
                                              continuous segment, test window,
                                              model lines, and test
                                              predictions (◆) highlighted
  sealevel_continuous_segment_table.png     — model comparison table image,
                                              ranked best-to-worst by RMSE

REQUIRES
--------
  numpy, pandas, matplotlib, scipy, scikit-learn — same as 13a3.
  No new packages to install.

USAGE
-----
  python 13a7_sealevel_continuous_segment_ml.py
"""

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ─── REUSE — imported from 13a3, never copied or modified ────────────────────
# Importing 13a3 also triggers its own ConvergenceWarning suppression,
# so this script does not need to repeat it.
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

_ml3 = import_module("13a3_sealevel_ml_models")

MODELS               = _ml3.MODELS              # 9 (name, note, fit_fn, predict_fn, can_extrap)
compute_annual_means = _ml3.compute_annual_means # originally from 13a_sealevel_regression
check_outliers       = _ml3.check_outliers       # 3-sigma residual check vs. simple trend
TARGET_YEAR          = _ml3.TARGET_YEAR          # 2100
RANDOM_STATE         = _ml3.RANDOM_STATE         # 42
PLOT_COLORS          = _ml3.PLOT_COLORS          # colour dict keyed by model name
FLAT_EXPLANATIONS    = _ml3.FLAT_EXPLANATIONS    # notes printed when 2100 projection is flat
predict_gpr          = _ml3.predict_gpr          # needed separately to request the std band

# ─── PATHS ───────────────────────────────────────────────────────────────────
LEIXOES_CSV   = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV     = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV       = PROJECT_DIR / "sealevel_continuous_segment_summary.csv"
OUT_PNG       = PROJECT_DIR / "sealevel_continuous_segment_chart.png"
OUT_TABLE_PNG = PROJECT_DIR / "sealevel_continuous_segment_table.png"

# ─── STATION CONFIGURATIONS ──────────────────────────────────────────────────
# Each entry defines one station's continuous post-gap segment and the
# train/test split within it.
#
# Segment boundaries are set by the documented gap structure of each
# station's tide gauge record — not by model results:
#   Leixões: gaps 1986–1994 and 1996–2001 → continuous segment starts 2002
#   Sines:   gaps 1988–1990 and 1993–1996 → continuous segment starts 1997
#
# Both stations share the same test window (2018–2022) so that their
# results are directly comparable.
#
# The train/test percentages are approximate: the exact number of qualifying
# annual means (≥6 usable months required by compute_annual_means) may
# differ from the nominal year count if any year within the segment range
# fails that quality threshold. The script prints the actual counts.

STATION_CONFIGS = [
    {
        "name":          "Leixões",
        "csv":           LEIXOES_CSV,
        "segment_start": 2002,   # first year after the 1996–2001 gap
        "train_end":     2017,   # last year of the training set  (≈76% of segment)
        "test_start":    2018,   # first year of the test set     (≈24% of segment)
        "segment_end":   2022,   # last year on record
        "gap_note":      "Documented gaps: 1986–1994 and 1996–2001",
    },
    {
        "name":          "Sines",
        "csv":           SINES_CSV,
        "segment_start": 1997,   # first year after the 1993–1996 gap
        "train_end":     2017,   # last year of the training set  (≈81% of segment)
        "test_start":    2018,   # first year of the test set     (≈19% of segment)
        "segment_end":   2022,   # last year on record
        "gap_note":      "Documented gaps: 1988–1990 and 1993–1996",
    },
]


# ─── TRAIN → TEST → APPLY for one station ────────────────────────────────────
def run_station(config):
    """
    Loads all available annual means for one station, filters to the
    documented continuous post-gap segment, splits that segment into a
    training set (years ≤ train_end) and a test set (years ≥ test_start),
    then runs each of the 9 models through the three-step sequence:

      STEP 1 — TRAIN  : fit on training set only
      STEP 2 — TEST   : predict test years with the TRAIN model; compute
                         RMSE, MAE, R²
      STEP 3 — APPLY  : refit on the FULL segment (train + test), project
                         to TARGET_YEAR (2100)

    Returns the raw data frames and fitted model dicts needed for charting.
    """
    station_name = config["name"]
    seg_start    = config["segment_start"]
    seg_end      = config["segment_end"]
    train_end    = config["train_end"]
    test_start   = config["test_start"]

    print("=" * 78)
    print(station_name)
    print("=" * 78)
    print(f"  {config['gap_note']}")
    print(f"  All modelling restricted to the continuous segment: "
          f"{seg_start}–{seg_end}")
    print()

    # ── Load and filter ────────────────────────────────────────────────────
    # annual_full is kept for the chart background; it plays no role in
    # any model's fitting, testing, or projection.
    annual_full = (
        compute_annual_means(config["csv"])
        .sort_values("year")
        .reset_index(drop=True)
    )

    annual_seg = annual_full[
        (annual_full["year"] >= seg_start) &
        (annual_full["year"] <= seg_end)
    ].copy().reset_index(drop=True)

    # ── Split within the segment ───────────────────────────────────────────
    annual_train = annual_seg[annual_seg["year"] <= train_end].copy()
    annual_test  = annual_seg[annual_seg["year"] >= test_start].copy()

    n_seg   = len(annual_seg)
    n_train = len(annual_train)
    n_test  = len(annual_test)

    # Guard: enough data to fit a model?
    if n_train < 5:
        raise SystemExit(
            f"\n{station_name}: only {n_train} training years available in the "
            f"segment up to {train_end}. Cannot fit any model reliably. "
            f"Check the data file or adjust the segment/split boundaries."
        )
    if n_test < 2:
        raise SystemExit(
            f"\n{station_name}: only {n_test} test years available from "
            f"{test_start} onward within the segment. Nothing meaningful to "
            f"evaluate. Check the data file or adjust the split boundary."
        )

    # Actual year ranges after the quality filter
    actual_seg_start   = int(annual_seg["year"].min())
    actual_seg_end     = int(annual_seg["year"].max())
    actual_train_start = int(annual_train["year"].min())
    actual_train_end   = int(annual_train["year"].max())
    actual_test_start  = int(annual_test["year"].min())
    actual_test_end    = int(annual_test["year"].max())

    print(f"Full historical record   : {len(annual_full)} years  "
          f"({int(annual_full.year.min())}–{int(annual_full.year.max())})"
          f"  [chart background only — not used in any model]")
    print(f"Continuous segment used  : {n_seg} years  "
          f"({actual_seg_start}–{actual_seg_end})")
    print(f"  TRAIN : {n_train} years  "
          f"({actual_train_start}–{actual_train_end})  "
          f"[{n_train / n_seg * 100:.0f}% of segment]")
    print(f"  TEST  : {n_test} years  "
          f"({actual_test_start}–{actual_test_end})  "
          f"[{n_test / n_seg * 100:.0f}% of segment]")

    # Warn if the quality filter moved the nominal segment start
    if actual_seg_start != seg_start:
        print(f"\n  Note: the nominal segment start ({seg_start}) was excluded "
              f"by the quality filter (fewer than 6 usable months that year).\n"
              f"  Actual segment starts at {actual_seg_start}.")

    # Outlier check on the segment (not the full record)
    check_outliers(annual_seg, station_name)
    print()

    # ── Prepare arrays ─────────────────────────────────────────────────────
    x_train = annual_train["year"].values.reshape(-1, 1).astype(float)
    y_train = annual_train["sea_level_m"].values

    x_test  = annual_test["year"].values.reshape(-1, 1).astype(float)
    y_test  = annual_test["sea_level_m"].values

    x_seg   = annual_seg["year"].values.reshape(-1, 1).astype(float)
    y_seg   = annual_seg["sea_level_m"].values

    last_obs_year = actual_seg_end
    last_observed = float(
        annual_seg.loc[
            annual_seg["year"] == last_obs_year, "sea_level_m"
        ].values[0]
    )

    train_period   = f"{actual_train_start}–{actual_train_end}"
    test_period    = f"{actual_test_start}–{actual_test_end}"
    segment_period = f"{actual_seg_start}–{actual_seg_end}"

    results      = []
    train_models = {}   # model fitted on TRAIN only → Step 2 test + chart diamonds
    seg_models   = {}   # model fitted on FULL SEGMENT → Step 3 apply + chart lines

    print(f"STEP 1+2 — Training each model on {train_period}, "
          f"then testing on {test_period}:")
    print()

    for model_name, model_note, fit_fn, predict_fn, can_extrapolate in MODELS:

        # ── STEP 1 — TRAIN ────────────────────────────────────────────────
        model_train = fit_fn(x_train, y_train)
        train_models[model_name] = model_train

        # ── STEP 2 — TEST ─────────────────────────────────────────────────
        y_pred_test = np.asarray(predict_fn(model_train, x_test)).flatten()

        resid_mm = (y_pred_test - y_test) * 1000
        rmse_mm  = float(np.sqrt(np.mean(resid_mm ** 2)))
        mae_mm   = float(np.mean(np.abs(resid_mm)))

        ss_res  = float(np.sum((y_test - y_pred_test) ** 2))
        ss_tot  = float(np.sum((y_test - np.mean(y_test)) ** 2))
        r2_test = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

        # ── STEP 3 — APPLY: refit on FULL SEGMENT, project to 2100 ───────
        # The segment-fitted model uses more data than the train-only model
        # and gives the best possible projection from this segment.
        # Note: this is the SEGMENT only — earlier scripts (13a3, 13a6) used
        # the full historical record for the Apply step. This script
        # consistently uses only the continuous segment throughout.
        model_seg = fit_fn(x_seg, y_seg)
        seg_models[model_name] = model_seg
        pred_2100 = float(
            predict_fn(model_seg, np.array([[float(TARGET_YEAR)]]))[0]
        )
        change_mm = (pred_2100 - last_observed) * 1000

        results.append({
            "station":                    station_name,
            "model":                      model_name,
            "can_extrapolate_trend":      can_extrapolate,
            "segment_period":             segment_period,
            "n_segment_years":            n_seg,
            "train_period":               train_period,
            "n_train_years":              n_train,
            "test_period":                test_period,
            "n_test_years":               n_test,
            "rmse_mm":                    round(rmse_mm,  1),
            "mae_mm":                     round(mae_mm,   1),
            "r2_test":                    round(r2_test,  3),
            "prediction_2100_m":          round(pred_2100, 3),
            "change_vs_last_observed_mm": round(change_mm, 1),
        })

    results_df = (
        pd.DataFrame(results)
        .sort_values("rmse_mm")
        .reset_index(drop=True)
    )

    # ── Print results ──────────────────────────────────────────────────────
    print("RESULTS — ranked best-to-worst by test RMSE")
    print("(RMSE and MAE in mm — how far off each model's test predictions "
          "were; lower is better)")
    print("(R² — how much of the test window variation the model explains; "
          "closer to 1 is better; negative = worse than predicting the mean)")
    print()
    display_cols = [
        "model", "rmse_mm", "mae_mm", "r2_test",
        "prediction_2100_m", "change_vs_last_observed_mm",
    ]
    print(results_df[display_cols].to_string(index=False))
    print()

    # Flat-prediction warnings (same logic as 13a6)
    for _, row in results_df.iterrows():
        if (abs(row["change_vs_last_observed_mm"]) < 5
                and row["model"] in FLAT_EXPLANATIONS):
            print(
                f"Note on {row['model']}: its 2100 prediction is essentially "
                f"flat (less than 5 mm from the last observed year). "
                f"{FLAT_EXPLANATIONS[row['model']]}"
            )

    # Extrapolation capability
    capable   = [m[0] for m in MODELS if m[4]]
    incapable = [m[0] for m in MODELS if not m[4]]
    print()
    print("Which models can structurally continue a trend past the last "
          "observed year:")
    print(f"  Can extrapolate    : {', '.join(capable)}")
    print(f"  Cannot extrapolate : {', '.join(incapable)}")
    print("  (This is a property of how each algorithm is built, not a "
          "measure of test accuracy.)")
    print()

    return (annual_full, annual_seg, annual_train, annual_test,
            results_df, train_models, seg_models)


# ─── Plot one station panel ───────────────────────────────────────────────────
def plot_station(ax, station_name, annual_full, annual_seg,
                 annual_train, annual_test, train_models, seg_models, config):
    """
    Draws one station panel with three visual layers plus model output:

      Layer 1 — Very light grey small dots: the FULL historical record,
                 including the gap years. These are shown as context only
                 and play no role in any model. Their presence makes the
                 gap periods visible.

      Layer 2 — Dark filled dots: the CONTINUOUS SEGMENT used for all
                 training, testing, and projection.

      Layer 3 — Blue shaded band + dashed vertical line: the test window
                 (2018–2022) and the train/test boundary.

      Model output:
        - One coloured line per model: the SEGMENT-refitted model projected
          from the segment start to 2100.
        - Small diamond markers (◆) at each test year: what the TRAIN-ONLY
          model predicted for those years, so the test accuracy is visible
          as well as the long-run projection.
        - GPR 95% confidence band (shaded).
    """
    train_end_y  = config["train_end"]
    test_start_y = config["test_start"]

    actual_seg_start  = int(annual_seg["year"].min())
    actual_seg_end    = int(annual_seg["year"].max())
    actual_test_start = int(annual_test["year"].min())
    actual_test_end   = int(annual_test["year"].max())
    n_train           = len(annual_train)
    n_test            = len(annual_test)

    # Layer 1: full historical record (context only, never modelled)
    ax.scatter(
        annual_full["year"], annual_full["sea_level_m"],
        s=10, color="#DDDDDD", zorder=1,
        label="Full historical record (not used in models)",
    )

    # Layer 2: continuous segment (what was actually modelled)
    ax.scatter(
        annual_seg["year"], annual_seg["sea_level_m"],
        s=22, color="#444444", zorder=4,
        label="Continuous segment (used for train/test/apply)",
    )

    # Test window shade
    ax.axvspan(
        actual_test_start - 0.5, actual_test_end + 0.5,
        alpha=0.10, color="#1976D2", zorder=0,
        label=f"Test window ({actual_test_start}–{actual_test_end})",
    )

    # Train/test split line
    ax.axvline(
        train_end_y + 0.5, color="#555555", lw=1.2,
        linestyle="--", zorder=3,
        label=f"Train/test split (≤{train_end_y} / ≥{test_start_y})",
    )

    # Model lines and test-prediction diamonds
    x_plot = np.linspace(actual_seg_start, TARGET_YEAR, 400).reshape(-1, 1)

    for model_name, _note, _fit_fn, predict_fn, _can_extrap in MODELS:
        color       = PLOT_COLORS[model_name]
        model_seg   = seg_models[model_name]
        model_train = train_models[model_name]

        # Full segment → 2100 projection
        if model_name == "Gaussian Process Regression":
            y_plot, y_std = predict_gpr(model_seg, x_plot, return_std=True)
            ax.fill_between(
                x_plot.flatten(),
                y_plot - 1.96 * y_std,
                y_plot + 1.96 * y_std,
                color=color, alpha=0.10, zorder=1,
            )
        else:
            y_plot = predict_fn(model_seg, x_plot)

        ax.plot(
            x_plot.flatten(), y_plot,
            color=color, lw=1.6, alpha=0.75,
            label=model_name, zorder=2,
        )

        # Diamond markers: train-only model predictions at each test year
        x_test_arr  = annual_test["year"].values.reshape(-1, 1).astype(float)
        y_pred_test = np.asarray(predict_fn(model_train, x_test_arr)).flatten()
        ax.scatter(
            annual_test["year"], y_pred_test,
            marker="D", s=22, color=color,
            edgecolors="white", linewidths=0.4,
            zorder=6,
            # no label: these are visible in the shaded test window;
            # explained in the panel title below
        )

    ax.set_title(
        f"{station_name}  |  Segment {actual_seg_start}–{actual_seg_end}  |  "
        f"Train {int(annual_train.year.min())}–{int(annual_train.year.max())} "
        f"({n_train} yrs)  /  "
        f"Test {actual_test_start}–{actual_test_end} ({n_test} yrs)\n"
        f"Lines = segment refit → 2100  |  "
        f"◆ = test prediction (train-only model)  |  "
        f"Light grey = full record (not used)",
        fontsize=8.2, fontweight="bold",
    )
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Sea level (m)", fontsize=10)

    # X axis spans the full historical record so the gaps are visible
    ax.set_xlim(int(annual_full["year"].min()) - 3, TARGET_YEAR + 3)
    ax.legend(fontsize=5.6, loc="upper left", framealpha=0.92, ncol=2)
    ax.grid(True, alpha=0.22)


# ─── Summary table PNG ────────────────────────────────────────────────────────
def build_and_save_table(all_results):
    df = all_results.copy()

    df["RMSE (mm)"]            = df["rmse_mm"].map(lambda v: f"{v:.1f}")
    df["MAE (mm)"]             = df["mae_mm"].map(lambda v: f"{v:.1f}")
    df["R² (test)"]            = df["r2_test"].map(
        lambda v: f"{v:.3f}" if not (isinstance(v, float) and np.isnan(v)) else "—"
    )
    df["2100 (m)"]             = df["prediction_2100_m"].map(lambda v: f"{v:.3f}")
    df["Change vs 2022 (mm)"]  = df["change_vs_last_observed_mm"].map(
        lambda v: f"{v:+.1f}"
    )
    df["Extrapolates trend?"]  = df["can_extrapolate_trend"].map(
        {True: "Yes", False: "No"}
    )
    df["Segment"]              = df["segment_period"]
    df["Train"]                = df["train_period"]
    df["Test"]                 = df["test_period"]

    # Rank by test RMSE within each station (best first)
    df = df.sort_values(["station", "rmse_mm"]).reset_index(drop=True)

    table_cols = [
        "station", "model",
        "Segment", "Train", "Test",
        "RMSE (mm)", "MAE (mm)", "R² (test)",
        "2100 (m)", "Change vs 2022 (mm)",
        "Extrapolates trend?",
    ]
    table_df = df[table_cols].rename(
        columns={"station": "Station", "model": "Model"}
    )

    print("=" * 78)
    print("FINAL SUMMARY TABLE — both stations, ranked best-RMSE-first")
    print("(All models trained on continuous post-gap segment only)")
    print("=" * 78)
    print(table_df.to_string(index=False))
    print()

    n_rows  = len(table_df) + 1
    fig_h   = max(4, 0.42 * n_rows + 0.6)
    fig, ax = plt.subplots(figsize=(20, fig_h))
    ax.axis("off")

    tbl = ax.table(
        cellText=table_df.values.tolist(),
        colLabels=list(table_df.columns),
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.0)
    tbl.scale(1, 1.65)
    tbl.auto_set_column_width(col=list(range(len(table_df.columns))))

    for (row, _col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#CCCCCC")
        if row == 0:
            cell.set_facecolor("#2E4057")
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#F2F2F2" if row % 2 == 0 else "#FFFFFF")

    plt.tight_layout()
    plt.savefig(OUT_TABLE_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {OUT_TABLE_PNG}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(
        "13a7 — Continuous post-gap segment, single chronological "
        "train/test split\n"
        "  Documented gap years are excluded from ALL model training, "
        "testing, and projection.\n"
        "  They appear only as background context in the chart.\n"
    )
    for cfg in STATION_CONFIGS:
        print(
            f"  {cfg['name']}: {cfg['gap_note']}\n"
            f"    Continuous segment : {cfg['segment_start']}–"
            f"{cfg['segment_end']}\n"
            f"    TRAIN : ≤ {cfg['train_end']}  |  "
            f"TEST  : ≥ {cfg['test_start']}  |  "
            f"APPLY : refit on segment, project to {TARGET_YEAR}\n"
        )
    print(
        "  Note: if a nominal segment-start year has fewer than 6 usable\n"
        "  months in the quality-filtered data, the actual segment will\n"
        "  start one year later. The script reports any such adjustment.\n"
    )

    station_outputs  = []
    all_results_list = []

    for cfg in STATION_CONFIGS:
        (annual_full, annual_seg, annual_train, annual_test,
         results_df, train_models, seg_models) = run_station(cfg)

        station_outputs.append(
            (cfg, annual_full, annual_seg, annual_train, annual_test,
             train_models, seg_models)
        )
        all_results_list.append(results_df)

    all_results = pd.concat(all_results_list, ignore_index=True)
    all_results.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}\n")

    build_and_save_table(all_results)

    # ── Chart ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    fig.suptitle(
        "Sea Level Rise — 9 ML Models | Continuous Post-Gap Segments Only\n"
        "Train ≤ 2017  |  Test 2018–2022  |  Projection to 2100\n"
        "Light grey dots = full historical record (not used in any model)  |  "
        "Dark dots = continuous segment modelled",
        fontsize=10, fontweight="bold",
    )

    for ax, (cfg, annual_full, annual_seg, annual_train, annual_test,
              train_models, seg_models) in zip(axes, station_outputs):
        plot_station(
            ax, cfg["name"],
            annual_full, annual_seg, annual_train, annual_test,
            train_models, seg_models, cfg,
        )

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"Saved: {OUT_PNG}")

    print()
    print("=" * 78)
    print("HOW TO READ THIS OUTPUT")
    print("=" * 78)
    print(
        "Test RMSE, MAE, and R² measure how well each model predicted sea\n"
        "level for 2018–2022, trained only on the continuous segment years\n"
        "≤ 2017. Lower RMSE/MAE = smaller average prediction error.\n"
        "R² closer to 1 = the model tracked the actual year-to-year\n"
        "observations better. Negative R² = the model did worse than\n"
        "simply predicting the historical mean every year — a known\n"
        "challenge when annual noise (~40 mm) is large relative to the\n"
        "trend signal (~2 mm/year).\n"
        "\n"
        "Unlike 13a3 and 13a6, no data from across the documented gap\n"
        "periods is included anywhere in these models. Every model was\n"
        "trained on a single, unbroken run of annual observations — the\n"
        "key methodological improvement in this script.\n"
        "\n"
        "The 2100 projection (APPLY step) refits each model on the full\n"
        "continuous segment (train + test combined, 16–21 years). This\n"
        "is a shorter record than 13a3 / 13a6 used, so the projection\n"
        "carries more uncertainty and is best read as a supplementary\n"
        "comparison, not as the primary 2100 estimate.\n"
        "\n"
        "Only models marked 'Yes' under 'Extrapolates trend?' produce a\n"
        "meaningful 2100 number. Tree-based models (KNN, Decision Tree,\n"
        "Random Forest, Gradient Boosting) cannot continue a trend past\n"
        "the last observed year — their 2100 value will be close to the\n"
        "last few years on record regardless of the long-term trend.\n"
        "\n"
        "In the chart:\n"
        "  Light grey dots  = full historical record (context only;\n"
        "                     gap periods are visible as breaks)\n"
        "  Dark grey dots   = continuous segment used for modelling\n"
        "  Shaded blue band = test window (2018–2022)\n"
        "  Dashed line      = train/test split boundary\n"
        "  Coloured lines   = each model's projection to 2100\n"
        "                     (segment-refitted)\n"
        "  ◆ markers        = each model's test predictions (2018–2022)\n"
        "                     from the train-only fit — compare these to\n"
        "                     the dark dots in the shaded window to see\n"
        "                     how closely the models tracked reality"
    )
    print()
    print("Done.")


if __name__ == "__main__":
    main()
