
from pathlib import Path
import rasterio
import numpy as np
import pandas as pd

# Project root directory
ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data" / "raw"

flood_path = DATA / "dhemaji_flood_mask_2024.tif"
landcover_path = DATA / "dhemaji_landcover_2021.tif"
csv_path = DATA / "dhemaji_impact_statistics_2024.csv"


def inspect_raster(path):
    print(f"\n--- {path.name} ---")

    with rasterio.open(path) as src:
        print("Width:", src.width)
        print("Height:", src.height)
        print("Bands:", src.count)
        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print("NoData:", src.nodata)
        print("Bounds:", src.bounds)

        data = src.read(1, masked=True)

        valid = data.compressed()

        print("Valid pixels:", valid.size)
        print(
            "Unique sample values:",
            np.unique(valid[:100000])[:20]
        )

        return {
            "crs": src.crs,
            "transform": src.transform,
            "width": src.width,
            "height": src.height,
        }


flood_info = inspect_raster(flood_path)
landcover_info = inspect_raster(landcover_path)

print("\n--- Grid alignment check ---")

aligned = (
    flood_info["crs"] == landcover_info["crs"]
    and flood_info["transform"] == landcover_info["transform"]
    and flood_info["width"] == landcover_info["width"]
    and flood_info["height"] == landcover_info["height"]
)

print("Raster grids aligned:", aligned)

print("\n--- Exported Impact Statistics ---")

stats = pd.read_csv(csv_path)
print(stats.to_string(index=False))
