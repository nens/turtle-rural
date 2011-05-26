# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import csv
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import turtlebase.arcgis
import turtlebase.general
import turtlebase.graph
import nens.gp

log = logging.getLogger(__name__)


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
        if len(sys.argv) == 3:
            log.info("Reading input parameters")
            input_yz = sys.argv[1]
            #input_locations = sys.argv[2]
            output_workspace = sys.argv[2]
            #output_locations_lizardweb = sys.argv[4]
        else:
            log.warning("usage: <input_yz_table> <output workspace>")
            #sys.exit(1)

        output_graphs = os.path.join(output_workspace, "graph")
        output_csv = os.path.join(output_workspace, "csv")

        if not os.path.isdir(output_graphs):
            os.makedirs(output_graphs)
        turtlebase.graph.create_cross_section_graph(
                            gp, input_yz, output_graphs)

        if not os.path.isdir(output_csv):
            os.makedirs(output_csv)

        row = gp.SearchCursor(input_yz)
        for item in nens.gp.gp_iterator(row):
            if item.GetValue('P_ORDER') == 1:
                turtlebase.general.add_to_csv(output_file, [('Location: %s' % item.GetValue('PROIDENT'))], "wb")
                turtlebase.general.add_to_csv(output_file, ('Streefpeil %s' % item.GetValue('TARGET_LVL')), "ab")
                turtlebase.general.add_to_csv(output_file, ('Gemeten waterstand: %s' % item.GetValue('WATER_LVL')), "ab")
                turtlebase.general.add_to_csv(output_file, (''), "ab")
                turtlebase.general.add_to_csv(output_file, ('Afstand tot midden (m)', 'Hoogte (m NAP)'), "ab")
            turtlebase.general.add_to_csv(output_file, (item.GetValue('DIST_MID', 'BED_LVL'), "ab"))

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            #gp.delete(workspace_gdb)

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
