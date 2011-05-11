# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.spatial
import turtlebase.general

log = logging.getLogger(__name__)


def join_waterlevel_to_level_area(gp, fc_level_area, area_ident,
                                  return_periods, waterlevel_dict):
    """
    join waterlevels from waterlevel_dict to level areas
    """
    log.debug(" - update records")
    for return_period in return_periods:
        if not turtlebase.arcgis.is_fieldname(
            gp, fc_level_area, "WS_%s" % return_period):
                log.debug(" - add field WS_%s" % return_period)
                gp.addfield_management(fc_level_area,
                                "WS_%s" % return_period, "Double")

    row = gp.UpdateCursor(fc_level_area)

    for item in nens.gp.gp_iterator(row):
        item_id = item.GetValue(area_ident)
        log.debug(" - update waterlevel for %s" % item_id)
        if item_id in waterlevel_dict:
            for return_period in return_periods:
                waterlevel_value = float(
                    waterlevel_dict[item_id][
                        "ws_%s" % return_period]) / 100
                item.SetValue("WS_%s" % return_period, waterlevel_value)
        else:
            for return_period in return_periods:
                item.SetValue("WS_%s" % return_period, -999)
        row.UpdateRow(item)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        # --------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = (
            turtlebase.arcgis.create_temp_geodatabase(gp, workspace)())
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        # --------------------------------------------------------------------
        # check inputfields
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
            log.error("Usage: python rural_inundatie.py <peilgebieden feature>\
                <input_waterlevel_table> <input_ahn_raster> <output grid>")
            sys.exit(1)

        # --------------------------------------------------------------------
        #check input parameters
        log.info('Checking presence of input files... ')
        if not(gp.exists(input_peilgebieden)):
            log.error("inputfile peilgebieden: %s does not exist!",
                      input_peilgebieden)
            sys.exit(5)
        if not(gp.exists(input_waterlevel_table)):
            log.error("inputfile resultaten: %s does not exist!",
                      input_waterlevel_table)
            sys.exit(5)
        if not(gp.exists(input_ahn_raster)):
            log.error("inputfile hoogtegrid: %s does not exist!",
                      input_ahn_raster)
            sys.exit(5)

        log.info('input parameters checked... ')
        # --------------------------------------------------------------------
        # Check geometry input parameters
        cellsize = config.get('Inundatie', 'cellsize')

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
            log.error("Cell size of AHN is %s, must be 25",
                      gp.describe(input_ahn_raster).MeanCellHeight)
            geometry_check_list.append(input_ahn_raster + " -> (Cellsize %s)",
                                       cellsize)

        if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
            log.error("Input AHN is a floating point raster,\
             for this script an integer is nessecary")
            geometry_check_list.append(input_ahn_raster + " -> (Integer)")

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

        log.info('input format checked... ')
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")
        gpgident = config.get('General', 'gpgident')

        missing_fields = []

        # create return period list
        return_periods = config.get(
            'Inundatie', 'herhalingstijden').split(", ")
        log.debug(" - return periods: %s" % return_periods)

        # <check required fields from input data,
        # append them to list if missing>"
        if not turtlebase.arcgis.is_fieldname(
                    gp, input_peilgebieden, gpgident):
            log.debug(" - missing: %s in %s",
                      (gpgident, input_peilgebieden))
            missing_fields.append("%s: %s",
                    (input_peilgebieden, gpgident))

        if not turtlebase.arcgis.is_fieldname(
                gp, input_waterlevel_table, gpgident):
            log.debug(" - missing: %s in %s",
                      (gpgident, input_waterlevel_table))
            missing_fields.append("%s: %s",
                    (input_waterlevel_table, gpgident))

        for return_period in return_periods:
            if not turtlebase.arcgis.is_fieldname(
                    gp, input_waterlevel_table, "WS_%s" % return_period):
                log.debug(" - missing: %s in %s" % ("WS_%s",
                                return_period, input_waterlevel_table))
                missing_fields.append("%s: %s",
                        (input_waterlevel_table, "WS_%s" % return_period))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)

        #---------------------------------------------------------------------
        # Environments
        log.info("Setting environments")
        temp_peilgebieden = (
                turtlebase.arcgis.get_random_file_name(workspace_gdb))
        log.debug(" - export level areas")
        gp.select_analysis(input_peilgebieden, temp_peilgebieden)

        # use extent from level areas
        gp.extent = gp.describe(temp_peilgebieden).extent

        # add waterlevel to peilgebieden
        log.info("Read waterlevels from table")
        waterlevel_dict = nens.gp.get_table(
            gp, input_waterlevel_table, primary_key=gpgident.lower())
        join_waterlevel_to_level_area(
                    gp, temp_peilgebieden, gpgident,
                    return_periods, waterlevel_dict)

        #---------------------------------------------------------------------
        log.info("A) Create rasters for waterlevels")
        # Create waterlevel rasters
        if output_folder_waterlevel == "#":
            output_folder_waterlevel = workspace_gdb

        for return_period in return_periods:
            log.info(" - create raster for ws_%s" % return_period)
            out_raster_dataset = (output_folder_waterlevel + "/ws_%s",
                                  return_period)
            if not gp.exists(out_raster_dataset):
                gp.FeatureToRaster_conversion(temp_peilgebieden, "WS_%s",
                                return_period, out_raster_dataset, cellsize)
            else:
                log.error("output waterlevel raster already exists,\
                delete this first or change output folder")
                sys.exit(1)

        #---------------------------------------------------------------------
        log.info("B) Create Inundation raster")
        inundation_raster_list = []

        # create ahn ascii
        ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        log.debug("ahn ascii: %s" % ahn_ascii)
        gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

        # inundatie stedelijk
        return_period_urban = config.get(
            'Inundatie', 'herhalingstijd_inundatie_stedelijk')
        if config.get('Inundatie', 'percentage_inundatie_stedelijk') != "-":
            log.debug(" - create inundation urban")
            waterlevel = "%s/ws_%s" % (
                output_folder_waterlevel, return_period_urban)
            if gp.exists(waterlevel):
                inundation_urban = turtlebase.arcgis.get_random_file_name(
                                                          workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(
                                    ahn_ascii, ahn_ascii, waterlevel, 1,
                                    return_period_urban, inundation_urban,
                                    workspace, use_lgn=False)
                inundation_raster_list.append(inundation_urban)
            else:
                log.error("%s does not exists! check ini-file and tempfolder",
                        waterlevel)

        # inundatie hoogwaardige landbouw
        return_period_agriculture = config.get(
            'Inundatie', 'herhalingstijd_inundatie_hoogwaardig')
        if config.get('Inundatie', 'percentage_inundatie_hoogwaardig') != "-":
            log.debug(" - create inundation agriculture")
            waterlevel = "%s/ws_%s" % (
                        output_folder_waterlevel, return_period_agriculture)
            if gp.exists(waterlevel):
                # Inundation with lgn
                inundation_agriculture = (
                    turtlebase.arcgis.get_random_file_name(
                                            workspace, ".asc"))
                turtlebase.spatial.create_inundation_raster(
                                    ahn_ascii, ahn_ascii, waterlevel,
                                    2, return_period_agriculture,
                                    inundation_agriculture, workspace,
                                    use_lgn=False)
                inundation_raster_list.append(inundation_agriculture)
            else:
                log.error("%s does not exists! check ini-file and tempfolder",
                          waterlevel)

        # inundatie akkerbouw
        return_period_rural = config.get(
            'Inundatie', 'herhalingstijd_inundatie_akker')
        if config.get('Inundatie', 'percentage_inundatie_akker') != "-":
            log.debug(" - create inundation rural")
            waterlevel = "%s/ws_%s" % (
                output_folder_waterlevel, return_period_rural)
            if gp.exists(waterlevel):
                inundation_rural = turtlebase.arcgis.get_random_file_name(
                                                        workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(
                                ahn_ascii, ahn_ascii, waterlevel,
                                3, return_period_rural, inundation_rural,
                                workspace, use_lgn=False)
                inundation_raster_list.append(inundation_rural)
            else:
                log.error("%s does not exists! check ini-file and tempfolder",
                          waterlevel)

        # inundatie grasland
        return_period_grass = config.get(
            'Inundatie', 'herhalingstijd_inundatie_grasland')
        if config.get('Inundatie', 'percentage_inundatie_grasland') != "-":
            log.debug(" - create inundation grass")
            waterlevel = ("%s/ws_%s",
                          (output_folder_waterlevel, return_period_grass))
            if gp.exists(waterlevel):
                inundation_grass = turtlebase.arcgis.get_random_file_name(
                                                        workspace, ".asc")
                turtlebase.spatial.create_inundation_raster(
                                ahn_ascii, ahn_ascii, waterlevel,
                                4, return_period_grass, inundation_grass,
                                workspace, use_lgn=False)
                inundation_raster_list.append(inundation_grass)
            else:
                log.error("%s does not exists! check ini-file and tempfolder",
                          waterlevel)

        if len(inundation_raster_list) > 1:
            log.info(" - merge inundation rasters")
            turtlebase.spatial.merge_ascii(
                inundation_raster_list, output_inundation, workspace)
        else:
            log.error("there are no inundation rasters available")

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            #gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

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
