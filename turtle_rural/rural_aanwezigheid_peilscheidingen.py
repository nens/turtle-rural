# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import turtlebase.arcgis
import turtlebase.filenames

log = logging.getLogger(__name__)

def populate_ident(gp, fc, fieldname_ident):
    '''
    '''
    fieldname_objectid = 'OBJECTID'
    rows = gp.UpdateCursor(fc)
    row = rows.Next()
    while row:
        ident_value = row.getValue(fieldname_objectid)
        row.SetValue(fieldname_ident, ident_value)
        rows.UpdateRow(row)
        row = rows.Next()
    
def create_where_clause_kunstwerken_zonder_peilscheiding(gp, fc, list_idents):
    '''
    Creates a where clause usable in arcgis. for all items NOT in provided list_idents
    '''
    return ''

def create_where_clause_peilscheiding_vereist(gp, fc, fieldname_object, objects_list): #fieldname_ident_kst, fieldname_ident_kgm, 
    '''
    Creates a where clause usable in arcgis. For all items NOT provided in 
    '''
    
    list_ident_values_wc = []
    rows = gp.SearchCursor(fc)
    row = rows.Next()
    while row:
        
    
#        ident_value_kst = row.getValue(fieldname_ident_kst)
#        ident_value_kgm = row.getValue(fieldname_ident_kgm)
#        if ident_value_kgm == None and ident_value_kst == None:
            
        ident_value_wc =  row.getValue(fieldname_object)
        if not ident_value_wc in objects_list:
            list_ident_values_wc.append('"' + fieldname_object + '"' + ' <> ' + str(ident_value_wc))
        
        row = rows.Next()
    
    where_clause = " AND ".join(list_ident_values_wc)
    return where_clause

def read_idents(gp, fc, fieldname_ident):
    '''
    Uses gp object to read out all values available in fieldname_ident in fc
    returns them as a list. 
    '''
    list_idents = []
    rows = gp.SearchCursor(fc)
    row = rows.Next()
    while row:
        ident_value = row.GetValue(fieldname_ident)
        if not ident_value in list_idents:
            list_idents.append(ident_value)
        else:
            log.warning('De ident %s komt dubbel voor in %s' %(ident_value,fc))
        row = rows.Next()
    return list_idents

def main():
    try:
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
        """
        nodig voor deze tool:
        """
        
        if len(sys.argv) == 8:
            peilvakken_input = sys.argv[1]
            watergangen_as_input = sys.argv[2]
            stuwen_input = sys.argv[3]
            gemalen_input = sys.argv[4]
            afstand_input = sys.argv[5]
            output_peilscheiding_vereist = sys.argv[6]
            dummy = sys.argv[7]
              
        else:
            log.warning("usage: <argument1> <argument2>")
            #sys.exit(1)

        for argv in sys.argv[1:5]:
            turtlebase.filenames.check_filename(argv)
        for argv in sys.argv[6:]:
            turtlebase.filenames.check_filename(argv)
            
        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)
        if not turtlebase.arcgis.is_file_of_type(gp, peilvakken_input, 'Polygon'):
            log.error("%s is not a %s feature class!" % (peilvakken_input, 'Polygon'))
            geometry_check_list.append("%s -> (%s)" % (peilvakken_input, 'Polygon'))

        if not turtlebase.arcgis.is_file_of_type(gp, watergangen_as_input, 'Polyline'):
            log.error("%s is not a %s feature class!" % (watergangen_as_input, 'Polyline'))
            geometry_check_list.append("%s -> (%s)" % (watergangen_as_input, 'Polyline'))

        if not turtlebase.arcgis.is_file_of_type(gp, stuwen_input, 'Point'):
            log.error("%s is not a %s feature class!" % (stuwen_input, 'Point'))
            geometry_check_list.append("%s -> (%s)" % (stuwen_input, 'Point'))

        if not turtlebase.arcgis.is_file_of_type(gp, gemalen_input, 'Point'):
            log.error("%s is not a %s feature class!" % (gemalen_input, 'Point'))
            geometry_check_list.append("%s -> (%s)" % (gemalen_input, 'Point'))


        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        kstident_fieldname = config.get('GENERAL', 'kstident')
        kgmident_fieldname = config.get('GENERAL', 'kgmident')
        
        check_fields = {stuwen_input: [kstident_fieldname],
                         gemalen_input: [kgmident_fieldname]}
        
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
        
        # Create temp files
        kunstwerken_merged = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        kunstwerken_merged_buffer = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        peilscheidingen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        correcte_peilscheidingen =  turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        peilscheidingen_buffer =  turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        log.info('kunstwerken_merged %s' %kunstwerken_merged)
        log.info('kunstwerken_merged_buffer %s' %kunstwerken_merged_buffer)
        log.info('peilscheidingen %s' %peilscheidingen)
        log.info('correcte_peilscheidingen %s' %correcte_peilscheidingen)
        
        # Read kunstwerken ids
        log.info('Reading which kunstwerken are available')
        log.info('Stuwen')
        list_stuwen_idents =read_idents(gp, stuwen_input, kstident_fieldname) 
        log.info('Gemalen')
        list_gemalen_idents = read_idents(gp, gemalen_input, kgmident_fieldname) 
        # Process: Merge kunstwerken tot 1 bestand
        log.info('Samenvoegen kunstwerken')
        gp.Merge_management("%s;%s" %(stuwen_input,gemalen_input), kunstwerken_merged)
        
        
        # Process: Intersect
        log.info('Bepalen vereiste locaties peilscheidingen')
        gp.Intersect_analysis("%s #;%s #" %(watergangen_as_input, peilvakken_input), peilscheidingen, "ALL", "", "POINT")
        
        
        # Aanmaken unieke ident peilscheidingen
        peilscheidingident_fieldname = 't_id'
        if turtlebase.arcgis.is_fieldname(gp, peilscheidingen, peilscheidingident_fieldname) == False:
            gp.Addfield_management(peilscheidingen, peilscheidingident_fieldname, 'LONG')
        # Populate ident peilscheidingen 
        populate_ident(gp, peilscheidingen, peilscheidingident_fieldname)
        
        # Process: Buffer kunstwerken met door gebruiker ingegeven afstand
        log.info('Bufferen peilscheidingen')
        afstand_input_value = "%s Meters" %afstand_input
        gp.Buffer_analysis(peilscheidingen, peilscheidingen_buffer, afstand_input_value)

        # Process: Intersect (2)
        log.info('Controle aanwezige peilscheidingen')
        gp.Intersect_analysis("%s #;%s #" %(kunstwerken_merged, peilscheidingen_buffer), correcte_peilscheidingen, "ALL", "", "POINT")
        
        # Tijdelijke proces:
#        where_clause = create_where_clause_kunstwerken_zonder_peilscheiding()
        log.info('Selecteren van locaties waar verwachte peilscheiding niet aanwezig')
#        list_kunstwerken_idents = list_gemalen_idents + list_stuwen_idents
#        log.info(list_kunstwerken_idents)
        list_peilscheidingen_idents = read_idents(gp, correcte_peilscheidingen, peilscheidingident_fieldname) 
        
        where_clause_peilscheiding_vereist = create_where_clause_peilscheiding_vereist(gp, peilscheidingen, peilscheidingident_fieldname, list_peilscheidingen_idents)
        log.info(where_clause_peilscheiding_vereist)
        gp.Select_analysis(peilscheidingen, output_peilscheiding_vereist, where_clause_peilscheiding_vereist)
        gp.Select_analysis(correcte_peilscheidingen, dummy)
        #---------------------------------------------------------------------
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
