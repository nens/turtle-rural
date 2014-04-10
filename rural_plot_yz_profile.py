# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import tempfile
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
        if len(sys.argv) == 3:
            log.info("Reading input parameters")
            input_yz = sys.argv[1]
            #input_locations = sys.argv[2]
            output_workspace = sys.argv[2]
            #output_locations_lizardweb = sys.argv[4]
        else:
            log.warning("usage: <input_yz_table> <output workspace>")
            #sys.exit(1)

        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        check_fields = {input_yz: ['proident', "xcoord", "ycoord", "target_lvl", "water_lvl", "dist_mid", "bed_lvl", "bed_lvl_s"]}
        for input_fc, fieldnames in check_fields.items():
            for fieldname in fieldnames:
                if not turtlebase.arcgis.is_fieldname(
                        gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (
                                    fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------

        output_graphs = os.path.join(output_workspace, "graph")
        log.info("output graphs: %s" % output_graphs)
        output_csv = os.path.join(output_workspace, "csv")
        log.info("output csv: %s" % output_csv)

        if not os.path.isdir(output_graphs):
            os.makedirs(output_graphs)
        log.info("Create graphs for cross sections")
        turtlebase.graph.create_cross_section_graph(gp, input_yz, output_graphs)

        if not os.path.isdir(output_csv):
            os.makedirs(output_csv)

        row = gp.SearchCursor(input_yz)
        log.info("Create CSV files")
        for item in nens.gp.gp_iterator(row):

            if item.GetValue('P_ORDER') == 1:
                output_file = os.path.join(output_csv, "%s.csv" % item.GetValue('PROIDENT'))
                turtlebase.general.add_to_csv(output_file, [('Location:           ', item.GetValue('PROIDENT'))], "wb")
                turtlebase.general.add_to_csv(output_file, [('X-coordinaat:       ', round(item.GetValue('XCOORD'), 2))], "ab")
                turtlebase.general.add_to_csv(output_file, [('Y-coordinaat:       ', round(item.GetValue('YCOORD'), 2))], "ab")
                turtlebase.general.add_to_csv(output_file, [('Streefpeil:         ', item.GetValue('TARGET_LVL'))], "ab")
                turtlebase.general.add_to_csv(output_file, [('Gemeten waterstand: ', item.GetValue('WATER_LVL'))], "ab")
                turtlebase.general.add_to_csv(output_file, [('')], "ab")
                turtlebase.general.add_to_csv(output_file, [('Afstand tot midden (m)', 'Hoogte (m NAP)', "Hoogte zachte bodem (m NAP)")], "ab")
            try:
                turtlebase.general.add_to_csv(output_file, [(round(item.GetValue('DIST_MID'), 2), round(item.GetValue('BED_LVL'), 2), round(item.GetValue('BED_LVL_S'), 2))], "ab")
            except:
                continue

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
