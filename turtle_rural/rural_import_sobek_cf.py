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
        #---------------------------------------------------------------------
        # Input parameters
        """
        nodig voor deze tool:
        """
        if len(sys.argv) == 4:
            sobek_case_folder = sys.argv[1]
            output_gdb = sys.argv[2]
            config = sys.argv[3]
        else:
            log.warning("usage: <sobek_case_folder> <output_gdb>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_files = []

        check_files = ['network.ntw', 'boundary.dat', 'profile.dat', 'profile.def', 'struct.dat', 'struct.def', 'initial.dat', 'friction.dat', 'control.def']
        for check_file in check_files:
            if not os.path.isfile(os.path.join(sobek_case_folder, check_file)):
                missing_files.append(check_file)

        if len(missing_files) > 0:
            log.error("missing files in sobek directory: %s" % missing_files)
            sys.exit(2)
        #---------------------------------------------------------------------
        import sobek_to_gml
        sys.argv[1] = os.path.join(sys.argv[1], 'network.ntw')
        sys.argv[2] = turtlebase.arcgis.get_random_file_name(workspace)
        xml_file = sys.argv[2] + ".gml"
        options, args = nens.gp.parse_arguments({1: ('arg', 0), # input network.ntw
                                                 2: ('arg', 1), # output path + name - extension
                                                 3: ('arg', 2), # config file
                                                 })
        sobek_to_gml.main(options, args)

        import arcpy
        arcpy.CheckOutExtension("DataInteroperability")
        log.info("DataInteroperability extension checked out") 
        arcpy.QuickImport_interop(xml_file, output_gdb)

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        #try:
        #    log.debug("delete temporary workspace: %s" % workspace_gdb)
        try:
            gp.delete(xml_file)
        except:
            log.debug("failed to delete %s" % xml_file)

        #    log.info("workspace deleted")
        #except:
        #    log.warning("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        arcpy.CheckInExtension("DataInteroperability")
        del gp
