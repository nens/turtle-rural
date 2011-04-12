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
#* Purpose    : Rainfall Runoff + Channel Flow results
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): NaverwerkingRRCF
#*
#* Project    : Turtle
#*
#* $Id$ <Id Name Rev must be added to svn:keywords>
#*
#* $Name:  $
#*
#* initial programmer :  Coen Nengerman
#* initial date       :  20100222
#**********************************************************************
__revision__ = "$Rev$"[6:-2]
version = '10.03.%s' % __revision__

import logging
log = logging.getLogger('nens.turtle.rural.rrcfnaverwerking')

# Import system modules
import sys
import os
import time
import arcgisscripting
import nens.tools
import nens.gp
import turtlebase.arcgis
import turtlebase.voronoi
import turtlebase.spatial
import turtlebase.filenames
import turtlebase.general

# Create the Geoprocessor object
gp = arcgisscripting.create()

def translate_dict(input_dict, translate_field, area_field):
    output_dict = turtlebase.voronoi.defaultdict(dict)

    for row in input_dict:
        gpgid = row['gpgident']
        if gpgid != '':
            output_dict[gpgid][row[translate_field]] = row[area_field]

    return output_dict

def toetsing(input_percentage, allowable_percentage, no_data_value):
    """
    """
    if input_percentage == no_data_value:
        return  9
    elif input_percentage >= allowable_percentage:
        return 1
    else:
        return 0

def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path tools: %s" % nens.tools.__file__)
    log.debug("revision tools: %s" % nens.tools.__revision__)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.voronoi: %s" % turtlebase.voronoi.__file__)
    log.debug("path turtlebase.spatial: %s" % turtlebase.spatial.__file__)
    log.debug("revision turtlebase.spatial: %s" % turtlebase.spatial.__revision__)
    log.debug("path turtlebase.filenames: %s" % turtlebase.filenames.__file__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)

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
    log.info("Naverwerking RRCF")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: "+str(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    # Check the settings for this script
    checkIni = nens.tools.checkKeys(options.ini, ["herhalingstijden", "field_streefpeil", "cellsize", "lgn_conv_ident",
                                                  "input_field_k5", "percentage_inundatie_stedelijk",
                                                  "herhalingstijd_inundatie_stedelijk", "field_percentage_inundatie_stedelijk",
                                                  "field_toetsing_inundatie_stedelijk", "percentage_inundatie_hoogwaardig",
                                                  "herhalingstijd_inundatie_hoogwaardig", "field_percentage_inundatie_hoogwaardig",
                                                  "field_toetsing_inundatie_hoogwaardig", "percentage_inundatie_akker",
                                                  "herhalingstijd_inundatie_akker", "field_percentage_inundatie_akker",
                                                  "field_toetsing_inundatie_akker", "percentage_inundatie_grasland",
                                                  "herhalingstijd_inundatie_grasland", "field_percentage_inundatie_grasland",
                                                  "field_toetsing_inundatie_grasland", "percentage_overlast_stedelijk",
                                                  "herhalingstijd_overlast_stedelijk", "field_percentage_overlast_stedelijk",
                                                  "field_toetsing_overlast_stedelijk", "percentage_overlast_hoogwaardig",
                                                  "herhalingstijd_overlast_hoogwaardig", "field_percentage_overlast_hoogwaardig",
                                                  "field_toetsing_overlast_hoogwaardig", "percentage_overlast_akker",
                                                  "herhalingstijd_overlast_akker", "field_percentage_overlast_akker",
                                                  "field_toetsing_overlast_akker", "percentage_overlast_grasland",
                                                  "herhalingstijd_overlast_grasland", "field_percentage_overlast_grasland",
                                                  "field_toetsing_overlast_grasland", "calculation_point_ident"])

    if len(checkIni) > 0:
        log.error("missing keys in turtle-settings.ini file (header naverwerking_rrcf)")
        log.error(checkIni)
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
    # Input parameters
    # check for illegal characters in input:
    for argv in sys.argv[1:]:
        turtlebase.filenames.check_filename(argv)

    if len(sys.argv) == 11:
        # input parameters
        input_voronoi_polygon = sys.argv[1]
        input_rrcf_waterlevel = sys.argv[2]
        input_ahn_raster = sys.argv[3]
        input_lgn_raster = sys.argv[4]
        input_lgn_conversion = sys.argv[5]

        # output parameters
        output_result_table = sys.argv[6]

        # optional output
        output_inundation = sys.argv[7]
        if output_inundation == "#":
            output_inundation = turtlebase.arcgis.get_random_file_name(workspace_gdb)

        if len(os.path.basename(output_inundation)) > 13:
            log.error("filename raster output (%s) cannot contain more than 13 characters" % os.path.basename(output_inundation))
            sys.exit(1)

        output_waterdamage = sys.argv[8]
        if output_waterdamage == "#":
            output_waterdamage = turtlebase.arcgis.get_random_file_name(workspace_gdb)

        if len(os.path.basename(output_waterdamage)) > 13:
            log.error("filename raster output (%s) cannot contain more than 13 characters" % os.path.basename(output_waterdamage))
            sys.exit(1)

        output_inundation_total = sys.argv[9]
        if len(os.path.basename(output_inundation_total)) > 13:
            log.error("filename raster output (%s) cannot contain more than 13 characters" % os.path.basename(output_inundation_total))
            sys.exit(1)

        output_waterdamage_total = sys.argv[10]
        if len(os.path.basename(output_waterdamage_total)) > 13:
            log.error("filename raster output (%s) cannot contain more than 13 characters" % os.path.basename(output_waterdamage_total))
            sys.exit(1)

    else:
        log.error("usage: <input_voronoi_polygon> <input_rrcf_waterlevel> <input_ahn_raster> \
        <input_lgn_raster> <input_lgn_conversion> <output_result_table> \
        <output_inundation> <output_waterdamage> <output inundation total> <output waterdamage total>")
        sys.exit(1)
    #----------------------------------------------------------------------------------------
    temp_voronoi = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.select_analysis(input_voronoi_polygon, temp_voronoi)

    # Check geometry input parameters
    cellsize = options.ini['cellsize']

    log.info("Check geometry of input parameters")
    geometry_check_list = []

    if input_lgn_conversion != "#":
        if not gp.exists(input_lgn_conversion):
            errormsg = "%s does not exist" % input_lgn_conversion
            log.error(errormsg)
            geometry_check_list.append(errormsg)

    log.debug(" - check voronoi polygon: %s" % temp_voronoi)
    if gp.describe(temp_voronoi).ShapeType != 'Polygon':
        log.error("Input voronoi is not a polygon feature class!")
        geometry_check_list.append(temp_voronoi + " -> (Polygon)")

    log.debug(" - check ahn raster %s" % input_ahn_raster)
    if gp.describe(input_ahn_raster).DataType != 'RasterDataset':
        log.error("Input AHN is not a raster dataset")
        sys.exit(1)

    if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
        log.error("Input AHN is a floating point raster, for this script an integer is nessecary")
        geometry_check_list.append(input_ahn_raster + " -> (Integer)")

    if gp.describe(input_ahn_raster).MeanCellHeight != float(cellsize):
        log.error("Cell size of AHN is %s, must be 25" % gp.describe(input_ahn_raster).MeanCellHeight)
        geometry_check_list.append(input_ahn_raster + " -> (Cellsize %s)" % cellsize)

    log.debug(" - check lgn raster %s" % input_lgn_raster)
    if gp.describe(input_lgn_raster).DataType != 'RasterDataset':
        log.error("Input LGN is not a raster dataset")
        sys.exit(1)

    if gp.describe(input_lgn_raster).PixelType[0] not in ['U', 'S']:
        log.error("Input LGN is a floating point raster, for this script an integer is nessecary")
        geometry_check_list.append(input_lgn_raster + " -> (Integer)")

    if gp.describe(input_lgn_raster).MeanCellHeight != float(cellsize):
        log.error("Cell size of LGN is %s, must be 25" % gp.describe(input_lgn_raster).MeanCellHeight)
        geometry_check_list.append(input_lgn_raster + " -> (Cellsize %s)" % cellsize)

    if len(geometry_check_list) > 0:
        log.error("check input: %s" % geometry_check_list)
        sys.exit(2)
    #----------------------------------------------------------------------------------------
    # Check required fields in database
    log.info("Check required fields in input data")
    # create return period list
    return_periods = options.ini['herhalingstijden'].split(", ")
    log.debug(" - return periods: %s" % return_periods)

    missing_fields = []

    for return_period in return_periods:
        if not turtlebase.arcgis.is_fieldname(gp, input_rrcf_waterlevel, "WS_%s" % return_period):
            log.debug(" - missing: %s in %s" % ("WS_%s" % return_period, input_rrcf_waterlevel))
            missing_fields.append("%s: %s" % (input_rrcf_waterlevel, "WS_%s" % return_period))

    #<check required fields from input data, append them to list if missing>"
    check_fields = {input_rrcf_waterlevel: [options.ini['calculation_point_ident'], options.ini['field_streefpeil']]}
    if input_lgn_conversion != "#":
        check_fields[input_lgn_conversion] = [options.ini['lgn_conv_ident'], options.ini['input_field_k5']]
    for input_fc,fieldnames in check_fields.items():
        for fieldname in fieldnames:
            if not turtlebase.arcgis.is_fieldname(gp, input_fc, fieldname):
                errormsg = "fieldname %s not available in %s" % (fieldname, input_fc)
                log.error(errormsg)
                missing_fields.append(errormsg)

    if len(missing_fields) > 0:
        log.error("missing fields in input data: %s" % missing_fields)
        sys.exit(2)
    #----------------------------------------------------------------------------------------
    # Environments
    log.info("Set environments")
    gp.extent = gp.describe(temp_voronoi).extent #use extent from LGN

    #----------------------------------------------------------------------------------------
    # read waterlevel table as a dictionary
    log.info("Read waterlevel table")
    waterlevel_dict = nens.gp.get_table(gp, input_rrcf_waterlevel, primary_key=options.ini['calculation_point_ident'].lower())
    log.debug(waterlevel_dict)


    # Add fields to output
    for return_period in return_periods:
        if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, "WS_%s" % return_period):
            log.info(" - add field WS_%s" % return_period)
            gp.addfield(temp_voronoi, "WS_%s" % return_period, "double")

    if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, options.ini['field_streefpeil']):
            log.info(" - add field %s" % options.ini['field_streefpeil'])
            gp.addfield(temp_voronoi, options.ini['field_streefpeil'], "double")

    # copy waterlevel to voronoi polygons
    rows = gp.UpdateCursor(temp_voronoi)
    for row in nens.gp.gp_iterator(rows):
        row_id = row.GetValue(options.ini['calculation_point_ident'])
        if waterlevel_dict.has_key(row_id):
            log.debug(waterlevel_dict[row_id])
            for return_period in return_periods:
                row.SetValue("WS_%s" % return_period, waterlevel_dict[row_id]['ws_%s' % return_period])
                row.SetValue(options.ini['field_streefpeil'], waterlevel_dict[row_id][options.ini['field_streefpeil'].lower()])

            rows.UpdateRow(row)

    #----------------------------------------------------------------------------------------
    # Create waterlevel rasters
    log.info("Create rasters for waterlevels")
    for return_period in return_periods:
        log.info(" - create raster for ws_%s" % return_period)
        out_raster_dataset = workspace_gdb + "/ws_%s" % return_period
        gp.FeatureToRaster_conversion(temp_voronoi, "WS_%s" % return_period, out_raster_dataset, cellsize)

    #----------------------------------------------------------------------------------------
    # Create target level raster
    log.info("Create targetlevel raster")
    out_raster_targetlevel = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.FeatureToRaster_conversion(temp_voronoi, options.ini['field_streefpeil'], out_raster_targetlevel, cellsize)

    #----------------------------------------------------------------------------------------
    # Create freeboard raster
    log.info("Create freeboard raster")

    # create ahn ascii
    ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    log.debug("ahn ascii: %s" % ahn_ascii)
    gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

    targetlevel_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    log.debug("targetlevel ascii: %s" % targetlevel_ascii)
    gp.RasterToASCII_conversion(out_raster_targetlevel, targetlevel_ascii)

    freeboard_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
    turtlebase.spatial.create_freeboard_raster(ahn_ascii, targetlevel_ascii, freeboard_ascii)

    #----------------------------------------------------------------------------------------
    # Create K5 LGN
    log.info("Reclass LGN to K5 raster")
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
    # Create inundation raster
    # als ws_ > ahn, dan inundatie
    inundation_raster_list = []
    inundation_total_raster_list = []

    log.info("Create inundation rasters")
    # inundatie stedelijk
    return_period_urban = options.ini['herhalingstijd_inundatie_stedelijk']
    if options.ini['percentage_inundatie_stedelijk'] != "-":
        log.debug(" - create inundation urban")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_urban)
        if gp.exists(waterlevel):
            inundation_urban = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel, 1,
                                                        return_period_urban, inundation_urban, workspace, use_lgn=True)
            inundation_raster_list.append(inundation_urban)
            if output_inundation_total != '#':
                # Inundation without lgn
                inundation_total_urban = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           1, return_period_urban, inundation_total_urban, workspace, use_lgn=False)
                inundation_total_raster_list.append(inundation_total_urban)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie hoogwaardige landbouw
    return_period_agriculture = options.ini['herhalingstijd_inundatie_hoogwaardig']
    if options.ini['percentage_inundatie_hoogwaardig'] != "-":
        log.debug(" - create inundation agriculture")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_agriculture)
        if gp.exists(waterlevel):
            # Inundation with lgn
            inundation_agriculture = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                       2, return_period_agriculture, inundation_agriculture, workspace, use_lgn=True)
            inundation_raster_list.append(inundation_agriculture)
            if output_inundation_total != '#':
                # Inundation without lgn
                inundation_total_agriculture = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           2, return_period_agriculture, inundation_total_agriculture, workspace, use_lgn=False)
                inundation_total_raster_list.append(inundation_total_agriculture)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie akkerbouw
    return_period_rural = options.ini['herhalingstijd_inundatie_akker']
    if options.ini['percentage_inundatie_akker'] != "-":
        log.debug(" - create inundation rural")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_rural)
        if gp.exists(waterlevel):
            inundation_rural = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                       3, return_period_rural, inundation_rural, workspace, use_lgn=True)
            inundation_raster_list.append(inundation_rural)
            if output_inundation_total != '#':
                # Inundation without lgn
                inundation_total_rural = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           3, return_period_rural, inundation_total_rural, workspace, use_lgn=False)
                inundation_total_raster_list.append(inundation_total_rural)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # inundatie grasland
    return_period_grass = options.ini['herhalingstijd_inundatie_grasland']
    if options.ini['percentage_inundatie_grasland'] != "-":
        log.debug(" - create inundation grass")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_grass)
        if gp.exists(waterlevel):
            inundation_grass = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                       4, return_period_grass, inundation_grass, workspace, use_lgn=True)
            inundation_raster_list.append(inundation_grass)
            if output_inundation_total != '#':
                # Inundation without lgn
                inundation_total_grass = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           4, return_period_grass, inundation_total_grass, workspace, use_lgn=False)
                inundation_total_raster_list.append(inundation_total_grass)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    if len(inundation_raster_list) > 1:
        log.info("Merge inundation rasters")
        output_inundation_exists = turtlebase.spatial.merge_ascii(inundation_raster_list, output_inundation, workspace)
    else:
        log.error("there are no inundation rasters available")

    if len(inundation_total_raster_list) > 1:
        log.info("Merge inundation total rasters")
        output_inundation_total_exists = turtlebase.spatial.merge_ascii(inundation_total_raster_list, output_inundation_total, workspace)

    #----------------------------------------------------------------------------------------
    # Create waterdamage raster
    # als ws_ > freeboard, dan overlast
    damage_raster_list = []
    damage_total_raster_list = []

    log.info("Create waterdamage rasters")
    # overlast stedelijk
    return_period_urban_damage = options.ini['herhalingstijd_overlast_stedelijk']
    if options.ini['percentage_overlast_stedelijk'] != "-":
        log.debug(" - create waterdamage urban")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_urban_damage)
        if gp.exists(waterlevel):
            damage_urban = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                       1, return_period_urban_damage, damage_urban, workspace, use_lgn=True)
            damage_raster_list.append(damage_urban)
            if output_waterdamage_total != '#':
                # Waterdamage without lgn
                damage_total_urban = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           1, return_period_urban_damage, damage_total_urban, workspace, use_lgn=False)
                damage_total_raster_list.append(damage_total_urban)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # overlast hoogwaardig
    return_period_agriculture_damage = options.ini['herhalingstijd_overlast_hoogwaardig']
    if options.ini['percentage_overlast_hoogwaardig'] != "-":
        log.debug(" - create waterdamage intensive agriculture")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_agriculture_damage)
        if gp.exists(waterlevel):
            damage_agriculture = workspace + "/damage_agri_%s.asc" % return_period_agriculture_damage
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                       2, return_period_agriculture_damage, damage_agriculture, workspace, use_lgn=True)
            damage_raster_list.append(damage_agriculture)
            if output_waterdamage_total != '#':
                # Waterdamage without lgn
                damage_total_agriculture = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           1, return_period_agriculture_damage, damage_total_agriculture, workspace, use_lgn=False)
                damage_total_raster_list.append(damage_total_agriculture)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # overlast akker
    return_period_rural_damage = options.ini['herhalingstijd_overlast_akker']
    if options.ini['percentage_overlast_akker'] != "-":
        log.debug(" - create waterdamage rural")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_rural_damage)
        if gp.exists(waterlevel):
            damage_rural = workspace + "/damage_rural_%s.asc" % return_period_rural_damage
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                       3, return_period_rural_damage, damage_rural, workspace, use_lgn=True)
            damage_raster_list.append(damage_rural)
            if output_waterdamage_total != '#':
                # Waterdamage without lgn
                damage_total_rural = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           1, return_period_rural_damage, damage_total_rural, workspace, use_lgn=False)
                damage_total_raster_list.append(damage_total_rural)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # overlast grasland
    return_period_grass_damage = options.ini['herhalingstijd_overlast_grasland']
    if options.ini['percentage_overlast_grasland'] != "-":
        log.debug(" - create waterdamage grass")
        waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_grass_damage)
        if gp.exists(waterlevel):
            damage_grass = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
            turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                       4, return_period_grass_damage, damage_grass, workspace, use_lgn=True)
            damage_raster_list.append(damage_grass)
            if output_waterdamage_total != '#':
                # Waterdamage without lgn
                damage_total_grass = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           1, return_period_grass_damage, damage_total_grass, workspace, use_lgn=False)
                damage_total_raster_list.append(damage_total_grass)
        else:
            log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

    # Merge waterdamage rasters
    if len(damage_raster_list) > 1:
        log.info("Merge waterdamage rasters")
        output_waterdamage_exists = turtlebase.spatial.merge_ascii(damage_raster_list, output_waterdamage, workspace)
    else:
        log.error("there are no waterdamage rasters available")

    if len(damage_total_raster_list) > 1:
        log.info("Merge waterdamage total rasters")
        output_inundation_total_exists = turtlebase.spatial.merge_ascii(damage_total_raster_list, output_waterdamage_total, workspace)
    #----------------------------------------------------------------------------------------
    # calculate percentage inundation
    """
    input:
    - inundatie / overlast (raster dataset)
    - input_voronoi_polygon (met GPGIDENT) (feature class)
    - lgn_k5 (raster dataset)
    """
    # dissolve voronoi based on gpgident
    log.debug("dissolve voronoi polygons, based on gpgident")
    temp_fc_gpgident = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.Dissolve_management(temp_voronoi, temp_fc_gpgident, options.ini["peilgebied_ident"])

    # Calculate area total, gpgident
    if not turtlebase.arcgis.is_fieldname(gp, temp_fc_gpgident, "area_total"):
        gp.addfield(temp_fc_gpgident, "area_total", "Double")
    turtlebase.arcgis.calculate_area(gp, temp_fc_gpgident, "area_total")

    gpgident_dict = nens.gp.get_table(gp, temp_fc_gpgident, primary_key=options.ini["peilgebied_ident"].lower())
    log.debug("gpgident_dict: %s" % gpgident_dict)

    # create feature class from lgn k5 ascii
    output_reclass_lgn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.ASCIIToRaster_conversion(lgn_k5_ascii, output_reclass_lgn)
    temp_fc_lgn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.RasterToPolygon_conversion(output_reclass_lgn, temp_fc_lgn, "NO_SIMPLIFY")

    # union lgn with gpg-areas
    temp_fc_union_lgn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.Union_analysis(temp_fc_gpgident+";"+temp_fc_lgn, temp_fc_union_lgn)
    dissolve_lyr = turtlebase.arcgis.get_random_layer_name()
    gp.MakeFeatureLayer_management(temp_fc_union_lgn, dissolve_lyr, "%s <> ''" % options.ini["peilgebied_ident"])
    temp_fc_dissolve_lgn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
    gp.Dissolve_management(dissolve_lyr, temp_fc_dissolve_lgn, "%s; GRIDCODE" % options.ini["peilgebied_ident"])

    # Calculate area lgn
    if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_lgn, "area_lgn"):
        gp.addfield(temp_fc_dissolve_lgn, "area_lgn", "Double")
    turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_lgn, "area_lgn")

    lgn_dict = nens.gp.get_table(gp, temp_fc_dissolve_lgn)
    translate_lgn_dict = translate_dict(lgn_dict, 'gridcode', 'area_lgn')
    log.debug("translate_lgn_dict: %s" % translate_lgn_dict)

    # Create feature class from inundation_grid
    """ values: 10, 25, 50, 100"""
    if output_inundation_exists == 0:
        temp_fc_inundation = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.RasterToPolygon_conversion(output_inundation, temp_fc_inundation, "NO_SIMPLIFY")
        temp_fc_union_inundation = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Union_analysis(temp_fc_dissolve_lgn+";"+temp_fc_inundation, temp_fc_union_inundation)
        dissolve_inundation_lyr = turtlebase.arcgis.get_random_layer_name()
        gp.MakeFeatureLayer_management(temp_fc_union_inundation, dissolve_inundation_lyr, "GRIDCODE_1 > 0")
        temp_fc_dissolve_inundation = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Dissolve_management(dissolve_inundation_lyr, temp_fc_dissolve_inundation, "%s; GRIDCODE; GRIDCODE_1" % options.ini["peilgebied_ident"])

        # Calculate area inundation
        if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_inundation, "area_inund"):
            gp.addfield(temp_fc_dissolve_inundation, "area_inun", "Double")
        turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_inundation, "area_inun")

        inundation_dict = nens.gp.get_table(gp, temp_fc_dissolve_inundation)
        translate_inundation_dict = translate_dict(inundation_dict, 'gridcode_1', 'area_inun')
        log.debug("translate_inundation_dict: %s" % translate_inundation_dict)
    else:
        translate_inundation_dict = {}


    # Create feature class from waterdamage grid
    """ values: 10, 15, 25"""
    if output_waterdamage_exists == 0:
        temp_fc_waterdamage = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.RasterToPolygon_conversion(output_waterdamage, temp_fc_waterdamage, "NO_SIMPLIFY")
        temp_fc_union_waterdamage = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Union_analysis(temp_fc_dissolve_lgn+";"+temp_fc_waterdamage, temp_fc_union_waterdamage)
        dissolve_waterdamage_lyr = turtlebase.arcgis.get_random_layer_name()
        gp.MakeFeatureLayer_management(temp_fc_union_waterdamage, dissolve_waterdamage_lyr, "GRIDCODE_1 > 0")
        temp_fc_dissolve_waterdamage = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Dissolve_management(dissolve_waterdamage_lyr, temp_fc_dissolve_waterdamage, "%s; GRIDCODE; GRIDCODE_1" % options.ini["peilgebied_ident"])

        # Calculate area waterdamage
        if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_waterdamage, "area_damag"):
            gp.addfield(temp_fc_dissolve_waterdamage, "area_damag", "Double")
        turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_waterdamage, "area_damag")

        waterdamage_dict = nens.gp.get_table(gp, temp_fc_dissolve_waterdamage)
        translate_waterdamage_dict = translate_dict(waterdamage_dict, 'gridcode_1', 'area_damag')
        log.debug("translate_waterdamage_dict: %s" % translate_waterdamage_dict)
    else:
        translate_waterdamage_dict = {}

    no_data_value = float(options.ini["no_data_value"])
    result_dict = {}
    log.info("Calculating results")
    for gpgident,fields in gpgident_dict.items():
        # area_total
        area_total = fields['area_total']

        #set defaults
        percentage_inundation_urban = no_data_value
        percentage_inundation_agriculture = no_data_value
        percentage_inundation_rural = no_data_value
        percentage_inundation_grass = no_data_value
        toetsing_inundation_urban = 9
        toetsing_inundation_agriculture = 9
        toetsing_inundation_rural = 9
        toetsing_inundation_grass = 9

        percentage_waterdamage_urban = no_data_value
        percentage_waterdamage_agriculture = no_data_value
        percentage_waterdamage_rural = no_data_value
        percentage_waterdamage_grass = no_data_value
        toetsing_waterdamage_urban = 9
        toetsing_waterdamage_agriculture = 9
        toetsing_waterdamage_rural = 9
        toetsing_waterdamage_grass = 9

        if translate_inundation_dict.has_key(gpgident):
            log.debug("Calculate percentage inundation for %s" % gpgident)
            if translate_inundation_dict[gpgident].has_key(float(options.ini['herhalingstijd_inundatie_stedelijk'])):
                area_inundation_urban = translate_inundation_dict[gpgident][float(options.ini['herhalingstijd_inundatie_stedelijk'])]
                area_urban = translate_lgn_dict[gpgident][1]
                percentage_inundation_urban = (float(area_inundation_urban) / float(area_urban)) * 100
                log.debug(" - urban inundation: %s percent" % percentage_inundation_urban)
                toetsing_inundation_urban = toetsing(percentage_inundation_urban, float(options.ini['percentage_inundatie_stedelijk']), no_data_value)

            if translate_inundation_dict[gpgident].has_key(float(options.ini['herhalingstijd_inundatie_hoogwaardig'])):
                area_inundation_agriculture = translate_inundation_dict[gpgident][float(options.ini['herhalingstijd_inundatie_hoogwaardig'])]
                area_agriculture = translate_lgn_dict[gpgident][2]
                percentage_inundation_agriculture = (float(area_inundation_agriculture) / float(area_agriculture)) * 100
                log.debug(" - agriculture inundation: %s percent" % percentage_inundation_agriculture)
                toetsing_inundation_agriculture = toetsing(percentage_inundation_agriculture, float(options.ini['percentage_inundatie_hoogwaardig']), no_data_value)

            if translate_inundation_dict[gpgident].has_key(float(options.ini['herhalingstijd_inundatie_akker'])):
                area_inundation_rural = translate_inundation_dict[gpgident][float(options.ini['herhalingstijd_inundatie_akker'])]
                area_rural = translate_lgn_dict[gpgident][3]
                percentage_inundation_rural = (float(area_inundation_rural) / float(area_rural)) * 100
                log.debug(" - rural inundation: %s percent" % percentage_inundation_rural)
                toetsing_inundation_rural = toetsing(percentage_inundation_rural, float(options.ini['percentage_inundatie_akker']), no_data_value)

            if translate_inundation_dict[gpgident].has_key(float(options.ini['herhalingstijd_inundatie_grasland'])):
                area_inundation_grass = translate_inundation_dict[gpgident][float(options.ini['herhalingstijd_inundatie_grasland'])]
                area_grass = translate_lgn_dict[gpgident][4]
                percentage_inundation_grass = (float(area_inundation_grass) / float(area_grass)) * 100
                log.debug(" - grass inundation: %s percent" % percentage_inundation_grass)
                toetsing_inundation_grass = toetsing(percentage_inundation_grass, float(options.ini['percentage_inundatie_grasland']), no_data_value)

        if translate_waterdamage_dict.has_key(gpgident):
            log.debug("Calculate percentage waterdamage for %s" % gpgident)
            if translate_waterdamage_dict[gpgident].has_key(float(options.ini['herhalingstijd_overlast_stedelijk'])):
                area_waterdamage_urban = translate_waterdamage_dict[gpgident][float(options.ini['herhalingstijd_overlast_stedelijk'])]
                area_urban = translate_lgn_dict[gpgident][1]
                percentage_waterdamage_urban = (float(area_waterdamage_urban) / float(area_urban)) * 100
                log.debug(" - urban waterdamage: %s percent" % percentage_waterdamage_urban)
                toetsing_inundation_agriculture = toetsing(percentage_waterdamage_urban, float(options.ini['percentage_overlast_stedelijk']), no_data_value)

            if translate_waterdamage_dict[gpgident].has_key(float(options.ini['herhalingstijd_overlast_hoogwaardig'])):
                area_waterdamage_agriculture = translate_waterdamage_dict[gpgident][float(options.ini['herhalingstijd_overlast_hoogwaardig'])]
                area_agriculture = translate_lgn_dict[gpgident][2]
                percentage_waterdamage_agriculture = (float(area_waterdamage_agriculture) / float(area_agriculture)) * 100
                log.debug(" - agriculture waterdamage: %s percent" % percentage_waterdamage_agriculture)
                toetsing_inundation_agriculture = toetsing(percentage_waterdamage_agriculture, float(options.ini['percentage_overlast_hoogwaardig']), no_data_value)

            if translate_waterdamage_dict[gpgident].has_key(float(options.ini['herhalingstijd_overlast_akker'])):
                area_waterdamage_rural = translate_waterdamage_dict[gpgident][float(options.ini['herhalingstijd_overlast_akker'])]
                area_rural = translate_lgn_dict[gpgident][3]
                percentage_waterdamage_rural = (float(area_waterdamage_rural) / float(area_rural)) * 100
                log.debug(" - rural waterdamage: %s percent" % percentage_waterdamage_rural)
                toetsing_waterdamage_rural = toetsing(percentage_waterdamage_rural, float(options.ini['percentage_overlast_akker']), no_data_value)

            if translate_waterdamage_dict[gpgident].has_key(options.ini['herhalingstijd_overlast_grasland']):
                area_waterdamage_grass = translate_waterdamage_dict[gpgident][float(options.ini['herhalingstijd_overlast_grasland'])]
                area_grass = translate_lgn_dict[gpgident][4]
                percentage_waterdamage_grass = (float(area_waterdamage_grass) / float(area_grass)) * 100
                log.debug(" - grass waterdamage: %s percent" % percentage_waterdamage_grass)
                toetsing_waterdamage_grass = toetsing(percentage_waterdamage_grass, float(options.ini['percentage_overlast_grasland']), no_data_value)

        result_dict[gpgident] = {options.ini['peilgebied_ident']: gpgident,
                                 options.ini['field_percentage_inundatie_stedelijk']: percentage_inundation_urban,
                                 options.ini['field_percentage_inundatie_hoogwaardig']: percentage_inundation_agriculture,
                                 options.ini['field_percentage_inundatie_akker']: percentage_inundation_rural,
                                 options.ini['field_percentage_inundatie_grasland']: percentage_inundation_grass,
                                 options.ini['field_percentage_overlast_stedelijk']: percentage_waterdamage_urban,
                                 options.ini['field_percentage_overlast_hoogwaardig']: percentage_waterdamage_agriculture,
                                 options.ini['field_percentage_overlast_akker']: percentage_waterdamage_rural,
                                 options.ini['field_percentage_overlast_grasland']: percentage_waterdamage_grass,
                                 options.ini['field_toetsing_inundatie_stedelijk']: toetsing_inundation_urban,
                                 options.ini['field_toetsing_inundatie_hoogwaardig']: toetsing_inundation_agriculture,
                                 options.ini['field_toetsing_inundatie_akker']: toetsing_inundation_rural,
                                 options.ini['field_toetsing_inundatie_grasland']: toetsing_inundation_grass,
                                 options.ini['field_toetsing_overlast_stedelijk']: toetsing_waterdamage_urban,
                                 options.ini['field_toetsing_overlast_hoogwaardig']: toetsing_waterdamage_agriculture,
                                 options.ini['field_toetsing_overlast_akker']: toetsing_waterdamage_rural,
                                 options.ini['field_toetsing_overlast_grasland']: toetsing_waterdamage_grass}
    #----------------------------------------------------------------------------------------
    # Create output table
    if not gp.exists(output_result_table):
        log.info("Create new output table")
        temp_result_table = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.CreateTable_management(os.path.dirname(temp_result_table), os.path.basename(temp_result_table))
        copy_table = True
    else:
        temp_result_table = output_result_table
        copy_table = False

    fields_to_add = [options.ini['field_percentage_inundatie_stedelijk'],
                     options.ini['field_percentage_inundatie_hoogwaardig'],
                     options.ini['field_percentage_inundatie_akker'],
                     options.ini['field_percentage_inundatie_grasland'],
                     options.ini['field_percentage_overlast_stedelijk'],
                     options.ini['field_percentage_overlast_hoogwaardig'],
                     options.ini['field_percentage_overlast_akker'],
                     options.ini['field_percentage_overlast_grasland'],
                     options.ini['field_toetsing_inundatie_stedelijk'],
                     options.ini['field_toetsing_inundatie_hoogwaardig'],
                     options.ini['field_toetsing_inundatie_akker'],
                     options.ini['field_toetsing_inundatie_grasland'],
                     options.ini['field_toetsing_overlast_stedelijk'],
                     options.ini['field_toetsing_overlast_hoogwaardig'],
                     options.ini['field_toetsing_overlast_akker'],
                     options.ini['field_toetsing_overlast_grasland']]

    if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, options.ini['peilgebied_ident']):
        log.debug(" - add field %s to %s" % (options.ini['peilgebied_ident'], temp_result_table))
        gp.addfield_management(temp_result_table, options.ini['peilgebied_ident'], 'text')

    for field in fields_to_add:
        if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, field):
            log.debug(" - add field %s to %s" % (field, temp_result_table))
            gp.addfield_management(temp_result_table, field, 'double')

    #----------------------------------------------------------------------------------------
    # Write results to output table
    log.info("Write results to output table")
    turtlebase.arcgis.write_result_to_output(temp_result_table, options.ini['peilgebied_ident'].lower(), result_dict)

    if copy_table == True:
        gp.TableToTable_conversion(temp_result_table, os.path.dirname(output_result_table), os.path.basename(output_result_table))

    #----------------------------------------------------------------------------------------
    # Delete temporary workspace geodatabase & ascii files
    try:
        log.debug("delete temporary workspace: %s" % workspace_gdb)
        gp.delete(workspace_gdb)

        log.info("workspace deleted")
    except:
        log.info("failed to delete %s" % workspace_gdb)

    log.debug("delete temporary ascii-files")
    file_list = os.listdir(workspace)
    for file in file_list:
        if file[-4:] == '.asc':
            log.debug("remove %s" % os.path.join(workspace, file))
            os.remove(os.path.join(workspace, file))

    log.info("Finished")
    del gp
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s' ,)
    from optparse import OptionParser
    parser = OptionParser()

    (options, args) = parser.parse_args()

    turtlebase.general.extend_options_for_turtle(options, "naverwerking_rrcf",
                              gpHandlerLevel = logging.INFO,
                              fileHandlerLevel = logging.DEBUG,
                              consoleHandlerLevel = None,
                              root_settings = 'turtle-settings.ini')

    ##import cProfile
    ##cProfile.run('main(options, args)')
    main(options, args)
