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
#* Purpose    : Calculate bottom width for channels
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): Calculate bottom width (manning)
#*
#* Project    : Turtle
#*
#* $Id: rural_template.py 10338 2010-03-29 08:50:10Z Coen $ <Id Name Rev must be added to svn:keywords>
#*
#* $Name:  $
#*
#* initial programmer :  Pieter Swinkels
#* initial date       :  20100104
#**********************************************************************
__revision__ = "$Rev: 10338 $"[6:-2]
version = '11.01.%s' % __revision__

NAME_SCRIPT = "manning"

import logging
log = logging.getLogger('nens.turtle.%s' % NAME_SCRIPT)

# Import system modules
import sys
import os
import arcgisscripting
import nens.gp
import turtlebase.arcgis
import turtlebase.filenames
import turtlebase.general

# Create the Geoprocessor object
gp = arcgisscripting.create()

def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.filenames: %s" % turtlebase.filenames.__file__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)


def main(options, args):
    # Create the Geoprocessor object
    gp = arcgisscripting.create()
    gp.RefreshCatalog
    gp.OverwriteOutput = 1

    debuglogging()
    #----------------------------------------------------------------------------------------
    #create header for logfile
    log.info("")
    log.info("*********************************************************")
    log.info("Calculate bottomwidth for channels (manning)")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: %s" %(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    # Check the settings for this script
    check_ini = turtlebase.general.missing_keys(options.ini, ["<vul hier de keys in uit de ini file>"])
    if len(check_ini) > 0:
        log.error("missing keys in turtle-settings.ini file (header %s)" % NAME_SCRIPT)
        log.error(check_ini)
        sys.exit(1)

    #----------------------------------------------------------------------------------------
    # Create workspace
    workspace = options.turtle_ini['location_temp']

    turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

    if not os.path.isdir(workspace):
        os.makedirs(workspace)
    workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
    if errorcode == 1:
        log.error("failed to create a file geodatabase in %s" % workspace)

    #----------------------------------------------------------------------------------------
    # Input parameters
    """
    nodig voor deze tool:
    """
    for argv in sys.argv[1:]:
        turtlebase.filenames.check_filename(argv)

    if len(sys.argv) == 7:
        input_channels = sys.argv[1]
        gauckler_manning_coefficient = sys.argv[2]  #1 / 22.5  # n
        conversion_constant = sys.argv[3]  #1  # k
        max_slope = sys.argv[4]  #0.000021  # S
        depth = sys.argv[5]  #0.8  # d
        talud = sys.argv[6]  #2  # T
    else:
        log.error("usage: <argument1> <argument2>")
        sys.exit(1)

    #----------------------------------------------------------------------------------------
    # Check geometry input parameters
    log.info("Check geometry of input parameters")
    geometry_check_list = []

    log.debug(" - check <input >: %s" % argument1)

    if not turtlebase.arcgis.is_file_of_type(gp, input_channels, 'Polyline'):
        log.error("%s is not a %s feature class!" % (input_channels, 'Polyline'))
        geometry_check_list.append("%s -> (%s)" % (input_channels, 'Polyline'))

    if len(geometry_check_list) > 0:
        log.error("check input: %s" % geometry_check_list)
        sys.exit(2)
    #----------------------------------------------------------------------------------------
    # Check required fields in input data
    log.info("Check required fields in input data")

    missing_fields = []

    #<check required fields from input data, append them to list if missing>
    check_fields = {}#check_fields = {input_1: [fieldname1, fieldname2], input_2: [fieldname1, fieldname2]}
    for input_fc,fieldnames in check_fields.items():
        for fieldname in fieldnames:
            if not turtlebase.arcgis.is_fieldname(gp, input_channels, "OVKIDENT"):
                errormsg = "fieldname %s not available in %s" % (fieldname, input_fc)
                log.error(errormsg)
                missing_fields.append(errormsg)

    if len(missing_fields) > 0:
        log.error("missing fields in input data: %s" % missing_fields)
        sys.exit(2)
    #----------------------------------------------------------------------------------------
    # Environments

    #----------------------------------------------------------------------------------------
    # uitlezen feature class
    channel_values = nens.gp.get_table(gp, input_channels, primary_key='ovkident')

    #wegschrijven feature class
    turtlebase.arcgis.write_result_to_output(output_table, output_ident, result_dict)

    #----------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------
    #----------------------------------------------------------------------------------------
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

    del gp
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    from optparse import OptionParser
    parser = OptionParser()

    (options, args) = parser.parse_args()

    turtlebase.general.extend_options_for_turtle(options, "%s" % NAME_SCRIPT,
                              gpHandlerLevel = logging.INFO,
                              fileHandlerLevel = logging.DEBUG,
                              consoleHandlerLevel = None,
                              root_settings = 'turtle-settings.ini')

    # cProfile for testing
    ##import cProfile
    ##cProfile.run('main(options, args)')
    main(options, args)
