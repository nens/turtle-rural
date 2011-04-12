# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

# Import system modules
import sys
import os
import logging
import traceback
import ConfigParser

# Import GIS modules
import arcgisscripting
import nens.gp

# Import Turtlebase modules
import turtlebase.arcgis
import turtlebase.filenames
import turtlebase.general
from turtlebase.logutils import LoggingConfig

log = logging.getLogger(__name__)


def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.filenames: %s" % turtlebase.filenames.__file__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)


def main():
    try:
        # Create the Geoprocessor object
        gp = arcgisscripting.create()
        gp.RefreshCatalog
        gp.OverwriteOutput = 1

        # Settings for all turtle tools
        script_full_path = sys.argv[0] #get absolute path of running script
        location_script = os.path.abspath(os.path.dirname(script_full_path))+"\\"
        ini_file = location_script + 'turtle-settings.ini'

        # Use configparser to read ini file
        config = ConfigParser.SafeConfigParser()
        config.read(ini_file)

        logfile = os.path.join(config.get('GENERAL','location_temp')
                               + config.get('GENERAL','filename_log'))
        logging_config = LoggingConfig(gp, logfile=logfile)

        debuglogging()
        #----------------------------------------------------------------------------------------
        #create header for logfile
        log.info("*********************************************************")
        log.info(__name__)
        log.info("This python script is developed by "
                 + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
        log.info("*********************************************************")
        log.info("arguments: %s" %(sys.argv))

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL','location_temp')

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
        pg_visited = {}
        afvoer_van = config.get('controle_afvoerrelaties', 'afvoer_van').lower()
        afvoer_naar = config.get('controle_afvoerrelaties', 'afvoer_naar').lower()
        boundary_str = config.get('controle_afvoerrelaties', 'boundary_str')
        for kwk_id, value in afvoer_data.items():
            if (afvoer_data[kwk_id][afvoer_van] != boundary_str) and not(oppervlak_data.has_key(value[afvoer_van])):
                log.error("["+ini['kwk_ident']+"] = "+kwk_id+", field "+afvoer_van+": ["+gpg_ident+"] = '"+afvoer_data[kwk_id][afvoer_van]+"' not found in RR_Oppervlak.")
                error_count += 1
            if (afvoer_data[kwk_id][afvoer_naar] != boundary_str) and not(oppervlak_data.has_key(value[afvoer_naar])):
                log.error("["+kwk_ident+"] = "+kwk_id+", field "+afvoer_naar+": ["+gpg_ident+"] = '"+afvoer_data[kwk_id][afvoer_naar]+"' not found in RR_Oppervlak.")
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

        log.info("*********************************************************")
        log.info("Finished")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp

