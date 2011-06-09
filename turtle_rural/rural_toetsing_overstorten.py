# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import os
import sys
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.voronoi
import turtlebase.general

log = logging.getLogger(__name__)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 5:
            # input parameter
            input_external_weir = sys.argv[1]
            input_voronoi_polygon = sys.argv[2]
            input_rrcf_waterlevel = sys.argv[3]
            # output parameters
            output_table_external_weir = sys.argv[4]
        else:
            log.error("usage: <input_external_weir> <input_voronoi_polygon> <input rrcf waterlevel> <output_table_external_weir>")
            sys.exit(1)

        temp_voronoi = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.select_analysis(input_voronoi_polygon, temp_voronoi)
        #----------------------------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        log.debug(" - check input_external_weir: %s" % input_external_weir)
        if gp.describe(input_external_weir).ShapeType != 'Point':
            log.error("Input_external_weir is not a point feature class!")
            geometry_check_list.append(input_external_weir + " -> (Point)")

        log.debug(" - check voronoi polygon: %s" % temp_voronoi)
        if gp.describe(temp_voronoi).ShapeType != 'Polygon':
            log.error("Input voronoi is not a polygon feature class!")
            geometry_check_list.append(temp_voronoi + " -> (Polygon)")

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #----------------------------------------------------------------------------------------
        # Check required fields in database
        log.info("Check required fields in input data")

        missing_fields = []
        if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, config.get('toetsing_overstorten', 'calculation_point_ident')):
            log.debug(" - missing: %s in %s" % (config.get('toetsing_overstorten', 'calculation_point_ident'), temp_voronoi))
            missing_fields.append("%s: %s" % (temp_voronoi, config.get('toetsing_overstorten', 'calculation_point_ident')))

        if not turtlebase.arcgis.is_fieldname(gp, input_rrcf_waterlevel, config.get('toetsing_overstorten', 'field_waterstand')):
            log.debug(" - missing: %s in %s" % (config.get('toetsing_overstorten', 'field_waterstand'), input_rrcf_waterlevel))
            missing_fields.append("%s: %s" % (input_rrcf_waterlevel, config.get('toetsing_overstorten', 'field_waterstand')))

        if not turtlebase.arcgis.is_fieldname(gp, input_external_weir, config.get('toetsing_overstorten', 'overstort_ident')):
            log.debug(" - missing: %s in %s" % (config.get('toetsing_overstorten', 'overstort_ident'), input_external_weir))
            missing_fields.append("%s: %s" % (input_external_weir, config.get('toetsing_overstorten', 'overstort_ident')))

        if not turtlebase.arcgis.is_fieldname(gp, input_external_weir, config.get('toetsing_overstorten', 'drempelhoogte')):
            log.debug(" - missing: %s in %s" % (config.get('toetsing_overstorten', 'drempelhoogte'), input_external_weir))
            missing_fields.append("%s: %s" % (input_external_weir, config.get('toetsing_overstorten', 'drempelhoogte')))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        # read waterlevel table as a dictionary
        log.info("Read waterlevel table")
        waterlevel_dict = nens.gp.get_table(gp, input_rrcf_waterlevel, primary_key=config.get('toetsing_overstorten', 'calculation_point_ident').lower())
        log.debug(waterlevel_dict)

        # Add fields to output
        if not turtlebase.arcgis.is_fieldname(gp, temp_voronoi, config.get('toetsing_overstorten', 'field_waterstand')):
            log.info(" - add field %s" % config.get('toetsing_overstorten', 'field_waterstand'))
            gp.addfield(temp_voronoi, "%s" % config.get('toetsing_overstorten', 'field_waterstand'), "double")

        # copy waterlevel to voronoi polygons
        rows = gp.UpdateCursor(temp_voronoi)
        for row in nens.gp.gp_iterator(rows):
            row_id = row.GetValue(config.get('toetsing_overstorten', 'calculation_point_ident'))
            if waterlevel_dict.has_key(row_id):
                log.debug(waterlevel_dict[row_id])
                row.SetValue(config.get('toetsing_overstorten', 'field_waterstand'), waterlevel_dict[row_id][config.get('toetsing_overstorten', 'field_waterstand').lower()])

                rows.UpdateRow(row)

        #----------------------------------------------------------------------------------------
        # Join external weirs to voronoi using spatial location (spatial join)
        log.info("join waterlevel to external weirs using a spatial location")
        temp_spatial_join = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.SpatialJoin_analysis(input_external_weir, temp_voronoi, temp_spatial_join, "JOIN_ONE_TO_ONE", "#", "#", "INTERSECTS")

        external_weir_dict = nens.gp.get_table(gp, temp_spatial_join, primary_key=config.get('toetsing_overstorten', 'overstort_ident').lower())

        result_dict = {}
        for k, v in external_weir_dict.items():
            waterlevel = v[config.get('toetsing_overstorten', 'field_waterstand').lower()]
            weir_height = v[config.get('toetsing_overstorten', 'drempelhoogte').lower()]
            if waterlevel is None or weir_height is None:
                waterlevel = -999
                weir_height = -999
                result_value = 9
            else:
                if float(waterlevel) > float(weir_height):
                    result_value = 1
                else:
                    result_value = 0

            result_dict[k] = {config.get('toetsing_overstorten', 'overstort_ident'): k,
                              config.get('toetsing_overstorten', 'field_waterstand'): waterlevel,
                              config.get('toetsing_overstorten', 'drempelhoogte'): weir_height,
                              config.get('toetsing_overstorten', 'field_toetsing_overlast_stedelijk'): result_value}
        #----------------------------------------------------------------------------------------
        # Create output table
        if not gp.exists(output_table_external_weir):
            log.info("Create new output table")
            temp_result_table = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.CreateTable_management(os.path.dirname(temp_result_table), os.path.basename(temp_result_table))
            copy_table = True
        else:
            temp_result_table = output_table_external_weir
            copy_table = False

        fields_to_add = [config.get('toetsing_overstorten', 'field_waterstand'),
                         config.get('toetsing_overstorten', 'drempelhoogte'),
                         config.get('toetsing_overstorten', 'field_toetsing_overlast_stedelijk')]

        if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, config.get('toetsing_overstorten', 'overstort_ident')):
            log.debug(" - add field %s to %s" % (config.get('toetsing_overstorten', 'overstort_ident'), temp_result_table))
            gp.addfield_management(temp_result_table, config.get('toetsing_overstorten', 'overstort_ident'), 'text')

        for field in fields_to_add:
            if not turtlebase.arcgis.is_fieldname(gp, temp_result_table, field):
                log.debug(" - add field %s to %s" % (field, temp_result_table))
                gp.addfield_management(temp_result_table, field, 'double')

        #----------------------------------------------------------------------------------------
        # Write results to output table
        log.info("Write results to output table")
        turtlebase.arcgis.write_result_to_output(temp_result_table, config.get('toetsing_overstorten', 'overstort_ident').lower(), result_dict)

        if copy_table == True:
            gp.TableToTable_conversion(temp_result_table, os.path.dirname(output_table_external_weir), os.path.basename(output_table_external_weir))

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.debug("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
