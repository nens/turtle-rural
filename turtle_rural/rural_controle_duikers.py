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
import turtlebase.general

log = logging.getLogger(__name__)

def create_output_dataset(output_filename, dict_fields):
    '''
    Creates an output feature class for the tool with specified field names
    '''
    out_path = os.path.dirname(output_filename)
    out_name = os.path.basename(output_filename)
    
    gp.CreateFeatureClass_management(out_path, out_name, 'POINT')
    addfieldnames(output_filename, dict_fields) 
    
    
def addfieldnames(output_filename, dict_fields):
    '''
    Adds fields to a feature class
    '''    
    for fieldname, type in dict_fields.iteritems():
        gp.AddField_management(output_filename, fieldname, type)

def addvalues(fc, fieldname_ident, dict_attribs):
    '''
    Adds values to a fc based on a dict with the structure dict1 = {[ident]:{fieldname1: value,fieldname2: value} }
    '''
    # Check for fields inbouwen
    
    # Add values
    row = gp.SearchCursor(fc)
    for item in nens.gp.gp_iterator(row):
        ovkident_value = item.getValue(fieldname_ident)
        # check for ident in dictionary
        if not ovkident_value in dict_attribs:
            continue
        
        for fieldname, value in dict_attribs[ovkident_value].iteritems():
            item.SetValue(fieldname,ovkident_value)
            row.UpdateRow(item)
    

def main():
    try:
        """
        Deze module controleert of hoeveel procent duikers onder streefpeil liggen en hoeveel procent duikers onder zij onder bodemniveau liggen.
          
        """
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)
        #---------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                        gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)
        #---------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 5:
            peilgebieden_fc = sys.argv[1]
            input_duikers = sys.argv[2]
            input_waterlopen_legger = sys.argv[3]
            output_fc = = sys.argv[4]
        else:
            log.error("usage: <peilgebieden> <duikers> <waterlopen_legger>")
            sys.exit(1)

        if not gp.exists(peilgebieden_fc):
                log.error("Features '%s' is not available in the hydrobase" % peilgebieden_fc)
                sys.exit(1)

        rr_peilgebied = os.path.join(hydrobase,
                                     config.get('waterbalans',
                                                'rr_peilgebied'))
        if not gp.exists(rr_peilgebied):
                log.error("Table '%s' is not available in the hydrobase" % config.get('waterbalans', 'rr_peilgebied'))
                sys.exit(1)

        rr_oppervlak = os.path.join(hydrobase,
                                    config.get('waterbalans',
                                               'rr_oppervlak'))
        if not gp.exists(rr_oppervlak):
                log.error("Table '%s' is not available in the hydrobase" % config.get('waterbalans', 'rr_oppervlak'))
                sys.exit(1)


        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        #check_fields = {}
        gpgident = config.get("general", "gpgident").lower()
        kwkident = config.get("general", "kwkident").lower()
        ovkident = config.get("general", "ovkident").lower()
        bodemhoogte_benedenstrooms = config.get("controle_kunstwerken", "bodemhoogte_benedenstrooms").lower()
        bodemhoogte_bovenstrooms = config.get("controle_kunstwerken", "bodemhoogte_bovenstrooms").lower()
        winterpeil = config.get("controle_kunstwerken", "winterpeil").lower()
        zomerpeil = config.get("controle_kunstwerken", "zomerpeil").lower()
        bodem_hoogte_berekend = config.get("controle_kunstwerken", "bodem_hoogte_berekend").lower()
        verhang = config.get("controle_kunstwerken", "verhang").lower()

        check_fields = {peilgebieden_fc: [gpgident, winterpeil, zomerpeil],
                         input_waterlopen_legger: [ovkident, bodemhoogte_benedenstrooms,bodemhoogte_bovenstrooms]}
        for input_fc, fieldnames in check_fields.items():
            for fieldname in fieldnames:
                if not turtlebase.arcgis.is_fieldname(
                        gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (
                                    fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments
        log.info("Check numbers of fields in input data")
        errorcode = 0
        nr_gpg = turtlebase.arcgis.fc_records(gp, peilgebieden_fc)
        if nr_gpg == 0:
            log.error("%s fc is empty" % peilgebieden_fc)
            errorcode += 1
        
        temp_workspace = tobecreated! 
       
        #---------------------------------------------------------------------
        # Join van duikers met watergangen
        # Creeer 
        duikers_incl_watergangen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        gp.Spatialjoin_analysis(input_duikers, input_waterlopen_legger, duikers_incl_watergangen)
        #---------------------------------------------------------------------
        # Join van duikers met peilgebieden
        duikers_incl_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        gp.Spatialjoin_analysis(input_duikers, peilgebieden_fc, duikers_incl_peilgebieden)

        # Initieer dictionary
        duikers = {}
        #---------------------------------------------------------------------
        # Inlezen data duikers, vullen dictionary
        row = gp.SearchCursor(duikers_incl_watergangen)
        for item in nens.gp.gp_iterator(row):
            kwkident_value = item.getValue(kwkident)
            if not kwkident_value in duikers:
                duikers[kwkident_value] = {}
            bodemhoogte_benedenstrooms_value = item.getValue(bodemhoogte_benedenstrooms)
            bodemhoogte_bovenstrooms_value = item.getValue(bodemhoogte_bovenstrooms)
            # Neem laagste waarde van de bodemhoogte
            bodem_hoogte_berekend_value = min([bodemhoogte_bovenstrooms_value, bodemhoogte_benedenstrooms_value])
            # bereken verhang
            verhang_value = (bodemhoogte_bovenstrooms_value -  bodemhoogte_benedenstrooms_value) / item.Shape.Length
            
            # sla op in dictionary
            duikers[kwkident_value][bodemhoogte_benedenstrooms] = bodemhoogte_benedenstrooms_value
            duikers[kwkident_value][bodemhoogte_bovenstrooms] =  bodemhoogte_bovenstrooms_value
            duikers[kwkident_value][bodem_hoogte_berekend] =  bodem_hoogte_berekend_value
            duikers[kwkident_value][verhang] =  verhang_value
    
    
        row = gp.SearchCursor(duikers_incl_peilgebieden)
        for item in nens.gp.gp_iterator(row):
            kwkident_value = item.getValue(kwkident)
            if not kwkident_value in duikers:
                duikers[kwkident_value] = {}
            winterpeil_value = item.getValue(winterpeil)
            zomerpeil_value = item.getValue(zomerpeil)
            
        
        # creeer output dataset
        dict_fields = {verhang:'DOUBLE', bodem_hoogte_berekend:'DOUBLE',bodemhoogte_bovenstrooms:'DOUBLE',\
                       bodemhoogte_benedenstrooms:'DOUBLE',kwkident:'TEXT', ovkident:'TEXT', gpgident:'TEXT'}
        
        
         
        # create rough copy 
        duikers_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        gp.Select_analysis(input_duikers,duikers_temp)
        
        # Vul de dataset met de waarden uit de dictionary
        addfieldnames(duikers_temp, dict_fields)
        addvalues(duikers_temp, duikers)
        
        # Create output file
        # als Append gebruikt wordt, kan er gebruik worden gemaakt van fieldmapping
        create_output_dataset(output_fc, dict_fields)
        gp.Append_management(duikers_temp,output_fc, 'NO_TEST')
                
        #---------------------------------------------------------------------
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
