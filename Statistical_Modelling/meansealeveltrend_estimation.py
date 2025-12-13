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

# -----------------------------
# MAIN SCRIPT
# -----------------------------

if __name__ == "__main__":

    for filename in FILES:
        path = DATA_DIR / filename
        station_name = filename.replace("sea_level_", "").replace("_monthly_cleaned.csv", "")

        print(f"\nStation: {station_name.upper()}")

        df = pd.read_csv(path)

        x = df["year_decimal"]
        y = df["sea_level_m"]

        # Linear regression
        result = linregress(x, y)

        slope_m_per_year = result.slope
        slope_mm_per_year = slope_m_per_year * 1000

        print(f"Sea level rise rate: {slope_mm_per_year:.2f} mm/year")
        print(f"R²: {result.rvalue**2:.3f}")
        print(f"p-value: {result.pvalue:.3e}")

        # Trend line
        trend = result.intercept + result.slope * x

        # Plot
        plt.figure(figsize=(10, 5))
        plt.plot(x, y, label="Observed", linewidth=0.7)
        plt.plot(x, trend, color="red", label="Linear trend")
        plt.xlabel("Year")
        plt.ylabel("Mean Sea Level (m)")
        plt.title(f"Mean Sea Level Trend – {station_name.capitalize()}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
