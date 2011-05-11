# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
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
            perc = 100 / float(len(value))
            for kw in value:
                afvoer_data_output[kw] = {percentage: perc}

                log.info("C) writing to output")
        turtlebase.arcgis.write_result_to_output(input_afvoer, kwkident, afvoer_data_output)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
