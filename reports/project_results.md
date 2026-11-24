
# FloodWatch — Project Results

## Study Area
Dhemaji District, Assam, India

## Satellite Data
- Satellite: Sentinel-1 SAR
- Polarization: VV
- Pre-flood observation: 24 June 2024
- Flood-period observation: 30 July 2024
- Land cover: ESA WorldCover 2021

## Flood Detection Method
Sentinel-1 radar backscatter change detection
using a linear backscatter ratio threshold of 1.25.

The resulting candidate flood mask was filtered
using permanent-water, terrain-slope, and
connected-pixel criteria.

## Results

| Metric | Estimated Area |
|---|---:|
| Potential flood inundation | 22.1486 km² |
| Exposed cropland | 5.1719 km² |
| Exposed built-up land | 0.0041 km² |
| Cropland share of detected flood area | 23.35% |

## Earth Engine Comparison
Earth Engine estimated 22.2254 km² of potential
inundation, compared with 22.1486 km² calculated
from the exported GeoTIFF in Python.

The difference is approximately 0.35%.

## Interpretation
Approximately 5.17 km² of land classified as
cropland in ESA WorldCover 2021 overlaps with
the detected potential inundation area.

Approximately 0.0041 km² of built-up land
also overlaps with the detected flood mask.

These are potential exposure estimates, not
verified agricultural losses or building damage.

## Limitations
- Flood classification has not been independently validated.
- Radar changes can reflect moisture or vegetation changes.
- Land-cover classifications are from 2021.
- Satellite coverage and spatial resolution limit precision.
- Results should not be used for emergency decisions.

## Project Links
Live application:
https://dhemaji-flood-mapping-2024.streamlit.app/

Source code:
https://github.com/Janween-Thomas/Satellite-Flood-Assessment

