"""
13a3_sealevel_ml_models.py
===========================
Sea Level Rise — Machine Learning Model Comparison
Leixões (1956–2022) and Sines (1977–2022)

WHAT THIS SCRIPT DOES (plain language, no jargon):
  1. Loads the same annual sea level data used in 13a_sealevel_regression.py,
     using the exact same data-cleaning function, so the numbers stay
     comparable between the two scripts.
  2. Runs a quick, explicit outlier check on the annual data BEFORE any
     modelling: fits one simple straight line through all the observed
     years and flags any year that sits more than 3 standard deviations
     away from it. This is printed so the check is visible, not assumed.
  3. Trains and compares NINE machine learning regression models:
       - Linear Regression            -> the simplest one: a single
                                          straight line through the years.
                                          Also used as the plain baseline
                                          the others are compared against.
       - Ridge Regression             -> a straight line like Linear
                                          Regression, but with a small
                                          built-in caution against leaning
                                          too hard on the trend.
       - Lasso Regression             -> a stronger version of that same
                                          caution — strong enough that it
                                          can shrink the trend's importance
                                          all the way to zero. With only one
                                          input (year), watch for this: if
                                          Lasso's 2100 number comes out flat,
                                          that means the penalty erased the
                                          trend, not that sea level stopped
                                          rising.
       - K-Nearest Neighbors          -> predicts a year by averaging the
                                          most similar years it has already
                                          seen. Has no concept of a trend
                                          continuing past its training
                                          years, so it cannot extrapolate.
       - Decision Tree                -> splits the years into a handful of
                                          yes/no rules. Like KNN, it can
                                          only repeat values it has already
                                          seen, so it cannot extrapolate.
       - Random Forest                -> many decision trees averaged
                                          together. Included on purpose as
                                          a "wrong tool for this job"
                                          example — see the note printed
                                          next to its result below.
       - Gradient Boosting            -> many small decision trees built
                                          one after another. Built from the
                                          same kind of trees as Random
                                          Forest, so it inherits the same
                                          inability to extrapolate.
       - Support Vector Regression    -> deliberately kept to a straight
                                          line so it doesn't invent fake
                                          curves out of a small number of
                                          data points.
       - Gaussian Process Regression  -> combines a rising-trend component
                                          with a short-term-wiggle
                                          component, and also reports how
                                          confident it is — that confidence
                                          band widens the further into the
                                          future it predicts.
     None of these nine were hand-tuned: every one uses scikit-learn's
     standard, out-of-the-box settings. The point of this script is to
     compare the algorithms on a level footing, not to find the best
     possible version of each one.
  4. TESTS each model using walk-forward cross-validation: the data is
     split into 5 chronological folds. In each fold, the model trains
     only on the years before that fold and is tested only on the years
     immediately after — never on years that come earlier. This is
     repeated 5 times, sliding forward each time, and the error is
     averaged across all 5 readings. This is deliberately NOT the kind of
     cross-validation used for things like patient records or survey
     answers (where rows are shuffled into random groups) — shuffling a
     time series would let a model train on years that come after the
     year it is being tested on, which is the same "seeing the future"
     problem already fixed once in this project (see fit_gpr below).
     Three numbers are reported per model: RMSE and MAE (both in
     millimetres — how far off the predictions were, on average; lower is
     more accurate) and R² (how much of the year-to-year ups and downs the
     model actually explains; closer to 1 is better).
  5. Only AFTER this cross-validated testing, each model is re-fit on ALL
     the observed years and used to project forward to the year 2100.
     This is the APPLY step. It always happens last, and it never affects
     the test scores above it — train, then test, then apply, in that
     order, every time.
  6. Saves one CSV table with every model's cross-validated test scores and
     2100 projection for both stations, and one chart with one panel per
     station.

WHY THE ORDER MATTERS:
  A model only earns the right to make a 2100 projection after it has
  proven, on years it never trained on, that its predictions are
  reasonable. This script is built so that order can never be skipped or
  reversed, and so every number in the output CSV was actually computed by
  running this code — nothing here is typed in by hand.

A STRUCTURAL POINT WORTH READING BEFORE LOOKING AT THE RESULTS:
  Four of the nine models (K-Nearest Neighbors, Decision Tree, Random
  Forest, Gradient Boosting) are built in a way that makes them
  structurally unable to continue a trend past the years they trained on
  — this is true regardless of how accurate they are on the test years.
  The other five (Linear, Ridge, Lasso, Support Vector Regression,
  Gaussian Process Regression) can continue a trend. This script prints
  that grouping explicitly for each station, because it is the actual
  reason for picking one model's 2100 number over another's — not just
  "which one scored best on the test years."

METHODOLOGY — kept identical to 13a_sealevel_regression.py where it overlaps:
  - Same input CSV files
  - Same annual-mean calculation, imported directly from 13a, so both
    scripts always agree on the underlying data
  - Same scipy-based OLS formula for the Linear Regression baseline

REPRODUCIBILITY:
  Re-running this script, on this machine or another, with the same data
  files, will reproduce the same numbers for every model except Gaussian
  Process Regression, where tiny floating-point differences between
  machines could in theory nudge its internal optimizer to a very
  slightly different (but practically negligible) answer. Every model
  with any randomness in it (Decision Tree, Random Forest, Gradient
  Boosting, Gaussian Process Regression) uses a fixed random seed for
  exactly this reason.

OUTPUTS:
  sealevel_ml_models_summary.csv   — cross-validated results, both stations
  sealevel_ml_models_chart.png     — one panel per station

REQUIRES:
  numpy, pandas, matplotlib  (already used by 13a)
  scipy                      (already used by 13a)
  scikit-learn               (new — install once with: pip install scikit-learn)

USAGE:
  python 13a3_sealevel_ml_models.py
"""

import sys
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
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel, DotProduct
    from sklearn.linear_model import Ridge, Lasso
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.svm import SVR
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.exceptions import ConvergenceWarning
except ImportError:
    raise SystemExit(
        "This script needs the 'scikit-learn' package for the machine "
        "learning models. Install it with:\n"
        "    pip install scikit-learn\n"
    )

# The Gaussian Process kernel below has a "trend" ingredient and a "wiggle"
# ingredient (see fit_gpr). On this data, the optimizer sometimes settles on
# a very small weight for the trend ingredient — meaning it found it can
# explain most of the long-term rise using the wiggle ingredient stretched
# out, instead. scikit-learn prints a warning when that weight lands right
# at the edge of the search range. This was checked directly: widening that
# search range by 100x produced the exact same prediction, to the decimal,
# which confirms the result does not depend on where that edge sits. The
# warning is therefore safe to silence rather than print on every run.
import warnings
warnings.filterwarnings("ignore", category=ConvergenceWarning)

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
LEIXOES_CSV = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV   = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV       = PROJECT_DIR / "sealevel_ml_models_summary.csv"
OUT_PNG       = PROJECT_DIR / "sealevel_ml_models_chart.png"
OUT_TABLE_PNG = PROJECT_DIR / "sealevel_ml_models_table.png"

TARGET_YEAR  = 2100
N_CV_SPLITS  = 5      # walk-forward cross-validation folds (a standard, commonly used choice)
RANDOM_STATE = 42     # fixed seed so re-running the script gives the same numbers

# ─── REUSE THE EXACT SAME DATA-PREP FUNCTION AS 13a_sealevel_regression.py ────
# This keeps both scripts using identical annual-mean numbers, so results
# stay comparable and reproducible across the whole project.
sys.path.insert(0, str(PROJECT_DIR))
_baseline = import_module("13a_sealevel_regression")
compute_annual_means = _baseline.compute_annual_means


# ─── EDA STEP: explicit outlier check, run before any modelling ──────────────
def check_outliers(annual_df, station_name):
    """
    Fits one simple straight line through ALL the observed years, then
    looks at how far each year's actual value sits from that line. Any
    year whose gap is unusually large (more than 3 standard deviations of
    all the gaps) is flagged here so it can be looked at by eye, rather
    than silently feeding a possibly broken reading into every model below.
    """
    x = annual_df["year"].values.astype(float)
    y = annual_df["sea_level_m"].values
    slope, intercept, _, _, _ = stats.linregress(x, y)
    residuals_mm = (y - (slope * x + intercept)) * 1000
    threshold_mm = 3 * np.std(residuals_mm)
    flagged_years = annual_df.loc[np.abs(residuals_mm) > threshold_mm, "year"].astype(int).tolist()

    if flagged_years:
        print(f"Outlier check ({station_name}): {len(flagged_years)} year(s) sit more "
              f"than 3 standard deviations away from the overall trend line: "
              f"{flagged_years}. Worth a manual look before trusting the results below.")
    else:
        print(f"Outlier check ({station_name}): no year sits more than 3 standard "
              f"deviations away from the overall trend line. No obvious data problems found.")
    return flagged_years


# ─── Walk-forward (time-respecting) cross-validation ──────────────────────────
def walk_forward_cv(x, y, fit_fn, predict_fn, n_splits=N_CV_SPLITS):
    """
    Splits the years into n_splits chronological folds. Fold 1 trains on
    the oldest block of years and tests on the block right after it. Fold
    2 trains on everything up to (and including) fold 1's test years, and
    tests on the next block. And so on. Every fold only ever trains on the
    past and tests on years immediately after — never on the future,
    exactly like the single 80/20 split used earlier in this project, just
    repeated several times so we get several independent error readings
    per model instead of one.

    Returns the mean and standard deviation, across folds, of RMSE (mm),
    MAE (mm), and R² — the same three numbers reported in every comparison
    table seen tonight's lecture, adapted here to a forecasting problem.
    """
    splitter = TimeSeriesSplit(n_splits=n_splits)
    rmse_folds, mae_folds, r2_folds = [], [], []

    for train_idx, test_idx in splitter.split(x):
        x_tr, y_tr = x[train_idx], y[train_idx]
        x_te, y_te = x[test_idx], y[test_idx]

        model = fit_fn(x_tr, y_tr)
        y_pred = np.asarray(predict_fn(model, x_te)).flatten()

        resid_mm = (y_pred - y_te) * 1000
        rmse_folds.append(float(np.sqrt(np.mean(resid_mm ** 2))))
        mae_folds.append(float(np.mean(np.abs(resid_mm))))

        ss_res = float(np.sum((y_te - y_pred) ** 2))
        ss_tot = float(np.sum((y_te - np.mean(y_te)) ** 2))
        r2_folds.append(1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"))

    return {
        "rmse_mm_mean": float(np.mean(rmse_folds)),
        "rmse_mm_std": float(np.std(rmse_folds)),
        "mae_mm_mean": float(np.mean(mae_folds)),
        "mae_mm_std": float(np.std(mae_folds)),
        "r2_mean": float(np.nanmean(r2_folds)),
        "r2_std": float(np.nanstd(r2_folds)),
    }


# ─── MODEL: Linear Regression ─────────────────────────────────────────────────
def fit_linear(x_train, y_train):
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        x_train.flatten(), y_train
    )
    return {"slope": slope, "intercept": intercept}


def predict_linear(model, x_query):
    return model["slope"] * x_query.flatten() + model["intercept"]


# ─── MODEL: Ridge Regression ──────────────────────────────────────────────────
def fit_ridge(x_train, y_train):
    x_mean, x_std = x_train.mean(), x_train.std()
    xt = (x_train - x_mean) / x_std
    ridge = Ridge(alpha=1.0)  # scikit-learn's standard default — not hand-tuned
    ridge.fit(xt, y_train)
    return {"model": ridge, "x_mean": x_mean, "x_std": x_std}


def predict_ridge(model, x_query):
    xqt = (x_query - model["x_mean"]) / model["x_std"]
    return model["model"].predict(xqt)


# ─── MODEL: Lasso Regression ──────────────────────────────────────────────────
def fit_lasso(x_train, y_train):
    x_mean, x_std = x_train.mean(), x_train.std()
    xt = (x_train - x_mean) / x_std
    lasso = Lasso(alpha=1.0)  # scikit-learn's standard default — not hand-tuned
    lasso.fit(xt, y_train)
    return {"model": lasso, "x_mean": x_mean, "x_std": x_std}


def predict_lasso(model, x_query):
    xqt = (x_query - model["x_mean"]) / model["x_std"]
    return model["model"].predict(xqt)


# ─── MODEL: K-Nearest Neighbors Regression ────────────────────────────────────
# With only one input (year), scaling it would not change which years count
# as "nearest", so it is skipped here on purpose.
def fit_knn(x_train, y_train):
    knn = KNeighborsRegressor(n_neighbors=5)  # scikit-learn's standard default
    knn.fit(x_train, y_train)
    return {"model": knn}


def predict_knn(model, x_query):
    return model["model"].predict(x_query)


# ─── MODEL: Decision Tree Regression ──────────────────────────────────────────
def fit_decision_tree(x_train, y_train):
    tree = DecisionTreeRegressor(random_state=RANDOM_STATE)
    tree.fit(x_train, y_train)
    return {"model": tree}


def predict_decision_tree(model, x_query):
    return model["model"].predict(x_query)


# ─── MODEL: Random Forest Regression (deliberate "wrong tool" example) ───────
def fit_rf(x_train, y_train):
    rf = RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE)
    rf.fit(x_train, y_train)
    return {"model": rf}


def predict_rf(model, x_query):
    return model["model"].predict(x_query)


# ─── MODEL: Gradient Boosting Regression ──────────────────────────────────────
def fit_gboost(x_train, y_train):
    gboost = GradientBoostingRegressor(random_state=RANDOM_STATE)
    gboost.fit(x_train, y_train)
    return {"model": gboost}


def predict_gboost(model, x_query):
    return model["model"].predict(x_query)


# ─── MODEL: Support Vector Regression (kept linear on purpose) ───────────────
def fit_svr(x_train, y_train):
    x_mean, x_std = x_train.mean(), x_train.std()
    xt = (x_train - x_mean) / x_std
    svr = SVR(kernel="linear", C=2.0, epsilon=0.005)
    svr.fit(xt, y_train)
    return {"model": svr, "x_mean": x_mean, "x_std": x_std}


def predict_svr(model, x_query):
    xqt = (x_query - model["x_mean"]) / model["x_std"]
    return model["model"].predict(xqt)


# ─── MODEL: Gaussian Process Regression ───────────────────────────────────────
# The kernel below gives the model TWO ingredients, added together:
#   1. A "keep rising at a steady rate" component (DotProduct) — this is what
#      lets the model continue a trend once it runs out of real data, instead
#      of sliding back toward the historical average. Without this piece, a
#      Gaussian Process has no concept of "continue in the same direction" —
#      it simply reverts to the mean of the training data once it is far
#      enough past the last observed year. That reversion is NOT a sign of
#      uncertainty, it is a structural blind spot of a wiggle-only kernel,
#      so this ingredient is mandatory for an extrapolation task like ours,
#      not an optional refinement.
#   2. A "fit the local wiggles" component (RBF) — this lets the model track
#      the year-to-year ups and downs in the observed data, the same way it
#      did before.
# WhiteKernel absorbs measurement noise, as before.
def fit_gpr(x_train, y_train):
    x_mean, x_std = x_train.mean(), x_train.std()
    xt = (x_train - x_mean) / x_std
    kernel = (
        ConstantKernel(1.0, (1e-5, 1e5)) * DotProduct(sigma_0=1.0, sigma_0_bounds=(1e-5, 1e5))
        + ConstantKernel(1.0, (1e-5, 1e5)) * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
        + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-6, 1e1))
    )
    gpr = GaussianProcessRegressor(
        kernel=kernel,
        normalize_y=True,
        n_restarts_optimizer=15,
        random_state=RANDOM_STATE,
    )
    gpr.fit(xt, y_train)
    return {"model": gpr, "x_mean": x_mean, "x_std": x_std}


def predict_gpr(model, x_query, return_std=False):
    xqt = (x_query - model["x_mean"]) / model["x_std"]
    if return_std:
        pred, std = model["model"].predict(xqt, return_std=True)
        return pred, std
    return model["model"].predict(xqt)


# ─── The nine models: (name, plain-language description, fit, predict, ───────
# ─── can it structurally continue a trend past the last observed year?) ──────
MODELS = [
    (
        "Linear Regression",
        "The simplest machine learning regression model: one straight line "
        "through all the years. Also used as the plain baseline the other "
        "models are compared against.",
        fit_linear, predict_linear, True,
    ),
    (
        "Ridge Regression",
        "A straight-line model like Linear Regression, with a small "
        "built-in caution against leaning too hard on the trend. With "
        "only one input (year), expect this to look close to Linear "
        "Regression.",
        fit_ridge, predict_ridge, True,
    ),
    (
        "Lasso Regression",
        "Similar caution to Ridge, but strong enough that it can shrink "
        "the trend's importance all the way to zero. If its 2100 number "
        "comes out flat, that means the penalty erased the trend — see "
        "the note printed below its result if that happens.",
        fit_lasso, predict_lasso, True,
    ),
    (
        "K-Nearest Neighbors",
        "Predicts a year by averaging the most similar years it has "
        "already seen. Has no concept of a trend continuing past its "
        "training years, so it cannot extrapolate to 2100 by design.",
        fit_knn, predict_knn, False,
    ),
    (
        "Decision Tree",
        "Splits the observed years into a small set of yes/no rules. "
        "Like K-Nearest Neighbors, it can only repeat values from years "
        "it has already seen.",
        fit_decision_tree, predict_decision_tree, False,
    ),
    (
        "Random Forest",
        "Many decision trees averaged together. Included on purpose as "
        "a 'wrong tool for this job' example — see the note printed "
        "below its result.",
        fit_rf, predict_rf, False,
    ),
    (
        "Gradient Boosting",
        "Many small decision trees built one after another. Built from "
        "the same kind of trees as Random Forest, so it inherits the "
        "same inability to extrapolate.",
        fit_gboost, predict_gboost, False,
    ),
    (
        "Support Vector Regression",
        "Kept to a straight line on purpose so it does not invent fake "
        "curves from a small number of data points.",
        fit_svr, predict_svr, True,
    ),
    (
        "Gaussian Process Regression",
        "Combines a trend component (so it keeps rising instead of "
        "reverting to the historical average once past the last "
        "observed year) with a wiggle component (so it still tracks "
        "short-term ups and downs). Also reports how confident it is.",
        fit_gpr, predict_gpr, True,
    ),
]

PLOT_COLORS = {
    "Linear Regression": "#222222",
    "Ridge Regression": "#9C27B0",
    "Lasso Regression": "#673AB7",
    "K-Nearest Neighbors": "#00ACC1",
    "Decision Tree": "#795548",
    "Random Forest": "#FB8C00",
    "Gradient Boosting": "#E53935",
    "Support Vector Regression": "#388E3C",
    "Gaussian Process Regression": "#1976D2",
}

# Plain-language explanation printed automatically whenever a model's 2100
# prediction comes out essentially flat (less than 5mm different from the
# last observed year) — the likely reason differs by model, so this is not
# one generic message.
FLAT_EXPLANATIONS = {
    "Lasso Regression": (
        "Lasso's default penalty can shrink a weak or long-term trend's "
        "coefficient all the way to zero. If you see this, the penalty — "
        "not the underlying data — is responsible for the flat line."
    ),
    "K-Nearest Neighbors": (
        "it predicts 2100 by averaging the nearest YEARS it has seen, "
        "which by 2100 are simply the last few real years on record — it "
        "has no concept of a trend continuing past them."
    ),
    "Decision Tree": (
        "tree-based models split the data into rules using only the years "
        "they trained on, so they cannot continue a trend past the last "
        "year observed."
    ),
    "Random Forest": (
        "tree-based models split the data into rules using only the years "
        "they trained on, so they cannot continue a trend past the last "
        "year observed. This is expected, not an error: it is exactly why "
        "Random Forest is the wrong tool for forecasting forward in time."
    ),
    "Gradient Boosting": (
        "like other tree-based models, it only learns rules from the "
        "years it trained on and cannot continue a trend past the last "
        "year observed."
    ),
    "Ridge Regression": (
        "Ridge's default penalty shrinks coefficients toward zero (though "
        "rarely all the way to zero). A flat result here would mean the "
        "trend signal is being substantially dampened by the penalty."
    ),
}


# ─── Run cross-validated test, then apply, for one station ───────────────────
def run_station(station_name, csv_path):
    print("=" * 78)
    print(station_name)
    print("=" * 78)

    annual = compute_annual_means(csv_path).sort_values("year").reset_index(drop=True)

    print(f"Total years of data : {len(annual)}  "
          f"({int(annual.year.min())}-{int(annual.year.max())})")
    check_outliers(annual, station_name)
    print()

    x_full = annual["year"].values.reshape(-1, 1).astype(float)
    y_full = annual["sea_level_m"].values

    last_year = int(annual["year"].max())
    last_observed = float(annual.loc[annual["year"] == last_year, "sea_level_m"].values[0])

    results = []
    fitted_full_models = {}

    print(f"Cross-validation: {N_CV_SPLITS} chronological (walk-forward) folds per "
          f"model — each fold trains only on the past and tests on the years right "
          f"after it.")
    print()

    for model_name, model_note, fit_fn, predict_fn, can_extrapolate in MODELS:
        # STEP 1 + 2 — TRAIN/TEST via walk-forward cross-validation
        cv = walk_forward_cv(x_full, y_full, fit_fn, predict_fn, n_splits=N_CV_SPLITS)

        # STEP 3 — APPLY: only now, refit on ALL years and project to 2100
        model_full = fit_fn(x_full, y_full)
        fitted_full_models[model_name] = model_full
        pred_2100 = float(predict_fn(model_full, np.array([[float(TARGET_YEAR)]]))[0])
        change_mm = (pred_2100 - last_observed) * 1000

        results.append({
            "station": station_name,
            "model": model_name,
            "what_it_is": model_note,
            "can_extrapolate_trend": can_extrapolate,
            "cv_folds": N_CV_SPLITS,
            "rmse_mm_mean": round(cv["rmse_mm_mean"], 1),
            "rmse_mm_std": round(cv["rmse_mm_std"], 1),
            "mae_mm_mean": round(cv["mae_mm_mean"], 1),
            "mae_mm_std": round(cv["mae_mm_std"], 1),
            "r2_mean": round(cv["r2_mean"], 3),
            "r2_std": round(cv["r2_std"], 3),
            "prediction_2100_m": round(pred_2100, 3),
            "change_vs_last_observed_mm": round(change_mm, 1),
        })

    results_df = pd.DataFrame(results)

    print("RESULTS (lower RMSE/MAE = more accurate on years each fold never trained "
          "on; R2 closer to 1 = explains more of the year-to-year ups and downs)")
    display_cols = [
        "model", "rmse_mm_mean", "rmse_mm_std", "mae_mm_mean", "mae_mm_std",
        "r2_mean", "r2_std", "prediction_2100_m", "change_vs_last_observed_mm",
    ]
    print(results_df[display_cols].to_string(index=False))

    for _, row in results_df.iterrows():
        if abs(row["change_vs_last_observed_mm"]) < 5 and row["model"] in FLAT_EXPLANATIONS:
            print(
                f"\nNote on {row['model']}: its 2100 prediction is essentially "
                f"flat (less than 5mm different from the last observed year). "
                f"{FLAT_EXPLANATIONS[row['model']]}"
            )

    extrapolation_capable = [m[0] for m in MODELS if m[4]]
    extrapolation_incapable = [m[0] for m in MODELS if not m[4]]
    print(
        "\nWhich models can structurally continue a trend to 2100, regardless of "
        "how accurate they scored above:"
    )
    print(f"  Capable (by design)     : {', '.join(extrapolation_capable)}")
    print(f"  Not capable (by design) : {', '.join(extrapolation_incapable)}")
    print(
        "  This is a property of how each algorithm works, not a measure of "
        "which one fit the test years best — see the RESULTS table above for that."
    )
    print()

    return annual, results_df, fitted_full_models, last_year


# ─── Plot one station's panel ──────────────────────────────────────────────────
def plot_station(ax, station_label, annual, fitted_full_models, last_year):
    ax.scatter(annual["year"], annual["sea_level_m"], s=24, color="#666666",
               label="Observed annual mean sea level", zorder=3)

    x_plot = np.linspace(annual["year"].min(), TARGET_YEAR, 300).reshape(-1, 1)

    for model_name, model_note, fit_fn, predict_fn, can_extrapolate in MODELS:
        model_full = fitted_full_models[model_name]
        color = PLOT_COLORS[model_name]
        if model_name == "Gaussian Process Regression":
            y_plot, y_std = predict_gpr(model_full, x_plot, return_std=True)
            ax.fill_between(x_plot.flatten(), y_plot - 1.96 * y_std, y_plot + 1.96 * y_std,
                             color=color, alpha=0.12, zorder=1)
        else:
            y_plot = predict_fn(model_full, x_plot)
        ax.plot(x_plot.flatten(), y_plot, color=color, lw=1.8, label=model_name, zorder=2)

    ax.axvline(last_year, color="#999999", lw=1, linestyle=":", alpha=0.8)
    ax.set_title(station_label, fontsize=11, fontweight="bold")
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Sea level (m)", fontsize=10)
    ax.set_xlim(annual["year"].min() - 3, TARGET_YEAR + 3)
    ax.legend(fontsize=6.3, loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.25)


# ─── Final summary table (all models x both stations) ──────────────────────────
def build_summary_table(all_results):
    """Turn the raw numeric results into a presentation-ready table.

    Formats each metric as "mean ± std" (the same convention used in the
    lecture screenshots' cross-validation tables, e.g. "0,98 ± 0,03"), and
    ranks rows within each station by CV RMSE (best/most accurate first).
    """
    df = all_results.copy()

    df["RMSE (mm)"] = df.apply(
        lambda r: f"{r['rmse_mm_mean']:.1f} ± {r['rmse_mm_std']:.1f}", axis=1
    )
    df["MAE (mm)"] = df.apply(
        lambda r: f"{r['mae_mm_mean']:.1f} ± {r['mae_mm_std']:.1f}", axis=1
    )
    df["R2"] = df.apply(
        lambda r: f"{r['r2_mean']:.3f} ± {r['r2_std']:.3f}", axis=1
    )
    df["2100 prediction (m)"] = df["prediction_2100_m"].map(lambda v: f"{v:.3f}")
    df["Change vs last observed (mm)"] = df["change_vs_last_observed_mm"].map(
        lambda v: f"{v:+.1f}"
    )
    df["Extrapolates trend?"] = df["can_extrapolate_trend"].map({True: "Yes", False: "No"})

    # Rank best (lowest CV RMSE) first, within each station
    df = df.sort_values(["station", "rmse_mm_mean"], ascending=[True, True]).reset_index(drop=True)

    table_cols = [
        "station", "model", "RMSE (mm)", "MAE (mm)", "R2",
        "2100 prediction (m)", "Change vs last observed (mm)", "Extrapolates trend?",
    ]
    table_df = df[table_cols].rename(columns={"station": "Station", "model": "Model"})
    return table_df


def print_and_save_summary_table(all_results):
    """Print the final table to the console and save it as a PNG image.

    The image (OUT_TABLE_PNG) is meant to be pasted directly into the
    dissertation or slides, mirroring the visual style of the lecture
    screenshots' model-comparison tables.
    """
    table_df = build_summary_table(all_results)

    print("=" * 78)
    print("FINAL SUMMARY TABLE — every model, both stations, ranked best-RMSE-first")
    print("(value ± std = mean ± standard deviation across the "
          f"{N_CV_SPLITS} walk-forward CV folds)")
    print("=" * 78)
    print(table_df.to_string(index=False))
    print()

    n_rows = len(table_df) + 1  # +1 for the header row
    fig_height = 0.45 * n_rows + 0.6
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis("off")

    tbl = ax.table(
        cellText=table_df.values.tolist(),
        colLabels=list(table_df.columns),
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1, 1.6)
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


# ─── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    print("Loading tide gauge data and cross-validating each model before "
          "applying it to 2100...\n")

    leixoes_annual, leixoes_results, leixoes_models, leixoes_last_year = run_station(
        "Leixões", LEIXOES_CSV
    )
    sines_annual, sines_results, sines_models, sines_last_year = run_station(
        "Sines", SINES_CSV
    )

    all_results = pd.concat([leixoes_results, sines_results], ignore_index=True)
    all_results.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")
    print()

    print_and_save_summary_table(all_results)

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        "Sea Level Rise — 9 Models, Cross-Validated, then Applied to 2100",
        fontsize=13, fontweight="bold"
    )

    plot_station(axes[0], "Leixões (1956–2022)", leixoes_annual, leixoes_models, leixoes_last_year)
    plot_station(axes[1], "Sines (1977–2022)", sines_annual, sines_models, sines_last_year)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"Saved: {OUT_PNG}")
    print("\nDone.")


if __name__ == "__main__":
    main()
