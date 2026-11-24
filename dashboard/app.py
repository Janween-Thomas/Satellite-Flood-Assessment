
"""FloodWatch — Dhemaji, Assam satellite flood impact dashboard.

Run from the project root with:
    python -m streamlit run dashboard/app.py
"""

from pathlib import Path

import folium
import numpy as np
import pandas as pd
import rasterio
import streamlit as st
import streamlit.components.v1 as components
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject, transform, transform_bounds

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FLOOD_FILE = RAW / "dhemaji_flood_mask_2024.tif"
LAND_FILE = RAW / "dhemaji_landcover_2021.tif"
STATS_FILE = PROCESSED / "python_impact_statistics.csv"

st.set_page_config(
    page_title="FloodWatch | Assam Flood Assessment",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.title("🌊 FloodWatch")
    st.markdown("### Study details")
    st.write("**Location:** Dhemaji, Assam, India")
    st.write("**Satellite:** Sentinel-1 SAR (VV)")
    st.write("**Comparison dates:** 24 June and 30 July 2024")
    st.write("**Flood threshold:** 1.25 (linear backscatter ratio)")
    st.write("**Land cover:** ESA WorldCover 2021")

    st.divider()

    st.info(
        "Academic research prototype — not a validated "
        "flood warning or building damage map."
    )

# =====================================================
# MAIN HEADER
# =====================================================

st.title("🌊 FloodWatch")
st.subheader(
    "Satellite-Based Flood Inundation Mapping "
    "and Impact Assessment"
)

st.caption(
    "Dhemaji district, Assam, India · "
    "Sentinel-1 SAR · June–July 2024"
)

st.warning(
    "Potential flood and land-cover exposure estimates "
    "are preliminary. They are not independently validated "
    "and should not be used for emergency decisions."
)

# =====================================================
# VERIFY DATA FILES
# =====================================================

required_files = [
    FLOOD_FILE,
    LAND_FILE,
    STATS_FILE
]

missing = [
    str(p.relative_to(ROOT))
    for p in required_files
    if not p.is_file()
]

if missing:
    st.error(
        "Missing project data files: "
        + ", ".join(missing)
    )

    st.info(
        "Place the two GeoTIFFs in data/raw/ and run "
        "src/calculate_impact.py to generate the CSV "
        "in data/processed/."
    )
    st.stop()

# =====================================================
# LOAD STATISTICS
# =====================================================

@st.cache_data(show_spinner=False)
def load_statistics(path: str, modification_time: float):
    return pd.read_csv(path)


stats_df = load_statistics(
    str(STATS_FILE),
    STATS_FILE.stat().st_mtime
)

if stats_df.empty:
    st.error("The impact statistics CSV is empty.")
    st.stop()

stats = stats_df.iloc[0]

flood_area = float(stats["potential_flood_km2"])
crop_area = float(stats["exposed_cropland_km2"])
built_area = float(stats["exposed_builtup_km2"])

crop_percent = (
    100 * crop_area / flood_area
    if flood_area > 0
    else 0.0
)

# =====================================================
# METRIC CARDS
# =====================================================

st.markdown("## Flood Impact Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Potential Flood Area",
    f"{flood_area:.2f} km²"
)

c2.metric(
    "Exposed Cropland",
    f"{crop_area:.2f} km²"
)

c3.metric(
    "Exposed Built-up Land",
    f"{built_area:.4f} km²"
)

c4.metric(
    "Cropland Share",
    f"{crop_percent:.2f}%"
)

# =====================================================
# PREPARE INTERACTIVE MAP LAYERS
# =====================================================

@st.cache_data(
    show_spinner="Preparing the interactive map layers..."
)
def prepare_map_layers(
    flood_path: str,
    land_path: str,
    flood_mtime: float,
    land_mtime: float
):

    # Browser-friendly preview resolution.
    # The original raster remains unchanged.
    preview_width = 2200

    with rasterio.open(flood_path) as flood_src, \
         rasterio.open(land_path) as land_src:

        if (
            flood_src.crs != land_src.crs
            or flood_src.transform != land_src.transform
            or flood_src.shape != land_src.shape
        ):
            raise ValueError(
                "Flood and land-cover rasters "
                "are not on the same grid."
            )

        if flood_src.crs is None:
            raise ValueError(
                "Flood raster has no coordinate "
                "reference system."
            )

        preview_height = max(
            1,
            round(
                flood_src.height
                * preview_width
                / flood_src.width
            )
        )

        # Convert UTM extent to latitude/longitude.
        west, south, east, north = transform_bounds(
            flood_src.crs,
            "EPSG:4326",
            *flood_src.bounds,
            densify_pts=21
        )

        dst_transform = from_bounds(
            west,
            south,
            east,
            north,
            preview_width,
            preview_height
        )

        shape = (
            preview_height,
            preview_width
        )

        flood_preview = np.full(
            shape,
            255,
            dtype=np.uint8
        )

        land_preview = np.full(
            shape,
            255,
            dtype=np.uint8
        )

        # Reproject both raster previews.
        for source, destination in (
            (flood_src, flood_preview),
            (land_src, land_preview)
        ):

            reproject(
                source=rasterio.band(source, 1),
                destination=destination,
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=(
                    source.nodata
                    if source.nodata is not None
                    else 255
                ),
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                dst_nodata=255,
                resampling=Resampling.nearest
            )

    # Create classification masks.
    flooded = flood_preview == 1
    valid_land = land_preview != 255

    crop = (
        flooded
        & valid_land
        & (land_preview == 40)
    )

    built = (
        flooded
        & valid_land
        & (land_preview == 50)
    )

    # Convert classification masks into
    # transparent colored image overlays.
    def rgba_overlay(mask, rgb, alpha):

        result = np.zeros(
            (*mask.shape, 4),
            dtype=np.uint8
        )

        result[mask, :3] = rgb
        result[mask, 3] = alpha

        return result

    flood_overlay = rgba_overlay(
        flooded,
        (0, 110, 255),
        140
    )

    crop_overlay = rgba_overlay(
        crop,
        (255, 0, 180),
        220
    )

    built_overlay = rgba_overlay(
        built,
        (255, 40, 40),
        230
    )

    bounds = [
        [south, west],
        [north, east]
    ]

    return (
        flood_overlay,
        crop_overlay,
        built_overlay,
        bounds
    )


# =====================================================
# FIND FULL-RESOLUTION BUILT-UP EXPOSURE PIXELS
# =====================================================

@st.cache_data(
    show_spinner="Finding exposed built-up locations..."
)
def get_builtup_locations(
    flood_path: str,
    land_path: str,
    flood_mtime: float,
    land_mtime: float
):

    points = []

    with rasterio.open(flood_path) as flood_src, \
         rasterio.open(land_path) as land_src:

        if (
            flood_src.crs != land_src.crs
            or flood_src.transform != land_src.transform
            or flood_src.shape != land_src.shape
        ):
            raise ValueError(
                "Flood and land-cover rasters "
                "must share the same grid."
            )

        # Process raster in small blocks.
        for _, window in flood_src.block_windows(1):

            flood = flood_src.read(
                1,
                window=window,
                masked=True
            )

            land = land_src.read(
                1,
                window=window,
                masked=True
            )

            # Identify exposed built-up pixels.
            affected = (
                ~np.ma.getmaskarray(flood)
                & ~np.ma.getmaskarray(land)
                & (flood.data == 1)
                & (land.data == 50)
            )

            rows, cols = np.where(affected)

            if not len(rows):
                continue

            # Convert block-relative pixels
            # to full-raster pixel positions.
            rows = rows + int(window.row_off)
            cols = cols + int(window.col_off)

            # Pixel centres in the raster CRS.
            xs, ys = rasterio.transform.xy(
                flood_src.transform,
                rows,
                cols,
                offset="center"
            )

            # Convert to geographical coordinates.
            lons, lats = transform(
                flood_src.crs,
                "EPSG:4326",
                xs,
                ys
            )

            points.extend(
                (float(lat), float(lon))
                for lat, lon in zip(lats, lons)
            )

    return points


# =====================================================
# CREATE INTERACTIVE FOLIUM MAP
# =====================================================

st.markdown("## Interactive Flood Inundation Map")

st.write(
    "Zoom into the map and use the layer selector "
    "to compare potential flooding, exposed cropland, "
    "and highlighted built-up exposure locations."
)

try:

    mtime_f = FLOOD_FILE.stat().st_mtime
    mtime_l = LAND_FILE.stat().st_mtime

    (
        flood_layer,
        crop_layer,
        built_layer,
        bounds
    ) = prepare_map_layers(
        str(FLOOD_FILE),
        str(LAND_FILE),
        mtime_f,
        mtime_l
    )

    builtup_locations = get_builtup_locations(
        str(FLOOD_FILE),
        str(LAND_FILE),
        mtime_f,
        mtime_l
    )

except Exception as exc:
    st.error(
        "Unable to prepare the map "
        "from the exported GeoTIFFs."
    )
    st.exception(exc)
    st.stop()


center = [
    (bounds[0][0] + bounds[1][0]) / 2,
    (bounds[0][1] + bounds[1][1]) / 2
]

m = folium.Map(
    location=center,
    zoom_start=10,
    tiles="OpenStreetMap",
    control_scale=True
)

# =====================================================
# SATELLITE BACKGROUND
# =====================================================

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/"
        "services/World_Imagery/MapServer/tile/"
        "{z}/{y}/{x}"
    ),
    attr="Tiles © Esri",
    name="Satellite Imagery",
    overlay=False,
    show=True
).add_to(m)

# =====================================================
# BLUE FLOOD EXTENT LAYER
# =====================================================

folium.raster_layers.ImageOverlay(
    image=flood_layer,
    bounds=bounds,
    name="Potential Flood Extent (Blue)",
    opacity=0.85,
    show=True,
    interactive=False
).add_to(m)

# =====================================================
# PINK CROPLAND EXPOSURE LAYER
# =====================================================

folium.raster_layers.ImageOverlay(
    image=crop_layer,
    bounds=bounds,
    name="Exposed Cropland (Pink)",
    opacity=0.95,
    show=False,
    interactive=False
).add_to(m)

# =====================================================
# RED BUILT-UP RASTER LAYER
# =====================================================

folium.raster_layers.ImageOverlay(
    image=built_layer,
    bounds=bounds,
    name="Exposed Built-up Raster (Red)",
    opacity=1.0,
    show=False,
    interactive=False
).add_to(m)

# =====================================================
# RED BUILT-UP EXPOSURE MARKERS
# =====================================================

# These markers use the original 10-metre
# raster instead of the downsampled preview.

markers = folium.FeatureGroup(
    name="Built-up Exposure Locations (Red Markers)",
    show=True
)

for lat, lon in builtup_locations:

    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color="#FF2020",
        weight=2,
        fill=True,
        fill_color="#FF2020",
        fill_opacity=0.9,
        tooltip=(
            "Potential built-up exposure "
            "(raster-cell centre)"
        )
    ).add_to(markers)

markers.add_to(m)

# =====================================================
# MAP CONTROLS
# =====================================================

folium.LayerControl(
    collapsed=False
).add_to(m)

m.fit_bounds(bounds)

# Embed map inside Streamlit.
map_html = m.get_root().render()

components.html(
    map_html,
    height=650,
    scrolling=False
)

# =====================================================
# MAP EXPLANATIONS
# =====================================================

st.caption(
    f"{len(builtup_locations)} original 10-metre raster "
    "cells overlap the potential flood mask and "
    "the built-up land-cover class. Red markers "
    "are enlarged for visibility and do not "
    "represent individual buildings."
)

st.markdown("### How to Interpret the Map")

st.markdown("""
- 🔵 **Blue:** Potential flood detected from SAR backscatter change.
- 🩷 **Pink:** Potential flooding overlapping 2021 cropland.
- 🔴 **Red raster:** Potential flooding overlapping built-up land.
- 📍 **Red circle markers:** Full-resolution centres of potentially exposed built-up pixels.
- 🛰️ **Satellite background:** Geographic context, not necessarily imagery from the 2024 flood event.
""")

st.info(
    "The interactive overlays are downsampled previews. "
    "Precise measurements come from the original "
    "10-metre GeoTIFFs. Missing satellite observations "
    "must not be interpreted as confirmed dry land."
)

# =====================================================
# LAND-COVER EXPOSURE CHART
# =====================================================

st.markdown("## Land-Cover Exposure Analysis")

impact_df = pd.DataFrame({
    "Land Type": [
        "Cropland",
        "Built-up Land",
        "Other Detected Flood Area"
    ],
    "Area (km²)": [
        crop_area,
        built_area,
        max(
            0.0,
            flood_area - crop_area - built_area
        )
    ]
})

chart_col, table_col = st.columns([2, 1])

with chart_col:
    st.bar_chart(
        impact_df.set_index("Land Type")["Area (km²)"]
    )

with table_col:
    st.dataframe(
        impact_df,
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# METHODOLOGY AND LIMITATIONS
# =====================================================

with st.expander("Methodology and limitations"):

    st.markdown("""
**Study area:** Dhemaji, Assam, India.

**Satellite data:** Sentinel-1 SAR VV observations around
24 June and 30 July 2024.

**Flood detection:** Pre-flood and post-flood linear radar
backscatter are compared using a ratio threshold of 1.25.

**Filtering:** Permanent-water, steep-slope and small-cluster
filtering are applied.

**Cropland exposure:** Flood mask overlap with ESA WorldCover
2021 cropland (class 40).

**Built-up exposure:** Flood mask overlap with ESA WorldCover
2021 built-up land (class 50).

**Area estimation:** Rasterio calculations use the exported
10-metre GeoTIFF grids.

**Limitations:** Backscatter changes may be caused by rainfall,
soil moisture, vegetation or surface roughness. The results
are not independently validated. WorldCover represents
2021 land cover rather than 2024 conditions.
""")

# =====================================================
# DOWNLOAD RESULTS
# =====================================================

st.markdown("## Download Results")

d1, d2 = st.columns(2)

with d1:
    st.download_button(
        "📥 Download Impact Statistics (CSV)",
        data=impact_df.to_csv(
            index=False
        ).encode("utf-8"),
        file_name="dhemaji_impact_summary.csv",
        mime="text/csv",
        use_container_width=True
    )

with d2:
    st.download_button(
        "🗺️ Download Interactive Map (HTML)",
        data=map_html.encode("utf-8"),
        file_name="dhemaji_interactive_flood_map.html",
        mime="text/html",
        use_container_width=True
    )

# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "FloodWatch | Dhemaji, Assam | "
    "Sentinel-1 SAR · ESA WorldCover 2021 | "
    "Google Earth Engine, Rasterio, Folium & Streamlit"
)
