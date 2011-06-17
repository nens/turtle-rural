import sys
sys.path[0:0] = [
  'c:\\python_ontwikkeling\\turtle-rural',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\eazysvn-1.12.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\coverage-3.4-py2.6-win32.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pep8-0.6.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\zest.releaser-3.20-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\setuptools-0.6c11-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\turtlebase',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pkginfo-0.8-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\py-nens',
  'c:\\python26\\arcgis10.0\\lib\\site-packages',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\mock-0.7.0-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pil-1.1.7-py2.6-win32.egg',
  ]
import os
import arcpy
import traceback
import turtlebase.arcgis
import arcgisscripting
gp = arcgisscripting.create

#locatie_data = "D:\\1103-375_deel1\\ahn2_05_non\\geogegevens\\raster"
#locatie_data = "c:/gistemp/test"
locatie_data = sys.argv[1]
#output_location = "c:/gistemp/test/output"
output_location = sys.argv[2]

if not os.path.isdir(output_location):
    os.makedirs(output_location)

def find_raster_files(location):
    raster_files_found = []
    for folder in os.listdir(location):
        arcpy.env.workspace = os.path.join(location, folder)
        raster_files = arcpy.ListRasters()
        if not raster_files is None:
            if len(raster_files) > 0:
                for raster in raster_files:
                    raster_files_found.append(os.path.join(location, folder, raster))
    return raster_files_found


def convert_float_raster_to_int(raster_files, workspace, i, mosaic):
    """
    convert each raster in raster_files list to a integer raster
    first multiply with 1000 to prevent to lose data (meter > millimeter)
    """
    integer_rasters = []
    arcpy.env.workspace = workspace
    for raster in raster_files:
        if os.path.basename(raster).startswith("n%s" % i):
            arcpy.AddMessage("Converting % s" % raster)
            rastername = os.path.basename(raster)
            temp_raster = os.path.join(workspace, rastername)
            times_raster = arcpy.sa.Times(raster, 1000)
            int_raster = arcpy.sa.Int(times_raster)
            int_raster.save(temp_raster)
            integer_rasters.append(temp_raster)

            arcpy.AddRastersToMosaicDataset_management(mosaic, '32_BIT_SIGNED', temp_raster)

    return integer_rasters

#---------------------------------------------------------------------
# Create workspace
workspace = "c:\\gisproject\\zzl\\ahn_zzl.gdb"
mosaic = "C:\\GISPROJECT\\ZZL\\ahn_zzl.gdb\\mosaic_zzl"

raster_files_found = find_raster_files(locatie_data)

try:
    for i in range(100):
        if i < 10:
            i = "0%s" % str(i)
        else:
            i = str(i)

        raster_dataset_name = "rasters_%s" % i
        arcpy.CreateRasterDataset_management(workspace, raster_dataset_name, "#", '32_BIT_SIGNED')
        workspace_i = os.path.join(workspace, raster_dataset_name)
        integer_rasters = convert_float_raster_to_int(raster_files_found, workspace_i, i, mosaic)
        arcpy.AddMessage(integer_rasters)


        #rastername = "ahn2_ % s" % i
        #if integer_rasters:
            #if len(integer_rasters) > 1:

                #arcpy.AddMessage("Merging rasters, this can take a while")
                #arcpy.AddMessage(integer_rasters)
                #arcpy.MosaicToNewRaster_management(integer_rasters, output_location, rastername, "#", "16_BIT_SIGNED", "0.5", 1)

except:
    arcpy.AddError(traceback.format_exc())
    sys.exit(1)

print "Finished"
