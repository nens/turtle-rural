# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

# Import system modules
import sys
import os
import shutil
import logging
import traceback
import ConfigParser

# Import GIS modules
import arcgisscripting
import nens.gp

# Import Turtlebase modules
import turtlebase.arcgis
import turtlebase.general
from turtle_rural import rural_convert_to_sobek
from turtlebase.logutils import LoggingConfig

log = logging.getLogger(__name__)

# Create the Geoprocessor object
gp = arcgisscripting.create()

def check_input_id_and_names(fc, id_field, name_field, ids_found):
    """
    check all used feature classes and check for multiple ids
    check for integer ids (sobek will give problems on that)
    check for apostroph in names and ids
    """
    number_of_warnings = 0
    
    fc_name = os.path.basename(fc)
    log.info(" - check ids and names in %s" % fc_name)
    table_def = nens.gp.get_table_def(gp, fc)  
    if id_field.lower() not in table_def.keys():
        log.error("%s not found in %s" % (id_field, fc))
    elif name_field.lower() not in table_def.keys():
        log.error("%s not found in %s" % (name_field, fc))
    else:            
        rows = gp.SearchCursor(fc)
        for row in nens.gp.gp_iterator(rows):
            id = row.GetValue(id_field)
            name = row.GetValue(name_field)
            if id is None:
                log.warning("id %s is empty" % id)
                number_of_warnings += 1

            if id in ids_found:
                log.warning("id %s is used more than once" % id)
                number_of_warnings += 1

            ids_found.add(id)
            
            if is_integer(id):
                if id < 10000:
                    log.warning("id %s is an integer" % id)
                    number_of_warnings += 1
                
            if id == "" or id == " ":
                log.warning("id %s is empty" % id)
                number_of_warnings += 1
                
            if "'" in id:
                log.warning("id %s contains an apostroph" % id)
                number_of_warnings += 1
                
            if name is not None:
                if "'" in name:
                    log.warning("%s contains an apostroph" % name)
                    number_of_warnings += 1
                    
    return number_of_warnings, ids_found


def is_integer(i):
    """checks if i is an integer or not
    """
    try:
        number = int(i.strip())
        return True
    except ValueError:
        return False


def read_settings_ini(settings, header):
    """Read extra settings for CF conversion
    """
    ini = turtlebase.general.read_ini_file(settings, header)
    settings_ini = turtlebase.general.convert_ini_settings_to_dictionary(ini)
    return settings_ini


def main():
    """Console script for Turtle-rural: CF Conversion
    """
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
        
        output_folder = sys.argv[1]
        log.info("output_dir: "+output_folder)
        
        #add extra logfile
        fileHandler2 = logging.FileHandler(output_folder+'\\cf_convert.log')
        logging.getLogger("").addHandler(fileHandler2)
        
        #----------------------------------------------------------------------------------------
        #create header for logfile
        log.info("*********************************************************")
        log.info(__name__)
        log.info("This python script is developed by "
                 + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
        log.info("*********************************************************")
        log.info("arguments: "+str(sys.argv))

        #----------------------------------------------------------------------------------------
        log.info("Output dir: "+output_folder)
        output_shapefiles = output_folder+'\\shapefiles'
        log.info("Output shapefiles: "+output_folder)
        output_sobek = output_folder+'\\sobek_input'
        log.info("Output sobek files: "+output_folder)

        #default settings
        settings = sys.argv[2]
        if settings == "#":
            settings = os.path.join(os.path.dirname(sys.argv[0]), config.get('CF', 'cf_default_ini'))
            log.info("default settings: %s" % settings)
            if not os.path.isfile(settings):
                log.error("cannot find default ini-file")
                sys.exit(1)
        
        #copy settings
        shutil.copyfile(settings, output_folder+'\\cf-settings.ini')

        #create folders for output data
        if not os.path.isdir(output_shapefiles):
            log.info("Creating '"+output_shapefiles+"'")
            os.makedirs(output_shapefiles)
        if not os.path.isdir(output_sobek):
            log.info("Creating '"+output_sobek+"'")
            os.makedirs(output_sobek)

        #----------------------------------------------------------------------------------------
        # Check ids and names in structures    
        ids_found = set()
        number_of_errors = 0

        # Check ids and names in bridge
        input_bridge = sys.argv[3]
        if input_bridge != "#":
            log.info("Check ids and names of input bridge")
            bridge_ini = read_settings_ini(settings, 'column.bridge')
            bridge_id = bridge_ini['id']
            bridge_name = bridge_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_bridge, bridge_id, bridge_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1
                
            # export shapefile
            log.info("export %s" % os.path.basename(input_bridge))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_bridge) + ".shp"
            gp.Select_analysis(input_bridge, output_shapefile)

        # Check ids and names in culvert
        input_culvert = sys.argv[4]
        if input_culvert != "#":
            log.info("Check ids and names of input culvert")
            culvert_ini = read_settings_ini(settings, 'column.culvert')
            culvert_id = culvert_ini['id']
            culvert_name = culvert_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_culvert, culvert_id, culvert_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1
                
            # export shapefile
            log.info("export %s" % os.path.basename(input_culvert))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_culvert) + ".shp"
            gp.Select_analysis(input_culvert, output_shapefile)

        # Check ids and names in syphon
        input_syphon = sys.argv[5]
        if input_syphon != "#":
            log.info("Check ids and names of input syphon")
            syphon_ini = read_settings_ini(settings, 'column.syphon')
            syphon_id = syphon_ini['id']
            syphon_name = syphon_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_syphon, syphon_id, syphon_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1

            # export shapefile
            log.info("export %s" % os.path.basename(input_syphon))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_syphon) + ".shp"
            gp.Select_analysis(input_syphon, output_shapefile)            

        # Check ids and names in pump
        input_pump = sys.argv[6]
        if input_pump != "#":
            log.info("Check ids and names of input pump")
            pump_ini = read_settings_ini(settings, 'column.pump')
            pump_id = pump_ini['id']
            pump_name = pump_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_pump, pump_id, pump_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1

            # export shapefile
            log.info("export %s" % os.path.basename(input_pump))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_pump) + ".shp"
            gp.Select_analysis(input_pump, output_shapefile)    

        # Check ids and names in weir
        input_weir = sys.argv[8]
        if input_weir != "#":
            log.info("Check ids and names of input weir")
            weir_ini = read_settings_ini(settings, 'column.weir')
            weir_id = weir_ini['id']
            weir_name = weir_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_weir, weir_id, weir_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1

            # export shapefile
            log.info("export %s" % os.path.basename(input_weir))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_weir) + ".shp"
            gp.Select_analysis(input_weir, output_shapefile)    
                
        # Check ids and names in univw
        input_univw = sys.argv[9]
        if input_univw != "#":
            log.info("Check ids and names of input univw")
            univw_ini = read_settings_ini(settings, 'column.univw')
            univw_id = univw_ini['id']
            univw_name = univw_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_univw, univw_id, univw_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1

            # export shapefile
            log.info("export %s" % os.path.basename(input_univw))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_univw) + ".shp"
            gp.Select_analysis(input_univw, output_shapefile)    

        
        #----------------------------------------------------------------------------------------
        # Check ids and names in xsection
        input_xsection = sys.argv[10]
        if input_xsection != "#":
            log.info("Check ids and names of input xsection")
            xsection_ini = read_settings_ini(settings, 'column.xsection')
            xsection_id = xsection_ini['id']
            xsection_name = xsection_ini['profile_id']

            number_of_warnings, ids_found = check_input_id_and_names(input_xsection, xsection_id, xsection_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1

            # export shapefile
            log.info("export %s" % os.path.basename(input_xsection))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_xsection) + ".shp"
            gp.Select_analysis(input_xsection, output_shapefile)    
        #----------------------------------------------------------------------------------------
        # Check ids and names in xsection definition
        input_xsection = sys.argv[11]
        if input_xsection != "#":
            log.info("Check ids and names of input xsection definition")
            xsection_ini = read_settings_ini(settings, 'column.xsection')
            xsection_id = xsection_ini['profile_id']
            xsection_name = xsection_ini['profile_id']
            ids_def_found = set()

            number_of_warnings, ids_found = check_input_id_and_names(input_xsection, xsection_id, xsection_name, ids_def_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1
        #----------------------------------------------------------------------------------------
        # Check ids and names in waterline
        input_waterline = sys.argv[14]
        if input_waterline != "#":
            log.info("Check ids and names of input waterline")
            waterline_ini = read_settings_ini(settings, 'column.waterline')
            waterline_id = waterline_ini['id']
            waterline_name = waterline_ini['name']

            number_of_warnings, ids_found = check_input_id_and_names(input_waterline, waterline_id, waterline_name, ids_found)
            if number_of_warnings > 0:
                log.error("validation of ids and names failed, %s warnings found, this will give problems in Sobek" % number_of_warnings)
                number_of_errors += 1
                
            # export shapefile
            log.info("export %s" % os.path.basename(input_waterline))
            output_shapefile = output_shapefiles + "\\" + os.path.basename(input_waterline) + ".shp"
            gp.Select_analysis(input_waterline, output_shapefile)        

        if number_of_errors > 0:
            log.error("errors in input data, check above warnings")
            sys.exit()
        #----------------------------------------------------------------------------------------
        rural_convert_to_sobek.main({},[output_sobek]+[settings]+sys.argv[3:])

        log.info("*********************************************************")
        log.info("Finished")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
