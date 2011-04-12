#!c:\Python25\python.exe
# -*- coding: utf-8 -*-
#***********************************************************************
#*
#***********************************************************************
#*                      All rights reserved                           **
#*
#*
#*                                                                    **
#*
#*
#*
#***********************************************************************
#* Purpose    : Calculating a inundation raster for the repetition times in
#*              RR_Resultaten
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): Inundatie
#*
#* Project    : Turtle-rural
#*
#* $Id$ <Id Name Rev must be added to svn:keywords>
#*
#* initial programmer :  Coen Nengerman
#* initial date       :  20060906
#**********************************************************************
__revision__ = "$Rev$"[6:-2]
version = "10.03.%s" % __revision__

NAME_SCRIPT = 'Inundatie'

import logging
log = logging.getLogger('nens.turtle.rural.inundatie')

# Import system modules
import sys
import os
import arcgisscripting
import shutil
import traceback
import nens.gp
import nens.tools
import turtlebase.general
import turtlebase.filenames
import turtlebase.arcgis
import turtlebase.spatial

# Create the Geoprocessor object
gp = arcgisscripting.create()

def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.filenames: %s" % turtlebase.filenames.__file__)
    log.debug("path turtlebase.spatial: %s" % turtlebase.spatial.__file__)
    log.debug("revision turtlebase.spatial: %s" % turtlebase.spatial.__revision__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)

def join_waterlevel_to_level_area(fc_level_area, area_ident, return_periods, waterlevel_dict):
    """
    join waterlevels from waterlevel_dict to level areas
    """
    log.debug(" - update records")
    for return_period in return_periods:
        if not turtlebase.arcgis.is_fieldname(gp, fc_level_area, "WS_%s" % return_period):
            log.debug(" - add field WS_%s" % return_period)
            gp.addfield_management(fc_level_area, "WS_%s" % return_period, "Double")

    row = gp.UpdateCursor(fc_level_area)

    for item in nens.gp.gp_iterator(row):
        item_id = item.GetValue(area_ident)
        log.debug(" - update waterlevel for %s" % item_id)
        if waterlevel_dict.has_key(item_id):
            for return_period in return_periods:
                waterlevel_value = float(waterlevel_dict[item_id]["ws_%s" % return_period]) / 100
                item.SetValue("WS_%s" % return_period, waterlevel_value)
        else:
            for return_period in return_periods:
                item.SetValue("WS_%s" % return_period, -999)
        row.UpdateRow(item)

def main(options, args):
    # Create the Geoprocessor object
    gp = arcgisscripting.create()
    gp.RefreshCatalog
    gp.OverwriteOutput = 1

    debuglogging()
    #----------------------------------------------------------------------------------------
    #create header for logfile
    log.info("")
    log.info("*********************************************************")
    log.info("Berekening Inundatie")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: "+str(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    # Check the settings for this script
    check_ini = turtlebase.general.missing_keys(options.ini, ["percentage_inundatie_stedelijk", "herhalingstijd_inundatie_stedelijk",
                                                              "cellsize", "percentage_inundatie_hoogwaardig",  "herhalingstijden",
                                                              "herhalingstijd_inundatie_hoogwaardig", "input_peilv_id",
                                                              "percentage_inundatie_akker", "herhalingstijd_inundatie_akker",
                                                              "percentage_inundatie_grasland", "herhalingstijd_inundatie_grasland"])
    if len(check_ini) > 0:
        log.error("missing keys in turtle-settings.ini file (header %s)" % NAME_SCRIPT)
        log.error(check_ini)
        sys.exit(1)

    #----------------------------------------------------------------------------------------
    # Create workspace
    workspace = options.turtle_ini['location_temp']

    turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

    if not os.path.isdir(workspace):
        os.makedirs(workspace)
    workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
    if errorcode == 1:
        log.error("failed to create a file geodatabase in %s" % workspace)

    #----------------------------------------------------------------------------------------
    #check inputfields
    log.info("Getting commandline parameters... ")
    for argv in sys.argv[1:]:
        turtlebase.filenames.check_filename(argv)

    if len(sys.argv) == 6:
        input_peilgebieden = sys.argv[1]
        input_waterlevel_table = sys.argv[2]
        input_ahn_raster = sys.argv[3]
        output_inundation = sys.argv[4]
        output_folder_waterlevel = sys.argv[5]
    else:
        log.error("Usage: python rural_inundatie.py <peilgebieden feature> <input_waterlevel_table> <input_ahn_raster> <output grid>")
        sys.exit(1)

    #----------------------------------------------------------------------------------------
    #check input parameters
    log.info('Checking presence of input files... ')
    if not(gp.exists(input_peilgebieden)):
        log.error("inputfile peilgebieden "+input_peilgebieden+" does not exist!")
        sys.exit(5)
    if not(gp.exists(input_waterlevel_table)):
        log.error("inputfile resultaten "+input_waterlevel_table+" does not exist!")
        sys.exit(5)
    if not(gp.exists(input_ahn_raster)):
        log.error("inputfile hoogtegrid "+input_ahn_raster+" does not exist!")
        sys.exit(5)

    log.info('input parameters checked... ')
    #----------------------------------------------------------------------------------------
    # Check geometry input parameters
    cellsize = options.ini['cellsize']

    log.info("Check geometry of input parameters")
    geometry_check_list = []

    log.debug(" - check level areas: %s" % input_peilgebieden)
    if gp.describe(input_peilgebieden).ShapeType != 'Polygon':
        log.error("Input level area is not a polygon feature class!")
        geometry_check_list.append(input_peilgebieden + " -> (Polygon)")

    log.debug(" - check ahn raster %s" % input_ahn_raster)
    if gp.describe(input_ahn_raster).DataType != 'RasterDataset':
        log.error("Input AHN is not a raster dataset")
        sys.exit(1)

    if gp.describe(input_ahn_raster).MeanCellHeight != float(cellsize):
        log.error("Cell size of AHN is %s, must be 25" % gp.describe(input_ahn_raster).MeanCellHeight)
        geometry_check_list.append(input_ahn_raster + " -> (Cellsize %s)" % cellsize)

    if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
        log.error("Input AHN is a floating point raster, for this script an integer is nessecary")
        geometry_check_list.append(input_ahn_raster + " -> (Integer)")

    if len(geometry_check_list) > 0:
        log.error("check input: %s" % geometry_check_list)
        sys.exit(2)

    log.info('input format checked... ')
    #----------------------------------------------------------------------------------------
    # Check required fields in input data
    log.info("Check required fields in input data")

    missing_fields = []

    # create return period list
    return_periods = options.ini['herhalingstijden'].split(", ")
    log.debug(" - return periods: %s" % return_periods)

    "<check required fields from input data, append them to list if missing>"
    if not turtlebase.arcgis.is_fieldname(gp, input_peilgebieden, options.ini['input_peilv_id']):
        log.debug(" - missing: %s in %s" % (options.ini['input_peilv_id'], input_peilgebieden))
        missing_fields.append("%s: %s" %(input_peilgebieden, options.ini['input_peilv_id']))

    if not turtlebase.arcgis.is_fieldname(gp, input_waterlevel_table, options.ini['input_peilv_id']):
        log.debug(" - missing: %s in %s" % (options.ini['input_peilv_id'], input_waterlevel_table))
        missing_fields.append("%s: %s" %(input_waterlevel_table, options.ini['input_peilv_id']))

    for return_period in return_periods:
        if not turtlebase.arcgis.is_fieldname(gp, input_waterlevel_table, "WS_%s" % return_period):
            log.debug(" - missing: %s in %s" % ("WS_%s" % return_period, input_waterlevel_table))
            missing_fields.append("%s: %s" % (input_waterlevel_table, "WS_%s" % return_period))

    if len(missing_fields) > 0:
        log.error("missing fields in input data: %s" % missing_fields)
        sys.exit(2)

    #----------------------------------------------------------------------------------------
    # Environments
    log.info("Setting environments")
    temp_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    log.debug(" - export level areas")
    gp.select_analysis(input_peilgebieden, temp_peilgebieden)

    gp.extent = gp.describe(temp_peilgebieden).extent #use extent from level areas

    # add waterlevel to peilgebieden
    log.info("Read waterlevels from table")
    waterlevel_dict = nens.gp.get_table(gp, input_waterlevel_table, primary_key=options.ini['input_peilv_id'].lower())
    join_waterlevel_to_level_area(temp_peilgebieden, options.ini['input_peilv_id'], return_periods, waterlevel_dict)

    #----------------------------------------------------------------------------------------
    log.info("A) Create rasters for waterlevels")
    # Create waterlevel rasters
    if output_folder_waterlevel == "#":
        output_folder_waterlevel = workspace_gdb

    for return_period in return_periods:
        log.info(" - create raster for ws_%s" % return_period)
        out_raster_dataset = output_folder_waterlevel + "/ws_%s" % return_period
        if not gp.exists(out_raster_dataset):
            gp.FeatureToRaster_conversion(temp_peilgebieden, "WS_%s" % return_period, out_raster_dataset, cellsize)
        else:
            log.error("output waterlevel raster already exists, delete this first or change output folder")
            sys.exit(1)

    #----------------------------------------------------------------------------------------
    log.info("B) Create Inundation raster")
    inundation_raster_list = []

    # create ahn ascii
    ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    log.debug("ahn ascii: %s" % ahn_ascii)
    gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

    # inundatie stedelijk
    return_period_urban = options.ini['herhalingstijd_inundatie_stedelijk']
    if options.ini['percentage_inundatie_stedelijk'] != "-":
        log.debug(" - create inundation urban")
        waterlevel = "%s/ws_%s" % (output_folder_waterlevel, return_period_urban)
        if gp.exists(waterlevel):
            inundation_urban = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(ahn_ascii, ahn_ascii, waterlevel, 1,
                                                        return_period_urban, inundation_urban,
                                                        workspace, use_lgn=False)
            inundation_raster_list.append(inundation_urban)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie hoogwaardige landbouw
    return_period_agriculture = options.ini['herhalingstijd_inundatie_hoogwaardig']
    if options.ini['percentage_inundatie_hoogwaardig'] != "-":
        log.debug(" - create inundation agriculture")
        waterlevel = "%s/ws_%s" % (output_folder_waterlevel, return_period_agriculture)
        if gp.exists(waterlevel):
            # Inundation with lgn
            inundation_agriculture = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(ahn_ascii, ahn_ascii, waterlevel,
                                                       2, return_period_agriculture,
                                                        inundation_agriculture, workspace,
                                                        use_lgn=False)
            inundation_raster_list.append(inundation_agriculture)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie akkerbouw
    return_period_rural = options.ini['herhalingstijd_inundatie_akker']
    if options.ini['percentage_inundatie_akker'] != "-":
        log.debug(" - create inundation rural")
        waterlevel = "%s/ws_%s" % (output_folder_waterlevel, return_period_rural)
        if gp.exists(waterlevel):
            inundation_rural = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(ahn_ascii, ahn_ascii, waterlevel,
                                                        3, return_period_rural, inundation_rural,
                                                        workspace, use_lgn=False)
            inundation_raster_list.append(inundation_rural)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie grasland
    return_period_grass = options.ini['herhalingstijd_inundatie_grasland']
    if options.ini['percentage_inundatie_grasland'] != "-":
        log.debug(" - create inundation grass")
        waterlevel = "%s/ws_%s" % (output_folder_waterlevel, return_period_grass)
        if gp.exists(waterlevel):
            inundation_grass = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(ahn_ascii, ahn_ascii, waterlevel,
                                                       4, return_period_grass, inundation_grass,
                                                        workspace, use_lgn=False)
            inundation_raster_list.append(inundation_grass)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    if len(inundation_raster_list) > 1:
        log.info(" - merge inundation rasters")
        output_inundation_exists = turtlebase.spatial.merge_ascii(inundation_raster_list, output_inundation, workspace)
    else:
        log.error("there are no inundation rasters available")

   #----------------------------------------------------------------------------------------
    # Delete temporary workspace geodatabase & ascii files
    try:
        log.debug("delete temporary workspace: %s" % workspace_gdb)
        gp.delete(temp_peilgebieden)
        gp.delete(workspace_gdb)

        log.info("workspace deleted")
    except:
        log.warning("failed to delete %s" % workspace_gdb)

    log.debug("delete temporary ascii-files")
    file_list = os.listdir(workspace)
    for file in file_list:
        if file[-4:] == '.asc':
            log.debug("remove %s" % os.path.join(workspace, file))
            os.remove(os.path.join(workspace, file))

    log.info("*********************************************************")
    log.info("Finished")
    log.info("*********************************************************")

    del gp
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    from optparse import OptionParser
    parser = OptionParser()

    (options, args) = parser.parse_args()

    turtlebase.general.extend_options_for_turtle(options, "%s" % NAME_SCRIPT,
                              gpHandlerLevel = logging.INFO,
                              fileHandlerLevel = logging.DEBUG,
                              consoleHandlerLevel = None,
                              root_settings = 'turtle-settings.ini')

    # cProfile for testing
    ##import cProfile
    ##cProfile.run('main(options, args)')
    main(options, args)


