// ============================================
// PROJECT: Satellite-Based Flood Mapping
// STUDY AREA: Dhemaji, Assam
// TASK: Flood Detection using Sentinel-1 SAR
// ============================================

// -------------------------------
// STEP 1: Load Dhemaji boundary
// -------------------------------
var districts = ee.FeatureCollection("FAO/GAUL/2015/level2");

var dhemaji = districts
  .filter(ee.Filter.eq("ADM1_NAME", "Assam"))
  .filter(ee.Filter.eq("ADM2_NAME", "Dhemaji"));

Map.centerObject(dhemaji, 9);

// -------------------------------
// STEP 2: Define dates
// -------------------------------
var beforeStart = '2024-06-23';
var beforeEnd   = '2024-06-25';

var afterStart  = '2024-07-29';
var afterEnd    = '2024-07-31';

// -------------------------------
// STEP 3: Load Sentinel-1 collection
// -------------------------------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(dhemaji)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
  .filter(ee.Filter.eq('relativeOrbitNumber_start', 143))
  .select('VV');

// -------------------------------
// STEP 4: Create before and after images
// -------------------------------
var before = s1
  .filterDate(beforeStart, beforeEnd)
  .median()
  .clip(dhemaji);

var after = s1
  .filterDate(afterStart, afterEnd)
  .median()
  .clip(dhemaji);

// -------------------------------
// STEP 5: Convert dB to linear
// -------------------------------
var beforeLinear = ee.Image.constant(10).pow(before.divide(10));
var afterLinear  = ee.Image.constant(10).pow(after.divide(10));

// -------------------------------
// STEP 6: Change detection ratio
// -------------------------------
var ratio = beforeLinear.divide(afterLinear);

// -------------------------------
// STEP 7: Flood threshold
// -------------------------------
// If backscatter decreases strongly after flooding,
// the ratio becomes larger.
var threshold = 1.25;

var flood = ratio.gt(threshold);

// -------------------------------
// STEP 8: Remove permanent water
// -------------------------------
var permanentWater = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
  .select('seasonality')
  .gte(10);

flood = flood.updateMask(permanentWater.not());

// -------------------------------
// STEP 9: Remove steep slopes
// -------------------------------
var dem = ee.Image('USGS/SRTMGL1_003');
var slope = ee.Terrain.slope(dem);

flood = flood.updateMask(slope.lt(5));

// -------------------------------
// STEP 10: Remove tiny noisy pixels
// -------------------------------
var connected = flood.selfMask().connectedPixelCount(100, true);
flood = flood.updateMask(connected.gte(8));

// -------------------------------
// STEP 11: Display results
// -------------------------------
Map.addLayer(before, {min: -25, max: 0}, 'Before Flood (VV)');
Map.addLayer(after, {min: -25, max: 0}, 'After Flood (VV)');
Map.addLayer(ratio, {min: 0.8, max: 2.0}, 'Backscatter Ratio');
Map.addLayer(flood.selfMask(), {palette: ['blue']}, 'Detected Flood Extent');

// Show study area
Map.addLayer(dhemaji, {color: 'yellow'}, 'Dhemaji Boundary');

// -------------------------------
// STEP 12: Calculate flooded area
// -------------------------------
var floodAreaImage = ee.Image.pixelArea().updateMask(flood);

var floodArea = floodAreaImage.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: dhemaji.geometry(),
  scale: 10,
  maxPixels: 1e10
});

var floodAreaSqKm = ee.Number(floodArea.get('area')).divide(1e6);

print('Estimated Flooded Area (sq km):', floodAreaSqKm);

// -------------------------------
// STEP 13: Print selected images info
// -------------------------------
print('Before image collection:', s1.filterDate(beforeStart, beforeEnd));
print('After image collection:', s1.filterDate(afterStart, afterEnd));