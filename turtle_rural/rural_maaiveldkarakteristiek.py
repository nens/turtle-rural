# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import tempfile
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import arcpy
import numpy

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
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        log.debug(" - check voronoi polygon: %s" % input_level_area_fc)
        if gp.describe(input_level_area_fc).ShapeType != 'Polygon':
            log.error("%s is not a polygon feature class!",
                      input_level_area_fc)
            geometry_check_list.append(input_level_area_fc + " -> (Polygon)")

        if gp.describe(input_ahn_raster).PixelType[0] not in ['F']:
            log.info(gp.describe(input_ahn_raster).PixelType)
            log.error("Input AHN is an integer raster, \
                    for this script a float is necessary")
            geometry_check_list.append(input_ahn_raster + " -> (Float)")

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

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
        #temp_level_area = os.path.join(workspace_gdb, "peilgebieden")
        #gp.select_analysis(input_level_area_fc, temp_level_area)
        # use extent from level area
        #gp.extent = gp.describe(temp_level_area).extent

        #---------------------------------------------------------------------
        rows = arcpy.SearchCursor(input_level_area_table)
        surface_level = {}
        for row in rows:
            gpg_id = row.GPGIDENT
            streefpeil = row.ZOMERPEIL
            surface_level[gpg_id] = streefpeil

        # create ahn ascii
        log.info("Create array from ahn")
        mv_procent_str = config.get('maaiveldkarakteristiek', 'mv_procent')
        field_range = mv_procent_str.split(', ')

        shapeName = arcpy.Describe(input_level_area_fc).shapeFieldName
        in_rows = arcpy.SearchCursor(input_level_area_fc)
        out_rows = arcpy.InsertCursor(output_surface_table)
        for in_row in in_rows:
            gpg_id = in_row.GPGIDENT
            log.info("calculate s-curve for %s" % gpg_id)
            streefpeil = float(surface_level[gpg_id])
            peilgebied = in_row.getValue(shapeName)
            ahn_temp = turtlebase.arcgis.get_random_file_name(workspace)
            arcpy.env.pyramid = "NONE"
            arcpy.Clip_management(input_ahn_raster, "#", ahn_temp, peilgebied, "#", "ClippingGeometry")

            myArray = arcpy.RasterToNumPyArray(ahn_temp)
            masked_array = myArray[myArray > -9999]
            total_cells = len(masked_array)
            boven_streefpeil = masked_array[masked_array > streefpeil]
            beneden_streefpeil = masked_array[masked_array < streefpeil]
            out_row = out_rows.newRow()
            out_row.setValue("GPGIDENT", gpg_id)
            if total_cells > 0:
                procent_beneden_mv = (len(beneden_streefpeil) / total_cells) * 100
                out_row.setValue("MV_Opm", "%s procent beneden streefpeil" % procent_beneden_mv)
            if len(boven_streefpeil) > 0:
                for p in field_range:
                    percentage = numpy.percentile(boven_streefpeil, float(p))
                    #log.info("percentage (%s): %s" % (p, percentage))
                    out_row.setValue("MV_HGT_%s" % int(p), float(percentage))

            out_rows.insertRow(out_row)

            del myArray
            del boven_streefpeil
            del beneden_streefpeil

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
