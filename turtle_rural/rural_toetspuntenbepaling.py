#!/usr/bin/python
# -*- coding: utf-8 -*-
#***********************************************************************
# this program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# this program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the nens libraray.  If not, see
# <http://www.gnu.org/licenses/>.
#
#***********************************************************************
#* Purpose    : Creating an s-curve for the unpaved areas, using gridbewerking.exe
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): Maaiveldcurve
#*
#* Project    : Turtle-rural
#*
#* $Id$ <Id Name Rev must be added to svn:keywords>
#*
#* initial programmer :  Coen Nengerman
#* initial date       :  20100323
#**********************************************************************
__revision__ = "$Rev$"[6:-2]
version = '10.03.%s' % __revision__

NAME_SCRIPT = "toetspunten"

import logging
log = logging.getLogger('nens.turtle.rural.%s' % NAME_SCRIPT)

# Import system modules
import sys
import os
import arcgisscripting
import nens.gp
import turtlebase.arcgis
import turtlebase.filenames
import turtlebase.general
import turtlebase.spatial

# Create the Geoprocessor object
gp = arcgisscripting.create()

def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.filenames: %s" % turtlebase.filenames.__file__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)

def create_output_table(output_table, area_ident, toetspunten_fields):
    """
    creates a new table when the table does not exist..
    adds all fields thats are needed for writing output
    """
    if not gp.exists(output_table):
        gp.CreateTable_management(os.path.dirname(output_table), os.path.basename(output_table))

    for fieldname in toetspunten_fields:
        if not turtlebase.arcgis.is_fieldname(gp, output_table, fieldname):
            gp.addfield_management(output_table, fieldname, "Double")

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'SOURCE'):
        gp.addfield_management(output_table, 'SOURCE', "Text", "#", "#", '256')

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'DATE_TIME'):
        gp.addfield_management(output_table, 'DATE_TIME', "Text", "#", "#", '40')

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'COMMENTS'):
        gp.addfield_management(output_table, 'COMMENTS', "Text", "#", "#", '256')

def add_integer_ident(temp_level_area, id_int_field, area_ident):
    """
    """
    log.debug(" - update records")
    if not turtlebase.arcgis.is_fieldname(gp, temp_level_area, id_int_field):
        log.debug(" - add field %s" % id_int_field)
        gp.addfield_management(temp_level_area, id_int_field, "Short")

    row = gp.UpdateCursor(temp_level_area)
    x = 1
    area_id_dict = {}

    for item in nens.gp.gp_iterator(row):
        item_id = item.GetValue(area_ident)
        if area_id_dict.has_key(item_id):
            item.SetValue(id_int_field, area_id_dict[item_id][id_int_field])
        else:
            item.SetValue(id_int_field, x)
            area_id_dict[item_id] = {id_int_field: x}
            x += 1
        row.UpdateRow(item)

    return area_id_dict

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
    log.info("Toetspuntenbepaling... ")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: %s" %(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    # Check the settings for this script
    check_ini = turtlebase.general.missing_keys(options.ini, ['input_peilgebied_ident', 'field_streefpeil', 'id_int',
                                                              'lgn_conv_ident', 'input_field_k5', 'cellsize'])
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
    use_onderbemalingen = False
    if len(sys.argv) == 8:
        input_level_area_fc = sys.argv[1] #shp
        input_level_area_table = sys.argv[2] #table [ZOMERPEIL],[WINTERPEIL]
        input_ahn_raster = sys.argv[3] #aux
        input_lgn_raster = sys.argv[4] #aux
        input_lgn_conversion = sys.argv[5] #csv
        input_onderbemalingen = sys.argv[6]
        if input_onderbemalingen == "#":
            use_onderbemalingen = False
        else:
            use_onderbemalingen = True
        output_file = sys.argv[7] #shp
    else:
        log.error("Usage: python toetspuntenbepaling.py <ahn-file> <lgn-file> <onderbemalingen-optional> <peilgebieden-feature> <peilvakgegevens-table> <conversietabel> <outputfile-HydroBase>")
        sys.exit(1)

    #----------------------------------------------------------------------------------------
    #check input parameters
    log.info('Checking presence of input files... ')
    if not(gp.exists(input_level_area_fc)):
        log.error("inputfile peilgebieden "+input_peilgebieden+" does not exist!")
        sys.exit(5)
    if not(gp.exists(input_level_area_table)):
        log.error("inputfile peilvakgegevens "+input_level_area_table+" does not exist!")
        sys.exit(5)
    if (use_onderbemalingen and not(gp.exists(input_onderbemalingen))):
        log.error("inputfile onderbemalingen "+input_onderbemalingen+" does not exist!")
        sys.exit(5)

    log.info('input parameters checked... ')

    #----------------------------------------------------------------------------------------
    # Check geometry input parameters
    cellsize = options.ini['cellsize']

    log.info("Check geometry of input parameters")
    geometry_check_list = []

    log.debug(" - check level area: %s" % input_level_area_fc)
    if gp.describe(input_level_area_fc).ShapeType != 'Polygon':
        errormsg = "%s is not a polygon feature class!" % input_level_area_fc
        log.error(errormsg)
        geometry_check_list.append(errormsg)

    if turtlebase.arcgis.check_whether_shapefile_has_empty_attribute_table(gp, input_level_area_fc):
        errormsg = "input '%s' is empty" % input_level_area_fc
        log.error(errormsg)
        sys.exit(1)

    if turtlebase.arcgis.check_whether_shapefile_has_empty_attribute_table(gp, input_level_area_table):
        errormsg = "input '%s' is empty" % input_level_area_table
        log.error(errormsg)
        sys.exit(1)

    if use_onderbemalingen:
        if turtlebase.arcgis.check_whether_shapefile_has_empty_attribute_table(gp, input_onderbemalingen):
            errormsg = "input '%s' is empty" % input_onderbemalingen
            log.error(errormsg)
            sys.exit(1)

    log.debug(" - check ahn raster %s" % input_ahn_raster)
    if gp.describe(input_ahn_raster).DataType != 'RasterDataset':
        log.error("Input AHN is not a raster dataset")
        sys.exit(1)

    if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
        errormsg = "Input AHN is a floating point raster, for this script an integer is nessecary"
        log.error(errormsg)
        geometry_check_list.append(errormsg)

    if gp.describe(input_ahn_raster).MeanCellHeight != float(cellsize):
        errormsg = "Cell size of AHN is %s, must be 25" % gp.describe(input_ahn_raster).MeanCellHeight
        log.error(errormsg)
        geometry_check_list.append(errormsg)

    log.debug(" - check ahn raster %s" % input_lgn_raster)
    if gp.describe(input_lgn_raster).DataType != 'RasterDataset':
        log.error("Input LGN is not a raster dataset")
        sys.exit(1)

    if gp.describe(input_lgn_raster).PixelType[0] not in ['U', 'S']:
        errormsg = "Input LGN is a floating point raster, for this script an integer is nessecary"
        log.error(errormsg)
        geometry_check_list.append(errormsg)

    if gp.describe(input_lgn_raster).MeanCellHeight != float(cellsize):
        errormsg = "Cell size of LGN is %s, must be 25" % gp.describe(input_lgn_raster).MeanCellHeight
        log.error(errormsg)
        geometry_check_list.append(errormsg)

    if len(geometry_check_list) > 0:
        log.error("check input: %s" % geometry_check_list)
        sys.exit(2)

    #----------------------------------------------------------------------------------------
    # Check required fields in input data
    log.info("Check required fields in input data")

    missing_fields = []

    "<check required fields from input data, append them to list if missing>"
    if not turtlebase.arcgis.is_fieldname(gp, input_level_area_fc, options.ini['input_peilgebied_ident']):
        log.debug(" - missing: %s in %s" % (options.ini['input_peilgebied_ident'], input_level_area_fc))
        missing_fields.append("%s: %s" %(input_level_area_fc, options.ini['input_peilgebied_ident']))

    if not turtlebase.arcgis.is_fieldname(gp, input_level_area_table, options.ini['input_peilgebied_ident']):
        log.debug(" - missing: %s in %s" % (options.ini['input_peilgebied_ident'], input_level_area_table))
        missing_fields.append("%s: %s" %(input_level_area_table, options.ini['input_peilgebied_ident']))

    if not turtlebase.arcgis.is_fieldname(gp, input_level_area_table, options.ini['field_streefpeil']):
        log.debug(" - missing: %s in %s" % (options.ini['field_streefpeil'], input_level_area_table))
        missing_fields.append("%s: %s" %(input_level_area_table, options.ini['field_streefpeil']))

    if len(missing_fields) > 0:
        log.error("missing fields in input data: %s" % missing_fields)
        sys.exit(2)

    #----------------------------------------------------------------------------------------
    # Environments
    log.info("Set environments")
    temp_level_area = os.path.join(workspace_gdb, "peilgebieden")
    if input_level_area_fc.endswith(".shp"):
        log.info("Copy features of level areas to workspace")
        gp.select_analysis(input_level_area_fc, temp_level_area)
    else:
        log.info("Copy level areas to workspace")
        gp.copy_management(input_level_area_fc, temp_level_area)
    gp.extent = gp.describe(temp_level_area).extent #use extent from level area

    #----------------------------------------------------------------------------------------
    # Create K5 LGN
    log.info("Translate LGN to NBW-classes")
    lgn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    lgn_k5_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")

    gp.RasterToASCII_conversion(input_lgn_raster, lgn_ascii)

    if input_lgn_conversion != '#':
        reclass_dict = nens.gp.get_table(gp, input_lgn_conversion,
                                         primary_key=options.ini['lgn_conv_ident'].lower())
        turtlebase.spatial.reclass_lgn_k5(lgn_ascii, lgn_k5_ascii, reclass_dict)
    else:
        turtlebase.spatial.reclass_lgn_k5(lgn_ascii, lgn_k5_ascii)
    #----------------------------------------------------------------------------------------
    # create ahn ascii
    log.info("Create ascii from ahn")

    ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    log.debug("ahn ascii: %s" % ahn_ascii)
    gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

    #----------------------------------------------------------------------------------------
    # Change ahn and lgn if use_ondermalingen == True
    if use_onderbemalingen:
        log.info("Cut out level deviations")
        gridcode_fieldname = "GRIDCODE"
        if not turtlebase.arcgis.is_fieldname(gp, input_onderbemalingen, gridcode_fieldname):
            log.debug(" - add field %s" % gridcode_fieldname)
            gp.addfield_management(input_onderbemalingen, gridcode_fieldname, "Short")

        row = gp.UpdateCursor(input_onderbemalingen)
        for item in nens.gp.gp_iterator(row):
            item.SetValue(gridcode_fieldname, 1)
            row.UpdateRow(item)

        onderbemaling_raster = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.FeatureToRaster_conversion(input_onderbemalingen, gridcode_fieldname, onderbemaling_raster, cellsize)

        onderbemaling_asc = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        gp.RasterToASCII_conversion(onderbemaling_raster, onderbemaling_asc)

        ahn_ascii = turtlebase.spatial.cut_out_onderbemaling(ahn_ascii, onderbemaling_asc, workspace)
        lgn_k5_ascii = turtlebase.spatial.cut_out_onderbemaling(lgn_k5_ascii, onderbemaling_asc, workspace)
    #----------------------------------------------------------------------------------------
    # Add ID Int to level area
    log.info("Create level area ascii")
    area_id_dict = add_integer_ident(temp_level_area, options.ini['id_int'].lower(), options.ini['input_peilgebied_ident'])

    out_raster_dataset = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.FeatureToRaster_conversion(temp_level_area, options.ini['id_int'], out_raster_dataset, cellsize)

    id_int_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    log.debug("id_int_ascii: %s" % id_int_ascii)
    gp.RasterToASCII_conversion(out_raster_dataset, id_int_ascii)

    #----------------------------------------------------------------------------------------
    log.info("Read targetlevel table")
    area_level_dict = nens.gp.get_table(gp, input_level_area_table, primary_key=options.ini['input_peilgebied_ident'].lower())
    target_level_dict = {}

    for k,v in area_level_dict.items():
        if area_id_dict.has_key(k):
            id_int = area_id_dict[k][options.ini['id_int'].lower()]
            target_level_dict[id_int] = {'targetlevel': v[options.ini['field_streefpeil'].lower()], 'gpgident': k}

    toetspunten_fields = ["DFLT_I_ST", "DFLT_I_HL", "DFLT_I_AK", "DFLT_I_GR", "DFLT_O_ST", "DFLT_O_HL", "DFLT_O_AK", "DFLT_O_GR",
                          "MTGMV_I_ST", "MTGMV_I_HL", "MTGMV_I_AK", "MTGMV_I_GR", "MTGMV_O_ST", "MTGMV_O_HL", "MTGMV_O_AK", "MTGMV_O_GR"]
    #----------------------------------------------------------------------------------------
    log.info("calculate toetspunten")
    #mv_procent_str = options.ini['mv_procent']
    #field_range = mv_procent_str.split(', ')
    #scurve_dict = turtlebase.spatial.create_scurve(ahn_ascii, id_int_ascii, target_level_dict, field_range)
    toetspunten_dict = turtlebase.spatial.calculcate_toetspunten(ahn_ascii, lgn_k5_ascii, id_int_ascii,
                                                                 toetspunten_fields, target_level_dict, onderbemaling="#")
    #----------------------------------------------------------------------------------------
    log.info("Create output table")
    create_output_table(output_file, options.ini['input_peilgebied_ident'], toetspunten_fields)
    #----------------------------------------------------------------------------------------
    # Add metadata
    import time
    date_time_str = time.strftime("%d %B %Y %H:%M:%S")
    source = input_ahn_raster

    for area_id,values in toetspunten_dict.items():
        toetspunten_dict[area_id]['date_time'] = date_time_str
        toetspunten_dict[area_id]['source'] = source

    #----------------------------------------------------------------------------------------
    # Write results to output table
    log.info("Write results to output table")
    turtlebase.arcgis.write_result_to_output(output_file, options.ini['input_peilgebied_ident'].lower(), toetspunten_dict)

    #----------------------------------------------------------------------------------------
    # Delete temporary workspace geodatabase & ascii files
    try:
        log.debug("delete temporary workspace: %s" % workspace_gdb)
        gp.delete(workspace_gdb)
        log.info("workspace deleted")
    except:
        log.debug("failed to delete %s" % workspace_gdb)

    tempfiles = os.listdir(workspace)
    for tempfile in tempfiles:
        if tempfile.endswith('.asc'):
            try:
                os.remove(os.path.join(workspace, tempfile))
            except Exception, e:
                log.debug(e)

    log.info("*********************************************************")
    log.info("Finished")
    log.info("*********************************************************")

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
