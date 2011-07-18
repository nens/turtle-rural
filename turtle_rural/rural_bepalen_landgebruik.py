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
import turtlebase.network
import turtlebase.general
import turtlebase.voronoi

log = logging.getLogger(__name__)


def check_for_landuse_types(output_intersect_landuse, type_field):
    """
    """
    landuse_type_list = []
    row = gp.SearchCursor(output_intersect_landuse)
    for item in nens.gp.gp_iterator(row):
        landuse_type = item.getValue(type_field)
        if landuse_type not in landuse_type_list:
            landuse_type_list.append(landuse_type)

    return landuse_type_list


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
        # Input parameters
        """
        nodig voor deze tool:
        """

        if len(sys.argv) == 6:
            input_polygon = sys.argv[1]
            input_channel = sys.argv[2]
            input_landuse = sys.argv[3]
            output_channel = sys.argv[4]
        else:
            log.warning("usage: python geo_genereren_afv_opp.py <input peilgebieden> <input watergangen> <input landgebruik> <output waterlijnen met oppervlak>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)
        gpg_obj = gp.describe(input_polygon_fc)
        if gpg_obj.ShapeType != 'Polygon':
            geometry_check_list.append("input peilgebieden does not contain polygons, it contains shapetype: %s" % gpg_obj.ShapeType)
        else:
            log.info(" - input peilgebieden is correct")

        ovk_obj = gp.describe(input_channel_fc)
        if ovk_obj.ShapeType != 'Polyline':
            geometry_check_list.append("input channel does not contain polyline, it contains shapetype: %s" % ovk_obj.ShapeType)
        else:
            log.info(" - input channel is correct")

        lu_obj = gp.describe(input_landuse_fc)
        if lu_obj.ShapeType != 'Polygon':
            geometry_check_list.append("input landuse does not contain polygons, it contains shapetype: %s" % lu_obj.ShapeType)
        else:
            log.info(" - input landuse is correct")
        #"<check geometry from input data, append to list if incorrect>"

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []
        ovk_field = config.get('general', 'ovkident')
        gpg_field = config.get('general', 'gpgident')
        landuse_type = config.get('afv_opp', 'landuse_type')

        if not turtlebase.arcgis.is_fieldname(gp, input_polygon_fc, gpg_field):
            log.error("missing field '%s' in %s" % (gpg_field, nput_polygon_fc))
            missing_fields.append("%s: %s" % (input_polygon_fc, gpg_field))

        if not turtlebase.arcgis.is_fieldname(gp, input_channel_fc, ovk_field):
            log.error("missing field '%s' in %s" % (ovk_field, input_channel_fc))
            missing_fields.append("%s: %s" % (input_channel_fc, ovk_field))

        if not turtlebase.arcgis.is_fieldname(gp, input_landuse_fc, 'type'):
            log.error("missing field 'type' in %s" % input_landuse_fc)
            missing_fields.append("%s: TYPE" % (input_landuse_fc))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments

        log.info(" - intersect areas with landuse")
        output_intersect_landuse = workspace_gdb + "/landuse_intersect"
        log.info(output_intersect_landuse)
        #tempfiles.append(output_intersect_landuse)
        gp.intersect_analysis(output_merge_fc + "; " + input_landuse_fc, output_intersect_landuse)

        landuse_type_list = check_for_landuse_types(output_intersect_landuse, "TYPE")
        if len(landuse_type_list) == 0:
            log.error("missing landuse types 'rural' and 'urban'")
            sys.exit(3)






        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
