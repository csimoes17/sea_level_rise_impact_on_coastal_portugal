"""
13b_coastal_risk_clustering.py
==============================
K-Means Clustering of Coastal NUTS3 Regions by Flood Risk Profile
Portugal — SSP5-8.5, Year 2100 (worst-case end-of-century scenario)

What this script does (plain language):
  1. Takes the NUTS3-level flood exposure data (Pillar 1) and infrastructure
     data (Pillar 2) at the worst-case scenario (SSP5-8.5, 2100)
  2. Builds a risk profile for each coastal NUTS3 region using 4 features:
       - Physical flood extent (flooded pixels)
       - Economic exposure (GDP at risk, €)
       - Relative exposure (fraction of NUTS3 area flooded)
       - Infrastructure at risk (building replacement cost, €)
  3. Normalises all features to the same scale (StandardScaler)
  4. Uses the Elbow Method and Silhouette Score to choose the optimal
     number of clusters (k)
  5. Assigns each NUTS3 to a risk tier: Priority / High / Moderate / Low
  6. Produces charts and a CSV ready to connect to Tableau as a new map layer

Why this is Machine Learning:
  K-Means is an unsupervised learning algorithm. It finds natural groupings
  in the data without being told which group each region belongs to.
  The algorithm minimises within-cluster variance — regions in the same
  cluster are more similar to each other than to regions in other clusters.
  This is a standard technique in spatial risk analysis and policy prioritisation.

Outputs:
  coastal_risk_clusters.csv         — NUTS3 regions with cluster assignments (raw CSV)
  coastal_risk_clusters.xlsx        — same data as Excel (use this in Tableau — avoids
                                       CSV separator detection issues on macOS)
  coastal_risk_clustering_chart.png — elbow curve, silhouette, scatter, profile

Usage: python 13b_coastal_risk_clustering.py
Requires: scikit-learn  →  pip install scikit-learn --break-system-packages
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_DIR  = Path(__file__).parent
PILLAR1_CSV  = PROJECT_DIR / "gdp_at_risk_pillar1.csv"
PILLAR2_CSV  = PROJECT_DIR / "infrastructure_at_risk_pillar2_detail.csv"
OUT_CSV      = PROJECT_DIR / "coastal_risk_clusters.csv"
OUT_XLSX     = PROJECT_DIR / "coastal_risk_clusters.xlsx"
OUT_PNG      = PROJECT_DIR / "coastal_risk_clustering_chart.png"

# ─── PARAMETERS ───────────────────────────────────────────────────────────────
CLUSTER_SCENARIO = "ssp585"    # SSP5-8.5: worst-case, most discriminating
CLUSTER_YEAR     = 2100        # End of century
K_RANGE          = range(2, 8) # Test k = 2 to 7 clusters
RANDOM_STATE     = 42          # Reproducibility seed
MIN_FLOOD_PX     = 1           # Exclude NUTS3 with zero flood exposure

# Risk tier labels (assigned after clustering, ordered by combined score)
# These are assigned programmatically based on centroid values — see below
TIER_NAMES = {0: "Low Risk", 1: "Moderate Risk", 2: "High Risk", 3: "Priority Risk"}
TIER_COLORS = {
    "Priority Risk":  "#C62828",
    "High Risk":      "#EF6C00",
    "Moderate Risk":  "#F9A825",
    "Low Risk":       "#2E7D32",
}


# ─── STEP 1: BUILD RISK FEATURE TABLE ─────────────────────────────────────────
def build_feature_table():
    """
    Join Pillar 1 (flood + GDP) and Pillar 2 (infrastructure) data
    at NUTS3 level for the target scenario and year.
    Returns a DataFrame with one row per NUTS3 region.
    """
    print("Loading Pillar 1 data (flood extent + GDP)...")
    p1 = pd.read_csv(PILLAR1_CSV)
    p1 = p1[(p1["scenario"] == CLUSTER_SCENARIO) &
            (p1["year"]     == CLUSTER_YEAR)].copy()

    print("Loading Pillar 2 data (infrastructure)...")
    p2 = pd.read_csv(PILLAR2_CSV)
    p2 = p2[(p2["scenario"] == CLUSTER_SCENARIO) &
            (p2["year"]     == CLUSTER_YEAR)].copy()
    # Rename to avoid collision
    p2 = p2.rename(columns={"value_eur": "infra_value_eur"})[["nuts3", "infra_value_eur"]]

    # Merge on NUTS3
    df = p1.merge(p2, on="nuts3", how="left")
    df["infra_value_eur"] = df["infra_value_eur"].fillna(0)

    # Filter: keep only NUTS3 with some flood exposure
    df = df[df["flooded_pixels"] >= MIN_FLOOD_PX].copy()

    # Derived features
    df["gdp_at_risk_bn"]    = df["gdp_at_risk_eur"]    / 1e9
    df["infra_value_bn"]    = df["infra_value_eur"]    / 1e9
    df["gdp_total_bn"]      = df["gdp_2022_eur"]       / 1e9

    print(f"\n  NUTS3 regions with flood exposure at SSP5-8.5/2100: {len(df)}")
    print("  Regions included:")
    for r in sorted(df["nuts3"].tolist()):
        print(f"    - {r}")

    return df


# ─── STEP 2: PREPARE FEATURES FOR CLUSTERING ──────────────────────────────────
def prepare_features(df):
    """
    Select, log-transform, and normalise the 4 clustering features.

    WHY LOG TRANSFORMATION?
    The raw feature distributions are extremely right-skewed: Grande Lisboa's
    GDP at risk (€4.5bn) is 15× larger than the next region (€0.3bn). In raw
    space, K-Means would simply isolate Lisboa as its own cluster and group
    everything else together — statistically correct but analytically useless.

    Log1p (log(x + 1)) compresses the scale so clustering operates on
    *proportional differences* rather than absolute magnitudes. This is
    standard practice in spatial risk analysis with skewed distributions.
    The result: meaningful risk tiers that reflect genuine differences across
    all 12 regions, not just "Lisboa vs the rest".

    StandardScaler: after log-transform, rescales each feature to mean=0,
    std=1, so no single feature dominates due to remaining scale differences.
    """
    feature_cols = [
        "flooded_pixels",      # Physical flood extent
        "gdp_at_risk_bn",      # Economic flow at risk (GDP)
        "fraction_flooded",    # Relative exposure (% of region flooded)
        "infra_value_bn",      # Infrastructure replacement cost
    ]

    X_raw = df[feature_cols].values

    # Log1p transform to handle skewed distributions
    X_log = np.log1p(X_raw)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_log)

    print(f"\nFeatures used for clustering (log1p-transformed, then standardised):")
    for i, col in enumerate(feature_cols):
        print(f"  {col}: raw mean={X_raw[:, i].mean():.4f}, "
              f"log mean={X_log[:, i].mean():.4f}, std={X_log[:, i].std():.4f}")

    return X_scaled, feature_cols, scaler


# ─── STEP 3: CHOOSE OPTIMAL k (ELBOW + SILHOUETTE) ────────────────────────────
def choose_k(X_scaled):
    """
    Elbow method: plot within-cluster sum of squares (inertia) vs k.
    The 'elbow' — where adding more clusters gives diminishing returns — is optimal k.

    Silhouette score: measures how well-separated clusters are (−1 to +1).
    Higher = better separation. Used to confirm the elbow choice.
    """
    inertias    = []
    silhouettes = []

    for k in K_RANGE:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        labels = km.fit_predict(X_scaled)
        inertias.append(km.inertia_)
        if k > 1:
            silhouettes.append(silhouette_score(X_scaled, labels))
        else:
            silhouettes.append(np.nan)

    return list(K_RANGE), inertias, silhouettes


# ─── STEP 4: FIT FINAL K-MEANS MODEL ──────────────────────────────────────────
def fit_kmeans(X_scaled, k):
    """
    Fit K-Means with the chosen k.
    n_init=50: run 50 times with different random seeds, keep the best result.
    This avoids local optima (a known limitation of K-Means).
    """
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=50)
    labels = km.fit_predict(X_scaled)
    score  = silhouette_score(X_scaled, labels)
    print(f"\nFinal model: k={k}, silhouette score={score:.4f}")
    return km, labels, score


# ─── STEP 5: LABEL CLUSTERS BY RISK LEVEL ─────────────────────────────────────
def label_clusters(df, labels, km, feature_cols, scaler, k):
    """
    Assign human-readable risk tier labels to clusters.
    Strategy: rank clusters by their mean 'combined risk score'
    (average of normalised GDP at risk + normalised flood pixels).
    Highest score → "Priority Risk", lowest → "Low Risk".
    """
    df = df.copy()
    df["cluster_id"] = labels

    # Compute mean raw values per cluster (for interpretability)
    cluster_means = df.groupby("cluster_id")[
        ["flooded_pixels", "gdp_at_risk_bn", "fraction_flooded", "infra_value_bn"]
    ].mean()

    # Rank clusters by combined economic exposure + flood extent
    cluster_means["combined_score"] = (
        cluster_means["gdp_at_risk_bn"] / cluster_means["gdp_at_risk_bn"].max() +
        cluster_means["flooded_pixels"]  / cluster_means["flooded_pixels"].max()
    )
    rank_order = cluster_means["combined_score"].rank(ascending=True).astype(int) - 1

    # Build tier labels (4 tiers → use first 4 names; fewer tiers → subset)
    tier_map_names = {
        0: "Low Risk",
        1: "Moderate Risk",
        2: "High Risk",
        3: "Priority Risk",
    }
    # Map cluster_id → rank → tier label
    cluster_to_tier = {}
    for cid, rank in rank_order.items():
        # If k < 4, collapse upper tiers
        tier_idx = min(rank, len(tier_map_names) - 1)
        cluster_to_tier[cid] = tier_map_names[tier_idx]

    df["risk_tier"] = df["cluster_id"].map(cluster_to_tier)
    print("\nCluster assignments:")
    summary = df.groupby(["risk_tier", "cluster_id"])["nuts3"].apply(list)
    for (tier, cid), regions in summary.items():
        print(f"  [{cid}] {tier}: {', '.join(sorted(regions))}")

    return df, cluster_to_tier, cluster_means


# ─── STEP 6: PLOT RESULTS ─────────────────────────────────────────────────────
def plot_results(df, k_range, inertias, silhouettes, optimal_k, cluster_means,
                 cluster_to_tier, feature_cols):
    """
    4-panel figure:
      Top-left:  Elbow curve (inertia vs k)
      Top-right: Silhouette scores vs k
      Bottom-left:  Scatter — GDP at risk vs Flooded pixels, coloured by tier
      Bottom-right: Bar chart — mean GDP at risk by risk tier
    """
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.suptitle(
        f"K-Means Coastal Risk Clustering — Portugal NUTS3 Regions\n"
        f"SSP5-8.5 / 2100 | k={optimal_k} clusters | "
        f"Features: flood extent, GDP at risk, relative exposure, infrastructure cost",
        fontsize=12, fontweight="bold"
    )

    ax_elbow, ax_sil, ax_scatter, ax_bar = axes.flatten()

    # ── Elbow curve ──
    ax_elbow.plot(k_range, inertias, "o-", color="#1565C0", lw=2, markersize=7)
    ax_elbow.axvline(optimal_k, color="#C62828", lw=1.5, linestyle="--",
                     label=f"Chosen k={optimal_k}")
    ax_elbow.set_title("Elbow Method — Inertia vs Number of Clusters", fontweight="bold")
    ax_elbow.set_xlabel("Number of clusters (k)")
    ax_elbow.set_ylabel("Inertia (within-cluster sum of squares)")
    ax_elbow.legend()
    ax_elbow.grid(True, alpha=0.3)

    # ── Silhouette scores ──
    sil_vals = [s for s in silhouettes if not np.isnan(s)]
    sil_k    = [k for k, s in zip(k_range, silhouettes) if not np.isnan(s)]
    ax_sil.bar(sil_k, sil_vals, color="#1565C0", alpha=0.7, edgecolor="white")
    ax_sil.axvline(optimal_k, color="#C62828", lw=1.5, linestyle="--",
                   label=f"Chosen k={optimal_k}")
    ax_sil.set_title("Silhouette Score vs Number of Clusters\n"
                     "(higher = better-separated clusters)", fontweight="bold")
    ax_sil.set_xlabel("Number of clusters (k)")
    ax_sil.set_ylabel("Silhouette Score (−1 to +1)")
    ax_sil.set_ylim(0, 1)
    ax_sil.legend()
    ax_sil.grid(True, alpha=0.3, axis="y")

    # ── Scatter: GDP at risk vs flooded pixels ──
    tier_order = ["Priority Risk", "High Risk", "Moderate Risk", "Low Risk"]
    for tier in tier_order:
        sub = df[df["risk_tier"] == tier]
        if len(sub) == 0:
            continue
        color = TIER_COLORS.get(tier, "#999999")
        ax_scatter.scatter(sub["flooded_pixels"] / 1000, sub["gdp_at_risk_bn"],
                           s=90, color=color, label=tier, zorder=3, edgecolors="white",
                           linewidths=0.5)
        for _, row in sub.iterrows():
            ax_scatter.annotate(
                row["nuts3"].replace(" (railway)", ""),
                (row["flooded_pixels"] / 1000, row["gdp_at_risk_bn"]),
                textcoords="offset points", xytext=(5, 3),
                fontsize=7, color="#333333"
            )

    ax_scatter.set_title("GDP at Risk vs Flood Exposure by NUTS3\n"
                         "(SSP5-8.5, 2100 — coloured by risk tier)", fontweight="bold")
    ax_scatter.set_xlabel("Flooded pixels (thousands)")
    ax_scatter.set_ylabel("GDP at Risk (€ billion)")
    ax_scatter.legend(fontsize=8)
    ax_scatter.grid(True, alpha=0.25)

    # ── Bar chart: mean GDP at risk by tier ──
    tier_summary = (df.groupby("risk_tier")[["gdp_at_risk_bn", "infra_value_bn"]]
                    .mean()
                    .reindex([t for t in tier_order if t in df["risk_tier"].values]))
    x_pos  = np.arange(len(tier_summary))
    width  = 0.38
    colors = [TIER_COLORS.get(t, "#999") for t in tier_summary.index]

    ax_bar.bar(x_pos - width/2, tier_summary["gdp_at_risk_bn"],
               width, label="Mean GDP at Risk (€bn)", color=colors, alpha=0.85,
               edgecolor="white")
    ax_bar.bar(x_pos + width/2, tier_summary["infra_value_bn"],
               width, label="Mean Infra Cost (€bn)", color=colors, alpha=0.45,
               edgecolor="white", hatch="//")
    ax_bar.set_title("Mean GDP at Risk and Infrastructure Cost\nby Risk Tier",
                     fontweight="bold")
    ax_bar.set_xticks(x_pos)
    ax_bar.set_xticklabels(tier_summary.index, rotation=10, ha="right")
    ax_bar.set_ylabel("€ billion (mean per NUTS3 region in tier)")
    ax_bar.legend(fontsize=8)
    ax_bar.grid(True, alpha=0.25, axis="y")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.show()   # displays chart in VS Code interactive window
    plt.close()
    print(f"\nSaved: {OUT_PNG}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("K-MEANS COASTAL RISK CLUSTERING — PORTUGAL NUTS3")
    print(f"Scenario: SSP5-8.5  |  Year: {CLUSTER_YEAR}")
    print("=" * 65)

    # Step 1: Build feature table
    df = build_feature_table()

    # Step 2: Normalise features
    X_scaled, feature_cols, scaler = prepare_features(df)

    # Step 3: Choose k
    print("\nRunning elbow method and silhouette analysis...")
    k_range_list, inertias, silhouettes = choose_k(X_scaled)

    # Print k selection table
    print(f"\n{'k':>3}  {'Inertia':>12}  {'Silhouette':>12}")
    print("-" * 32)
    for k, ine, sil in zip(k_range_list, inertias, silhouettes):
        sil_str = f"{sil:.4f}" if not np.isnan(sil) else "  n/a"
        print(f"{k:>3}  {ine:>12.4f}  {sil_str:>12}")

    # Choose k: highest silhouette score (auto-selection)
    valid_sils  = [(k, s) for k, s in zip(k_range_list, silhouettes) if not np.isnan(s)]
    optimal_k   = max(valid_sils, key=lambda x: x[1])[0]
    print(f"\nAuto-selected k={optimal_k} (highest silhouette score)")

    # OVERRIDE: force k=4 for policy-relevant risk tiers.
    # With only 12 regions, k=2 or k=3 is statistically optimal but produces
    # tiers that are too coarse for dissertation analysis and Tableau mapping.
    # k=4 (Priority / High / Moderate / Low) gives actionable policy categories
    # while remaining well above the minimum meaningful cluster size.
    CHOSEN_K = 4
    print(f"Overriding to k={CHOSEN_K} for policy-relevant tier granularity.")
    print("(Edit CHOSEN_K above to change this.)")

    # Step 4: Fit final model
    km, labels, sil_score = fit_kmeans(X_scaled, CHOSEN_K)

    # Step 5: Label clusters
    df, cluster_to_tier, cluster_means = label_clusters(
        df, labels, km, feature_cols, scaler, CHOSEN_K
    )

    # Step 6: Save output CSV (Tableau-ready)
    out_cols = [
        "nuts3", "risk_tier", "cluster_id",
        "flooded_pixels", "gdp_at_risk_bn", "fraction_flooded",
        "infra_value_bn", "gdp_total_bn",
    ]
    sorted_df = df[out_cols].sort_values(["risk_tier", "nuts3"])
    sorted_df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV}")
    sorted_df.to_excel(OUT_XLSX, index=False)
    print(f"Saved: {OUT_XLSX}  ← use this file in Tableau (avoids CSV separator issues)")

    # Print final table
    print("\n=== FINAL RISK TIER ASSIGNMENTS ===")
    print(df[["nuts3", "risk_tier", "gdp_at_risk_bn", "fraction_flooded",
              "infra_value_bn"]].sort_values(
        ["risk_tier", "gdp_at_risk_bn"], ascending=[True, False]
    ).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Step 7: Plot
    plot_results(df, k_range_list, inertias, silhouettes, CHOSEN_K,
                 cluster_means, cluster_to_tier, feature_cols)

    print("\nDone.")
    print(f"\nTableau: connect {OUT_XLSX.name} to nuts3_wgs84.geojson")
    print("  Join key: nuts3 (both files)")
    print("  Colour by: risk_tier (4 values: Priority/High/Moderate/Low Risk)")


if __name__ == "__main__":
    main()
