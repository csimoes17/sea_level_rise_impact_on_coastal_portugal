"""
13a2_sealevel_ml_comparison.py
===============================
Sea Level Rise — Multi-Model Comparison (Statistical Baselines + Machine Learning)
Leixões (1956-2022) and Sines (1977-2022)

WHY THIS SCRIPT EXISTS
-----------------------
13a_sealevel_regression.py fits a single linear OLS trend. This script responds to
external feedback asking for additional machine learning approaches (beyond the
K-means clustering already used elsewhere in the project), applied here because
sea level is the one place in the project built from raw observed data rather
than a deterministic formula (Pillars 1-3 are GIS/engineering calculations, so
fitting ML to their outputs would just relearn a known equation - circular,
not informative). Sea level is genuinely learned from data, which is why it is
the right target for this exercise.

MODEL SET (six models, two families)
-------------------------------------
Statistical baselines (classical regression, included for honest comparison):
  1. Linear OLS              - existing baseline, constant trend assumption
  2. Polynomial (quadratic)  - allows constant acceleration
  3. Piecewise / segmented   - allows a regime change at an estimated breakpoint

Machine learning models (the actual response to the feedback):
  4. Gaussian Process Regression (GPR) - Bayesian, kernel-based, gives calibrated
     uncertainty that widens with forecast horizon. The clearest, least disputed
     "machine learning" method in the set (Rasmussen & Williams, 2006).
  5. Support Vector Regression (SVR)   - margin/epsilon-insensitive loss, robust
     to noisy years; a genuinely different optimization objective from OLS,
     not just OLS in disguise. Kept LINEAR deliberately: a quadratic-feature SVR
     was tested and over-extrapolated just like plain polynomial regression -
     defeats the purpose of including a method that should behave safely far
     from the data.
  6. Random Forest Regression (bagged regression trees) - included as a
     DELIBERATE NEGATIVE EXAMPLE. Tree-based models cannot extrapolate beyond
     the training range by construction (prediction flattens at the boundary
     leaf value). Including it and showing exactly why it fails for a 2100
     projection is itself a useful, honest part of the comparison.

NOTE ON IMPLEMENTATION
-----------------------
This sandbox has no internet access, so scipy/scikit-learn could not be
installed. Every model below (including the Student-t statistics used for the
OLS confidence intervals) is implemented from first principles in numpy/pandas
only. The t-distribution CDF/PPF (via a regularized incomplete beta continued
fraction) was validated against standard t-tables to <0.0005 before use.

SELECTION CRITERIA
-------------------
  - In-sample R^2 / RMSE        (fit quality - NOT sufficient alone, can overfit)
  - AIC / BIC                   (parametric models only: linear, quadratic, piecewise)
  - Forward-chaining CV RMSE    (expanding-window, time-respecting - the primary
                                  fair comparison across ALL six models; ordinary
                                  k-fold would leak future years into the past)
  - Residual autocorrelation    (Durbin-Watson, parametric models)
  - 2100 extrapolation + uncertainty where available

Outputs:
  sealevel_ml_comparison_summary.csv   - all models x both stations, metrics + 2100 forecast
  sealevel_ml_comparison_chart.png     - observed + all model fits/extrapolations to 2100

Usage: python 13a2_sealevel_ml_comparison.py
"""

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

np.random.seed(42)  # reproducibility for RF bootstrap / SVR init

PROJECT_DIR = Path(__file__).parent
LEIXOES_CSV = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV   = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV     = PROJECT_DIR / "sealevel_ml_comparison_summary.csv"
OUT_PNG     = PROJECT_DIR / "sealevel_ml_comparison_chart.png"

FORECAST_YEAR = 2100


# =============================================================================
# STATISTICS HELPERS (replacing scipy.stats - validated against t-tables)
# =============================================================================
def _betacf(a, b, x, maxit=300, eps=3e-16):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, maxit + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def _betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                   + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    p = 0.5 * _betainc(df / 2.0, 0.5, x)
    return 1.0 - p if t > 0 else p


def t_ppf(p, df, lo=-50.0, hi=50.0, tol=1e-10):
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def durbin_watson(resid):
    diff = np.diff(resid)
    return np.sum(diff ** 2) / np.sum(resid ** 2)


# =============================================================================
# DATA LOADING
# =============================================================================
def compute_annual_means(csv_path, flag_threshold=1):
    df = pd.read_csv(csv_path)
    df = df[df["flag"] <= flag_threshold].copy()
    df["year"] = df["year_decimal"].astype(int)
    monthly_counts = df.groupby("year")["sea_level_m"].count()
    valid_years = monthly_counts[monthly_counts >= 6].index
    annual = (df[df["year"].isin(valid_years)]
              .groupby("year")["sea_level_m"].mean().reset_index())
    return annual


# =============================================================================
# MODEL 1: LINEAR OLS
# =============================================================================
def fit_linear(x, y):
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    resid = y - pred
    sse = np.sum(resid ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - sse / sst
    k = 2  # params: slope, intercept
    se_slope = np.sqrt(sse / (n - 2)) / np.sqrt(np.sum((x - x.mean()) ** 2))
    t_stat = slope / se_slope
    p_value = 2 * (1 - t_cdf(abs(t_stat), n - 2))
    t_crit = t_ppf(0.975, n - 2)
    aic = n * np.log(sse / n) + 2 * k
    bic = n * np.log(sse / n) + k * np.log(n)
    return dict(
        name="Linear OLS", family="Statistical baseline",
        slope_mm_yr=slope * 1000,
        ci_low_mm_yr=(slope - t_crit * se_slope) * 1000,
        ci_high_mm_yr=(slope + t_crit * se_slope) * 1000,
        r2=r2, p_value=p_value, aic=aic, bic=bic, k=k,
        dw=durbin_watson(resid),
        predict=lambda xq: slope * xq + intercept,
        predict_std=None,
    )


# =============================================================================
# MODEL 2: POLYNOMIAL (QUADRATIC)
# =============================================================================
def fit_poly2(x, y):
    n = len(x)
    x_mean, x_std = x.mean(), x.std()
    xt = (x - x_mean) / x_std
    coef = np.polyfit(xt, y, 2)  # [c2, c1, c0] in standardized x
    pred = np.polyval(coef, xt)
    resid = y - pred
    sse = np.sum(resid ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - sse / sst
    k = 3
    aic = n * np.log(sse / n) + 2 * k
    bic = n * np.log(sse / n) + k * np.log(n)
    # instantaneous slope at final year (curvature -> rate is not constant)
    c2, c1, c0 = coef
    slope_at_end_mm_yr = (2 * c2 * (x.max() - x_mean) / x_std + c1) / x_std * 1000

    def predict(xq):
        xqt = (xq - x_mean) / x_std
        return np.polyval(coef, xqt)

    return dict(
        name="Polynomial (quadratic)", family="Statistical baseline",
        r2=r2, aic=aic, bic=bic, k=k, dw=durbin_watson(resid),
        slope_at_end_mm_yr=slope_at_end_mm_yr,
        predict=predict, predict_std=None,
    )


# =============================================================================
# MODEL 3: PIECEWISE / SEGMENTED (1 breakpoint, continuous)
# =============================================================================
def fit_piecewise(x, y, min_seg=8):
    n = len(x)
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    candidates = xs[min_seg: n - min_seg]
    best = None
    for bp in candidates:
        hinge = np.maximum(0, xs - bp)
        X = np.column_stack([np.ones(n), xs, hinge])
        coef, _, _, _ = np.linalg.lstsq(X, ys, rcond=None)
        pred = X @ coef
        sse = np.sum((ys - pred) ** 2)
        if best is None or sse < best[0]:
            best = (sse, bp, coef)
    sse, bp, coef = best
    a, b1, delta = coef
    b2 = b1 + delta
    sst = np.sum((ys - ys.mean()) ** 2)
    r2 = 1 - sse / sst
    k = 4
    aic = n * np.log(sse / n) + 2 * k
    bic = n * np.log(sse / n) + k * np.log(n)
    pred_all = a + b1 * xs + delta * np.maximum(0, xs - bp)
    resid = ys - pred_all

    def predict(xq):
        return a + b1 * xq + delta * np.maximum(0, xq - bp)

    return dict(
        name="Piecewise (segmented)", family="Statistical baseline",
        breakpoint_year=bp, slope_before_mm_yr=b1 * 1000, slope_after_mm_yr=b2 * 1000,
        r2=r2, aic=aic, bic=bic, k=k, dw=durbin_watson(resid),
        predict=predict, predict_std=None,
    )


# =============================================================================
# MODEL 4: GAUSSIAN PROCESS REGRESSION (linear + RBF kernel)
# =============================================================================
def fit_gpr(x, y):
    n = len(x)
    x_mean, x_std = x.mean(), x.std()
    xt = (x - x_mean) / x_std
    y_mean = y.mean()
    yt = y - y_mean

    length_scales = [3, 5, 8, 12, 20, 35]
    sig_f2s = [0.0005, 0.002, 0.008, 0.03]
    sig_l2s = [0.001, 0.005, 0.02, 0.08]
    noise_vars = [1e-5, 1e-4, 1e-3]

    best = None
    for l in length_scales:
        for sf2 in sig_f2s:
            for sl2 in sig_l2s:
                for nv in noise_vars:
                    d2 = (xt[:, None] - xt[None, :]) ** 2
                    K = sl2 * np.outer(xt, xt) + sf2 * np.exp(-d2 / (2 * l * l)) + nv * np.eye(n)
                    try:
                        L = np.linalg.cholesky(K)
                    except np.linalg.LinAlgError:
                        continue
                    alpha = np.linalg.solve(L.T, np.linalg.solve(L, yt))
                    log_marg = -0.5 * yt @ alpha - np.sum(np.log(np.diag(L))) - n / 2 * np.log(2 * np.pi)
                    if best is None or log_marg > best[0]:
                        best = (log_marg, l, sf2, sl2, nv, L, alpha)
    log_marg, l, sf2, sl2, nv, L, alpha = best

    def predict_with_std(xq):
        xqt = (xq - x_mean) / x_std
        d2s = (xqt[:, None] - xt[None, :]) ** 2
        Ks = sl2 * np.outer(xqt, xt) + sf2 * np.exp(-d2s / (2 * l * l))
        mean = Ks @ alpha + y_mean
        v = np.linalg.solve(L, Ks.T)
        kss = sl2 * xqt * xqt + sf2 + nv
        var = np.maximum(kss - np.sum(v ** 2, axis=0), 1e-12)
        return mean, np.sqrt(var)

    pred_train, _ = predict_with_std(x)
    sse = np.sum((y - pred_train) ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - sse / sst

    return dict(
        name="Gaussian Process Regression", family="Machine learning",
        r2=r2, hyperparams=dict(length_scale=l, sig_f2=sf2, sig_l2=sl2, noise_var=nv),
        log_marginal_likelihood=log_marg,
        predict=lambda xq: predict_with_std(xq)[0],
        predict_std=lambda xq: predict_with_std(xq)[1],
    )


# =============================================================================
# MODEL 5: SUPPORT VECTOR REGRESSION (linear kernel, epsilon-insensitive loss)
# =============================================================================
def fit_svr(x, y, C=2.0, eps=0.01, lr0=0.3, n_iter=8000):
    """
    Linear-kernel SVR, epsilon-insensitive loss, fit via subgradient descent.
    NOTE: a fixed step size oscillates indefinitely on this non-smooth loss
    (verified empirically - the final iterate is sensitive to exactly which
    iteration you stop at, which is not an acceptable property for a result
    feeding a dissertation). Fixed by using a decaying step size (lr0/sqrt(it))
    plus Polyak averaging over the second half of training, which is the
    standard fix for subgradient-method convergence and gives a stable,
    reproducible solution independent of n_iter once n_iter is large enough.
    """
    n = len(x)
    x_mean, x_std = x.mean(), x.std()
    xt = (x - x_mean) / x_std
    y_mean = y.mean()
    yt = y - y_mean
    w, b = 0.0, 0.0
    w_sum, b_sum, cnt = 0.0, 0.0, 0
    for it in range(n_iter):
        lr = lr0 / np.sqrt(it + 1)
        pred = w * xt + b
        err = pred - yt
        mask = np.abs(err) > eps
        if mask.any():
            grad_w = w / n + (C / n) * np.sum(xt[mask] * np.sign(err[mask]))
            grad_b = (C / n) * np.sum(np.sign(err[mask]))
        else:
            grad_w, grad_b = w / n, 0.0
        w -= lr * grad_w
        b -= lr * grad_b
        if it >= n_iter // 2:
            w_sum += w
            b_sum += b
            cnt += 1
    w, b = w_sum / cnt, b_sum / cnt

    def predict(xq):
        xqt = (xq - x_mean) / x_std
        return w * xqt + b + y_mean

    pred_train = predict(x)
    sse = np.sum((y - pred_train) ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - sse / sst
    slope_mm_yr = (w / x_std) * 1000

    return dict(
        name="Support Vector Regression (linear)", family="Machine learning",
        r2=r2, slope_mm_yr=slope_mm_yr,
        predict=predict, predict_std=None,
    )


# =============================================================================
# MODEL 6: RANDOM FOREST (bagged regression trees) -- DELIBERATE NEGATIVE EXAMPLE
# =============================================================================
class _RegTree:
    def __init__(self, max_depth=4, min_leaf=4):
        self.max_depth, self.min_leaf = max_depth, min_leaf

    def fit(self, x, y, depth=0):
        if depth >= self.max_depth or len(x) < 2 * self.min_leaf:
            self.is_leaf, self.value = True, y.mean()
            return self
        order = np.argsort(x)
        xs, ys = x[order], y[order]
        n = len(xs)
        best = None
        for i in range(self.min_leaf, n - self.min_leaf):
            if xs[i] == xs[i - 1]:
                continue
            left_y, right_y = ys[:i], ys[i:]
            sse = np.sum((left_y - left_y.mean()) ** 2) + np.sum((right_y - right_y.mean()) ** 2)
            if best is None or sse < best[0]:
                best = (sse, (xs[i - 1] + xs[i]) / 2)
        if best is None:
            self.is_leaf, self.value = True, y.mean()
            return self
        self.is_leaf, self.split = False, best[1]
        self.left = _RegTree(self.max_depth, self.min_leaf).fit(x[x <= self.split], y[x <= self.split], depth + 1)
        self.right = _RegTree(self.max_depth, self.min_leaf).fit(x[x > self.split], y[x > self.split], depth + 1)
        return self

    def predict_one(self, v):
        if self.is_leaf:
            return self.value
        return self.left.predict_one(v) if v <= self.split else self.right.predict_one(v)

    def predict(self, x):
        return np.array([self.predict_one(v) for v in x])


def fit_random_forest(x, y, n_trees=50, max_depth=4, min_leaf=4, seed=42):
    n = len(x)
    rng = np.random.RandomState(seed)
    trees = []
    for _ in range(n_trees):
        idx = rng.randint(0, n, n)
        trees.append(_RegTree(max_depth, min_leaf).fit(x[idx], y[idx]))

    def predict(xq):
        return np.mean([t.predict(xq) for t in trees], axis=0)

    pred_train = predict(x)
    sse = np.sum((y - pred_train) ** 2)
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - sse / sst

    return dict(
        name="Random Forest (bagged trees)", family="Machine learning (negative example)",
        r2=r2, predict=predict, predict_std=None,
    )


# =============================================================================
# FORWARD-CHAINING (EXPANDING WINDOW) CROSS-VALIDATION
# =============================================================================
def forward_chaining_cv(x, y, fit_fn, min_train=20, step=1):
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    n = len(xs)
    errors = []
    for end in range(min_train, n, step):
        x_train, y_train = xs[:end], ys[:end]
        x_test, y_test = xs[end:end + 1], ys[end:end + 1]
        if len(x_test) == 0:
            continue
        try:
            m = fit_fn(x_train, y_train)
            pred = m["predict"](x_test)
            errors.append((pred[0] - y_test[0]) ** 2)
        except Exception:
            continue
    if not errors:
        return np.nan
    return np.sqrt(np.mean(errors))


# =============================================================================
# MAIN
# =============================================================================
def run_station(name, annual_df):
    x = annual_df["year"].values.astype(float)
    y = annual_df["sea_level_m"].values.astype(float)
    n = len(x)
    print(f"\n{'=' * 78}\n{name}  (n={n} years, {int(x.min())}-{int(x.max())})\n{'=' * 78}")

    models = {
        "linear":    fit_linear(x, y),
        "poly2":     fit_poly2(x, y),
        "piecewise": fit_piecewise(x, y),
        "gpr":       fit_gpr(x, y),
        "svr":       fit_svr(x, y),
        "rf":        fit_random_forest(x, y),
    }

    print("\n-- In-sample fit --")
    for key, m in models.items():
        extra = f"  AIC={m['aic']:.1f} BIC={m['bic']:.1f}" if "aic" in m else ""
        print(f"  {m['name']:<32s} R2={m['r2']:.4f}{extra}")

    print("\n-- Forward-chaining CV RMSE (time-respecting, fair across all 6) --")
    cv_fns = {
        "linear":    lambda xt, yt: fit_linear(xt, yt),
        "poly2":     lambda xt, yt: fit_poly2(xt, yt),
        "piecewise": lambda xt, yt: fit_piecewise(xt, yt, min_seg=max(4, len(xt) // 6)),
        "gpr":       lambda xt, yt: fit_gpr(xt, yt),
        "svr":       lambda xt, yt: fit_svr(xt, yt),
        "rf":        lambda xt, yt: fit_random_forest(xt, yt, n_trees=20),
    }
    cv_rmse = {}
    for key, fn in cv_fns.items():
        rmse = forward_chaining_cv(x, y, fn, min_train=max(15, n // 3))
        cv_rmse[key] = rmse
        print(f"  {models[key]['name']:<32s} CV-RMSE = {rmse*1000:.2f} mm")

    print(f"\n-- Extrapolation to {FORECAST_YEAR} --")
    x2100 = np.array([float(FORECAST_YEAR)])
    forecasts = {}
    for key, m in models.items():
        pred = m["predict"](x2100)[0]
        std = m["predict_std"](x2100)[0] if m.get("predict_std") else None
        change_mm = (pred - y[-1]) * 1000
        forecasts[key] = (pred, std, change_mm)
        unc = f"  +/- {std*1000:.0f} mm (1 std)" if std is not None else "  (no native uncertainty)"
        flat_note = "  <-- flat (cannot extrapolate)" if key == "rf" else ""
        print(f"  {m['name']:<32s} {pred:.3f} m  ({change_mm:+.0f} mm vs last observed){unc}{flat_note}")

    rows = []
    for key, m in models.items():
        rows.append({
            "station": name, "model": m["name"], "family": m["family"],
            "r2_train": round(m["r2"], 4),
            "aic": round(m["aic"], 1) if "aic" in m else None,
            "bic": round(m["bic"], 1) if "bic" in m else None,
            "cv_rmse_mm": round(cv_rmse[key] * 1000, 2) if not np.isnan(cv_rmse[key]) else None,
            "forecast_2100_m": round(forecasts[key][0], 3),
            "forecast_2100_std_mm": round(forecasts[key][1] * 1000, 1) if forecasts[key][1] is not None else None,
            "change_vs_last_obs_mm": round(forecasts[key][2], 1),
        })
    return models, rows, cv_rmse, forecasts


def main():
    print("Loading tide gauge data...")
    lx_ann = compute_annual_means(LEIXOES_CSV)
    sn_ann = compute_annual_means(SINES_CSV)

    lx_models, lx_rows, lx_cv, lx_fc = run_station("Leixoes", lx_ann)
    sn_models, sn_rows, sn_cv, sn_fc = run_station("Sines", sn_ann)

    all_rows = lx_rows + sn_rows
    df_out = pd.DataFrame(all_rows)
    df_out.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")

    # ── Plot ──────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(17, 7.5))
    fig.suptitle("Sea Level Rise — Statistical Baselines vs Machine Learning Model Comparison",
                 fontsize=13, fontweight="bold")

    colors = {
        "linear": "#777777", "poly2": "#9966CC", "piecewise": "#3F8F3F",
        "gpr": "#D32F2F", "svr": "#1976D2", "rf": "#FF8F00",
    }
    styles = {
        "linear": "--", "poly2": "-.", "piecewise": ":",
        "gpr": "-", "svr": "-", "rf": "-",
    }

    for ax, ann_df, models, station_label in [
        (axes[0], lx_ann, lx_models, "Leixoes (1956-2022)"),
        (axes[1], sn_ann, sn_models, "Sines (1977-2022)"),
    ]:
        x = ann_df["year"].values.astype(float)
        y = ann_df["sea_level_m"].values.astype(float)
        ax.scatter(x, y, s=12, color="#444444", alpha=0.6, zorder=5, label="Observed (annual mean)")

        x_line = np.linspace(x.min(), FORECAST_YEAR, 400)
        for key, m in models.items():
            pred = m["predict"](x_line)
            ax.plot(x_line, pred, color=colors[key], lw=1.8, linestyle=styles[key],
                     label=f"{m['name']}", zorder=4 if key != "rf" else 3, alpha=0.95)
            if m.get("predict_std"):
                std = m["predict_std"](x_line)
                ax.fill_between(x_line, pred - std, pred + std, color=colors[key], alpha=0.12, zorder=1)

        ax.axvline(x.max(), color="#aaaaaa", lw=0.9, linestyle=":", alpha=0.8)
        ax.set_title(station_label, fontsize=11, fontweight="bold")
        ax.set_xlabel("Year", fontsize=10)
        ax.set_ylabel("Sea level (m, tide-gauge datum)", fontsize=10)
        ax.set_xlim(x.min() - 3, FORECAST_YEAR + 3)
        ax.legend(fontsize=7.3, loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.25)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {OUT_PNG}")
    print("\nDone.")


if __name__ == "__main__":
    main()
