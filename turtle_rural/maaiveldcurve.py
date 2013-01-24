from osgeo import ogr
from osgeo import gdal

import numpy as np

import os
import shutil
import tempfile
import subprocess

def get_mapsheets(mask_fc, i_mapsheets, mapsheets_key, workspace):
    """
    temporary fix for users with gdal 1.6 (arcgis 9.3)
    locally import of ArcGIS libraries
    """
    import arcgisscripting
    import turtlebase.arcgis
    gp = arcgisscripting.create()
    mapsheets = []
    
    gp.MakeFeatureLayer_management(mask_fc, "mask_lyr")
    gp.MakeFeatureLayer_management(i_mapsheets, "mapsheets_lyr")
    gp.SelectLayerByLocation_management("mapsheets_lyr","INTERSECT","mask_lyr","#","NEW_SELECTION")
    
    mapsheets_tmp = turtlebase.arcgis.get_random_file_name(workspace, '.shp')
    gp.Select_analysis("mapsheets_lyr", mapsheets_tmp)
    rows = gp.searchcursor(mapsheets_tmp)
    row = rows.next()
    while row:
        mapsheets_value = row.GetValue(mapsheets_key)
        ext = row.Shape.extent
        mapsheets.append((mapsheets_value, ext))
        row = rows.next()

    return mapsheets


def get_mapsheets_gdal(mask_fc, i_mapsheets, mapsheets_key):
    """
    does not work with gdal 1.6, but is made for gdal >1.8 (does not need ArcGIS libraries)
    """
    # Get the mask geometry, note that multifeature masks are not implemented.
    mask_dataset = ogr.Open(mask_fc)
    mask_layer = mask_dataset[0]
    mask_feature = mask_layer[0]
    mask = mask_feature.geometry()

    # Determine which mapsheets intersect with mask
    mapsheets = []
    mapsheets_dataset = ogr.Open(i_mapsheets)
    for mapsheets_layer in mapsheets_dataset:
        for mapsheets_feature in mapsheets_layer:
            if mapsheets_feature.geometry().Intersects(mask):
                mapsheets.append(mapsheets_feature[mapsheets_key])
    return mapsheets


def get_array_from_grid(mask_fc, mapsheet, tiff_template, input_grid, extent, workspace, NODATA=-9999):
    """ Return height array with values outside mask set to NODATA. """
    output_tiff = os.path.join(workspace, mapsheet)
    turtle_base_dir = os.environ['TURTLE_BASE_DIR']
    
    gdal_dir = os.path.join(turtle_base_dir, 'gdal')
    gdalwarp_exe = "%s" % os.path.join(gdal_dir, 'gdalwarp.exe')

    if not os.path.isfile(os.path.join(gdal_dir, 'gdalwarp.exe')):
        raise Exception('gdalwarp.exe not found')

    args = [gdalwarp_exe, input_grid, output_tiff, "-cutline", mask_fc, "-te", extent, "-ts", "2000", "2500", "-dstnodata", NODATA, "-q"]
    proc = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=proc.communicate()
    exit_code=proc.wait()
    
    if exit_code:
        raise RuntimeError(stderr)
    else:
        print stdout

    # Read created tiff and close dataset
    output_dataset = gdal.Open(output_tiff)
    output_array = output_dataset.ReadAsArray()
    output_dataset = None
    os.remove(output_tiff)
    
    return output_array



def reclassify_array(array, NODATA=-9999):
    """
    """
    conversion = {1:2, 2:3, 3:4, 4:5, 5:0}
    nbw_array = np.ones(array.shape) * NODATA
    
    for k, v in conversion.items():
        nbw_array[array == k] = v
         
    return nbw_array
    
    
def get_groundcurve(histogram, bins_right):
    """ Return x, y of ground curve. """
    percentile_x = np.cumsum(histogram) / float(histogram.sum()) * 100
    percentile_y = bins_right  # right edges of bins.
    curve_x = np.arange(0, 101)
    curve_y = np.interp(curve_x, percentile_x, percentile_y)
    return curve_x, curve_y


def main(mask_fc, mapsheets, landgebruik, hoogtekaart, streefpeil, conversion, workspace):
    tiff_template = os.path.join(workspace, '%(mapsheet)s.tiff')
    
    mapsheets_key = 'BLADNR'
    NODATA = -9999
    
    # Bin settings
    BIN_MIN = streefpeil
    BIN_MAX = 500
    BIN_STEP = 1
    
    LANDUSE_EXCLUDE = (0, 255)

    # Initialize the histogram
    bins = np.arange(BIN_MIN, BIN_MAX + BIN_STEP, BIN_STEP)
    bins_right = bins[1:]
    histogram = np.zeros(bins.size - 1, dtype=np.uint64)
    histogram_per_landuse = {}

    # Loop mapsheets and add to histogram
    for (mapsheet, extent) in get_mapsheets(mask_fc, mapsheets, mapsheets_key, workspace):
        # Get data and index mask
        height_array = get_array_from_grid(mask_fc, mapsheet, tiff_template, hoogtekaart, extent, workspace, NODATA=NODATA)
        index_mask = height_array != NODATA
        
        # Determine histogram for this mapsheet and add to total histogram
        mapsheet_histogram = np.histogram(height_array[index_mask], bins)[0]
        histogram += mapsheet_histogram
        
        if landgebruik != '#':
            landuse_array = get_array_from_grid(mask_fc, mapsheet, tiff_template, landgebruik, extent, workspace, NODATA=NODATA)
            nbw_array = reclassify_array(landuse_array, NODATA=-9999)
            # Determine histogram per landuse
            mapsheet_histogram_per_landuse = {}
            landuses = np.unique(nbw_array[index_mask])
    
            for landuse in landuses:
                if landuse in LANDUSE_EXCLUDE:
                    continue
                index_landuse = nbw_array == landuse
                mapsheet_histogram_per_landuse[int(landuse)] = np.histogram(
                    height_array[np.logical_and(index_mask, index_landuse)], bins,
                )[0]
                if landuse in histogram_per_landuse:
                    histogram_per_landuse[landuse] += mapsheet_histogram_per_landuse[landuse]
                else:
                    histogram_per_landuse[landuse] = mapsheet_histogram_per_landuse[landuse]
        else:
            histogram_per_landuse[0] = np.histogram(
                    height_array[height_array != NODATA], bins=bins)[0]

    # Determine ground curves
    groundcurve_per_landuse = {}
    for landuse, histogram in histogram_per_landuse.iteritems():
        groundcurve_per_landuse[landuse] = get_groundcurve(histogram, bins_right)

    return groundcurve_per_landuse


if __name__ == '__main__':
    exit(main())
