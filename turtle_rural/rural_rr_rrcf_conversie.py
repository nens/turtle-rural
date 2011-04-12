#!/usr/bin/python
# -*- coding: utf-8 -*-
#***********************************************************************
# this program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# this program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the nens libraray.  If not, see
# <http://www.gnu.org/licenses/>.
#
#***********************************************************************
#* Purpose    : Rainfall Runoff conversion
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): RRConversion
#*
#* Project    : Turtle
#*
#* $Id$ <Id Name Rev must be added to svn:keywords>
#*
#* $Name:  $
#*
#* initial programmer :  Coen Nengerman
#* initial date       :  20080731
#**********************************************************************
__revision__ = "$Rev$"[6:-2]
version = '10.03.%s' % __revision__

import logging
log = logging.getLogger('nens.turtle.rural.RR_RRCF')

# Import system modules
import sys, os, arcgisscripting, shutil, locale
import nens.gp

from turtle_rural import trrrlib
import turtlebase.general
import turtlebase.arcgis


# Create the Geoprocessor object
gp = arcgisscripting.create()

def add_xy_coords(fc, xfield, yfield):
    rows = gp.UpdateCursor(fc)
    for row in nens.gp.gp_iterator(rows):
        if len(row.shape.centroid.split()) > 0:
            row.SetValue(xfield, row.shape.centroid.split()[0])
            row.SetValue(yfield, row.shape.centroid.split()[1])
            rows.UpdateRow(row)


def read_settings_ini(settings, header):
    ini = turtlebase.general.read_ini_file(settings, header)
    settings_ini = turtlebase.general.convert_ini_settings_to_dictionary(ini)
    return settings_ini


def main(options, args):
    # Create the Geoprocessor object
    gp = arcgisscripting.create()
    gp.RefreshCatalog
    gp.OverwriteOutput = 1
    log.info(trrrlib.__file__)
    #read conversion settings
    modeltype = "RR+RR_CF"

    #----------------------------------------------------------------------------------------
    #check inputfields
    log.info("Getting commandline parameters")

    log.info(sys.argv[7])
    if len(sys.argv) == 8:
        peilgebieden_feature = sys.argv[1]
        rr_dataset = sys.argv[2]
        rr_afvoer = sys.argv[3]
        afvoerkunstwerken = sys.argv[4]
        koppelpunten = sys.argv[5]
        settings = sys.argv[6]
        output_dir = sys.argv[7]

    else:
        log.error("Usage: python rural_rr_rrcf_conversie.py <peilgebieden_feature> <rr_dataset> <rr_afvoer> <afvoerkunstwerken> <koppelpunten> <settings>")
        sys.exit(1)

    rr_dataset = rr_dataset.replace("\\", "/")
    rr_dataset = rr_dataset.replace("'", "")
    sys.argv[2] = rr_dataset

    log.info("output_dir: "+output_dir)

    #add extra logfile
    fileHandler2 = logging.FileHandler(output_dir+'\\rr_rrcf_convert.log')
    logging.getLogger("nens.turtle").addHandler(fileHandler2)

    #----------------------------------------------------------------------------------------
    #create header for logfile
    log.info("")
    log.info("*********************************************************")
    log.info(modeltype+" Conversion... ")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: "+str(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    # Check the settings for this script
    checkIni = turtlebase.general.missing_keys(options.ini, ["rr_rrcf_default_settings", "drainage"])
    if len(checkIni) > 0:
        log.error("missing keys in turtle-settings.ini file (header RR)")
        log.error(checkIni)
        sys.exit(1)

    #default settings
    if settings == "#":
        location_script = os.path.dirname(sys.argv[0])
        settings = os.path.join(location_script, options.ini['rr_rrcf_default_settings'])

    #----------------------------------------------------------------------------------------
    #check input parameters
    log.info('Checking presence of input files')
    if not(gp.exists(peilgebieden_feature)):
        log.error("input_toetspunten "+input_toetspunten+" does not exist!")
        sys.exit(5)

    #checking if feature class contains polygons
    log.info("Checking if feature contains polygons")
    pg_obj = gp.describe(peilgebieden_feature)
    if pg_obj.ShapeType != "Polygon":
        log.error(peilgebieden_feature+" does not contain polygons, please add a feature class with polygons")
        log.error(" - gp message: " + gp.GetMessages(2))
        sys.exit(5)

    # add xy coordinates
    peilgebied_ini = read_settings_ini(settings, 'column.peilgebied')
    xcoord = peilgebied_ini['xcoord']
    ycoord = peilgebied_ini['ycoord']
    if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, xcoord):
        gp.addfield(peilgebieden_feature, xcoord, "Double")
    if not turtlebase.arcgis.is_fieldname(gp, peilgebieden_feature, ycoord):
        gp.addfield(peilgebieden_feature, ycoord, "Double")
    add_xy_coords(peilgebieden_feature, xcoord, ycoord)

    #checking if feature class contains points
    if afvoerkunstwerken != "#":
        log.info("Checking if feature contains points")
        ak_obj = gp.describe(afvoerkunstwerken)
        log.debug("ShapeType afvoerkunstwerken = "+ak_obj.ShapeType)
        if ak_obj.ShapeType != "Point":
            log.error(afvoerkunstwerken + " does not contain points, please add a feature class with points")
            log.error(" - gp message: " + gp.GetMessages(2))
            sys.exit(5)

    #check op punten
    if koppelpunten != "#":
        log.info("Checking if feature contains points")
        kp_obj = gp.describe(koppelpunten)
        log.debug("ShapeType koppelpunten = "+kp_obj.ShapeType)
        if kp_obj.ShapeType != "Point":
            log.error(koppelpunten + " does not contain points, please add a feature class with points")
            log.debug(gp.GetMessages(2))
            sys.exit()

    #copy settings to output directory
    shutil.copyfile(settings, output_dir+'\\RR_RRCF_Settings.ini')

    drainage = options.ini['drainage']
    log.info("drainage type is "+drainage)

    #export rrcf connection to output folder. Convert feature class to shape
    output_shapefiles = output_dir+'\\shapefiles'
    if not os.path.isdir(output_shapefiles):
        os.makedirs(output_shapefiles)
    log.debug("export rrcf connection nodes to" + output_shapefiles)

    gp.Select_analysis(koppelpunten, output_shapefiles + "\\rrcf_connection.shp")
    log.debug("features exported")

    output_sobek = output_dir+"\\sobek_input"
    if not os.path.isdir(output_sobek):
        os.makedirs(output_sobek)

    log.debug("from trrrlib import trrrlib")
    log.warning(sys.argv[2])
    parameters = sys.argv[1:6]+[settings]+[output_sobek]+[drainage]+[modeltype]
    #log.info("parameters for trrrlib: "+str(parameters)
    trrrlib.main({},sys.argv[1:6]+[settings]+[output_sobek]+[drainage]+[modeltype])
    if os.path.isfile(output_sobek + "/struct.def"):
        os.remove(output_sobek + "/struct.def")
    if os.path.isfile(output_sobek + "/profile.dat"):
        os.remove(output_sobek + "/profile.dat")
    log.info("*********************************************************")
    log.info(modeltype + " Conversie compleet")
    log.info("*********************************************************")

    del gp
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    from optparse import OptionParser
    parser = OptionParser()

    (options, args) = parser.parse_args()

    turtlebase.general.extend_options_for_turtle(options, "RR",
                              gpHandlerLevel = logging.INFO,
                              fileHandlerLevel = logging.DEBUG,
                              consoleHandlerLevel = logging.INFO,
                              root_settings = 'turtle-settings.ini')

    # cProfile for testing
    ##import cProfile
    ##cProfile.run('main(options, args)')
    main(options, args)
