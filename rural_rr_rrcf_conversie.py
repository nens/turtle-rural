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
from turtle_rural import trrrlib
from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils

log = logging.getLogger(__name__)


def add_xy_coords(gp, fc, xfield, yfield):
    rows = gp.UpdateCursor(fc)
    for row in nens.gp.gp_iterator(rows):
        part = row.Shape.GetPart(0)
        x_list = [float(pnt.x) for pnt in nens.gp.gp_iterator(part)]
        row.SetValue(xfield, x_list[0])
        y_list = [float(pnt.y) for pnt in nens.gp.gp_iterator(part)]
        row.SetValue(yfield, y_list[0])
        rows.UpdateRow(row)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #read conversion settings
        modeltype = "RR+RR_CF"

        #---------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters")

        if len(sys.argv) == 8:
            peilgebieden_feature = sys.argv[1]
            rr_dataset = sys.argv[2]
            afvoerkunstwerken = sys.argv[4]
            koppelpunten = sys.argv[5]
            settings = sys.argv[6]
            output_dir = sys.argv[7]
        else:
            log.error("Usage: python rural_rr_rrcf_conversie.py \
            <peilgebieden_feature> <rr_dataset> <rr_afvoer> \
            <afvoerkunstwerken> <koppelpunten> <settings>")
            sys.exit(1)

        rr_dataset = rr_dataset.replace("\\", "/")
        rr_dataset = rr_dataset.replace("'", "")
        sys.argv[2] = rr_dataset

        log.info("output_dir: " + output_dir)

        #add extra logfile
        fileHandler2 = logging.FileHandler(output_dir + '\\rr_rrcf_convert.log')
        logging.getLogger("nens.turtle").addHandler(fileHandler2)

        #---------------------------------------------------------------------
        #check input parameters
        log.info('Checking presence of input files')
        if not(gp.exists(peilgebieden_feature)):
            log.error("input_toetspunten " + peilgebieden_feature + " does not exist!")
            sys.exit(5)

        #----------------------------------------------------------------------------------------
        #default settings
        if settings == "#":
            location_script = os.path.dirname(sys.argv[0])
            settings = os.path.join(location_script, config.get('RR', 'rr_rrcf_default_settings'))

        rr_config = mainutils.read_config(settings, os.path.basename(settings))

        if not rr_config.get("column.peilgebied", 'paved_runoff_coefficient'):
            log.warning("paved_runoff_coefficient not available in rr+rrcf-settings, default will be used")
            rr_config.set("column.peilgebied", 'paved_runoff_coefficient', "-")
            rr_config.set("default.peilgebied", 'paved_runoff_coefficient', '0.2')

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        configfilename = os.path.join(workspace, "rr_rrcf_settings_temp.ini")
        configfile = open(configfilename, "wb")
        rr_config.write(configfile)
        configfile.close()
        settings = configfilename
        #----------------------------------------------------------------------------------------
        #checking if feature class contains polygons
        log.info("Checking if feature contains polygons")
        pg_obj = gp.describe(peilgebieden_feature)
        if pg_obj.ShapeType != "Polygon":
            log.error(peilgebieden_feature + " does not contain polygons, please add a feature class with polygons")
            log.error(" - gp message: " + gp.GetMessages(2))
            sys.exit(5)

        # If rr_afvoer is empty, ignore this table, because trrrlib will crash
        if sys.argv[3] != '#':
            if turtlebase.arcgis.fc_is_empty(gp, sys.argv[3]):
                log.warning("rr_afvoer is empty, this table will be ignored")
                sys.argv[3] = '#'

        # add xy coordinates
        xcoord = 'XCOORD'
        ycoord = 'YCOORD'
        if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, xcoord):
            gp.addfield(peilgebieden_feature, xcoord, "Double")
        if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, ycoord):
            gp.addfield(peilgebieden_feature, ycoord, "Double")
        add_xy_coords(gp, peilgebieden_feature, xcoord, ycoord)

        #checking if feature class contains points
        if afvoerkunstwerken != "#":
            log.info("Checking if feature contains points")
            ak_obj = gp.describe(afvoerkunstwerken)
            log.debug("ShapeType afvoerkunstwerken = " + ak_obj.ShapeType)
            if ak_obj.ShapeType != "Point":
                log.error(afvoerkunstwerken + " does not contain points, please add a feature class with points")
                log.error(" - gp message: " + gp.GetMessages(2))
                sys.exit(5)

        #check op punten
        if koppelpunten != "#":
            log.info("Checking if feature contains points")
            kp_obj = gp.describe(koppelpunten)
            log.debug("ShapeType koppelpunten = " + kp_obj.ShapeType)
            if kp_obj.ShapeType != "Point":
                log.error(koppelpunten + " does not contain points, please add a feature class with points")
                log.debug(gp.GetMessages(2))
                sys.exit()

        #copy settings to output directory
        shutil.copyfile(settings, output_dir + '\\RR_RRCF_Settings.ini')

        drainage = config.get('RR', 'drainage')
        log.info("drainage type is " + drainage)

        #export rrcf connection to output folder. Convert feature class to shape
        output_shapefiles = output_dir + '\\shapefiles'
        if not os.path.isdir(output_shapefiles):
            os.makedirs(output_shapefiles)
        log.debug("export rrcf connection nodes to" + output_shapefiles)

        gp.Select_analysis(koppelpunten, output_shapefiles + "\\rrcf_connection.shp")
        log.debug("features exported")

        output_sobek = output_dir + "\\sobek_input"
        if not os.path.isdir(output_sobek):
            os.makedirs(output_sobek)

        log.debug("from trrrlib import trrrlib")
        trrrlib.main({}, sys.argv[1:6] + [settings] + [output_sobek] + [drainage] + [modeltype])
        if os.path.isfile(output_sobek + "/struct.def"):
            os.remove(output_sobek + "/struct.def")
        if os.path.isfile(output_sobek + "/profile.dat"):
            os.remove(output_sobek + "/profile.dat")
        log.info("*********************************************************")
        log.info(modeltype + " Conversie compleet")
        log.info("*********************************************************")

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
