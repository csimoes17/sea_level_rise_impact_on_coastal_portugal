# last script used - edit once work restarts
# 
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import linregress

# -----------------------------
# CONFIGURATION
# -----------------------------

DATA_DIR = Path("Clean_and_Structuring")

FILES = [
    "sea_level_sines_monthly_cleaned.csv",
    "sea_level_leixoes_monthly_cleaned.csv"
]

START_YEAR = 1993
END_YEAR = 2022

# -----------------------------
# MAIN SCRIPT
# -----------------------------

if __name__ == "__main__":

    for filename in FILES:
        path = DATA_DIR / filename
        station_name = filename.replace("sea_level_", "").replace("_monthly_cleaned.csv", "")

        print(f"\nStation: {station_name.upper()}")

        # Load data
        df = pd.read_csv(path)

        # Filter to common period
        df_period = df[
            (df["year_decimal"] >= START_YEAR) &
            (df["year_decimal"] <= END_YEAR)
        ].dropna(subset=["year_decimal", "sea_level_m"])

        # Diagnostic check
        print(
            f"{station_name}: "
            f"{df['year_decimal'].min():.1f}–{df['year_decimal'].max():.1f} | "
            f"{df_period['year_decimal'].min():.1f}–{df_period['year_decimal'].max():.1f} | "
            f"rows before = {len(df)}, rows after = {len(df_period)}"
        )

        # Regression on FILTERED data
        x = df_period["year_decimal"]
        y = df_period["sea_level_m"]

        result = linregress(x, y)

        slope_mm_per_year = result.slope * 1000

        print(f"Sea level rise rate (1993–2022): {slope_mm_per_year:.2f} mm/year")
        print(f"R²: {result.rvalue**2:.3f}")
        print(f"p-value: {result.pvalue:.3e}")

        # Trend line (filtered)
        trend = result.intercept + result.slope * x

        # Plot
        plt.figure(figsize=(10, 5))
        plt.plot(x, y, label="Observed (1993–2022)", linewidth=0.7)
        plt.plot(x, trend, color="red", label="Linear trend")
        plt.xlabel("Year")
        plt.ylabel("Mean Sea Level (m)")
        plt.title(f"Mean Sea Level Trend (1993–2022) – {station_name.capitalize()}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
