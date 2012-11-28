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
import turtlebase.general

log = logging.getLogger(__name__)


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
        for argv in sys.argv[1:]:
            turtlebase.filenames.check_filename(argv)

        if len(sys.argv) == "<number of arguments for this tool>":
            peilvakken_input = sys.argv[1]
            watergangen_as_input = sys.argv[2]
            stuwen_input = sys.argv[3]
            gemalen_input = sys.argv[4]
            afstand_input = sys.argv[5]
            output_peilscheiding_vereist = sys.argv[6] 
        else:
            log.warning("usage: <argument1> <argument2>")
            #sys.exit(1)

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

#        missing_fields = []

        # In this tool it is not important which fields are available
        # Check fields is therefor disabled:    
#        check_fields = {}
#        #check_fields = {input_1: [fieldname1, fieldname2],
#        #                 input_2: [fieldname1, fieldname2]}
#        for input_fc, fieldnames in check_fields.items():
#            for fieldname in fieldnames:
#                if not turtlebase.arcgis.is_fieldname(
#                        gp, input_fc, fieldname):
#                    errormsg = "fieldname %s not available in %s" % (
#                                    fieldname, input_fc)
#                    log.error(errormsg)
#                    missing_fields.append(errormsg)
#
#        if len(missing_fields) > 0:
#            log.error("missing fields in input data: %s" % missing_fields)
#            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments
        
        # Create temp files
        kunstwerken_merged = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        kunstwerken_merged_buffer = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        peilscheidingen = turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        correcte_peilscheidingen =  turtlebase.arcgis.get_random_file_name(workspace_gdb, "")
        
        # Process: Merge kunstwerken tot 1 bestand
        log.info('Samenvoegen kunstwerken')
        gp.Merge_management("%s;%s" %(stuwen_input,gemalen_input), kunstwerken_merged)
        
        # Process: Buffer kunstwerken met door gebruiker ingegeven afstand
        log.info('Bufferen kunstwerken')
        afstand_input_value = "%s Meters" %afstand_input
        gp.Buffer_analysis(kunstwerken_merged, kunstwerken_merged_buffer, afstand_input_value)
        
        # Process: Intersect
        log.info('Bepalen vereiste locaties peilscheidingen')
        gp.Intersect_analysis("%s #;%s #" %(), peilscheidingen, "ALL", "", "POINT")
        
        # Process: Intersect (2)
        log.info('Controle aanwezige peilscheidingen')
        gp.Intersect_analysis("%s #;C:\\Users\\jonas.vanschrojenste\\Documents\\ArcGIS\\Default.gdb\\watergang_as_Intersect #" %(kunstwerken_merged_buffer, peilscheidingen), correcte_peilscheidingen, "ALL", "", "POINT")
        

        gp.Select_analysis(correcte_peilscheidingen, output_peilscheiding_vereist)
        
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
