# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
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
        if len(sys.argv) == 4:
            input_calculation_points = sys.argv[1]
            input_level_area = sys.argv[2] # peilgebieden
            output_afv_oppervlak = sys.argv[3]
        else:
            log.error("usage: <input_calculation_points> <input_level_areas> <output_voronoi>")
            sys.exit(1)
        #----------------------------------------------------------------------------------------
        # Check input parameters
        geometry_check_list = []
        if gp.describe(input_calculation_points).ShapeType != 'Point':
            log.error("Input calculations points is not a points feature class!")
            geometry_check_list.append(input_calculation_points + " -> (Point)")

        if gp.describe(input_level_area).ShapeType != 'Polygon':
            log.error("Input calculations points is not a points feature class!")
            geometry_check_list.append(input_level_area + " -> (Polygon)")

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #----------------------------------------------------------------------------------------
        # Check required fields in database
        log.info("Check required fields in input data")
        gpgident = config.get('GENERAL', 'gpgident')
        calculation_point = config.get('rrcf_voronoi', 'calculation_point_ident')

        missing_fields = []
        if not turtlebase.arcgis.is_fieldname(gp, input_calculation_points, calculation_point):
            log.debug(" - missing: %s in %s" % (calculation_point, input_calculation_points))
            missing_fields.append("%s: %s" % (input_calculation_points, calculation_point))

        if not turtlebase.arcgis.is_fieldname(gp, input_level_area, gpgident):
            log.debug(" - missing: %s in %s" % (gpgident, input_level_area))
            missing_fields.append("%s: %s" % (input_level_area, gpgident))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        # Create voronoi polygons
        temp_voronoi = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        temp_voronoi = turtlebase.voronoi.create_voronoi(input_calculation_points, calculation_point, input_level_area, gpgident, temp_voronoi, workspace_gdb)
        gp.CopyFeatures_management(temp_voronoi, output_afv_oppervlak)

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase
        try:
            log.info("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp

