
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


# Project paths
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "processed"

OUTPUT.mkdir(parents=True, exist_ok=True)

flood_file = DATA / "dhemaji_flood_mask_2024.tif"
landcover_file = DATA / "dhemaji_landcover_2021.tif"


# Read a smaller preview from each raster
with rasterio.open(flood_file) as flood_src, \
     rasterio.open(landcover_file) as land_src:

    target_width = 1200

    scale = target_width / flood_src.width
    target_height = round(flood_src.height * scale)

    flood = flood_src.read(
        1,
        out_shape=(target_height, target_width),
        resampling=Resampling.nearest,
        masked=True
    )

    landcover = land_src.read(
        1,
        out_shape=(target_height, target_width),
        resampling=Resampling.nearest,
        masked=True
    )

    bounds = flood_src.bounds


# Create classification map
#
# 0 = non-flooded land
# 1 = detected flood
# 2 = detected flood on cropland
# 3 = detected flood on built-up land

classification = np.zeros(
    flood.shape, dtype=np.uint8
)

valid_flood = ~np.ma.getmaskarray(flood)
valid_land = ~np.ma.getmaskarray(landcover)

is_flood = valid_flood & (flood.data == 1)

classification[is_flood] = 1

classification[
    is_flood & valid_land & (landcover.data == 40)
] = 2

classification[
    is_flood & valid_land & (landcover.data == 50)
] = 3


# Colors
colors = [
    "#F0F4EF",  # Other land
    "#1769FF",  # Potential flood
    "#E83EBC",  # Flooded cropland
    "#E53935",  # Flooded built-up
]

cmap = ListedColormap(colors)
norm = BoundaryNorm(
    [-0.5, 0.5, 1.5, 2.5, 3.5],
    cmap.N
)


# Plot
fig, ax = plt.subplots(figsize=(13, 8))

ax.imshow(
    classification,
    cmap=cmap,
    norm=norm,
    extent=[
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top
    ],
    origin="upper",
    interpolation="nearest"
)

ax.set_title(
    "Dhemaji Flood Inundation & Land-Cover Exposure\n"
    "Sentinel-1 SAR | June–July 2024",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlabel("Easting (metres, UTM Zone 46N)")
ax.set_ylabel("Northing (metres, UTM Zone 46N)")

from matplotlib.patches import Patch

legend_items = [
    Patch(facecolor="#F0F4EF", label="Other / No detected flood"),
    Patch(facecolor="#1769FF", label="Potential flood"),
    Patch(facecolor="#E83EBC", label="Exposed cropland"),
    Patch(facecolor="#E53935", label="Exposed built-up"),
]

ax.legend(
    handles=legend_items,
    loc="lower left",
    framealpha=0.95
)

plt.tight_layout()

output_file = OUTPUT / "dhemaji_flood_impact_map.png"

plt.savefig(
    output_file,
    dpi=180,
    bbox_inches="tight"
)

print("Map saved to:", output_file)

plt.show()
