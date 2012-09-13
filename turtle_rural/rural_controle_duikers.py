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

def calculate_stuwen(stuwen_dict, config, nodatavalue,\
                                      bodemhoogte_benedenstrooms, bodemhoogte_bovenstrooms,\
                                      stuw_hoogte, zomerpeil, winterpeil,\
                                      output_field_stuw_percentage_bodem, output_field_stuw_tov_winterpeil,\
                                      output_field_stuw_tov_zomerpeil):
    '''
    '''
    for kunstwerk_ident in stuwen_dict:
        # Bereken minimale bodemhoogte in watergang
        bodemhoogte_benedenstrooms_value = stuwen_dict[kunstwerk_ident][bodemhoogte_benedenstrooms] 
        bodemhoogte_bovenstrooms_value = stuwen_dict[kunstwerk_ident][bodemhoogte_bovenstrooms]
        bodemhoogte_value = get_lowest_value([bodemhoogte_bovenstrooms_value, bodemhoogte_benedenstrooms_value], nodatavalue)
        
        # Bereken hoogte stuw tov bodem
        stuw_hoogte_value = stuwen_dict[kunstwerk_ident][stuw_hoogte]
        stuwhoogte_tov_bodem = calc_height_stuw_tov_value(stuw_hoogte_value, bodemhoogte_value, nodatavalue)
        stuwen_dict[kunstwerk_ident][output_field_stuw_percentage_bodem] = stuwhoogte_tov_bodem
        
        # Bereken hoogte stuw tov zomerpeil
        zomerpeil_value = stuwen_dict[kunstwerk_ident][zomerpeil]
        stuwhoogte_tov_zomerpeil = calc_height_stuw_tov_value(stuw_hoogte_value, zomerpeil_value, nodatavalue)
        stuwen_dict[kunstwerk_ident][output_field_stuw_tov_zomerpeil] = stuwhoogte_tov_zomerpeil

        # Bereken hoogte stuw tov winterpeil       
        winterpeil_value = stuwen_dict[kunstwerk_ident][winterpeil]
        stuwhoogte_tov_winterpeil = calc_height_stuw_tov_value(stuw_hoogte_value, winterpeil_value, nodatavalue)
        stuwen_dict[kunstwerk_ident][output_field_stuw_tov_winterpeil] = stuwhoogte_tov_winterpeil
        
    return stuwen_dict
    
def calc_height_stuw_tov_value(stuw_hoogte_value, bodemhoogte_value, nodatavalue):
    '''
    
    '''
    if valid_value(stuw_hoogte_value)!= nodatavalue and valid_value(bodemhoogte_value)!= nodatavalue:
        stuwhoogte_tov_bodem = stuw_hoogte_value - bodemhoogte_value
    else:
        stuwhoogte_tov_bodem = nodatavalue
        
    return stuwhoogte_tov_bodem

def get_lowest_value(list_values, nodatavalue):
        min_list = []
        for value in list_values:
            if valid_value(value):
                value_fl = float(value)
                min_list.append(value_fl)

        if min_list == []:
            lowest_value = nodatavalue
        else:
            lowest_value = min(min_list)
        return lowest_value
   
def  assess_shape(duiker_vorm):
    """
    De codes van de vorm opening:
    99 onbekend (aanname = rond)
    98 Overig (aanname = rond)
    1 rond
    2 rechthoekig
    3 eivormig
    4 muil
    5 ellips
    6 heul
    """
    diameter_nodig = [1,3,4,5,6,98,99]
    hoogte_nodig = [2]
    

def calculate_duikers(duikers_dict, config, nodatavalue, treshold_value_verhang_duikers, duiker_vorm\
                      bodemhoogte_benedenstrooms, bodemhoogte_bovenstrooms, duiker_middellijn_diam, duiker_hoogte\
                      duikerhoogte_bovenstrooms, duikerhoogte_benedenstrooms, zomerpeil, winterpeil,\
                      output_field_duikerlengte, output_field_duikerverhang, output_field_percentage_bodem,
                      output_field_percentage_bovenwinterpeil, output_field_percentage_bovenzomerpeil):
    """
    input: dictionary met duiker informatie
    output: dictionary met berekende duiker informatie
    indien een berekening niet kan, of als er nodata waarden zijn dan wordt er -9999 ingevuld 
    

    De codes van de vorm opening:
    99 onbekend (aanname = rond)
    98 Overig (aanname = rond)
    1 rond
    2 rechthoekig
    3 eivormig
    4 muil
    5 ellips
    6 heul
    """
    diameter_nodig = [1,3,4,5,6,98,99]
    hoogte_nodig = [2]

            
    
    for kunstwerk_ident in duikers_dict:
        # Bepaal de vorm van de duikers, en kies het bijbehorende hoogteveld
        duiker_vorm = duikers_dict[kunstwerk_ident][bodemhoogte_benedenstrooms] 
        if duiker_vorm in hoogte_nodig:
            hoogte = duiker_hoogte
        else:
            hoogte = duiker_middellijn_diam
        
        # --------------------------------------------------------------------------------------
        # Bereken percentage boven waterspiegel
        # Neem laagste waarde van de bodemhoogte
        
        bodemhoogte_benedenstrooms_value = duikers_dict[kunstwerk_ident][bodemhoogte_benedenstrooms] 
        bodemhoogte_bovenstrooms_value = duikers_dict[kunstwerk_ident][bodemhoogte_bovenstrooms] 
        bodem_hoogte_berekend_value = get_lowest_value([bodemhoogte_bovenstrooms_value,bodemhoogte_benedenstrooms_value], nodatavalue)
        
        duikerhoogte_bovenstrooms_value = duikers_dict[kunstwerk_ident][duikerhoogte_bovenstrooms]
        duikerhoogte_benedenstrooms_value = duikers_dict[kunstwerk_ident][duikerhoogte_benedenstrooms]
        
        duikerhoogte_value = get_lowest_value([duikerhoogte_benedenstrooms_value, duikerhoogte_bovenstrooms_value], nodatavalue)
        
        # --------------------------------------------------------------------------------------
        # Bereken verhang duiker
        lengte =  duikers_dict[kunstwerk_ident][output_field_duikerlengte]
        verhang_value = calc_verhang(duikerhoogte_bovenstrooms_value, duikerhoogte_benedenstrooms_value,lengte)
        if verhang_value == None:
            log.warning('Verhang kon niet berekend worden voor kunstwerk %s' %kunstwerk_ident)
        if verhang_value > treshold_value_verhang_duikers:
            log.warning('Verhang van kunstwerk %s is groter dan %s' %(kunstwerk_ident, treshold_value_verhang_duikers) )
        if verhang_value < 0:
            log.warning('Verhang van kunstwerk %s is negatief' %(kunstwerk_ident) )
        duikers_dict[kunstwerk_ident][output_field_duikerverhang] = verhang_value
        
        winterpeil_value= float(duikers_dict[kunstwerk_ident][winterpeil])
        zomerpeil_value= float(duikers_dict[kunstwerk_ident][zomerpeil])
        hoogte_value = duikers_dict[kunstwerk_ident][hoogte]
        
        # als alle waarden valid dan toepassen, anders niet
        # Bereken percentage voor diverse peilen:
        perc_bovenwaterlijn_zomerpeil = calc_percentage_above_waterlevel(hoogte_value, duikerhoogte_value, zomerpeil_value, nodatavalue)
        perc_bovenwaterlijn_winterpeil = calc_percentage_above_waterlevel(hoogte_value, duikerhoogte_value, winterpeil_value, nodatavalue)
        duikers_dict[kunstwerk_ident][output_field_percentage_bovenwinterpeil] = round(perc_bovenwaterlijn_winterpeil,2)
        duikers_dict[kunstwerk_ident][output_field_percentage_bovenzomerpeil] = round(perc_bovenwaterlijn_zomerpeil,2)
        
        # Bereken percentage van de duiker onder bodemniveau
        perc_under_bottomlevel = calc_percentage_under_bottomlevel(duikerhoogte_value, bodem_hoogte_berekend_value, hoogte_value, nodatavalue)
        duikers_dict[kunstwerk_ident][output_field_percentage_bodem] = round(perc_under_bottomlevel,2)
        
    return duikers_dict

   
    
def calc_percentage_under_bottomlevel(duikerhoogte_value, bodemhoogte_value, hoogte_value, nodatavalue):
    '''
    '''
    if valid_value(bodemhoogte_value)== nodatavalue:
        perc_underbottomlevel = nodatavalue
    elif valid_value(hoogte_value)!= nodatavalue and valid_value(duikerhoogte_value)!= nodatavalue and valid_value(bodemhoogte_value)!= nodatavalue:
        duikerhoogte_value_nap = duikerhoogte_value + hoogte_value
        
        
        perc_underbottomlevel = (1-(duikerhoogte_value_nap - bodemhoogte_value)/hoogte_value) * 100
        if perc_underbottomlevel > 100:
            perc_underbottomlevel = 100
        if perc_underbottomlevel < 0:
            perc_underbottomlevel = 0
    else:
        perc_underbottomlevel = nodatavalue
    return perc_underbottomlevel
    

def calc_percentage_above_waterlevel(hoogte_value, duikerhoogte_value, peil, nodatavalue):
    '''
    Berekend het percentage van de duiker boven peilniveau
    '''
    if valid_value(hoogte_value)!= nodatavalue and valid_value(duikerhoogte_value)!= nodatavalue and valid_value(peil)!= nodatavalue:
        duikerhoogte_value_nap = duikerhoogte_value + hoogte_value
        
        perc_bovenwaterlijn = ((duikerhoogte_value_nap - peil)/hoogte_value) * 100
        if perc_bovenwaterlijn > 100:
            perc_bovenwaterlijn = 100
        if perc_bovenwaterlijn < 0:
            perc_bovenwaterlijn = 0
    else:
        perc_bovenwaterlijn = nodatavalue
    return perc_bovenwaterlijn

def add_fc_attribs_to_dict(gp, fc, dict_values, fieldname_ident, attrib_type, fieldname_attrib_type):
    '''
    Adds specific shape objects to dictionary
    '''
    row = gp.SearchCursor(fc)
    for item in nens.gp.gp_iterator(row):
        ident_value = item.getValue(fieldname_ident)
        if not ident_value in dict_values:
            dict_values[ident_value] = {}
        if attrib_type == 'Length':
            dict_values[ident_value][fieldname_attrib_type]= item.shape.Length 
    
    return dict_values

def add_fc_values_to_dict(gp, fc, dict_values, fieldname_ident, list_fieldnames):
    '''
    Adds values to a dict from a fc.
    Input:
        - gp object 
        - feature class
        - dict_values, can be empty dict, or dict with structure: dict = {ident:{fieldname:value, fieldname1: value1, fieldname2: value2}}
        - fieldname ident: will be ident in dictionary
        - list_fieldnames. is list of fieldnames that will be read. 
    
    '''
    count = 1
    count_rounder = 1
    log.debug('Checking whether fieldnames exist in fc')
    for field_name in list_fieldnames:
        if not turtlebase.arcgis.is_fieldname(gp, fc, field_name):
            log.error('Fieldname %s is not available in %s' %(field_name,fc)) 
    
    log.info('Adding values from %s' %fc)
    
    row = gp.SearchCursor(fc)
    for item in nens.gp.gp_iterator(row):
        ident_value = item.getValue(fieldname_ident)
        
        # Adding a count for every 100 features processed. 
        count = count + 1
        if int(count / 100) != count_rounder:
            log.info("Processing feature nr %s" % count)
            count_rounder = int(count / 100)

        for field_name in list_fieldnames:
            value = item.getValue(field_name)
            if not ident_value in dict_values:
                dict_values[ident_value] = {}
            if valid_value(value):
                dict_values[ident_value][field_name] = value
            else:
                dict_values[ident_value][field_name] = -9999
            
    return dict_values

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
    list_of_none_values = [None,0,'0','None']
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

    
def create_output_dataset(gp, output_filename, dict_fields, type= 'POLYLINE'):
    '''
    Creates an output feature class for the tool with specified field names
    '''
    out_path = os.path.dirname(output_filename)
    out_name = os.path.basename(output_filename)
    
    gp.CreateFeatureClass_management(out_path, out_name, type)
    addfieldnames(gp, output_filename, dict_fields) 
    
    
def addfieldnames(gp, output_filename, dict_fields):
    '''
    Adds fields to a feature class
    '''    
    for fieldname, type in dict_fields.iteritems():
        if turtlebase.arcgis.is_fieldname(gp, output_filename, fieldname) == True:
            continue
            
        gp.AddField_management(output_filename, fieldname, type)

def add_dict_values_to_fc(gp, fc, fieldname_ident, dict_attribs, nodatavalue):
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
        log.debug('Adding %s' %kduident_value)
        for fieldname, value in dict_attribs[kduident_value].iteritems():
            #log.info('%s  %s' %(fieldname,value))
            if value == None:
                value = nodatavalue
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
        if len(sys.argv) == 9:
            peilgebieden_fc = sys.argv[1]
            input_duikers = sys.argv[2]
            input_stuwen = sys.argv[3]
            input_sifons = sys.argv[4]
            input_waterlopen_legger = sys.argv[5]
            output_duikers = sys.argv[6]
            output_stuwen = sys.argv[7]
            output_sifons = sys.argv[8]
        else:
            log.error("usage: <peilgebieden> <duikers> <stuwen> <sifons> <waterlopen_legger> <duikers_out> <stuwen_out> <sifons_out>")
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
        ovkident = config.get("general", "ovkident").lower()
        
        #legger
        bodemhoogte_benedenstrooms = config.get("controle_kunstwerken", "bodemhoogte_benedenstrooms").lower()
        bodemhoogte_bovenstrooms = config.get("controle_kunstwerken", "bodemhoogte_bovenstrooms").lower()
        bodem_hoogte_berekend = config.get("controle_kunstwerken", "bodem_hoogte_berekend").lower()
        
        #peilgebieden
        winterpeil = config.get("controle_kunstwerken", "winterpeil").lower()
        zomerpeil = config.get("controle_kunstwerken", "zomerpeil").lower()
        
        #verhang = config.get("controle_kunstwerken", "verhang").lower()
        
        #duikers
        kduident = config.get("controle_kunstwerken", "kduident").lower()
        duiker_middellijn_diam= config.get("controle_kunstwerken", "duiker_middellijn_diam").lower()
        duiker_vorm= config.get("controle_kunstwerken", "duiker_vorm").lower()
        duikerhoogte_bovenstrooms= config.get("controle_kunstwerken", "duikerhoogte_bovenstrooms").lower()
        duikerhoogte_benedenstrooms= config.get("controle_kunstwerken", "duikerhoogte_benedenstrooms").lower()
        duikerhoogte= config.get("controle_kunstwerken", "duikerhoogte").lower()
        
        # Inlezen outputveldnamen
        output_field_duikerlengte = config.get("controle_kunstwerken", "output_field_duikerlengte").lower()
        output_field_duikerverhang = config.get("controle_kunstwerken", "output_field_duikerverhang").lower()
        output_field_percentage_bodem = config.get("controle_kunstwerken", "output_field_percentage_bodem").lower()
        output_field_percentage_bovenwinterpeil = config.get("controle_kunstwerken", "output_field_percentage_bovenwinterpeil").lower() 
        output_field_percentage_bovenzomerpeil = config.get("controle_kunstwerken", "output_field_percentage_bovenzomerpeil").lower()
        
        #standaardwaardes
        nodatavalue = int(config.get("controle_kunstwerken", "nodatavalue").lower())
        treshold_value_verhang_duikers = float(config.get("controle_kunstwerken", "treshold_value_verhang_duikers").lower())
        treshold_value_verhang_sifons = config.get("controle_kunstwerken", "treshold_value_verhang_sifons").lower()        

        #stuwen
        kstident = config.get("controle_kunstwerken", "kstident").lower()
        stuw_hoogte = config.get("controle_kunstwerken", "stuw_hoogte").lower()
        
        #sifons
        ksyident = config.get("controle_kunstwerken", "ksyident").lower()
        sifonhoogte_benedenstrooms = config.get("controle_kunstwerken", "sifonhoogte_benedenstrooms").lower()
        sifonhoogte_bovenstrooms = config.get("controle_kunstwerken", "sifonhoogte_bovenstrooms").lower()
        sifon_middellijn_diam = config.get("controle_kunstwerken", "sifon_middellijn_diam").lower()
        sifon_vorm = config.get("controle_kunstwerken", "sifon_vorm").lower()
        sifonhoogte = config.get("controle_kunstwerken", "sifonhoogte").lower()
        
        sifon_middellijn_diam2 = config.get("controle_kunstwerken", "sifon_middellijn_diam2").lower()
        output_field_sifonverhang = config.get("controle_kunstwerken", "output_field_sifonverhang").lower()
        output_field_sifon_percentage_bodem = config.get("controle_kunstwerken", "output_field_sifon_percentage_bodem").lower()
        output_field_sifon_percentage_bovenwinterpeil = config.get("controle_kunstwerken", "output_field_sifon_percentage_bovenwinterpeil").lower()
        output_field_sifon_percentage_bovenzomerpeil = config.get("controle_kunstwerken", "output_field_sifon_percentage_bovenzomerpeil").lower()

        # store fieldnames in a list, for convenience in further use
        list_fieldnames_watergangen = [ovkident, bodemhoogte_benedenstrooms,bodemhoogte_bovenstrooms]
        list_fieldnames_peilgebieden = [gpgident, winterpeil, zomerpeil]
        list_fieldnames_duikers = [kduident, duiker_middellijn_diam,duikerhoogte_bovenstrooms,duikerhoogte_benedenstrooms, duiker_vorm]
        list_fieldnames_stuwen = [kstident,stuw_hoogte]
        list_fieldnames_sifons = [ksyident,sifonhoogte_benedenstrooms,sifonhoogte_bovenstrooms,sifon_middellijn_diam,sifon_middellijn_diam2, sifon_vorm] 
        
        check_fields = {peilgebieden_fc: list_fieldnames_peilgebieden,
                         input_waterlopen_legger: list_fieldnames_watergangen,
                         input_duikers: list_fieldnames_duikers,
                         input_stuwen: list_fieldnames_stuwen,
                         input_sifons: list_fieldnames_sifons
                         }
        
        for input_fc, fieldnames in check_fields.items():
            if input_fc !='#':
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
        
        if input_duikers != '#':
            #-------------------------------------------------------------------------------------------------------------------------------
            # SECTION DUIKERS
            # 
            #
            #---------------------------------------------------------------------
            # check of alle benodigde bestanden zijn ingevuld:
            benodigdebestanden = [input_waterlopen_legger, peilgebieden_fc, output_duikers]
            for fc in benodigdebestanden:
                
                if fc =='#': 
                    log.error('Bestand %s is noodzakelijk om duikers te controleren' %fc)
            # Initieer dictionary
            duikers = {}
            #---------------------------------------------------------------------
            # Join van duikers met watergangen
            log.info('Koppel kunstwerken met watergangen')
            duikers_incl_watergangen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Spatialjoin_analysis(input_duikers, input_waterlopen_legger, duikers_incl_watergangen)
            # Wegschrijven data naar dictionary
            log.info('Schrijf informatie weg naar kunstwerken')
            duikers = add_fc_values_to_dict(gp, duikers_incl_watergangen, duikers, kduident, list_fieldnames_watergangen)
            
            #---------------------------------------------------------------------
            # Join van duikers met peilgebieden
            log.info('Koppel kunstwerken met peilgebieden')
            duikers_incl_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Spatialjoin_analysis(input_duikers, peilgebieden_fc, duikers_incl_peilgebieden)
            duikers = add_fc_values_to_dict(gp, duikers_incl_peilgebieden, duikers, kduident, list_fieldnames_peilgebieden)
            # Inlezen data uit de duikers            
            output_field_duikerlengte = config.get("controle_kunstwerken", "output_field_duikerlengte").lower()
            duikers = add_fc_attribs_to_dict(gp, duikers_incl_peilgebieden, duikers, kduident, 'Length', output_field_duikerlengte)
            duikers = add_fc_values_to_dict(gp, duikers_incl_peilgebieden, duikers, kduident, list_fieldnames_duikers)
            
            
            #---------------------------------------------------------------------
            # Berekeningen
            
            # Bereken de percentages onder en boven maaiveld
            log.info('Start calculation')
            duikers = calculate_duikers(duikers, config, nodatavalue, treshold_value_verhang_duikers, duiker_vorm\
                          bodemhoogte_benedenstrooms, bodemhoogte_bovenstrooms,duiker_middellijn_diam, duikerhoogte\
                          duikerhoogte_bovenstrooms,duikerhoogte_benedenstrooms, zomerpeil, winterpeil,\
                          output_field_duikerlengte, output_field_duikerverhang, output_field_percentage_bodem,\
                          output_field_percentage_bovenwinterpeil, output_field_percentage_bovenzomerpeil)
                          
            #log.info(duikers)
            #log.info('dict_fields %s' %dict_fields)
            log.info('Creeer output file')
            # create rough copy 
            duikers_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Select_analysis(input_duikers,duikers_temp)
            
            # Creeer output fields with types
            dict_fields = create_dict_fields(duikers)
            log.info('Vul output file met berekende waarden')
            log.info('duikers_temp %s' %duikers_temp)
            # Vul de dataset met de waarden uit de dictionary
            addfieldnames(gp, duikers_temp, dict_fields)
            add_dict_values_to_fc(gp, duikers_temp, kduident, duikers, nodatavalue)
            
            # Create output file
            log.info('Opschonen output file')
    
            # Als Append gebruikt wordt, kan er gebruik worden gemaakt van fieldmapping
            if output_duikers == '#':
                log.error('Geen output feature class ingevuld. Kan waarden niet wegschrijven')
                sys.exit(1)
                        
            create_output_dataset(gp, output_duikers, dict_fields)
            gp.Append_management(duikers_temp,output_duikers, 'NO_TEST')
            log.info('Duikers finished')
            #---------------------------------------------------------------------
            
            #-------------------------------------------------------------------------------------------------------------------------------
            # END OF SECTION DUIKERS
            # 
            #
            #---------------------------------------------------------------------
        
        if input_sifons != '#':
            #-------------------------------------------------------------------------------------------------------------------------------
            # SECTION SIFON
            # 
            #
            #---------------------------------------------------------------------
            # check of alle benodigde bestanden zijn ingevuld:
            benodigdebestanden = [input_waterlopen_legger, peilgebieden_fc, output_sifons]
            for fc in benodigdebestanden:
                
                if fc =='#': 
                    log.error('Bestand %s is noodzakelijk om sifons te controleren' %fc)
            # Initieer dictionary
            sifons = {}
            #---------------------------------------------------------------------
            # Join van duikers met watergangen
            log.info('Koppel kunstwerken met watergangen')
            sifons_incl_watergangen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Spatialjoin_analysis(input_sifons, input_waterlopen_legger, sifons_incl_watergangen)
            # Wegschrijven data naar dictionary
            log.info('Schrijf informatie weg naar kunstwerken')
            sifons = add_fc_values_to_dict(gp, sifons_incl_watergangen, sifons, ksyident, list_fieldnames_watergangen)
            
            #---------------------------------------------------------------------
            # Join van duikers met peilgebieden
            log.info('Koppel kunstwerken met peilgebieden')
            sifons_incl_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Spatialjoin_analysis(input_sifons, peilgebieden_fc, sifons_incl_peilgebieden)
            sifons = add_fc_values_to_dict(gp, sifons_incl_peilgebieden, sifons, ksyident, list_fieldnames_peilgebieden)
            
            # Inlezen data uit de sifons
            output_field_sifonlengte = config.get("controle_kunstwerken", "output_field_sifonlengte").lower()            
            sifons = add_fc_attribs_to_dict(gp, sifons_incl_peilgebieden, sifons, ksyident, 'Length', output_field_sifonlengte)
            sifons = add_fc_values_to_dict(gp, sifons_incl_peilgebieden, sifons, ksyident, list_fieldnames_sifons)
            
            #---------------------------------------------------------------------
            # Berekeningen
            log.info('Start calculation')

            sifons = calculate_duikers(sifons, config, nodatavalue, treshold_value_verhang_sifons, sifon_vorm\
                          bodemhoogte_benedenstrooms, bodemhoogte_bovenstrooms,sifon_middellijn_diam, sifonhoogte\
                          sifonhoogte_bovenstrooms,sifonhoogte_benedenstrooms, zomerpeil, winterpeil,\
                          output_field_sifonlengte, output_field_sifonverhang, output_field_sifon_percentage_bodem,\
                          output_field_sifon_percentage_bovenwinterpeil, output_field_sifon_percentage_bovenzomerpeil)
                          
            
            #log.info('dict_fields %s' %dict_fields)
            log.info('Creeer output file')
            # create rough copy 
            sifons_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Select_analysis(input_sifons,sifons_temp)
            
            # Creeer output fields with types
            dict_fields = create_dict_fields(sifons)
            log.info('Vul output file met berekende waarden')
            log.info('duikers_temp %s' %sifons_temp)
            # Vul de dataset met de waarden uit de dictionary
            addfieldnames(gp, sifons_temp, dict_fields)
            add_dict_values_to_fc(gp, sifons_temp, ksyident, sifons, nodatavalue)
            
            # Create output file
            log.info('Opschonen output file')
    
            # Als Append gebruikt wordt, kan er gebruik worden gemaakt van fieldmapping
            if output_sifons == '#':
                log.error('Geen output feature class ingevuld. Kan waarden niet wegschrijven')
                sys.exit(1)
                        
            create_output_dataset(gp, output_sifons, dict_fields)
            gp.Append_management(sifons_temp,output_sifons, 'NO_TEST')
            log.info('Sifons finished')
            #---------------------------------------------------------------------
            
            #-------------------------------------------------------------------------------------------------------------------------------
            # END OF SECTION SIFONS
            # 
            #
            #---------------------------------------------------------------------
        
        if input_stuwen != '#':
            #-------------------------------------------------------------------------------------------------------------------------------
            # SECTION STUWEN
            # 
            #
            #---------------------------------------------------------------------
            # check of alle benodigde bestanden zijn ingevuld:
            benodigdebestanden = [input_waterlopen_legger, peilgebieden_fc, output_stuwen]
            for index, fc in enumerate(benodigdebestanden):
                if fc =='#': 
                    log.error('Bestand %s is noodzakelijk om duikers te controleren' %benodigdebestanden[index])
            # Initieer dictionary
            stuwen = {}        
        
            #---------------------------------------------------------------------
            # Join van duikers met watergangen
            log.info('Koppel kunstwerken met watergangen')
            stuwen_incl_watergangen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Spatialjoin_analysis(input_stuwen, input_waterlopen_legger,stuwen_incl_watergangen,'JOIN_ONE_TO_ONE', 'KEEP_ALL', '#', 'CLOSEST')
            # Wegschrijven data naar dictionary
            log.info('Schrijf informatie weg naar kunstwerken')
            stuwen = add_fc_values_to_dict(gp, stuwen_incl_watergangen, stuwen, kstident, list_fieldnames_watergangen)
            #---------------------------------------------------------------------
            # Join van duikers met peilgebieden
            log.info('Koppel kunstwerken met peilgebieden')
            stuwen_incl_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            
            gp.Spatialjoin_analysis(input_stuwen, peilgebieden_fc, stuwen_incl_peilgebieden)
            stuwen = add_fc_values_to_dict(gp, stuwen_incl_peilgebieden, stuwen, kstident, list_fieldnames_peilgebieden)
            
            # Inlezen data uit de duikers
            stuwen = add_fc_values_to_dict(gp, stuwen_incl_peilgebieden, stuwen, kstident, list_fieldnames_stuwen)
            
            #---------------------------------------------------------------------
            # Berekeningen
            log.info('Start calculation')
            # Inlezen outputveldnamen
            output_field_stuw_percentage_bodem = config.get("controle_kunstwerken", "output_field_stuw_percentage_bodem").lower()
            output_field_stuw_tov_winterpeil = config.get("controle_kunstwerken", "output_field_stuw_tov_winterpeil").lower()
            output_field_stuw_tov_zomerpeil = config.get("controle_kunstwerken", "output_field_stuw_tov_zomerpeil").lower() 
            
            stuwen = calculate_stuwen(stuwen, config, nodatavalue,\
                                      bodemhoogte_benedenstrooms, bodemhoogte_bovenstrooms,\
                                      stuw_hoogte, zomerpeil, winterpeil,\
                                      output_field_stuw_percentage_bodem, output_field_stuw_tov_winterpeil,\
                                      output_field_stuw_tov_zomerpeil)
        
            
            #log.info('dict_fields %s' %dict_fields)
            log.info('Creeer output file stuwen')
            # create rough copy 
            stuwen_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
            gp.Select_analysis(input_stuwen, stuwen_temp)
            
            # Creeer output fields with types
            dict_fields = create_dict_fields(stuwen)
            log.info('Vul output file met berekende waarden')
            log.info('stuwen_temp %s' %stuwen_temp)
            # Vul de dataset met de waarden uit de dictionary
            addfieldnames(gp, stuwen_temp, dict_fields)
            add_dict_values_to_fc(gp, stuwen_temp, kstident, stuwen, nodatavalue)
            
            # Create output file
            log.info('Opschonen output file')
    
            # Als Append gebruikt wordt, kan er gebruik worden gemaakt van fieldmapping
            if output_stuwen == '#':
                log.error('Geen output feature class ingevuld. Kan waarden niet wegschrijven')
                sys.exit(1)
            create_output_dataset(gp, output_stuwen, dict_fields, 'POINT')
            gp.Append_management(stuwen_temp,output_stuwen, 'NO_TEST')
            log.info('Stuwen finished')
        
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            #gp.delete(workspace_gdb)

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
