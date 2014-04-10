# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback
import tempfile

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.spatial
import turtlebase.voronoi

log = logging.getLogger(__name__)


def translate_dict(input_dict, translate_field, area_field):
    output_dict = turtlebase.voronoi.defaultdict(dict)

    for row in input_dict:
        gpgid = row['gpgident']
        if gpgid != '':
            output_dict[gpgid][int(row[translate_field])] = row[area_field]

    return output_dict

def calculate_toetsing(translate_dict, gpgident, lgn_klasse, translate_lgn_dict,
                       hhtijd, toetsing_percentage, no_data_value):
    """
    """
    toetsing_result = 9
    percentage = no_data_value

    if toetsing_percentage != "-":
        float(toetsing_percentage)

        if hhtijd != "-":
            log.debug("hhtijd: %s" % hhtijd)
            hhtijd_int = int(hhtijd)

            if hhtijd_int in translate_dict[gpgident]:
                area_inundation = translate_dict[gpgident][hhtijd_int]
                if lgn_klasse in translate_lgn_dict[gpgident]:
                    area_total = translate_lgn_dict[gpgident][lgn_klasse]
                    percentage = (float(area_inundation) / float(area_total)) * 100
                    toetsing_result = toetsing(percentage, toetsing_percentage, no_data_value)
                else:
                    percentage = -999
                    toetsing_result = 9

    return toetsing_result, percentage


def toetsing(input_percentage, allowable_percentage, no_data_value):
    """
    """
    if input_percentage == no_data_value:
        return 9
    elif float(input_percentage) >= float(allowable_percentage):
        return 1
    else:
        return 0


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')
        if workspace == "-":
            workspace = tempfile.gettempdir()

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                        gp, workspace)
        if errorcode == 1:
                log.error("failed to create a file geodatabase in %s" % workspace)
        # Input parameters
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
                output_inundation = os.path.join(workspace_gdb, "inun_nbw")

            if len(os.path.basename(output_inundation)) > 13:
                log.error("filename raster output (%s) cannot contain more than 13 characters" % os.path.basename(output_inundation))
                sys.exit(1)

            output_waterdamage = sys.argv[8]
            if output_waterdamage == "#":
                output_waterdamage = os.path.join(workspace_gdb, "damage_nbw")

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
        temp_voronoi = os.path.join(workspace_gdb, "voronoi")
        gp.select_analysis(input_voronoi_polygon, temp_voronoi)

        # Check geometry input parameters
        cellsize = gp.describe(input_ahn_raster).MeanCellHeight

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

        log.debug(" - check lgn raster %s" % input_lgn_raster)
        if gp.describe(input_lgn_raster).DataType != 'RasterDataset':
            log.error("Input LGN is not a raster dataset")
            sys.exit(1)

        if gp.describe(input_lgn_raster).PixelType[0] not in ['U', 'S']:
            log.error("Input LGN is a floating point raster, for this script an integer is nessecary")
            geometry_check_list.append(input_lgn_raster + " -> (Integer)")

        if gp.describe(input_lgn_raster).MeanCellHeight != float(cellsize):
            log.error("Cell size of LGN is %s, must be %s" % (
                                    gp.describe(input_lgn_raster).MeanCellHeight, cellsize))
            geometry_check_list.append(input_lgn_raster + " -> (Cellsize %s)" % cellsize)

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #----------------------------------------------------------------------------------------
        # Check required fields in database
        log.info("Check required fields in input data")
        # create return period list
        return_periods = config.get('naverwerking_rrcf', 'herhalingstijden').split(", ")
        log.debug(" - return periods: %s" % return_periods)

        missing_fields = []

        for return_period in return_periods:
            if not turtlebase.arcgis.is_fieldname(gp, input_rrcf_waterlevel, "WS_%s" % return_period):
                log.debug(" - missing: %s in %s" % ("WS_%s" % return_period, input_rrcf_waterlevel))
                missing_fields.append("%s: %s" % (input_rrcf_waterlevel, "WS_%s" % return_period))

        #<check required fields from input data, append them to list if missing>"
        field_streefpeil = config.get('naverwerking_rrcf', 'field_streefpeil')
        check_fields = {input_rrcf_waterlevel: [config.get('naverwerking_rrcf', 'calculation_point_ident'), field_streefpeil]}
        if input_lgn_conversion != "#":
            check_fields[input_lgn_conversion] = [config.get('naverwerking_rrcf', 'lgn_conv_ident'),
                                                    config.get('naverwerking_rrcf', 'input_field_k5')]
        for input_fc, fieldnames in check_fields.items():
            for fieldname in fieldnames:
                if not turtlebase.arcgis.is_fieldname(gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments
        log.info("Set environments")
        gp.extent = gp.describe(temp_voronoi).extent  # use extent from LGN

        #---------------------------------------------------------------------
        # read waterlevel table as a dictionary
        log.info("Read waterlevel table")
        waterlevel_dict = nens.gp.get_table(gp, input_rrcf_waterlevel, primary_key=config.get('naverwerking_rrcf', 'calculation_point_ident').lower())
        log.debug(waterlevel_dict)

        # Add fields to output
        for return_period in return_periods:
            if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, "WS_%s" % return_period):
                log.info(" - add field WS_%s" % return_period)
                gp.addfield(temp_voronoi, "WS_%s" % return_period, "double")

        if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, field_streefpeil):
                log.info(" - add field %s" % field_streefpeil)
                gp.addfield(temp_voronoi, field_streefpeil, "double")

        # copy waterlevel to voronoi polygons
        rows = gp.UpdateCursor(temp_voronoi)
        for row in nens.gp.gp_iterator(rows):
            row_id = row.GetValue(config.get('naverwerking_rrcf', 'calculation_point_ident'))
            if row_id in waterlevel_dict:
                log.debug(waterlevel_dict[row_id])
                for return_period in return_periods:
                    row.SetValue("WS_%s" % return_period, waterlevel_dict[row_id]['ws_%s' % return_period])
                    row.SetValue(field_streefpeil,
                                 waterlevel_dict[row_id][field_streefpeil.lower()])
                rows.UpdateRow(row)

        #---------------------------------------------------------------------
        # Create waterlevel rasters
        log.info("Create rasters for waterlevels")
        for return_period in return_periods:
            log.info(" - create raster for ws_%s" % return_period)
            out_raster_dataset = workspace_gdb + "/ws_%s" % return_period
            gp.FeatureToRaster_conversion(temp_voronoi, "WS_%s" % return_period, out_raster_dataset, cellsize)

        #---------------------------------------------------------------------
        # Create target level raster
        log.info("Create targetlevel raster")
        out_raster_targetlevel = os.path.join(workspace_gdb, "targetlv")
        gp.FeatureToRaster_conversion(temp_voronoi, field_streefpeil, out_raster_targetlevel, cellsize)

        #---------------------------------------------------------------------
        # Create freeboard raster
        log.info("Create freeboard raster")

        # create ahn ascii
        ahn_ascii = os.path.join(workspace, "ahn.asc")
        log.debug("ahn ascii: %s" % ahn_ascii)
        gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

        targetlevel_ascii = os.path.join(workspace, "targetlvl.asc")
        log.debug("targetlevel ascii: %s" % targetlevel_ascii)
        gp.RasterToASCII_conversion(out_raster_targetlevel, targetlevel_ascii)

        freeboard_ascii = os.path.join(workspace, "freeboard.asc")
        turtlebase.spatial.create_freeboard_raster(ahn_ascii, targetlevel_ascii, freeboard_ascii)

        #----------------------------------------------------------------------------------------
        # Create K5 LGN
        log.info("Reclass LGN to K5 raster")
        lgn_ascii = os.path.join(workspace, "lgn.asc")
        lgn_k5_ascii = os.path.join(workspace, "lgn_k5.asc")

        gp.RasterToASCII_conversion(input_lgn_raster, lgn_ascii)

        if input_lgn_conversion != '#':
            reclass_dict = nens.gp.get_table(gp, input_lgn_conversion,
                                             primary_key=config.get('naverwerking_rrcf', 'lgn_conv_ident').lower())
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
        return_period_urban = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_stedelijk')
        if config.get('naverwerking_rrcf', 'percentage_inundatie_stedelijk') != "-":
            log.info(" - create inundation urban")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_urban)
            if gp.exists(waterlevel):
                inundation_urban = os.path.join(workspace, "inun_urban.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel, 1,
                                                            return_period_urban, inundation_urban, workspace, use_lgn=True)
                inundation_raster_list.append(inundation_urban)
                if output_inundation_total != '#':
                    # Inundation without lgn
                    inundation_total_urban = os.path.join(workspace, "inun_total_urban.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               1, return_period_urban, inundation_total_urban, workspace, use_lgn=False)
                    inundation_total_raster_list.append(inundation_total_urban)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # inundatie hoogwaardige landbouw
        return_period_agriculture = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_hoogwaardig')
        if config.get('naverwerking_rrcf', 'percentage_inundatie_hoogwaardig') != "-":
            log.info(" - create inundation agriculture")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_agriculture)
            if gp.exists(waterlevel):
                # Inundation with lgn
                inundation_agriculture = os.path.join(workspace, "inun_agri.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           2, return_period_agriculture, inundation_agriculture, workspace, use_lgn=True)
                inundation_raster_list.append(inundation_agriculture)
                if output_inundation_total != '#':
                    # Inundation without lgn
                    inundation_total_agriculture = os.path.join(workspace, "inun_total_agri.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               2, return_period_agriculture, inundation_total_agriculture, workspace, use_lgn=False)
                    inundation_total_raster_list.append(inundation_total_agriculture)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # inundatie akkerbouw
        return_period_rural = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_akker')
        if config.get('naverwerking_rrcf', 'percentage_inundatie_akker') != "-":
            log.info(" - create inundation rural")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_rural)
            if gp.exists(waterlevel):
                inundation_rural = os.path.join(workspace, "inun_rural.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           3, return_period_rural, inundation_rural, workspace, use_lgn=True)
                inundation_raster_list.append(inundation_rural)
                if output_inundation_total != '#':
                    # Inundation without lgn
                    inundation_total_rural = os.path.join(workspace, "inun_total_rural.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               3, return_period_rural, inundation_total_rural, workspace, use_lgn=False)
                    inundation_total_raster_list.append(inundation_total_rural)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # inundatie grasland
        return_period_grass = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_grasland')
        if config.get('naverwerking_rrcf', 'percentage_inundatie_grasland') != "-":
            log.info(" - create inundation grass")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_grass)
            if gp.exists(waterlevel):
                log.debug("waterlevel grasland = %s" % waterlevel)
                inundation_grass = os.path.join(workspace, "inun_grass.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                           4, return_period_grass, inundation_grass, workspace, use_lgn=True)
                inundation_raster_list.append(inundation_grass)
                if output_inundation_total != '#':
                    # Inundation without lgn
                    inundation_total_grass = os.path.join(workspace, "inun_total_grass.asc")
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
            turtlebase.spatial.merge_ascii(inundation_total_raster_list, output_inundation_total, workspace)

        #----------------------------------------------------------------------------------------
        # Create waterdamage raster
        # als ws_ > freeboard, dan overlast
        damage_raster_list = []
        damage_total_raster_list = []

        log.info("Create waterdamage rasters")
        # overlast stedelijk
        return_period_urban_damage = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_stedelijk')
        if config.get('naverwerking_rrcf', 'percentage_overlast_stedelijk') != "-":
            log.info(" - create waterdamage urban")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_urban_damage)
            if gp.exists(waterlevel):
                damage_urban = os.path.join(workspace, "damage_urban.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                           1, return_period_urban_damage, damage_urban, workspace, use_lgn=True)
                damage_raster_list.append(damage_urban)
                if output_waterdamage_total != '#':
                    # Waterdamage without lgn
                    damage_total_urban = os.path.join(workspace, "damage_total_urban.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               1, return_period_urban_damage, damage_total_urban, workspace, use_lgn=False)
                    damage_total_raster_list.append(damage_total_urban)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # overlast hoogwaardig
        return_period_agriculture_damage = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_hoogwaardig')
        if config.get('naverwerking_rrcf', 'percentage_overlast_hoogwaardig') != "-":
            log.info(" - create waterdamage agriculture")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_agriculture_damage)
            if gp.exists(waterlevel):
                damage_agriculture = workspace + "/damage_agri_%s.asc" % return_period_agriculture_damage
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                           2, return_period_agriculture_damage, damage_agriculture, workspace, use_lgn=True)
                damage_raster_list.append(damage_agriculture)
                if output_waterdamage_total != '#':
                    # Waterdamage without lgn
                    damage_total_agriculture = os.path.join(workspace, "damage_total_agri.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               1, return_period_agriculture_damage, damage_total_agriculture, workspace, use_lgn=False)
                    damage_total_raster_list.append(damage_total_agriculture)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # overlast akker
        return_period_rural_damage = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_akker')
        if config.get('naverwerking_rrcf', 'percentage_overlast_akker') != "-":
            log.info(" - create waterdamage rural")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_rural_damage)
            if gp.exists(waterlevel):
                damage_rural = workspace + "/damage_rural_%s.asc" % return_period_rural_damage
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                           3, return_period_rural_damage, damage_rural, workspace, use_lgn=True)
                damage_raster_list.append(damage_rural)
                if output_waterdamage_total != '#':
                    # Waterdamage without lgn
                    damage_total_rural = os.path.join(workspace_gdb, "damage_total_rural.asc")
                    turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, ahn_ascii, waterlevel,
                                                               1, return_period_rural_damage, damage_total_rural, workspace, use_lgn=False)
                    damage_total_raster_list.append(damage_total_rural)
            else:
                log.error("%s does not exists! check ini-file and tempfolder" % waterlevel)

        # overlast grasland
        return_period_grass_damage = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_grasland')
        if config.get('naverwerking_rrcf', 'percentage_overlast_grasland') != "-":
            log.info(" - create waterdamage grass")
            waterlevel = "%s/ws_%s" % (workspace_gdb, return_period_grass_damage)
            if gp.exists(waterlevel):
                damage_grass = os.path.join(workspace_gdb, "damage_grass.asc")
                turtlebase.spatial.create_inundation_raster(lgn_k5_ascii, freeboard_ascii, waterlevel,
                                                           4, return_period_grass_damage, damage_grass, workspace, use_lgn=True)
                damage_raster_list.append(damage_grass)
                if output_waterdamage_total != '#':
                    # Waterdamage without lgn
                    damage_total_grass = os.path.join(workspace_gdb, "damage_total_grass.asc")
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
            turtlebase.spatial.merge_ascii(damage_total_raster_list, output_waterdamage_total, workspace)
        #----------------------------------------------------------------------------------------
        # calculate percentage inundation
        """
        input:
        - inundatie / overlast (raster dataset)
        - input_voronoi_polygon (met GPGIDENT) (feature class)
        - lgn_k5 (raster dataset)
        """
        gpgident_field = config.get('General', 'gpgident')
        # dissolve voronoi based on gpgident

        log.debug("dissolve voronoi polygons, based on gpgident")
        temp_fc_gpgident = os.path.join(workspace_gdb, "temp_fc_gpgident")
        gp.Dissolve_management(temp_voronoi, temp_fc_gpgident, gpgident_field)

        # Calculate area total, gpgident
        if not turtlebase.arcgis.is_fieldname(gp, temp_fc_gpgident, "area_total"):
            gp.addfield(temp_fc_gpgident, "area_total", "Double")
        turtlebase.arcgis.calculate_area(gp, temp_fc_gpgident, "area_total")

        gpgident_dict = nens.gp.get_table(gp, temp_fc_gpgident, primary_key=gpgident_field.lower())
        log.debug("gpgident_dict: %s" % gpgident_dict)

        # create feature class from lgn k5 ascii
        output_reclass_lgn = os.path.join(workspace_gdb, "reclass_lgn")
        gp.ASCIIToRaster_conversion(lgn_k5_ascii, output_reclass_lgn)
        temp_fc_lgn = os.path.join(workspace_gdb, "fc_lgn")
        gp.RasterToPolygon_conversion(output_reclass_lgn, temp_fc_lgn, "NO_SIMPLIFY")

        # union lgn with gpg-areas
        temp_fc_union_lgn = os.path.join(workspace_gdb, "fc_union_lgn")
        gp.Union_analysis(temp_fc_gpgident + ";" + temp_fc_lgn, temp_fc_union_lgn)
        dissolve_lyr = turtlebase.arcgis.get_random_layer_name()
        gp.MakeFeatureLayer_management(temp_fc_union_lgn, dissolve_lyr, "%s <> ''" % gpgident_field)
        temp_fc_dissolve_lgn = os.path.join(workspace_gdb, "dissolve_lgn")
        if turtlebase.arcgis.is_fieldname(gp, dissolve_lyr, "GRIDCODE"):
            gp.Dissolve_management(dissolve_lyr, temp_fc_dissolve_lgn, "%s; GRIDCODE" % gpgident_field)
            gridcode = "gridcode"
        elif turtlebase.arcgis.is_fieldname(gp, dissolve_lyr, "grid_code"):
            gp.Dissolve_management(dissolve_lyr, temp_fc_dissolve_lgn, "%s; grid_code" % gpgident_field)
            gridcode = "grid_code"
        else:
            log.error("no field GRIDCODE or grid_code available in %s" % dissolve_lyr)
            sys.exit(2)

        # Calculate area lgn
        if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_lgn, "area_lgn"):
            gp.addfield(temp_fc_dissolve_lgn, "area_lgn", "Double")
        turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_lgn, "area_lgn")

        lgn_dict = nens.gp.get_table(gp, temp_fc_dissolve_lgn)
        translate_lgn_dict = translate_dict(lgn_dict, gridcode, 'area_lgn')
        log.debug("translate_lgn_dict: %s" % translate_lgn_dict)

        # Create feature class from inundation_grid
        """ values: 10, 25, 50, 100"""
        if output_inundation_exists == 0:
            temp_fc_inundation = os.path.join(workspace_gdb, "inundation")
            log.info(output_inundation)
            gp.RasterToPolygon_conversion(output_inundation, temp_fc_inundation, "NO_SIMPLIFY")
            temp_fc_union_inundation = os.path.join(workspace_gdb, "union_inun")
            gp.Union_analysis(temp_fc_dissolve_lgn + ";" + temp_fc_inundation, temp_fc_union_inundation)
            dissolve_inundation_lyr = turtlebase.arcgis.get_random_layer_name()
            if turtlebase.arcgis.is_fieldname(gp, temp_fc_union_inundation, "GRIDCODE_1"):
                gp.MakeFeatureLayer_management(temp_fc_union_inundation, dissolve_inundation_lyr, "GRIDCODE_1 > 0")
                gridcode_1 = "gridcode_1"
            elif turtlebase.arcgis.is_fieldname(gp, temp_fc_union_inundation, "GRID_CODE1"):
                gp.MakeFeatureLayer_management(temp_fc_union_inundation, dissolve_inundation_lyr, "GRID_CODE1 > 0")
                gridcode_1 = "grid_code1"
            elif turtlebase.arcgis.is_fieldname(gp, temp_fc_union_inundation, "GRID_CODE_1"):
                gp.MakeFeatureLayer_management(temp_fc_union_inundation, dissolve_inundation_lyr, "GRID_CODE_1 > 0")
                gridcode_1 = "grid_code_1"
            else:
                log.error("No field available named gridcode_1 or grid_code1")
                log.warning(nens.gp.get_table_def(gp, temp_fc_union_inundation))
                sys.exit(1)
            temp_fc_dissolve_inundation = os.path.join(workspace_gdb, "dissolve_inun")
            dissolve_string = "%s;%s;%s" % (gpgident_field.upper(), gridcode, gridcode_1)
            log.debug(" - dissolve layer: %s" % dissolve_inundation_lyr)
            gp.Dissolve_management(dissolve_inundation_lyr, temp_fc_dissolve_inundation, dissolve_string)

            # Calculate area inundation
            if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_inundation, "area_inund"):
                gp.addfield(temp_fc_dissolve_inundation, "area_inun", "Double")
            turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_inundation, "area_inun")

            inundation_dict = nens.gp.get_table(gp, temp_fc_dissolve_inundation)
            translate_inundation_dict = translate_dict(inundation_dict, gridcode_1, 'area_inun')
            log.debug("translate_inundation_dict: %s" % translate_inundation_dict)
        else:
            translate_inundation_dict = {}

        # Create feature class from waterdamage grid
        """ values: 10, 15, 25"""
        if output_waterdamage_exists == 0:
            try:
                temp_fc_waterdamage = os.path.join(workspace_gdb, "damage")
                gp.RasterToPolygon_conversion(output_waterdamage, temp_fc_waterdamage, "NO_SIMPLIFY")
                waterdamage = True
            except:
                log.warning("waterdamage raster is empty")
                waterdamage = False

            if waterdamage:
                temp_fc_union_waterdamage = os.path.join(workspace_gdb, "damage_union")
                gp.Union_analysis(temp_fc_dissolve_lgn + ";" + temp_fc_waterdamage, temp_fc_union_waterdamage)

                dissolve_waterdamage_lyr = turtlebase.arcgis.get_random_layer_name()
                gp.MakeFeatureLayer_management(temp_fc_union_waterdamage, dissolve_waterdamage_lyr, "%s > 0" % gridcode_1)

                temp_fc_dissolve_waterdamage = os.path.join(workspace_gdb, "dissolve_damage")
                gp.Dissolve_management(dissolve_waterdamage_lyr, temp_fc_dissolve_waterdamage, "%s; %s; %s" % (gpgident_field, gridcode, gridcode_1))

                # Calculate area waterdamage
                if not turtlebase.arcgis.is_fieldname(gp, temp_fc_dissolve_waterdamage, "area_damag"):
                    gp.addfield(temp_fc_dissolve_waterdamage, "area_damag", "Double")
                turtlebase.arcgis.calculate_area(gp, temp_fc_dissolve_waterdamage, "area_damag")

                waterdamage_dict = nens.gp.get_table(gp, temp_fc_dissolve_waterdamage)
                translate_waterdamage_dict = translate_dict(waterdamage_dict, gridcode_1, 'area_damag')
                log.debug("translate_waterdamage_dict: %s" % translate_waterdamage_dict)
            else:
                translate_waterdamage_dict = {}
        else:
            translate_waterdamage_dict = {}

        no_data_value = float(config.get('naverwerking_rrcf', 'no_data_value'))
        result_dict = {}
        log.info("Calculating results")
        for gpgident, fields in gpgident_dict.items():
            # area_total
            #area_total = fields['area_total']

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

            if gpgident in translate_inundation_dict:
                log.debug("Calculate percentage inundation for %s" % gpgident)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_stedelijk')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_inundatie_stedelijk')
                toetsing_inundation_urban, percentage_inundation_urban = calculate_toetsing(translate_inundation_dict,
                                                                                            gpgident, 1, translate_lgn_dict,
                                                                                            hhtijd, toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_hoogwaardig')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_inundatie_hoogwaardig')
                toetsing_inundation_agriculture, percentage_inundation_agriculture = calculate_toetsing(translate_inundation_dict,
                                                                                                        gpgident, 2, translate_lgn_dict,
                                                                                                        hhtijd, toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_akker')
                toetsing_perc = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_akker')
                toetsing_inundation_rural, percentage_inundation_rural = calculate_toetsing(translate_inundation_dict, gpgident,
                                                               3, translate_lgn_dict, hhtijd,
                                                               toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_inundatie_grasland')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_inundatie_grasland')
                toetsing_inundation_grass, percentage_inundation_grass = calculate_toetsing(translate_inundation_dict, gpgident,
                                                               4, translate_lgn_dict, hhtijd,
                                                               toetsing_perc, no_data_value)

            if gpgident in translate_waterdamage_dict:
                log.debug("Calculate percentage waterdamage for %s" % gpgident)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_stedelijk')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_overlast_stedelijk')
                toetsing_waterdamage_urban, percentage_waterdamage_urban = calculate_toetsing(translate_inundation_dict, gpgident,
                                                                                              1, translate_lgn_dict, hhtijd,
                                                                                              toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_hoogwaardig')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_overlast_hoogwaardig')
                toetsing_waterdamage_agriculture, percentage_waterdamage_agriculture = calculate_toetsing(translate_inundation_dict, gpgident,
                                                                                                          2, translate_lgn_dict, hhtijd,
                                                                                                          toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_akker')
                toetsing_perc = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_akker')
                toetsing_inundation_rural, percentage_waterdamage_rural = calculate_toetsing(translate_inundation_dict, gpgident,
                                                                                             3, translate_lgn_dict, hhtijd,
                                                                                             toetsing_perc, no_data_value)

                hhtijd = config.get('naverwerking_rrcf', 'herhalingstijd_overlast_grasland')
                toetsing_perc = config.get('naverwerking_rrcf', 'percentage_overlast_grasland')
                toetsing_inundation_grass, percentage_waterdamage_grass = calculate_toetsing(translate_inundation_dict, gpgident,
                                                                                             4, translate_lgn_dict, hhtijd,
                                                                                             toetsing_perc, no_data_value)

            result_dict[gpgident] = {
                    gpgident_field: gpgident,
                    config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_stedelijk'):
                                     percentage_inundation_urban,
                    config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_hoogwaardig'):
                                     percentage_inundation_agriculture,
                    config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_akker'):
                                     percentage_inundation_rural,
                    config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_grasland'):
                                      percentage_inundation_grass,
                    config.get('naverwerking_rrcf',
                            'field_percentage_overlast_stedelijk'):
                                      percentage_waterdamage_urban,
                    config.get('naverwerking_rrcf',
                            'field_percentage_overlast_hoogwaardig'):
                                      percentage_waterdamage_agriculture,
                    config.get('naverwerking_rrcf',
                            'field_percentage_overlast_akker'):
                                      percentage_waterdamage_rural,
                    config.get('naverwerking_rrcf',
                            'field_percentage_overlast_grasland'):
                                     percentage_waterdamage_grass,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_stedelijk'):
                                     toetsing_inundation_urban,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_hoogwaardig'):
                                      toetsing_inundation_agriculture,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_akker'):
                                     toetsing_inundation_rural,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_grasland'):
                                     toetsing_inundation_grass,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_stedelijk'):
                                     toetsing_waterdamage_urban,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_hoogwaardig'):
                                     toetsing_waterdamage_agriculture,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_akker'):
                                     toetsing_waterdamage_rural,
                    config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_grasland'):
                                     toetsing_waterdamage_grass,
                                     }
        #---------------------------------------------------------------------
        # Create output table
        if not gp.exists(output_result_table):
            log.info("Create new output table")
            temp_result_table = os.path.join(workspace_gdb, "result_table")
            gp.CreateTable_management(os.path.dirname(temp_result_table), os.path.basename(temp_result_table))
            copy_table = True
        else:
            temp_result_table = output_result_table
            copy_table = False

        fields_to_add = [config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_stedelijk'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_hoogwaardig'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_akker'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_inundatie_grasland'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_overlast_stedelijk'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_overlast_hoogwaardig'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_overlast_akker'),
                         config.get('naverwerking_rrcf',
                            'field_percentage_overlast_grasland'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_stedelijk'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_hoogwaardig'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_akker'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_inundatie_grasland'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_stedelijk'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_hoogwaardig'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_akker'),
                         config.get('naverwerking_rrcf',
                            'field_toetsing_overlast_grasland')]

        if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, gpgident_field):
            log.debug(" - add field %s to %s" % (gpgident_field, temp_result_table))
            gp.addfield_management(temp_result_table, gpgident_field, 'text')

        for field in fields_to_add:
            if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, field):
                log.debug(" - add field %s to %s" % (field, temp_result_table))
                gp.addfield_management(temp_result_table, field, 'double')

        #----------------------------------------------------------------------------------------
        # Write results to output table
        log.info("Write results to output table")
        turtlebase.arcgis.write_result_to_output(temp_result_table, gpgident_field.lower(), result_dict)

        if copy_table == True:
            gp.TableToTable_conversion(temp_result_table, os.path.dirname(output_result_table), os.path.basename(output_result_table))

        #---------------------------------------------------------------------
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
                    
        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
