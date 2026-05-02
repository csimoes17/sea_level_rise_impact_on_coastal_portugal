"""
13a_sealevel_regression.py
==========================
Sea Level Trend Analysis — Linear Regression on PSMSL Tide Gauge Data
Leixões (1956–2022) and Sines (1977–2022)

What this script does (plain language):
  1. Loads monthly sea level observations from two Portuguese tide gauges
  2. Computes annual means to remove the seasonal cycle
  3. Fits a linear regression: sea_level = slope × year + intercept
  4. Extracts the trend rate (mm/year), R², p-value, and 95% confidence interval
  5. Does this twice: full record AND from 1993 (satellite altimetry era)
  6. Plots observed data + trend line + IPCC AR6 scenario projections on the same chart

Why this matters for the dissertation:
  The regression anchors the IPCC AR6 projections in observed Portuguese data.
  If the observed trend at Leixões/Sines is consistent with IPCC SSP2-4.5 or SSP5-8.5,
  it provides a consistency check for the scenario choice. It also demonstrates statistical methodology
  (OLS regression, hypothesis testing, confidence intervals).

Outputs:
  sealevel_regression_summary.csv    — trend rates, R², p-values, 95% CI
  sealevel_regression_chart.png      — observed data + trends + IPCC AR6 overlay

Usage: python 13a_sealevel_regression.py
"""

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
LEIXOES_CSV = PROJECT_DIR / "sea_level_leixoes_monthly_cleaned.csv"
SINES_CSV   = PROJECT_DIR / "sea_level_sines_monthly_cleaned.csv"
OUT_CSV     = PROJECT_DIR / "sealevel_regression_summary.csv"
OUT_PNG     = PROJECT_DIR / "sealevel_regression_chart.png"

# ─── IPCC AR6 SSP PROJECTIONS ─────────────────────────────────────────────────
# Values are metres of SLR relative to 2020 baseline (Fox-Kemper et al., 2021)
SLR_ANCHORS = {
    "SSP1-2.6": {2020: 0.00, 2030: 0.07, 2050: 0.20, 2075: 0.30, 2100: 0.40},
    "SSP2-4.5": {2020: 0.00, 2030: 0.10, 2050: 0.30, 2075: 0.45, 2100: 0.60},
    "SSP5-8.5": {2020: 0.00, 2030: 0.13, 2050: 0.40, 2075: 0.70, 2100: 1.00},
}
SCENARIO_COLORS  = {"SSP1-2.6": "#2196F3", "SSP2-4.5": "#FF9800", "SSP5-8.5": "#F44336"}
SCENARIO_STYLES  = {"SSP1-2.6": "--",      "SSP2-4.5": "-.",       "SSP5-8.5": ":"}


# ─── HELPER: annual means ─────────────────────────────────────────────────────
def compute_annual_means(csv_path, flag_threshold=1):
    """
    Load monthly tide gauge CSV, filter to quality-flagged records,
    and return annual mean sea level (only years with ≥6 months of data).

    Flag convention (PSMSL): 0 = good, 1 = interpolated, ≥2 = suspect/missing.
    We keep flag ≤ 1 (good + minor interpolation).
    """
    df = pd.read_csv(csv_path)
    df = df[df["flag"] <= flag_threshold].copy()
    df["year"] = df["year_decimal"].astype(int)

    # Count valid months per year
    monthly_counts = df.groupby("year")["sea_level_m"].count()
    valid_years = monthly_counts[monthly_counts >= 6].index

    # Annual mean
    annual = (df[df["year"].isin(valid_years)]
              .groupby("year")["sea_level_m"]
              .mean()
              .reset_index())
    return annual


# ─── HELPER: OLS regression ───────────────────────────────────────────────────
def ols_regression(annual_df, station_name, start_year=None):
    """
    Ordinary Least Squares linear regression of sea level on year.

    Returns a dict with:
      slope_mm_yr   — trend rate in mm/year (key result)
      ci_low/high   — 95% confidence interval on slope (mm/year)
      r_squared     — coefficient of determination (0–1)
      p_value       — probability of observing this trend by chance alone
      n_years       — number of annual data points used
    """
    df = annual_df.copy()
    if start_year:
        df = df[df["year"] >= start_year]

    x = df["year"].values.astype(float)
    y = df["sea_level_m"].values

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # 95% CI: t-distribution with n-2 degrees of freedom
    n      = len(x)
    t_crit = stats.t.ppf(0.975, df=n - 2)

    return {
        "station":       station_name,
        "period":        f"{int(x.min())}–{int(x.max())}",
        "n_years":       n,
        "slope_mm_yr":   round(slope * 1000, 3),          # m/yr → mm/yr
        "ci_low_mm_yr":  round((slope - t_crit * std_err) * 1000, 3),
        "ci_high_mm_yr": round((slope + t_crit * std_err) * 1000, 3),
        "r_squared":     round(r_value ** 2, 4),
        "p_value":       round(p_value, 8),
        # Keep internal values for plotting
        "_slope":        slope,
        "_intercept":    intercept,
        "_x_min":        x.min(),
        "_x_max":        x.max(),
    }


# ─── HELPER: interpolate IPCC SLR scenario ────────────────────────────────────
def ipcc_slr(scenario, year):
    """Linear interpolation of IPCC AR6 SLR between anchor years."""
    anchors = SLR_ANCHORS[scenario]
    years   = sorted(anchors.keys())
    values  = [anchors[y] for y in years]
    return float(np.interp(year, years, values))


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("Loading tide gauge data...")
    lx_ann = compute_annual_means(LEIXOES_CSV)
    sn_ann = compute_annual_means(SINES_CSV)
    print(f"  Leixões: {len(lx_ann)} annual data points "
          f"({int(lx_ann.year.min())}–{int(lx_ann.year.max())})")
    print(f"  Sines:   {len(sn_ann)} annual data points "
          f"({int(sn_ann.year.min())}–{int(sn_ann.year.max())})")

    # ── Run regressions ───────────────────────────────────────────────────────
    lx_full = ols_regression(lx_ann, "Leixões — full record")
    lx_1993 = ols_regression(lx_ann, "Leixões — 1993–2022", start_year=1993)
    sn_full = ols_regression(sn_ann, "Sines — full record")
    sn_1993 = ols_regression(sn_ann, "Sines — 1993–2022",   start_year=1993)
    all_regs = [lx_full, lx_1993, sn_full, sn_1993]

    # ── Print summary table ───────────────────────────────────────────────────
    print("\n" + "=" * 75)
    print("SEA LEVEL TREND ANALYSIS — RESULTS SUMMARY")
    print("=" * 75)
    cols = ["station", "period", "n_years", "slope_mm_yr",
            "ci_low_mm_yr", "ci_high_mm_yr", "r_squared", "p_value"]
    df_out = pd.DataFrame(all_regs)[cols]
    print(df_out.to_string(index=False))
    print()
    print("Interpretation guide:")
    print("  slope_mm_yr  — sea level rise rate in mm per year")
    print("  ci_low/high  — 95% confidence interval: true trend is within this range")
    print("  r_squared    — proportion of variance explained by the linear trend (0–1)")
    print("  p_value      — probability of this trend occurring by chance; <0.05 = significant")
    print()

    # Compare to IPCC AR6 expected rate near 2020
    print("IPCC AR6 implied rates near 2020 (linear approximation 2020–2030):")
    for scen in ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]:
        rate = (ipcc_slr(scen, 2030) - ipcc_slr(scen, 2020)) / 10 * 1000
        print(f"  {scen}: ~{rate:.1f} mm/yr")
    print()

    # Save CSV
    df_out.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        "Sea Level Trend Analysis — Portuguese Tide Gauges vs IPCC AR6 Projections",
        fontsize=13, fontweight="bold"
    )

    for ax, ann_df, reg_full, reg_1993, station_label in [
        (axes[0], lx_ann, lx_full, lx_1993, "Leixões (Norte — 1956–2022)"),
        (axes[1], sn_ann, sn_full, sn_1993, "Sines (Alentejo Litoral — 1977–2022)"),
    ]:
        # Convert to anomaly: sea level change relative to 2020
        # (so IPCC projections and observations share the same baseline)
        pred_at_2020 = reg_full["_intercept"] + reg_full["_slope"] * 2020
        anomaly = ann_df["sea_level_m"] - pred_at_2020

        # ── Observed annual means ──
        ax.scatter(ann_df["year"], anomaly,
                   s=10, color="#888888", alpha=0.55, zorder=2,
                   label="Observed (annual mean)")

        # ── Full-record regression trend line ──
        x_trend = np.array([reg_full["_x_min"], reg_full["_x_max"]])
        y_trend = (reg_full["_slope"] * x_trend + reg_full["_intercept"]) - pred_at_2020
        ax.plot(x_trend, y_trend, color="#222222", lw=2.2, zorder=4,
                label=(f"OLS trend (full): {reg_full['slope_mm_yr']:+.2f} mm/yr  "
                       f"[{reg_full['ci_low_mm_yr']:+.2f}, {reg_full['ci_high_mm_yr']:+.2f}]  "
                       f"R²={reg_full['r_squared']:.3f}"))

        # ── 1993–2022 regression trend line (dashed) ──
        x_sat = np.array([1993, reg_1993["_x_max"]])
        y_sat = (reg_1993["_slope"] * x_sat + reg_1993["_intercept"]) - pred_at_2020
        ax.plot(x_sat, y_sat, color="#222222", lw=1.8, linestyle="--", zorder=4,
                label=(f"OLS trend (1993–): {reg_1993['slope_mm_yr']:+.2f} mm/yr  "
                       f"R²={reg_1993['r_squared']:.3f}"))

        # ── IPCC AR6 scenarios (2020 → 2100) ──
        x_ipcc = np.linspace(2020, 2100, 200)
        for scen in ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]:
            y_ipcc = np.array([ipcc_slr(scen, yr) for yr in x_ipcc])
            ax.plot(x_ipcc, y_ipcc,
                    color=SCENARIO_COLORS[scen],
                    lw=2, linestyle=SCENARIO_STYLES[scen],
                    label=f"IPCC AR6 {scen} (2100: +{SLR_ANCHORS[scen][2100]:.2f} m)",
                    zorder=3)

        # ── Vertical marker at 2020 ──
        ax.axvline(2020, color="#999999", lw=1, linestyle=":", alpha=0.8)
        ax.axhline(0, color="#999999", lw=0.8, linestyle="-", alpha=0.5)
        ax.text(2021, -0.01, "2020\nbaseline", fontsize=7.5, color="#777777", va="top")

        ax.set_title(station_label, fontsize=11, fontweight="bold")
        ax.set_xlabel("Year", fontsize=10)
        ax.set_ylabel("Sea Level Change relative to 2020 (m)", fontsize=10)
        ax.set_xlim(ann_df["year"].min() - 3, 2103)
        ax.legend(fontsize=7.5, loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.25)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f m"))

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.show()   # displays chart in VS Code interactive window
    plt.close()
    print(f"Saved: {OUT_PNG}")
    print("\nDone.")


if __name__ == "__main__":
    main()
