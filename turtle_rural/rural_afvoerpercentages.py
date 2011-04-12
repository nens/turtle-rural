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
        #check inputfields
        log.info("Getting commandline parameters")
        if len(sys.argv) == 2:
            input_afvoer = sys.argv[1] #shape

            log.info("input afvoer: %s" % input_afvoer)
        else:
            log.error("Usage: python rural_afvoerpercentages.py <rr_afvoer>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        log.info("A) Read RR_Afvoer")
        kwkident = config.get('GENERAL', 'kwkident').lower()
        if not turtlebase.arcgis.is_fieldname(gp, input_afvoer, kwkident):
            log.error("field %s not found, we cannot continue" % kwkident)
            sys.exit(1)
        afvoer_data = nens.gp.get_table(gp, input_afvoer, primary_key=kwkident)

        log.info("B) Calculate percentages")
        log.info(" - calculate kw's per peilgebied")
        peilgebied = {}
        afvoer_van = config.get('afvoerpercentages', 'afvoer_van').lower()
        for key, value in afvoer_data.items():
            gpg_van = value[afvoer_van]
            if gpg_van in peilgebied:
                peilgebied[gpg_van].append(key)
            else:
                peilgebied[gpg_van] = [key]

        afvoer_data_output = {}
        log.info(" - calculate percentages")
        percentage = config.get('afvoerpercentages', 'percentage')
        for key, value in peilgebied.items():
            perc = 100/float(len(value))
            for kw in value:
                afvoer_data_output[kw] = {percentage: perc}

        fieldsAfvoer = {percentage: {'type': 'FLOAT'}}

        log.info("C) writing to output")
        turtlebase.arcgis.write_result_to_output(input_afvoer, kwkident, afvoer_data_output)
        #nens.tools_gp.writeDictToDBF_withErrorchecking(gp, os.path.dirname(input_afvoer)+'\\', os.path.basename(input_afvoer), fieldsAfvoer, afvoer_data_output, options.ini['kwk_ident'])

        log.info("*********************************************************")
        log.info("Finished")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
