"""
13a6_sealevel_train_test.py
============================
Sea Level Rise — 9 ML Models, Single Chronological Train/Test Split
Leixões and Sines

WHAT THIS SCRIPT DOES (plain language)
----------------------------------------
This script asks a simple, concrete question:

  If you had trained a sea-level model on all the data available up to
  the end of 2008, how well would each of the 9 machine learning models
  have predicted sea level for the 14 years that followed (2009–2022)?

That is a single, clean train/test split — the same fundamental idea used
in every introductory ML course, applied here to a real time series:

  TRAIN  :  everything up to and including 2008
  TEST   :  2009 through 2022 (years the model never saw during training)
  APPLY  :  refit on the FULL record (all years), then project to 2100

This is the correct chronological order — train on the past, test on the
future, apply last. Nothing in the test set was used to fit the model, and
the 2100 projection only happens after both train and test are complete.

HOW THIS DIFFERS FROM 13a3_sealevel_ml_models.py
--------------------------------------------------
13a3 used walk-forward cross-validation (5 folds, sliding forward through
time), which gives FIVE independent error estimates per model and averages
them. That is statistically more robust, and is the right approach when you
want a general picture of how a model performs across different historical
periods.

This script uses a SINGLE split instead. That gives ONE error estimate per
model — less robust statistically — but it has advantages for this specific
use case:

  1. More training data. With a 2008 cutoff, each model trains on about
     30-50 years of data before it is tested. In 13a3's first fold, some
     models were trained on as few as 8 years. More training data generally
     helps the model learn the underlying trend more reliably.

  2. A meaningful, recent test window. 2009-2022 is a real, continuous
     14-year block of observed data — not scattered across the historical
     record. How well each model does on those 14 specific years is a
     concrete, interpretable result.

  3. Simpler to explain. "Trained on 1956-2008, tested on 2009-2022" is
     immediately understandable to any reader, including a dissertation
     assessor.

WHY THE 2008 CUTOFF?
--------------------
It was chosen to give a roughly 80/20 split (train on the larger part of
the record, test on the more recent part) — a standard ML convention.
Critically, this cutoff was chosen BEFORE running any model. It was not
picked because it makes any particular model look good. If you want to
verify this: run 13a3 first (it uses a completely different method), form
your own expectation of which models perform best, and only then look at
this script's results. The results of this script did not influence the
choice of 2008 in any way.

THE CHART PRODUCED BY THIS SCRIPT
----------------------------------
Each station panel shows three layers:
  - Observed annual means (grey dots, all years on record)
  - A shaded band over the test window (2009-2022) so the period is
    visually obvious
  - Each of the 9 models drawn as a line from the first observed year
    to 2100, using the FULL-RECORD refit (the Apply step). On top of
    this, each model's TEST PREDICTIONS (2009-2022, from the train-only
    fit) are plotted as small diamond markers in the same colour. This
    lets you see, in the same panel, both where a model goes in the long
    run AND how closely its test-period predictions tracked what was
    actually observed.

A NOTE ON MODELS THAT CANNOT EXTRAPOLATE TO 2100
-------------------------------------------------
Four of the nine models (K-Nearest Neighbors, Decision Tree, Random
Forest, Gradient Boosting) are structurally unable to project a trend
beyond the last year they trained on. Their 2100 "predictions" will
essentially repeat or average the last few years of the full record —
this is a property of how those algorithms work, not a numerical error.
This script flags those models explicitly in the output so the limitation
is visible, not hidden.

REPRODUCIBILITY
---------------
Re-running this script with the same input CSV files produces identical
results for all models except Gaussian Process Regression (GPR), where
tiny floating-point differences between machines can nudge its internal
optimiser slightly. All models with any randomness use RANDOM_STATE=42
(imported from 13a3) for exactly this reason.

OUTPUTS
-------
  sealevel_train_test_summary.csv     — all 9 models × 2 stations, test
                                        metrics + 2100 projection
  sealevel_train_test_chart.png       — observed + test predictions +
                                        projections to 2100, both stations
  sealevel_train_test_table.png       — model comparison table image,
                                        ranked best-to-worst by test RMSE

REQUIRES
--------
  numpy, pandas, matplotlib, scipy, scikit-learn — same as 13a3.
  No new packages to install.

USAGE
-----
  python 13a6_sealevel_train_test.py
"""

import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ─── REUSE — imported from 13a3, never copied or modified ────────────────────
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

_ml3 = import_module("13a3_sealevel_ml_models")

MODELS            = _ml3.MODELS             # 9 (name, note, fit_fn, predict_fn, can_extrap)
compute_annual_means = _ml3.compute_annual_means  # originally from 13a
check_outliers    = _ml3.check_outliers
TARGET_YEAR       = _ml3.TARGET_YEAR        # 2100
RANDOM_STATE      = _ml3.RANDOM_STATE       # 42
PLOT_COLORS       = _ml3.PLOT_COLORS        # colour dict for the 9 models
FLAT_EXPLANATIONS = _ml3.FLAT_EXPLANATIONS  # notes printed when a 2100 prediction is flat
predict_gpr       = _ml3.predict_gpr        # needed separately to request the uncertainty band

# ─── PATHS ───────────────────────────────────────────────────────────────────
LEIXOES_CSV   = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV     = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV       = PROJECT_DIR / "sealevel_train_test_summary.csv"
OUT_PNG       = PROJECT_DIR / "sealevel_train_test_chart.png"
OUT_TABLE_PNG = PROJECT_DIR / "sealevel_train_test_table.png"

# ─── SPLIT YEAR ──────────────────────────────────────────────────────────────
# Train on everything up to and including this year.
# Test on everything after it.
# Chosen BEFORE running any model, as a standard ~80/20 chronological split.
TRAIN_END_YEAR  = 2008
TEST_START_YEAR = TRAIN_END_YEAR + 1   # 2009


# ─── Run train → test → apply for one station ─────────────────────────────────
def run_station(station_name, csv_path):
    print("=" * 78)
    print(station_name)
    print("=" * 78)

    annual = compute_annual_means(csv_path).sort_values("year").reset_index(drop=True)

    # ── Split ──────────────────────────────────────────────────────────────
    annual_train = annual[annual["year"] <= TRAIN_END_YEAR].copy()
    annual_test  = annual[annual["year"] >= TEST_START_YEAR].copy()

    n_train = len(annual_train)
    n_test  = len(annual_test)

    if n_train < 5:
        raise SystemExit(
            f"{station_name}: only {n_train} training years available before "
            f"{TRAIN_END_YEAR}. Cannot fit any model reliably. Check the data "
            f"file or adjust TRAIN_END_YEAR."
        )
    if n_test < 2:
        raise SystemExit(
            f"{station_name}: only {n_test} test years available from "
            f"{TEST_START_YEAR} onward. Nothing meaningful to test on."
        )

    print(f"Full record : {len(annual)} years  "
          f"({int(annual.year.min())}–{int(annual.year.max())})")
    print(f"TRAIN set   : {n_train} years  "
          f"({int(annual_train.year.min())}–{int(annual_train.year.max())})")
    print(f"TEST set    : {n_test} years  "
          f"({int(annual_test.year.min())}–{int(annual_test.year.max())})")

    # Outlier check on the FULL record before any modelling
    check_outliers(annual, station_name)
    print()

    # ── Prepare arrays ─────────────────────────────────────────────────────
    x_train = annual_train["year"].values.reshape(-1, 1).astype(float)
    y_train = annual_train["sea_level_m"].values

    x_test  = annual_test["year"].values.reshape(-1, 1).astype(float)
    y_test  = annual_test["sea_level_m"].values

    x_all   = annual["year"].values.reshape(-1, 1).astype(float)
    y_all   = annual["sea_level_m"].values

    last_year     = int(annual["year"].max())
    last_observed = float(
        annual.loc[annual["year"] == last_year, "sea_level_m"].values[0]
    )

    train_period = (f"{int(annual_train.year.min())}–"
                    f"{int(annual_train.year.max())}")
    test_period  = (f"{int(annual_test.year.min())}–"
                    f"{int(annual_test.year.max())}")

    results        = []
    train_models   = {}   # model fitted on TRAIN only  → for test predictions + chart
    full_models    = {}   # model fitted on ALL data     → for 2100 projection + chart

    print(f"STEP 1+2 — Training each model on {train_period}, "
          f"then testing on {test_period}:")
    print()

    for model_name, model_note, fit_fn, predict_fn, can_extrapolate in MODELS:

        # ── STEP 1 — TRAIN ─────────────────────────────────────────────────
        model_train = fit_fn(x_train, y_train)
        train_models[model_name] = model_train

        # ── STEP 2 — TEST ──────────────────────────────────────────────────
        y_pred_test = np.asarray(predict_fn(model_train, x_test)).flatten()

        resid_mm = (y_pred_test - y_test) * 1000
        rmse_mm  = float(np.sqrt(np.mean(resid_mm ** 2)))
        mae_mm   = float(np.mean(np.abs(resid_mm)))

        ss_res = float(np.sum((y_test - y_pred_test) ** 2))
        ss_tot = float(np.sum((y_test - np.mean(y_test)) ** 2))
        r2_test = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

        # ── STEP 3 — APPLY: refit on ALL data, project to 2100 ────────────
        model_full  = fit_fn(x_all, y_all)
        full_models[model_name] = model_full
        pred_2100   = float(
            predict_fn(model_full, np.array([[float(TARGET_YEAR)]]))[0]
        )
        change_mm   = (pred_2100 - last_observed) * 1000

        results.append({
            "station":                   station_name,
            "model":                     model_name,
            "can_extrapolate_trend":     can_extrapolate,
            "train_period":              train_period,
            "n_train_years":             n_train,
            "test_period":               test_period,
            "n_test_years":              n_test,
            "rmse_mm":                   round(rmse_mm,  1),
            "mae_mm":                    round(mae_mm,   1),
            "r2_test":                   round(r2_test,  3),
            "prediction_2100_m":         round(pred_2100,   3),
            "change_vs_last_observed_mm": round(change_mm, 1),
        })

    results_df = pd.DataFrame(results).sort_values("rmse_mm").reset_index(drop=True)

    # ── Print results ───────────────────────────────────────────────────────
    print("RESULTS — ranked best-to-worst by test RMSE")
    print("(RMSE and MAE: how far off the predictions were in the test window, "
          "in mm — lower is better)")
    print("(R2: how much of the test window's ups and downs the model explains "
          "— closer to 1 is better; negative means worse than predicting the mean)")
    print()
    display_cols = [
        "model", "rmse_mm", "mae_mm", "r2_test",
        "prediction_2100_m", "change_vs_last_observed_mm",
    ]
    print(results_df[display_cols].to_string(index=False))
    print()

    # Flat-prediction warnings
    for _, row in results_df.iterrows():
        if (abs(row["change_vs_last_observed_mm"]) < 5
                and row["model"] in FLAT_EXPLANATIONS):
            print(
                f"Note on {row['model']}: its 2100 prediction is essentially flat "
                f"(less than 5 mm from the last observed year). "
                f"{FLAT_EXPLANATIONS[row['model']]}"
            )

    # Extrapolation capability summary
    capable    = [m[0] for m in MODELS if m[4]]
    incapable  = [m[0] for m in MODELS if not m[4]]
    print()
    print("Which models can structurally continue a trend past the last "
          "observed year:")
    print(f"  Can extrapolate    : {', '.join(capable)}")
    print(f"  Cannot extrapolate : {', '.join(incapable)}")
    print("  (This is a property of how each algorithm works, not a measure "
          "of accuracy.)")
    print()

    return annual, annual_train, annual_test, results_df, train_models, full_models


# ─── Plot one station panel ───────────────────────────────────────────────────
def plot_station(ax, station_label, annual, annual_train, annual_test,
                 train_models, full_models):
    """
    Draws one station panel:
      - Grey scatter: all observed annual means
      - Light blue shade: the test window (2009-2022)
      - Vertical dashed line: the train/test split year
      - One coloured line per model (all-data refit, to 2100)
      - Small diamond markers at each test year (train-only predictions)
        — these show how close each model was to the observed test data
      - GPR 95% confidence band
    """
    first_year = int(annual["year"].min())
    last_year  = int(annual["year"].max())

    test_start = int(annual_test["year"].min())
    test_end   = int(annual_test["year"].max())

    # Observed data
    ax.scatter(annual["year"], annual["sea_level_m"],
               s=18, color="#666666", zorder=5, label="Observed (annual mean)")

    # Shaded test window
    ax.axvspan(test_start - 0.5, test_end + 0.5,
               alpha=0.08, color="#1976D2", zorder=0,
               label=f"Test window ({test_start}–{test_end})")

    # Train/test split marker
    ax.axvline(TRAIN_END_YEAR + 0.5, color="#555555", lw=1.2,
               linestyle="--", zorder=4,
               label=f"Train/test split ({TRAIN_END_YEAR})")

    # Model lines (all-data refit → projection to 2100)
    x_plot = np.linspace(first_year, TARGET_YEAR, 400).reshape(-1, 1)

    for model_name, _note, _fit_fn, predict_fn, _can_extrap in MODELS:
        color       = PLOT_COLORS[model_name]
        model_full  = full_models[model_name]
        model_train = train_models[model_name]

        # Full projection line
        if model_name == "Gaussian Process Regression":
            y_plot, y_std = predict_gpr(model_full, x_plot, return_std=True)
            ax.fill_between(
                x_plot.flatten(),
                y_plot - 1.96 * y_std,
                y_plot + 1.96 * y_std,
                color=color, alpha=0.10, zorder=1,
            )
        else:
            y_plot = predict_fn(model_full, x_plot)

        ax.plot(x_plot.flatten(), y_plot,
                color=color, lw=1.6, alpha=0.75,
                label=model_name, zorder=2)

        # Test predictions: small diamonds showing where the TRAIN-only
        # model predicted for each test year (the key test metric, made visual)
        x_test_plot = annual_test["year"].values.reshape(-1, 1).astype(float)
        y_pred_test = np.asarray(predict_fn(model_train, x_test_plot)).flatten()
        ax.scatter(annual_test["year"], y_pred_test,
                   marker="D", s=22, color=color,
                   edgecolors="white", linewidths=0.4,
                   zorder=6)   # no label: these are for visual inspection only;
                                # explained in the title note below

    # Axis labels and styling
    ax.set_title(
        f"{station_label}\n"
        f"Lines = all-data refit → 2100 projection  |  "
        f"◆ = test prediction (train-only model)",
        fontsize=9.5, fontweight="bold",
    )
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Sea level (m)", fontsize=10)
    ax.set_xlim(first_year - 3, TARGET_YEAR + 3)
    ax.legend(fontsize=6.5, loc="upper left", framealpha=0.92)
    ax.grid(True, alpha=0.22)


# ─── Summary table PNG ────────────────────────────────────────────────────────
def build_and_save_table(all_results):
    df = all_results.copy()

    df["RMSE (mm)"]                  = df["rmse_mm"].map(lambda v: f"{v:.1f}")
    df["MAE (mm)"]                   = df["mae_mm"].map(lambda v: f"{v:.1f}")
    df["R² (test window)"]           = df["r2_test"].map(
        lambda v: f"{v:.3f}" if not np.isnan(v) else "—"
    )
    df["2100 prediction (m)"]        = df["prediction_2100_m"].map(lambda v: f"{v:.3f}")
    df["Change vs 2022 (mm)"]        = df["change_vs_last_observed_mm"].map(
        lambda v: f"{v:+.1f}"
    )
    df["Extrapolates trend?"]        = df["can_extrapolate_trend"].map(
        {True: "Yes", False: "No"}
    )
    df["Train period"]               = df["train_period"]
    df["Test period"]                = df["test_period"]

    # Rank by test RMSE ascending (best first) within each station
    df = df.sort_values(["station", "rmse_mm"]).reset_index(drop=True)

    table_cols = [
        "station", "model",
        "Train period", "Test period",
        "RMSE (mm)", "MAE (mm)", "R² (test window)",
        "2100 prediction (m)", "Change vs 2022 (mm)",
        "Extrapolates trend?",
    ]
    table_df = df[table_cols].rename(columns={"station": "Station", "model": "Model"})

    # Print to console
    print("=" * 78)
    print("FINAL SUMMARY TABLE — both stations, ranked best-RMSE-first")
    print("=" * 78)
    print(table_df.to_string(index=False))
    print()

    # Save as PNG
    n_rows    = len(table_df) + 1
    fig_h     = max(4, 0.42 * n_rows + 0.6)
    fig, ax   = plt.subplots(figsize=(18, fig_h))
    ax.axis("off")

    tbl = ax.table(
        cellText=table_df.values.tolist(),
        colLabels=list(table_df.columns),
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
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
        "13a6 — Single chronological train/test split\n"
        f"  TRAIN : all years  ≤ {TRAIN_END_YEAR}\n"
        f"  TEST  : all years  ≥ {TEST_START_YEAR}\n"
        f"  APPLY : refit on full record, project to {TARGET_YEAR}\n"
    )

    (lx_annual, lx_train, lx_test,
     lx_results, lx_train_models, lx_full_models) = run_station(
        "Leixões", LEIXOES_CSV
    )

    (sn_annual, sn_train, sn_test,
     sn_results, sn_train_models, sn_full_models) = run_station(
        "Sines", SINES_CSV
    )

    all_results = pd.concat([lx_results, sn_results], ignore_index=True)
    all_results.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}\n")

    build_and_save_table(all_results)

    # ── Chart ────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(17, 7))
    last_data_year = int(max(lx_annual["year"].max(), sn_annual["year"].max()))
    fig.suptitle(
        f"Sea Level Rise — 9 ML Models  |  "
        f"Train: up to {TRAIN_END_YEAR}  |  "
        f"Test: {TEST_START_YEAR}–{last_data_year}  |  "
        f"Projection: to {TARGET_YEAR}",
        fontsize=12, fontweight="bold",
    )

    plot_station(
        axes[0],
        f"Leixões ({int(lx_annual.year.min())}–{int(lx_annual.year.max())})",
        lx_annual, lx_train, lx_test,
        lx_train_models, lx_full_models,
    )
    plot_station(
        axes[1],
        f"Sines ({int(sn_annual.year.min())}–{int(sn_annual.year.max())})",
        sn_annual, sn_train, sn_test,
        sn_train_models, sn_full_models,
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
        "The test RMSE and R² tell you how well each model predicted sea\n"
        "level for the years 2009–2022, having been trained only on data\n"
        "before 2009. Lower RMSE = smaller prediction error. R² closer to\n"
        "1 = the model tracked the actual ups and downs well. Negative R²\n"
        "= the model did worse than simply predicting the historical average\n"
        "every year.\n"
        "\n"
        "The 2100 projection is produced by refitting each model on the\n"
        "FULL record (1956-2022 / 1977-2022) — it does not come from the\n"
        "train-only model. Only models marked 'Yes' under Extrapolates\n"
        "trend? produce a meaningful 2100 number. The others will give a\n"
        "value close to the last few observed years, regardless of the\n"
        "long-term trend.\n"
        "\n"
        "The chart's diamond markers (◆) show what each model predicted\n"
        "for the test years (2009-2022) using only training data. Compare\n"
        "them visually to the grey observed dots in the shaded test window."
    )
    print()
    print("Done.")


if __name__ == "__main__":
    main()
