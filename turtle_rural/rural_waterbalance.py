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
import turtlebase.general

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
        """
        nodig voor deze tool:
        peilgebieden
        rr_peilgebied
        rr_grondsoort
        rr_kwelwegzijging
        rr_oppervlak
        """

        if len(sys.argv) == 6:
            peilgebieden_fc = sys.argv[1]
            rr_peilgebied = sys.argv[2]
            rr_grondsoort = sys.argv[3]
            rr_kwelwegzijging = sys.argv[4]
            rr_oppervlak = sys.argv[5]
        else:
            log.warning("usage: <peilgebieden> <rr_peilgebied> <rr_grondsoort> <rr_kwelwegzijging> <rr_oppervlak>")
            #sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)

        #"<check geometry from input data, append to list if incorrect>"

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        """
        Check fields:
        - GPGIDENT (peilgebieden_fc) 
        - GAFIDENT (peilgebieden_fc)
        - GAFNAAM (peilgebieden_fc)
        """
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        #check_fields = {}
        gpgident = config.get("general", "gpgident").lower()
        gafident = config.get("waterbalance", "gafnaam").lower()
        gafnaam = config.get("waterbalance", "gafident").lower()

        check_fields = {peilgebieden_fc: [gpgident, "gafident", "gafnaam"],
                         rr_peilgebied: ["gpgident", "zomerpeil", "winterpeil"]}
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
        # Environments
        peilgebieden = nens.gp.get_table(gp, peilgebieden_fc, primary_key=gpgident, no_shape=True)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_peilgebied, gpgident)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_grondsoort, gpgident)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_kwelwegzijging, gpgident)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_oppervlak, gpgident)

        polders = {}
        for k, v in peilgebieden.items():
            if v[gafident] in polders:
                polders[gafident]["peilgebieden"].append(k)
            else:
                polders[gafident] = {"peilgebieden": [k]}

        #log.info(polders)
        #log.info(peilgebieden)
        for k, v in peilgebieden.items():
            log.info(v.keys())

        #turtlebase.arcgis.write_result_to_output(output_waterbezwaar_tbl,
        #                                         gpgident, waterbezwaar)
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
