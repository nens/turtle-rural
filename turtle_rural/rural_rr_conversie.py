# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

# Import system modules
import sys
import os
import logging
import shutil
import traceback

# Import GIS modules
import nens.gp

# Import Turtlebase modules
import turtlebase.arcgis
import turtlebase.general
from turtle_rural import trrrlib
from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils

log = logging.getLogger(__name__)


def add_xy_coords(gp, fc, xfield, yfield):
    rows = gp.UpdateCursor(fc)
    for row in nens.gp.gp_iterator(rows):
        row.SetValue(xfield, row.shape.centroid.split()[0])
        row.SetValue(yfield, row.shape.centroid.split()[1])
        rows.UpdateRow(row)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        output_dir = sys.argv[7]
        if not gp.exists(output_dir):
            os.makedirs(output_dir)

        log.info("output_dir: " + output_dir)

        #add extra logfile
        fileHandler2 = logging.FileHandler(output_dir + '\\rr_convert.log')
        logging.getLogger("nens").addHandler(fileHandler2)
        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters... ")
        if len(sys.argv) != 0:
            peilgebieden_feature = sys.argv[1]
            rr_dataset = sys.argv[2]
            afvoerkunstwerken = sys.argv[4]
            settings = sys.argv[6]
        else:
            log.error("Usage: python rural_rr_conversie.py <peilgebieden_feature> <rr_dataset> <rr_afvoer> <afvoerkunstwerken> <settings>")
            sys.exit(1)

        rr_dataset = rr_dataset.replace("'", "")
        rr_dataset = rr_dataset.replace("\\", "/")
        sys.argv[2] = rr_dataset

        #default settings
        if settings == "#":
            location_script = os.path.dirname(sys.argv[0])
            settings = os.path.join(location_script, config.get('RR', 'rr_default_settings'))

        #----------------------------------------------------------------------------------------
        #check input parameters
        log.info('Checking presence of input files')
        if not(gp.exists(peilgebieden_feature)):
            log.error("input_toetspunten " + peilgebieden_feature + " does not exist!")
            sys.exit(5)

        #checking if feature class contains polygons
        log.info("Checking if feature contains polygons")
        if gp.describe(peilgebieden_feature).ShapeType != "Polygon":
            log.error(peilgebieden_feature + " does not contain polygons, please add a feature class with polygons")
            sys.exit(5)

        # add xy coordinates
        peilgebied_ini = mainutils.read_config(__file__, config.get('RR', 'rr_default_settings'))
        xcoord = peilgebied_ini.get('column.peilgebied', 'xcoord')
        ycoord = peilgebied_ini.get('column.peilgebied', 'ycoord')
        if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, xcoord):
            gp.addfield(peilgebieden_feature, xcoord, "Double")
        if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, ycoord):
            gp.addfield(peilgebieden_feature, ycoord, "Double")
        add_xy_coords(gp, peilgebieden_feature, xcoord, ycoord)

        #checking if feature class contains points
        if afvoerkunstwerken != "#":
            log.info("Checking if feature contains points")
            log.debug("ShapeType afvoerkunstwerken = " + gp.describe(afvoerkunstwerken).ShapeType)
            if gp.describe(afvoerkunstwerken).ShapeType != "Point":
                log.error(afvoerkunstwerken + " does not contain points, please add a feature class with points")
                sys.exit(5)

        #copy settings to output directory
        shutil.copyfile(settings, output_dir + '\\RR_Settings.ini')

        drainage = config.get('RR', 'drainage')
        log.info("drainage type is " + drainage)

        output_sobek = output_dir + "\\sobek_input"
        if not gp.exists(output_sobek):
            os.makedirs(output_sobek)

        trrrlib.main({}, sys.argv[1:6] + [settings] + [output_sobek] + [drainage] + ["RR"])
        log.info("*********************************************************")
        log.info("RR Conversie compleet")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
