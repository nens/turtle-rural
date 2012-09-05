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

def create_dict_fields(duikers):
    '''
    output: {verhang:'DOUBLE', bodem_hoogte_berekend:'DOUBLE',bodemhoogte_bovenstrooms:'DOUBLE',\
                      bodemhoogte_benedenstrooms:'DOUBLE',kduident:'TEXT', ovkident:'TEXT', gpgident:'TEXT'}
    '''
    fieldmapping = {}
    for ident, value in duikers.iteritems():
        for fieldname in value:
            if fieldname[-5:] == 'ident':
                fieldmapping[fieldname] = 'TEXT'
            else:
           
                fieldmapping[fieldname] = 'DOUBLE'
            
              
        break
     
    return fieldmapping
      #  dict_fields = 
        
def valid_value(value):
    '''
    Controle value, nulll, 0 of None
    '''
    list_of_none_values = [None,0,'0', ]
    if value in list_of_none_values:
        return False
    else:
        return True
    
def calc_verhang(h_bo, h_be, lengte):
    '''
    bereken verhang
    '''
    values = [h_bo, h_be, lengte]
    for value in values:
        if valid_value(value) == False:
            log.warning('Value %s is false' %value)
            log.warning('Verhang wordt niet berekend')
            verhang_value = None
            return verhang_value
            
    verhang_value = (h_bo -  h_be) / lengte
    return verhang_value

    
def create_output_dataset(gp, output_filename, dict_fields):
    '''
    Creates an output feature class for the tool with specified field names
    '''
    out_path = os.path.dirname(output_filename)
    out_name = os.path.basename(output_filename)
    
    gp.CreateFeatureClass_management(out_path, out_name, 'POLYLINE')
    addfieldnames(gp, output_filename, dict_fields) 
    
    
def addfieldnames(gp, output_filename, dict_fields):
    '''
    Adds fields to a feature class
    '''    
    for fieldname, type in dict_fields.iteritems():
        if turtlebase.arcgis.is_fieldname(gp, output_filename, fieldname) == True:
            continue
            
        gp.AddField_management(output_filename, fieldname, type)

def addvalues(gp, fc, fieldname_ident, dict_attribs):
    '''
    Adds values to a fc based on a dict with the structure dict1 = {[ident]:{fieldname1: value,fieldname2: value} }
    '''
    # Check for fields inbouwen
    
    # Add values
    row = gp.UpdateCursor(fc)
    for item in nens.gp.gp_iterator(row):
        kduident_value = item.getValue(fieldname_ident)
        # check for ident in dictionary
        if not kduident_value in dict_attribs:
            continue
        
        for fieldname, value in dict_attribs[kduident_value].iteritems():
            #log.info('%s  %s' %(fieldname,value))
            if value == None:
                value = -999
            item.SetValue(fieldname,value)
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
        
        # wordt globaal al geladen. maar werkt niet (?)
        
        import nens.gp
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
            output_fc = sys.argv[4]
        else:
            log.error("usage: <peilgebieden> <duikers> <waterlopen_legger>")
            sys.exit(1)

        if not gp.exists(peilgebieden_fc):
                log.error("Features '%s' is not available in the hydrobase" % peilgebieden_fc)
                sys.exit(1)

        # TOEVOEGEN: CONTROLE basisdata

        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        #check_fields = {}
        gpgident = config.get("general", "gpgident").lower()
        kduident = config.get("controle_kunstwerken", "kduident").lower()
        ovkident = config.get("general", "ovkident").lower()
        bodemhoogte_benedenstrooms = config.get("controle_kunstwerken", "bodemhoogte_benedenstrooms").lower()
        bodemhoogte_bovenstrooms = config.get("controle_kunstwerken", "bodemhoogte_bovenstrooms").lower()
        winterpeil = config.get("controle_kunstwerken", "winterpeil").lower()
        zomerpeil = config.get("controle_kunstwerken", "zomerpeil").lower()
        bodem_hoogte_berekend = config.get("controle_kunstwerken", "bodem_hoogte_berekend").lower()
        verhang = config.get("controle_kunstwerken", "verhang").lower()
        duiker_middellijn_diam= config.get("controle_kunstwerken", "duiker_middellijn_diam").lower()
        duikerhoogte_bovenstrooms= config.get("controle_kunstwerken", "duikerhoogte_bovenstrooms").lower()
        duikerhoogte_benedenstrooms= config.get("controle_kunstwerken", "duikerhoogte_benedenstrooms").lower()

        check_fields = {peilgebieden_fc: [gpgident, winterpeil, zomerpeil],
                         input_waterlopen_legger: [ovkident, bodemhoogte_benedenstrooms,bodemhoogte_bovenstrooms],
                         input_duikers: [duiker_middellijn_diam,duikerhoogte_bovenstrooms,duikerhoogte_benedenstrooms]
                         }
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
        
   
       
        #---------------------------------------------------------------------
        # Join van duikers met watergangen
        # Creeer 
        log.info('Koppel kunstwerken met watergangen')
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
        # Inlezen data uit de watergangen
        log.info('duikers_incl_watergangen %s' %duikers_incl_watergangen)
        treshold_value_verhang_duikers = 0.05
        row = gp.SearchCursor(duikers_incl_watergangen)
        for item in nens.gp.gp_iterator(row):
            kduident_value = item.getValue(kduident)
            ovkident_value = item.getValue(ovkident)
            
            if not kduident_value in duikers:
                duikers[kduident_value] = {}
            bodemhoogte_benedenstrooms_value = item.getValue(bodemhoogte_benedenstrooms)
            bodemhoogte_bovenstrooms_value = item.getValue(bodemhoogte_bovenstrooms)
            # Neem laagste waarde van de bodemhoogte
            bodem_hoogte_berekend_value = min([bodemhoogte_bovenstrooms_value, bodemhoogte_benedenstrooms_value])
            # bereken verhang
            verhang_value = calc_verhang(bodemhoogte_bovenstrooms_value, bodemhoogte_benedenstrooms_value,  item.Shape.Length)
            if verhang_value == None:
                log.warning('Verhang kon niet berekend worden voor duiker %s' %kduident_value)
            if verhang_value > treshold_value_verhang_duikers:
                log.warning('Verhang van duiker %s is groter dan %s' %(kduident_value, treshold_value_verhang_duikers) )
            # sla op in dictionary
            duikers[kduident_value][bodemhoogte_benedenstrooms] = bodemhoogte_benedenstrooms_value
            duikers[kduident_value][bodemhoogte_bovenstrooms] =  bodemhoogte_bovenstrooms_value
            duikers[kduident_value][bodem_hoogte_berekend] =  bodem_hoogte_berekend_value
            duikers[kduident_value][verhang] =  verhang_value
            duikers[kduident_value][ovkident] =  ovkident_value
            # deze verplaatsen naar inlezen data duikers:
            duikers[kduident_value][kduident] =  kduident_value
        
        # Inlezen data uit de peilgebieden
        log.info('Koppel kunstwerken met peilgebieden')
        row = gp.SearchCursor(duikers_incl_peilgebieden)
        for item in nens.gp.gp_iterator(row):
            kduident_value = item.getValue(kduident)
            if not kduident_value in duikers:
                duikers[kduident_value] = {}
            winterpeil_value = item.getValue(winterpeil)
            zomerpeil_value = item.getValue(zomerpeil)
            gpgident_value = item.getValue(gpgident)
            
            duikers[kduident_value][zomerpeil] =  zomerpeil_value
            duikers[kduident_value][winterpeil] =  winterpeil_value
            duikers[kduident_value][gpgident] =  gpgident_value
            
        # inlezen data uit de duikers en berekening van % dekking
        log.info('Bereken dekkingspercentages')
        count = 1
        count_rounder = 1
        row = gp.SearchCursor(input_duikers)
        for item in nens.gp.gp_iterator(row):
            kduident_value = item.getValue(kduident)
            # Add counter
            count = count + 1

            if int(count / 100) != count_rounder:
                log.info("Processing duiker %s" % count)
                count_rounder = int(count / 100)
                
            min_list = []
            duiker_middellijn_diam_value = item.getValue(duiker_middellijn_diam) 
            duikerhoogte_benedenstrooms_value = item.getValue(duikerhoogte_benedenstrooms)
            duikerhoogte_bovenstrooms_value = item.getValue(duikerhoogte_bovenstrooms)
            
            duikerhoogte_bovenstrooms_value
            if valid_value(duikerhoogte_benedenstrooms_value):
                duikerhoogte_benedenstrooms_value_fl = float(duikerhoogte_benedenstrooms_value)
                min_list.append(duikerhoogte_benedenstrooms_value_fl)
            if valid_value(duikerhoogte_bovenstrooms_value):
                duikerhoogte_bovenstrooms_value_fl = float(duikerhoogte_bovenstrooms_value)
                min_list.append(duikerhoogte_benedenstrooms_value_fl)
            if min_list == []:
                duikerhoogte_value = -999
            else:
                duikerhoogte_value = min(min_list)
                
            
            peil_hoogte = min([duikers[kduident_value][winterpeil],duikers[kduident_value][zomerpeil]])
            
            duikers[kduident_value][duiker_middellijn_diam] =  duiker_middellijn_diam_value
            duikers[kduident_value][duikerhoogte_bovenstrooms] =  duikerhoogte_bovenstrooms_value
            duikers[kduident_value][duikerhoogte_benedenstrooms] =  duikerhoogte_benedenstrooms_value
            
            # als alle waarden valid dan toepassen, anders niet
            if valid_value(duiker_middellijn_diam_value) and valid_value(duikerhoogte_value) and valid_value(peil_hoogte):
                duikerhoogte_value_nap = duikerhoogte_value + duiker_middellijn_diam_value
                
                perc_bovenwaterlijn = ((duikerhoogte_value_nap - peil_hoogte)/duiker_middellijn_diam_value) * 100
            else:
                perc_bovenwaterlijn = -99
            duikers[kduident_value]['perc_wat'] = perc_bovenwaterlijn
            
        
        # creeer output dataset
        dict_fields = create_dict_fields(duikers)
      #  dict_fields = {verhang:'DOUBLE', bodem_hoogte_berekend:'DOUBLE',bodemhoogte_bovenstrooms:'DOUBLE',\
       #                bodemhoogte_benedenstrooms:'DOUBLE',kduident:'TEXT', ovkident:'TEXT', gpgident:'TEXT',\
        #               zomerpeil}
        
        log.info('dict_fields %s' %dict_fields)
        log.info('Creeer output file')
        # create rough copy 
        duikers_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        gp.Select_analysis(input_duikers,duikers_temp)
        
        log.info('Vul output file met berekende waarden')
        # Vul de dataset met de waarden uit de dictionary
        addfieldnames(gp, duikers_temp, dict_fields)
        addvalues(gp, duikers_temp, kduident, duikers)
        
        # Create output file
        log.info('Opschonen output file')
        # als Append gebruikt wordt, kan er gebruik worden gemaakt van fieldmapping
        create_output_dataset(gp, output_fc, dict_fields)
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
