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
#* Purpose    : <purpose>
#* Function   : main
#* Usage      : Run from Turtle rural toolbox (ArcGIS): <name of script>
#*
#* Project    : Turtle
#*
#* $Id$ <Id Name Rev must be added to svn:keywords>
#*
#* $Name:  $
#*
#* initial programmer :  <name programmer>
#* initial date       :  <date>
#**********************************************************************
__revision__ = "$Rev$"[6:-2]
version = '10.03.%s' % __revision__

NAME_SCRIPT = "test_rural"

import logging
log = logging.getLogger('nens.turtle.rural.%s' % NAME_SCRIPT)

# Import system modules
import sys
import os
import turtlebase.general

def main(options, args):
    #----------------------------------------------------------------------------------------
    #create header for logfile
    log.info("")
    log.info("*********************************************************")
    log.info("test turtle rural")
    log.info("This python script is developed by "
             + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
    log.info(version)
    log.debug('loading module (%s)' % __revision__)
    log.info("*********************************************************")
    log.info("arguments: %s" %(sys.argv))
    log.info("")

    #----------------------------------------------------------------------------------------
    location_scripts = "C:\\office.nelen-schuurmans.nl\\Products\\Turtle\\Trunk\\TurtleRural\\srcPython\\"
    location_testdata = "L:\\Intern\\Kennismanagement\\Turtle\\TestdatabaseRural\\"
    tests = []

    #----------------------------------------------------------------------------------------
    # TEST 1.1.1 OppervlakteParameter
    script = location_scripts+"rural_oppervlakteparameter.py"

    args = [location_testdata+"HydroBase\\HydrobaseRR_TEST.mdb\\RR_Features\\PeilGebieden",
            location_testdata+"LGN\\lgn5_zien",
            location_testdata+"LGN\\Conv_Maaiveld_toetspunt.dbf",
            location_testdata+"HydroBase\\HydrobaseRR_TEST.mdb\\RR_Oppervlak"]
    
    tests.append(' '.join([script] + args))

    #----------------------------------------------------------------------------------------
    # TEST 1.1.5 Toetspunten
    script = location_scripts+"rural_toetspuntenbepaling.py"

    args = [location_testdata+"HydroBase\\HydrobaseRR_TEST.mdb\\RR_Features\\PeilGebieden",
            location_testdata+"HydroBase\\HydrobaseRR_TEST.mdb\\RR_Peilgebied",
            location_testdata+"AHN\\ahn25_zien location_testdata",
            location_testdata+"LGN\\lgn5_zien",
            location_testdata+"LGN\\Conv_Maaiveld_toetspunt.dbf",
            location_testdata+"HydroBase\\HydrobaseRR_TEST.mdb\\RR_Toetspunten"]
    tests.append(' '.join([script] + args))

    log.info(tests)
    for test in tests:
        log.info("TEST %s" % test.split()[0])
        if os.system(test) > 0:
            log.warning("%s failed" % test.split()[0])
            
    log.info("*********************************************************")     
    log.info("Finished")
    log.info("*********************************************************")     
    
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



