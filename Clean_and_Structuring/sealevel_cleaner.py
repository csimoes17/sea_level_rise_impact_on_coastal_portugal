import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# -----------------------------
# CONFIGURATION
# -----------------------------

# Folder where BOTH input and output files live
DATA_DIR = Path("Clean_and_Structuring")

INPUT_FILES = [
    "sea_level_sines_monthly.csv",
    "sea_level_leixoes_monthly.csv"
]

# PSMSL standard column names
COLUMNS = ["year_decimal", "sea_level_mm", "flag", "quality"]

# -----------------------------
# FUNCTIONS
# -----------------------------

def clean_sea_level(file_path: Path) -> pd.DataFrame:
    """
    Load and clean PSMSL monthly sea-level data.
    """
    df = pd.read_csv(
        file_path,
        sep=";",
        names=COLUMNS,
        header=None
    )

    # Replace PSMSL missing value code with NaN
    df["sea_level_mm"] = df["sea_level_mm"].replace(-99999, np.nan)

    # Drop rows with missing sea level values
    df = df.dropna(subset=["sea_level_mm"])

    # Convert millimeters to meters
    df["sea_level_m"] = df["sea_level_mm"] / 1000.0

    # Keep only relevant columns
    df = df[["year_decimal", "sea_level_m", "flag"]]

    return df


def plot_time_series(df: pd.DataFrame, station_name: str):
    """
    Plot sea level time series.
    """
    plt.figure(figsize=(10, 5))
    plt.plot(df["year_decimal"], df["sea_level_m"], linewidth=0.8)
    plt.xlabel("Year")
    plt.ylabel("Mean Sea Level (m)")
    plt.title(f"Mean Sea Level – {station_name}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# -----------------------------
# MAIN SCRIPT
# -----------------------------

if __name__ == "__main__":

    for filename in INPUT_FILES:
        input_path = DATA_DIR / filename

        # Build output filename: original + "_cleaned.csv"
        output_filename = input_path.stem + "_cleaned.csv"
        output_path = DATA_DIR / output_filename

        print(f"\nProcessing file: {filename}")

        # Clean data
        df_clean = clean_sea_level(input_path)

        # Basic validation output
        print(df_clean.describe())

        # Plot
        plot_time_series(df_clean, input_path.stem)

        # Save cleaned data in SAME folder
        df_clean.to_csv(output_path, index=False)

        print(f"Cleaned file saved as: {output_filename}")
