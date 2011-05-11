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
import turtlebase.filenames
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
        #check inputfields
        log.info("Getting commandline parameters")
        if len(sys.argv) == 3:
            input_oppervlak = sys.argv[1]
            input_afvoer = sys.argv[2]

            log.info("input oppervlak: %s" % input_oppervlak)
            log.info("input afvoer: %s" % input_afvoer)
        else:
            log.error("Usage: python rural_controle_afvoer.py <rr_oppervlakte> <rr_afvoer>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        error_count = 0

        log.info("A-1) Read RR_Oppervlak")
        gpgident = config.get('GENERAL', 'gpgident').lower()
        if not turtlebase.arcgis.is_fieldname(gp, input_oppervlak, gpgident):
            log.error("field %s not found, we cannot continue" % gpgident)
            sys.exit(1)
        oppervlak_data = nens.gp.get_table(gp, input_oppervlak, primary_key=gpgident)

        log.info("A-2) Read RR_Afvoer")
        kwkident = config.get('GENERAL', 'kwkident').lower()
        if not turtlebase.arcgis.is_fieldname(gp, input_afvoer, kwkident):
            log.error("field %s not found, we cannot continue" % kwkident)
            sys.exit(1)
        afvoer_data = nens.gp.get_table(gp, input_afvoer, primary_key=kwkident)

        log.info("B-1) Checking links from KW's")
        afvoer_van = config.get('controle_afvoerrelaties', 'afvoer_van').lower()
        afvoer_naar = config.get('controle_afvoerrelaties', 'afvoer_naar').lower()
        boundary_str = config.get('controle_afvoerrelaties', 'boundary_str')
        for kwk_id, value in afvoer_data.items():
            if (afvoer_data[kwk_id][afvoer_van] != boundary_str) and not(oppervlak_data.has_key(value[afvoer_van])):
                log.error("[" + kwkident + "] = " + kwk_id + ", field " + afvoer_van + ": [" + gpgident + "] = '" + afvoer_data[kwk_id][afvoer_van] + "' not found in RR_Oppervlak.")
                error_count += 1
            if (afvoer_data[kwk_id][afvoer_naar] != boundary_str) and not(oppervlak_data.has_key(value[afvoer_naar])):
                log.error("[" + kwkident + "] = " + kwk_id + ", field " + afvoer_naar + ": [" + gpgident + "] = '" + afvoer_data[kwk_id][afvoer_naar] + "' not found in RR_Oppervlak.")
                error_count += 1

        log.info("B-2) Checking links from GPG's")
        for gpg_ident in oppervlak_data.keys():
            #try to find gpg_ident in afvoer_data
            for value in afvoer_data.values():
                if value[afvoer_naar] == gpg_ident:
                    break
                if value[afvoer_van] == gpg_ident:
                    break
            else:
                log.error("%s: %s not found in RR_Afvoer." % (gpgident, gpg_ident))
                error_count += 1

        if error_count == 0:
            log.info("No errors were found.")
        else:
            log.warning("%s error(s) were found." % error_count)
        #----------------------------------------------------------------------------------------
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

