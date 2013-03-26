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

log = logging.getLogger(__name__)


def create_output_table(gp, output_surface_table, area_ident, field_range):
    """
    creates a new table when the table does not exist..
    adds all fields thats are needed for writing output
    """
    if not gp.exists(output_surface_table):
        gp.CreateTable_management(os.path.dirname(
                output_surface_table), os.path.basename(output_surface_table))

    if not turtlebase.arcgis.is_fieldname(
                    gp, output_surface_table, area_ident):
        gp.addfield_management(output_surface_table,
                    area_ident, "Text", "#", "#", '50')

    for field in field_range:
        if not turtlebase.arcgis.is_fieldname(
                    gp, output_surface_table, "MV_HGT_%s" % field):
            gp.addfield_management(
                    output_surface_table, "MV_HGT_%s" % field, "Double")

    if not turtlebase.arcgis.is_fieldname(gp, output_surface_table, 'SOURCE'):
        gp.addfield_management(output_surface_table,
                        'SOURCE', "Text", "#", "#", '256')

    if not turtlebase.arcgis.is_fieldname(
                gp, output_surface_table, 'DATE_TIME'):
        gp.addfield_management(output_surface_table,
                    'DATE_TIME', "Text", "#", "#", '40')

    if not turtlebase.arcgis.is_fieldname(
                gp, output_surface_table, 'COMMENTS'):
        gp.addfield_management(output_surface_table,
                'COMMENTS', "Text", "#", "#", '256')


def add_integer_ident(gp, temp_level_area, id_int_field, area_ident):
    """a
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
        if workspace == "-":
            workspace = tempfile.gettempdir()
        log.info("workspace: %s" % workspace)

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                                                gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #---------------------------------------------------------------------
        # Input parameters
        """
        nodig voor deze tool:
        """
        if len(sys.argv) == 5:
            input_level_area_fc = sys.argv[1]
            input_level_area_table = sys.argv[2]
            input_ahn_raster = sys.argv[3]
            output_surface_table = sys.argv[4]
        else:
            log.error("usage: <input_level_area_fc> <input_level_area_table> \
                    <input_ahn_raster> <output_surface_table>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        cellsize = gp.describe(input_ahn_raster).MeanCellHeight

        log.info("Check geometry of input parameters")
        geometry_check_list = []

        log.debug(" - check voronoi polygon: %s" % input_level_area_fc)
        if gp.describe(input_level_area_fc).ShapeType != 'Polygon':
            log.error("%s is not a polygon feature class!",
                      input_level_area_fc)
            geometry_check_list.append(input_level_area_fc + " -> (Polygon)")

        if gp.describe(input_ahn_raster).PixelType[0] not in ['U', 'S']:
            log.error("Input AHN is a floating point raster, \
                    for this script an integer is necessary")
            geometry_check_list.append(input_ahn_raster + " -> (Integer)")

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        else:
            print "A"
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        # <check required fields from input data,
        # append them to list if missing>"
        if not turtlebase.arcgis.is_fieldname(
                            gp, input_level_area_fc, config.get(
                            'maaiveldkarakteristiek',
                            'input_peilgebied_ident')):
            log.debug(" - missing: %s in %s" % (
                    config.get('maaiveldkarakteristiek',
                               'input_peilgebied_ident'), input_level_area_fc))
            missing_fields.append("%s: %s" % (
                    input_level_area_fc, config.get('maaiveldkarakteristiek',
                                                    'input_peilgebied_ident')))
        if not turtlebase.arcgis.is_fieldname(
                            gp, input_level_area_table, config.get(
                            'maaiveldkarakteristiek',
                            'input_peilgebied_ident')):
            log.debug(" - missing: %s in %s" % (
                    config.get('maaiveldkarakteristiek',
                               'input_peilgebied_ident'),
                    input_level_area_table))
            missing_fields.append("%s: %s" % (
                            input_level_area_table, config.get(
                                'maaiveldkarakteristiek',
                                'input_peilgebied_ident')))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments
        log.info("Set environments")
        temp_level_area = os.path.join(workspace_gdb, "peilgebieden")
        gp.select_analysis(input_level_area_fc, temp_level_area)
        # use extent from level area
        gp.extent = gp.describe(temp_level_area).extent

        #---------------------------------------------------------------------
        # create ahn ascii
        log.info("Create ascii from ahn")

        ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        log.debug("ahn ascii: %s" % ahn_ascii)
        gp.RasterToASCII_conversion(input_ahn_raster, ahn_ascii)

        #---------------------------------------------------------------------
        # Add ID Int to level area
        log.info("Create level area ascii")
        area_id_dict = add_integer_ident(gp, temp_level_area, config.get(
                    'maaiveldkarakteristiek', 'id_int').lower(),
                                         config.get('maaiveldkarakteristiek',
                                                    'input_peilgebied_ident'))

        out_raster_dataset = turtlebase.arcgis.get_random_file_name(
                                                        workspace_gdb)
        gp.FeatureToRaster_conversion(temp_level_area, config.get(
            'maaiveldkarakteristiek', 'id_int'), out_raster_dataset, cellsize)

        id_int_ascii = turtlebase.arcgis.get_random_file_name(
                            workspace, ".asc")
        log.debug("id_int_ascii: %s" % id_int_ascii)
        gp.RasterToASCII_conversion(out_raster_dataset, id_int_ascii)

        #---------------------------------------------------------------------
        log.info("Read targetlevel table")
        area_level_dict = nens.gp.get_table(
                            gp, input_level_area_table, primary_key=config.get(
                                'maaiveldkarakteristiek',
                                'input_peilgebied_ident').lower())
        target_level_dict = {}

        for k, v in area_level_dict.items():
            if k in area_id_dict:
                id_int = area_id_dict[k][config.get('maaiveldkarakteristiek',
                                                    'id_int').lower()]
                target_level_dict[id_int] = {
                            'targetlevel': v[config.get(
                            'maaiveldkarakteristiek',
                            'field_streefpeil').lower()],
                            'gpgident': k,
                                             }
        #---------------------------------------------------------------------
        log.info("create S-Curve")
        mv_procent_str = config.get('maaiveldkarakteristiek', 'mv_procent')
        field_range = mv_procent_str.split(', ')
        #scurve_dict = turtlebase.spatial.create_scurve(ahn_ascii,
        # id_int_ascii, target_level_dict, field_range)
        scurve_dict = turtlebase.spatial.surface_level_statistics(
                            ahn_ascii, id_int_ascii,
                            target_level_dict, field_range)
        #---------------------------------------------------------------------
        log.info("Create output table")
        create_output_table(gp, output_surface_table, config.get(
            'maaiveldkarakteristiek', 'input_peilgebied_ident'), field_range)
        #---------------------------------------------------------------------
        # Add metadata
        import time
        date_time_str = time.strftime("%d %B %Y %H:%M:%S")
        source = input_ahn_raster

        for k, v in scurve_dict.items():
            scurve_dict[k]['date_time'] = date_time_str
            scurve_dict[k]['source'] = source

        #---------------------------------------------------------------------
        # Write results to output table
        log.info("Write results to output table")
        turtlebase.arcgis.write_result_to_output(
                            output_surface_table, config.get(
                                'maaiveldkarakteristiek',
                                'input_peilgebied_ident').lower(), scurve_dict)

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
