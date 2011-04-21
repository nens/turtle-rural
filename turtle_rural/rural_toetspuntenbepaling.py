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


def create_output_table(gp, output_table, area_ident, toetspunten_fields):
    """
    creates a new table when the table does not exist..
    adds all fields thats are needed for writing output
    """
    if not gp.exists(output_table):
        gp.CreateTable_management(os.path.dirname(output_table),
                                  os.path.basename(output_table))

    for fieldname in toetspunten_fields:
        if not turtlebase.arcgis.is_fieldname(gp, output_table, fieldname):
            gp.addfield_management(output_table, fieldname, "Double")

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'SOURCE'):
        gp.addfield_management(output_table, 'SOURCE', "Text", "#", "#", '256')

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'DATE_TIME'):
        gp.addfield_management(output_table,
                               'DATE_TIME', "Text", "#", "#", '40')

    if not turtlebase.arcgis.is_fieldname(gp, output_table, 'COMMENTS'):
        gp.addfield_management(output_table, 'COMMENTS',
                               "Text", "#", "#", '256')


def add_integer_ident(gp, temp_level_area, id_int_field, area_ident):
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
        if item_id in area_id_dict:
            item.SetValue(id_int_field, area_id_dict[item_id][id_int_field])
        else:
            item.SetValue(id_int_field, x)
            area_id_dict[item_id] = {id_int_field: x}
            x += 1
        row.UpdateRow(item)

    return area_id_dict


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

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                            gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #---------------------------------------------------------------------
        # check inputfields
        log.info("Getting commandline parameters... ")
        if len(sys.argv) == 8:
            input_level_area_fc = sys.argv[1]
            input_level_area_table = sys.argv[2]
            input_ahn_raster = sys.argv[3]
            input_lgn_raster = sys.argv[4]
            input_lgn_conversion = sys.argv[5]
            input_onderbemalingen = sys.argv[6]
            if input_onderbemalingen == "#":
                use_onderbemalingen = False
            else:
                use_onderbemalingen = True
            output_file = sys.argv[7]
        else:
            log.error("Usage: python toetspuntenbepaling.py <ahn-file> \
                        <lgn-file> <onderbemalingen-optional> \
                        <peilgebieden-feature> <peilvakgegevens-table> \
                        <conversietabel> <outputfile-HydroBase>")
            sys.exit(1)
        #---------------------------------------------------------------------
        # check input parameters
        log.info('Checking presence of input files... ')
        if not(gp.exists(input_level_area_fc)):
            log.error("inputfile peilgebieden %s does not exist!",
                      input_level_area_fc)
            sys.exit(5)
        if not(gp.exists(input_level_area_table)):
            log.error("inputfile peilvakgegevens %s does not exist!",
                      input_level_area_table)
            sys.exit(5)
        if (use_onderbemalingen and not(gp.exists(input_onderbemalingen))):
            log.error("inputfile onderbemalingen %s does not exist!",
                      input_onderbemalingen)
            sys.exit(5)

        log.info('input parameters checked... ')

        #---------------------------------------------------------------------
        # Check geometry input parameters
        cellsize = config.get('toetspunten', 'cellsize')

        log.info("Check geometry of input parameters")
        geometry_check_list = []

        log.debug(" - check level area: %s" % input_level_area_fc)
        if gp.describe(input_level_area_fc).ShapeType != 'Polygon':
            errormsg = ("%s is not a polygon feature class!",
                        input_level_area_fc)
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if turtlebase.arcgis.fc_is_not_empty(gp, input_level_area_fc):
            errormsg = "input '%s' is empty" % input_level_area_fc
            log.error(errormsg)
            sys.exit(1)

        if turtlebase.arcgis.fc_is_not_empty(gp, input_level_area_table):
            errormsg = "input '%s' is empty" % input_level_area_table
            log.error(errormsg)
            sys.exit(1)

        if use_onderbemalingen:
            if turtlebase.arcgis.fc_is_not_empty(gp, input_onderbemalingen):
                errormsg = "input '%s' is empty" % input_onderbemalingen
                log.error(errormsg)
                sys.exit(1)

        log.debug(" - check ahn raster %s" % input_ahn_raster)
        if gp.describe(input_ahn_raster).DataType != 'RasterDataset':
            log.error("Input AHN is not a raster dataset")
            sys.exit(1)

        if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
            errormsg = ("Input AHN is a floating point raster, \
                        for this script an integer is nessecary")
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if gp.describe(input_ahn_raster).MeanCellHeight != float(cellsize):
            errormsg = ("Cell size of AHN is %s, must be 25",
                        gp.describe(input_ahn_raster).MeanCellHeight)
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        log.debug(" - check ahn raster %s" % input_lgn_raster)
        if gp.describe(input_lgn_raster).DataType != 'RasterDataset':
            log.error("Input LGN is not a raster dataset")
            sys.exit(1)

        if gp.describe(input_lgn_raster).PixelType[0] not in ['U', 'S']:
            errormsg = ("Input LGN is a floating point raster, \
                        for this script an integer is nessecary")
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if gp.describe(input_lgn_raster).MeanCellHeight != float(cellsize):
            errormsg = ("Cell size of LGN is %s, must be 25",
                        gp.describe(input_lgn_raster).MeanCellHeight)
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")
        gpgident = config.get('GENERAL', 'gpgident')
        streefpeil = config.get('toetspunten', 'field_streefpeil')

        missing_fields = []

        # check required fields from input data, append them to list if missing
        if not turtlebase.arcgis.is_fieldname(
                    gp, input_level_area_fc, gpgident):
            log.debug(" - missing: %s in %s", (
                        gpgident, input_level_area_fc))
            missing_fields.append("%s: %s", (
                        input_level_area_fc, gpgident))

        if not turtlebase.arcgis.is_fieldname(
                    gp, input_level_area_table, gpgident):
            log.debug(" - missing: %s in %s", (
                        gpgident, input_level_area_table))
            missing_fields.append("%s: %s", (
                        input_level_area_table, gpgident))

        if not turtlebase.arcgis.is_fieldname(
                    gp, input_level_area_table, streefpeil):
            log.debug(" - missing: %s in %s", (
                        streefpeil, input_level_area_table))
            missing_fields.append("%s: %s", (
                        input_level_area_table, streefpeil))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s", missing_fields)
            sys.exit(2)

        #---------------------------------------------------------------------
        # Environments
        log.info("Set environments")
        temp_level_area = os.path.join(workspace_gdb, "peilgebieden")
        if input_level_area_fc.endswith(".shp"):
            log.info("Copy features of level areas to workspace")
            gp.select_analysis(input_level_area_fc, temp_level_area)
        else:
            log.info("Copy level areas to workspace")
            gp.copy_management(input_level_area_fc, temp_level_area)
        # use extent from level area
        gp.extent = gp.describe(temp_level_area).extent

        #---------------------------------------------------------------------
        # Create K5 LGN
        log.info("Translate LGN to NBW-classes")
        lgn_ascii = turtlebase.arcgis.get_random_file_name(
                                            workspace, ".asc")
        lgn_k5_ascii = turtlebase.arcgis.get_random_file_name(
                                            workspace, ".asc")

        gp.RasterToASCII_conversion(input_lgn_raster, lgn_ascii)
        lgn_ident = config.get('toetspunten', 'lgn_conv_ident')

        if input_lgn_conversion != '#':
            reclass_dict = nens.gp.get_table(gp, input_lgn_conversion,
                                             primary_key=lgn_ident)
            turtlebase.spatial.reclass_lgn_k5(
                            lgn_ascii, lgn_k5_ascii, reclass_dict)
        else:
            turtlebase.spatial.reclass_lgn_k5(lgn_ascii, lgn_k5_ascii)
        #---------------------------------------------------------------------
        # create ahn ascii
        log.info("Create ascii from ahn")

        ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        log.debug("ahn ascii: %s" % ahn_ascii)
        gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

        #---------------------------------------------------------------------
        # Change ahn and lgn if use_ondermalingen == True
        if use_onderbemalingen:
            log.info("Cut out level deviations")
            gridcode_fieldname = "GRIDCODE"
            if not turtlebase.arcgis.is_fieldname(
                    gp, input_onderbemalingen, gridcode_fieldname):
                log.debug(" - add field %s" % gridcode_fieldname)
                gp.addfield_management(
                    input_onderbemalingen, gridcode_fieldname, "Short")

            row = gp.UpdateCursor(input_onderbemalingen)
            for item in nens.gp.gp_iterator(row):
                item.SetValue(gridcode_fieldname, 1)
                row.UpdateRow(item)

            onderbemaling_raster = turtlebase.arcgis.get_random_file_name(
                                                            workspace_gdb)
            gp.FeatureToRaster_conversion(
                            input_onderbemalingen, gridcode_fieldname,
                            onderbemaling_raster, cellsize)

            onderbemaling_asc = turtlebase.arcgis.get_random_file_name(
                                                    workspace, ".asc")
            gp.RasterToASCII_conversion(onderbemaling_raster,
                                        onderbemaling_asc)

            ahn_ascii = turtlebase.spatial.cut_out_onderbemaling(
                            ahn_ascii, onderbemaling_asc, workspace)
            lgn_k5_ascii = turtlebase.spatial.cut_out_onderbemaling(
                            lgn_k5_ascii, onderbemaling_asc, workspace)

        #---------------------------------------------------------------------
        # Add ID Int to level area
        log.info("Create level area ascii")
        id_int = 'id_int'
        area_id_dict = add_integer_ident(gp, temp_level_area,
                                         id_int, gpgident)

        out_raster_dataset = turtlebase.arcgis.get_random_file_name(
                                                        workspace_gdb)
        gp.FeatureToRaster_conversion(temp_level_area, id_int,
                                      out_raster_dataset, cellsize)

        id_int_ascii = turtlebase.arcgis.get_random_file_name(
                                            workspace, ".asc")
        log.debug("id_int_ascii: %s" % id_int_ascii)
        gp.RasterToASCII_conversion(out_raster_dataset, id_int_ascii)

        #---------------------------------------------------------------------
        log.info("Read targetlevel table")
        area_level_dict = nens.gp.get_table(gp, input_level_area_table,
                                            primary_key=gpgident)
        target_level_dict = {}

        for k, v in area_level_dict.items():
            if k in area_id_dict:
                id_int = area_id_dict[k][id_int]
                target_level_dict[id_int] = {'targetlevel': v[streefpeil],
                                             'gpgident': k}

        toetspunten_fields = ["DFLT_I_ST", "DFLT_I_HL", "DFLT_I_AK",
                              "DFLT_I_GR", "DFLT_O_ST", "DFLT_O_HL",
                              "DFLT_O_AK", "DFLT_O_GR", "MTGMV_I_ST",
                              "MTGMV_I_HL", "MTGMV_I_AK", "MTGMV_I_GR",
                              "MTGMV_O_ST", "MTGMV_O_HL", "MTGMV_O_AK",
                              "MTGMV_O_GR"]
        #---------------------------------------------------------------------
        log.info("calculate toetspunten")
        toetspunten_dict = turtlebase.spatial.calculcate_toetspunten(
                            ahn_ascii, lgn_k5_ascii, id_int_ascii,
                            toetspunten_fields, target_level_dict,
                            onderbemaling="#")
        #---------------------------------------------------------------------
        log.info("Create output table")
        create_output_table(gp, output_file, gpgident, toetspunten_fields)
        #---------------------------------------------------------------------
        # Add metadata
        import time
        date_time_str = time.strftime("%d %B %Y %H:%M:%S")
        source = input_ahn_raster

        for area_id, values in toetspunten_dict.items():
            toetspunten_dict[area_id]['date_time'] = date_time_str
            toetspunten_dict[area_id]['source'] = source

        #---------------------------------------------------------------------
        # Write results to output table
        log.info("Write results to output table")
        turtlebase.arcgis.write_result_to_output(
                    output_file, gpgident, toetspunten_dict)

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

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
