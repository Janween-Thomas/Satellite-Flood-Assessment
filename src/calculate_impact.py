
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio


# 1. Define paths
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"

FLOOD_FILE = DATA / "dhemaji_flood_mask_2024.tif"
LAND_FILE = DATA / "dhemaji_landcover_2021.tif"
CSV_FILE = DATA / "dhemaji_impact_statistics_2024.csv"


# 2. Read and calculate raster statistics
def calculate_impact():
    flooded_pixels = 0
    cropland_pixels = 0
    builtup_pixels = 0
    overlap_pixels = 0

    with rasterio.open(FLOOD_FILE) as flood_src, \
         rasterio.open(LAND_FILE) as land_src:

        # Confirm spatial alignment
        if (
            flood_src.crs != land_src.crs
            or flood_src.transform != land_src.transform
            or flood_src.width != land_src.width
            or flood_src.height != land_src.height
        ):
            raise ValueError(
                "Flood and land-cover rasters are not aligned."
            )

        if not flood_src.crs.is_projected:
            raise ValueError(
                "A projected CRS is required for "
                "this pixel-area calculation."
            )

        pixel_area_m2 = abs(
            flood_src.transform.a * flood_src.transform.e
            - flood_src.transform.b * flood_src.transform.d
        )

        # Process in blocks to reduce memory usage
        for _, window in flood_src.block_windows(1):
            flood = flood_src.read(
                1, window=window, masked=True
            )

            land = land_src.read(
                1, window=window, masked=True
            )

            valid_flood = ~np.ma.getmaskarray(flood)
            valid_land = ~np.ma.getmaskarray(land)

            is_flooded = (
                valid_flood & (flood.data == 1)
            )

            common_valid = valid_flood & valid_land

            flooded_pixels += np.count_nonzero(is_flooded)

            overlap_pixels += np.count_nonzero(common_valid)

            cropland_pixels += np.count_nonzero(
                is_flooded
                & valid_land
                & (land.data == 40)
            )

            builtup_pixels += np.count_nonzero(
                is_flooded
                & valid_land
                & (land.data == 50)
            )

    # Convert square metres to square kilometres
    pixel_to_km2 = pixel_area_m2 / 1_000_000

    return {
        "potential_flood_km2":
            flooded_pixels * pixel_to_km2,
        "exposed_cropland_km2":
            cropland_pixels * pixel_to_km2,
        "exposed_builtup_km2":
            builtup_pixels * pixel_to_km2,
        "common_valid_pixels": overlap_pixels,
    }


# 3. Calculate results
results = calculate_impact()

print("\n========== PYTHON FLOOD ASSESSMENT ==========")

for key, value in results.items():
    print(f"{key}: {value}")

# 4. Compare with Earth Engine results
gee = pd.read_csv(CSV_FILE).iloc[0]

print("\n========== EARTH ENGINE COMPARISON ==========")

for metric in [
    "potential_flood_km2",
    "exposed_cropland_km2",
    "exposed_builtup_km2",
]:
    python_value = results[metric]
    gee_value = float(gee[metric])

    print(f"\n{metric}")
    print(f"  Python:       {python_value:.6f} km2")
    print(f"  Earth Engine: {gee_value:.6f} km2")
    print(f"  Difference:   {python_value - gee_value:.6f} km2")

# 5. Save results
OUTPUT = ROOT / "data" / "processed"
OUTPUT.mkdir(parents=True, exist_ok=True)

pd.DataFrame([results]).to_csv(
    OUTPUT / "python_impact_statistics.csv",
    index=False
)

print("\nResults saved successfully.")
