import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from pathlib import Path

import rasterio
from rasterio.merge import merge

# -----------------------------
# CONFIGURATION
# -----------------------------

# Always resolves to the folder where THIS script lives,
# regardless of which directory you run it from.
DATA_DIR = Path(__file__).parent

INPUT_DEMS = [
    "COP DEM 1.tif",
    "COP DEM 2.tif",
]

OUTPUT_FILENAME = "dem_portugal_merged.tif"

# Approximate bounding box for mainland Portugal (WGS84)
# Used only for the diagnostic plot — merge is NOT clipped
PORTUGAL_BOUNDS = {
    "west":  -9.55,
    "east":  -6.15,
    "south": 36.80,
    "north": 42.20,
}

# -----------------------------
# STEP 1 — INSPECT INPUT TILES
# -----------------------------

print("=" * 60)
print("STEP 1: Inspecting input DEM tiles")
print("=" * 60)

for filename in INPUT_DEMS:
    path = DATA_DIR / filename
    with rasterio.open(path) as src:
        b = src.bounds
        print(f"\n  File     : {filename}")
        print(f"  CRS      : {src.crs}")
        print(f"  Width    : {src.width} px   |  Height : {src.height} px")
        print(f"  Res (deg): {src.res[0]:.8f} × {src.res[1]:.8f}")
        print(f"  West     : {b.left:.5f}   East  : {b.right:.5f}")
        print(f"  South    : {b.bottom:.5f}  North : {b.top:.5f}")
        print(f"  NoData   : {src.nodata}")
        print(f"  Dtype    : {src.dtypes[0]}")

# -----------------------------
# STEP 2 — MERGE TILES
# -----------------------------

print("\n" + "=" * 60)
print("STEP 2: Merging tiles")
print("=" * 60)

src_files = [rasterio.open(DATA_DIR / f) for f in INPUT_DEMS]

# merge() creates a union of all input extents.
# strategy="first" uses the first valid pixel when tiles overlap (default).
merged_array, merged_transform = merge(src_files)

# Copy metadata from the first source and update for merged output
merged_meta = src_files[0].meta.copy()
merged_meta.update({
    "driver":    "GTiff",
    "height":    merged_array.shape[1],
    "width":     merged_array.shape[2],
    "transform": merged_transform,
    "compress":  "lzw",       # lossless compression — keeps file small
    "tiled":     True,
    "blockxsize": 256,
    "blockysize": 256,
})

# Close input files
for src in src_files:
    src.close()

print(f"\n  Merged array shape : {merged_array.shape}  (bands, rows, cols)")
print(f"  Merged dtype       : {merged_array.dtype}")
print(f"  Transform          : {merged_transform}")

# Quick stats on valid (non-nodata) pixels
nodata_val = merged_meta.get("nodata")
if nodata_val is not None:
    valid_mask = merged_array[0] != nodata_val
else:
    valid_mask = np.isfinite(merged_array[0])

valid_pixels = merged_array[0][valid_mask]

print(f"\n  Valid pixels  : {valid_mask.sum():,}")
print(f"  Elevation min : {valid_pixels.min():.2f} m")
print(f"  Elevation max : {valid_pixels.max():.2f} m")
print(f"  Elevation mean: {valid_pixels.mean():.2f} m")

# -----------------------------
# STEP 3 — SAVE MERGED RASTER
# -----------------------------

print("\n" + "=" * 60)
print("STEP 3: Saving merged raster")
print("=" * 60)

output_path = DATA_DIR / OUTPUT_FILENAME

with rasterio.open(output_path, "w", **merged_meta) as dst:
    dst.write(merged_array)

print(f"\n  Saved : {output_path}")

# Confirm saved file
with rasterio.open(output_path) as check:
    b = check.bounds
    print(f"\n  Verification of saved file:")
    print(f"  CRS    : {check.crs}")
    print(f"  Size   : {check.width} × {check.height} px")
    print(f"  West   : {b.left:.5f}  East  : {b.right:.5f}")
    print(f"  South  : {b.bottom:.5f}  North : {b.top:.5f}")
    print(f"  NoData : {check.nodata}")

# -----------------------------
# STEP 4 — DIAGNOSTIC PLOT
# -----------------------------

print("\n" + "=" * 60)
print("STEP 4: Generating diagnostic plot")
print("=" * 60)

with rasterio.open(output_path) as src:
    dem_data = src.read(1).astype("float32")
    nd = src.nodata
    if nd is not None:
        dem_data[dem_data == nd] = np.nan
    else:
        dem_data[~np.isfinite(dem_data)] = np.nan

    extent = [
        src.bounds.left,
        src.bounds.right,
        src.bounds.bottom,
        src.bounds.top,
    ]

# Clip display range so low coastal elevations are visible
vmin, vmax = 0, 500

fig, ax = plt.subplots(figsize=(8, 12))

im = ax.imshow(
    dem_data,
    cmap="terrain",
    norm=mcolors.Normalize(vmin=vmin, vmax=vmax),
    extent=extent,
    origin="upper",
)

# Portugal bounding box overlay
rect = mpatches.Rectangle(
    (PORTUGAL_BOUNDS["west"], PORTUGAL_BOUNDS["south"]),
    PORTUGAL_BOUNDS["east"] - PORTUGAL_BOUNDS["west"],
    PORTUGAL_BOUNDS["north"] - PORTUGAL_BOUNDS["south"],
    linewidth=1.5,
    edgecolor="red",
    facecolor="none",
    label="Mainland Portugal (approx.)",
)
ax.add_patch(rect)

plt.colorbar(im, ax=ax, label="Elevation (m)", shrink=0.6)
ax.set_xlabel("Longitude (°)")
ax.set_ylabel("Latitude (°)")
ax.set_title("Merged Copernicus DEM — Portugal\n(clipped display: 0–500 m)")
ax.legend(loc="lower right")
ax.grid(True, linewidth=0.4, alpha=0.5)
plt.tight_layout()
plt.show()

print("\nScript 04 complete.")
print(f"Output: {output_path}")
