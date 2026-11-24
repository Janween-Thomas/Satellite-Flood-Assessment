
// ==============================================
// PROJECT: SATELLITE-BASED FLOOD MAPPING
// PHASE 3: FLOOD IMPACT ASSESSMENT
// STUDY AREA: DHEMAJI, ASSAM
// ==============================================


// STEP 1: Load Dhemaji district

var districts = ee.FeatureCollection(
  'FAO/GAUL/2015/level2'
);

var dhemaji = districts
  .filter(ee.Filter.eq('ADM1_NAME', 'Assam'))
  .filter(ee.Filter.eq('ADM2_NAME', 'Dhemaji'));

Map.centerObject(dhemaji, 9);


// STEP 2: Load Sentinel-1 imagery

var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(dhemaji)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains(
    'transmitterReceiverPolarisation', 'VV'
  ))
  .filter(ee.Filter.eq(
    'orbitProperties_pass', 'ASCENDING'
  ))
  .filter(ee.Filter.eq(
    'relativeOrbitNumber_start', 143
  ))
  .select('VV');


// STEP 3: Select before and after images

var beforeCollection = s1.filterDate(
  '2024-06-23', '2024-06-25'
);

var afterCollection = s1.filterDate(
  '2024-07-29', '2024-07-31'
);

print('Before image count:', beforeCollection.size());
print('After image count:', afterCollection.size());

var before = beforeCollection.median()
  .clip(dhemaji);

var after = afterCollection.median()
  .clip(dhemaji);


// STEP 4: Convert dB to linear values

var beforeLinear = ee.Image.constant(10)
  .pow(before.divide(10));

var afterLinear = ee.Image.constant(10)
  .pow(after.divide(10));


// STEP 5: Calculate backscatter ratio

var ratio = beforeLinear.divide(afterLinear);


// STEP 6: Detect potential flood pixels

var threshold = 1.25;

var flood = ratio.gt(threshold);


// STEP 7: Remove permanent water

var permanentWater = ee.Image(
  'JRC/GSW1_4/GlobalSurfaceWater'
)
.select('seasonality')
.gte(10);

flood = flood.updateMask(permanentWater.not());


// STEP 8: Remove steep terrain

var dem = ee.Image('USGS/SRTMGL1_003');

var slope = ee.Terrain.slope(dem);

flood = flood.updateMask(slope.lt(5));


// STEP 9: Remove small isolated pixels

var connected = flood.selfMask()
  .connectedPixelCount(100, true);

flood = flood.updateMask(connected.gte(8));

var floodMask = flood.selfMask();


// STEP 10: Load ESA WorldCover

var landcover = ee.ImageCollection(
  'ESA/WorldCover/v200'
)
.first()
.select('Map')
.clip(dhemaji);


// STEP 11: Identify cropland

// ESA WorldCover class 40 = Cropland

var cropland = landcover.eq(40);


// STEP 12: Identify built-up land

// ESA WorldCover class 50 = Built-up

var builtup = landcover.eq(50);


// STEP 13: Identify affected cropland

var affectedCropland = floodMask
  .updateMask(cropland);


// STEP 14: Identify affected built-up land

var affectedBuiltup = floodMask
  .updateMask(builtup);


// STEP 15: Calculate area using pixelArea

var pixelArea = ee.Image.pixelArea();

var totalFloodArea = pixelArea
  .updateMask(floodMask)
  .rename('total_flood_m2');

var cropFloodArea = pixelArea
  .updateMask(affectedCropland)
  .rename('cropland_m2');

var builtFloodArea = pixelArea
  .updateMask(affectedBuiltup)
  .rename('builtup_m2');


// STEP 16: Combine area layers

var areaLayers = totalFloodArea
  .addBands(cropFloodArea)
  .addBands(builtFloodArea);


// STEP 17: Calculate areas within Dhemaji

var statistics = areaLayers.reduceRegion({
  reducer: ee.Reducer.sum(),
  geometry: dhemaji.geometry(),
  scale: 10,
  maxPixels: 1e10,
  tileScale: 4
});


// STEP 18: Convert square metres to sq km

var floodKm2 = ee.Number(
  statistics.get('total_flood_m2')
).divide(1e6);

var cropKm2 = ee.Number(
  statistics.get('cropland_m2', 0)
).divide(1e6);

var builtKm2 = ee.Number(
  statistics.get('builtup_m2', 0)
).divide(1e6);


// STEP 19: Print results

print('================================');

print('FLOOD IMPACT ASSESSMENT RESULTS');

print('================================');

print('Total Potential Flood Area (km2):', floodKm2);

print('Flooded Cropland Area (km2):', cropKm2);

print('Flooded Built-up Area (km2):', builtKm2);


// STEP 20: Display flood extent

Map.addLayer(
  floodMask,
  {palette: ['0066FF']},
  'Potential Flood Extent',
  true,
  0.8
);


// STEP 21: Display affected cropland

Map.addLayer(
  affectedCropland,
  {palette: ['FF00FF']},
  'Affected Cropland',
  false
);


// STEP 22: Display affected built-up areas

Map.addLayer(
  affectedBuiltup,
  {palette: ['FF0000']},
  'Affected Built-up Land',
  false
);


// STEP 23: Add transparent district boundary

var boundary = dhemaji.style({
  color: 'FFFF00',
  fillColor: '00000000',
  width: 3
});

Map.addLayer(
  boundary,
  {},
  'Dhemaji Boundary'
);

// ==============================================
// STEP 24: EXPORT FLOOD AND IMPACT DATA
// ==============================================

// Use a projected coordinate reference system
// suitable for the Dhemaji study area.
var exportCRS = 'EPSG:32646';

// Mask pixels where either SAR composite
// has no valid observation.
var validSAR = before.mask().and(after.mask());

// Exported raster values:
// 1   = detected potential flood
// 0   = valid observation, not detected as flood
// 255 = no data or outside study area

var exportFlood = floodMask
  .unmask(0)
  .updateMask(validSAR)
  .clip(dhemaji)
  .rename('flood')
  .toByte()
  .unmask(255);

// Export the flood mask as GeoTIFF.
Export.image.toDrive({
  image: exportFlood,
  description: 'Dhemaji_Flood_Mask_2024',
  folder: 'FloodWatch_Exports',
  fileNamePrefix: 'dhemaji_flood_mask_2024',
  region: dhemaji.geometry(),
  scale: 10,
  crs: exportCRS,
  maxPixels: 1e10,
  fileFormat: 'GeoTIFF',
  formatOptions: {
    noData: 255
  }
});


// ==============================================
// STEP 25: EXPORT ESA WORLDCOVER
// ==============================================

var exportLandcover = landcover
  .rename('landcover')
  .toByte()
  .unmask(255);

Export.image.toDrive({
  image: exportLandcover,
  description: 'Dhemaji_Landcover_2021',
  folder: 'FloodWatch_Exports',
  fileNamePrefix: 'dhemaji_landcover_2021',
  region: dhemaji.geometry(),
  scale: 10,
  crs: exportCRS,
  maxPixels: 1e10,
  fileFormat: 'GeoTIFF',
  formatOptions: {
    noData: 255
  }
});


// ==============================================
// STEP 26: EXPORT STATISTICS AS CSV
// ==============================================

var resultFeature = ee.Feature(null, {
  district: 'Dhemaji',
  state: 'Assam',
  before_date: '2024-06-24',
  after_date: '2024-07-30',
  algorithm: 'Sentinel-1 VV ratio threshold',
  ratio_threshold: threshold,
  landcover_year: 2021,
  potential_flood_km2: floodKm2,
  exposed_cropland_km2: cropKm2,
  exposed_builtup_km2: builtKm2
});

var resultsTable = ee.FeatureCollection([
  resultFeature
]);

Export.table.toDrive({
  collection: resultsTable,
  description: 'Dhemaji_Impact_Statistics_2024',
  folder: 'FloodWatch_Exports',
  fileNamePrefix: 'dhemaji_impact_statistics_2024',
  fileFormat: 'CSV',
  selectors: [
    'district',
    'state',
    'before_date',
    'after_date',
    'algorithm',
    'ratio_threshold',
    'landcover_year',
    'potential_flood_km2',
    'exposed_cropland_km2',
    'exposed_builtup_km2'
  ]
});

print('Export tasks created. Open the Tasks tab.');

