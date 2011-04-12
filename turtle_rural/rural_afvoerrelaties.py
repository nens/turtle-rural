# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import time
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.filenames
import turtlebase.general

log = logging.getLogger(__name__)


def createLine(gp, pnt_id_counter,x0,y0,x1,y1):
    lineArray = gp.CreateObject("Array")
    pntA = gp.CreateObject("Point")
    pntA.id = pnt_id_counter
    pntA.x = x0
    pntA.y = y0
    pntB = gp.CreateObject("Point")
    pntB.id = pnt_id_counter
    pntB.x = x1
    pntB.y = y1
    lineArray.add(pntA)
    lineArray.add(pntB)
    #lineArray.RemoveAll()
    return lineArray, pnt_id_counter+2


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL','location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters... ")
        use_onderbemalingen = False
        if len(sys.argv) == 5:
            input_peilgebieden_feature = sys.argv[1]
            input_kunstwerken_feature = sys.argv[2]
            input_afvoer_table = sys.argv[3]
            output_feature = sys.argv[4]
        else:
            log.error("Usage: python rural_afvoerrelaties.py <peilgebieden feature> <kunstwerken feature> <afvoerrelaties table> <output feature>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        #check input parameters
        gpgident = config.get('GENERAL', 'gpgident')
        kwkident = config.get('GENERAL', 'kwkident')
        log.info('Checking presence of input files... ')
        if not(gp.exists(input_peilgebieden_feature)):
            log.error("inputfile peilgebieden %s does not exist!" % input_peilgebieden_feature)
            sys.exit(5)

        if not(gp.exists(input_afvoer_table)):
            log.error("inputfile Afvoerrelaties %s does not exist!" % input_afvoer_table)
            sys.exit(5)

        log.info('input parameters checked... ')
        #----------------------------------------------------------------------------------------
        log.info("A-1) prepare input_peilgebieden_feature... ")
        temp_peilgebieden_feature = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Select_analysis(input_peilgebieden_feature, temp_peilgebieden_feature)

        temp_peilg_meancenter_feature = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.MeanCenter_stats(temp_peilgebieden_feature, temp_peilg_meancenter_feature, '#', gpgident, '#')

        #fields are XCoord, YCoord, indexed by GPGIDENT
        peilgebieden_dict, error = nens.tools.addTableList_to_Dictionary(nens.tools_gp.readTable(gp, temp_peilg_meancenter_feature), {}, gpgident)
        if error != 0:
            log.error("- Error addTableList_to_Dictionary or readTable")
            sys.exit(5)

        log.info("A-2) prepare input_kunstwerken_feature... ")
        temp_kunstwerken_feature = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Select_analysis(input_kunstwerken_feature, temp_kunstwerken_feature)

        gp.addxy(temp_kunstwerken_feature)
        #fields are POINT_X, POINT_Y, indexed by KWKIDENT
        kunstwerken_dict, error = nens.tools.addTableList_to_Dictionary(nens.tools_gp.readTable(gp, temp_kunstwerken_feature), {}, kwkident)
        if error != 0:
            log.error("- Error addTableList_to_Dictionary or readTable")
            sys.exit(5)

        log.info("A-3) reading input_afvoer_table... ")
        relaties_dict, error = nens.tools.addTableList_to_Dictionary(nens.tools_gp.readTable(gp, input_afvoer_table), {}, options.ini['input_relaties_id'])
        if error != 0:
            log.error("- Error addTableList_to_Dictionary or readTable")
            sys.exit(5)

        log.info("B-1) calculating afvoerrelaties... ")
        def insertLineDict(x0,y0,x1,y1,ident,from_,from_type,to_,to_type,source_str,date_str,output_table_dict, output_lines_dict):
            output_table_dict[ident] = {'IDENT': ident, 'REL_FROM': from_, 'FROM_TYPE': from_type, 'REL_TO': to_, 'TO_TYPE': to_type, 'Bron': source_str, 'Datum': date_str}
            output_lines_dict[ident] = {'IDENT': ident, 'X0': x0, 'Y0': y0, 'X1': x1, 'Y1': y1}
            return output_table_dict, output_lines_dict

        output_table_dict = {}
        output_lines_dict = {}
        ident = 1
        warning_count = 0
        date_str = time.strftime('%x')
        source_str = "pg: "+os.path.basename(input_peilgebieden_feature)+" kw: "+os.path.basename(input_kunstwerken_feature)+" rel: "+os.path.basename(input_afvoer_table)
        if len(source_str) > 50:
            source_str = source_str[:50]
        #key is objectid
        for key, value in relaties_dict.items():
            kw_id = relaties_dict[key][config.get('afvoerrelaties', 'input_kwk_id_table')].strip()
            gpg_id_from = relaties_dict[key][config.get('afvoerrelaties', 'input_peilg_from')].strip()
            gpg_id_to = relaties_dict[key][config.get('afvoerrelaties', 'input_peilg_to')].strip()
            inserted = False
            if kw_id == "":
                #connect peilgebieden directly
                if not(peilgebieden_dict.has_key(gpg_id_from)):
                    log.warning("row ["+options.ini['input_relaties_id']+"] = '"+key+"': GPG from '"+gpg_id_from+"' does not exist in input_peilgebieden_feature")
                if not(peilgebieden_dict.has_key(gpg_id_to)):
                    log.warning("row ["+options.ini['input_relaties_id']+"] = '"+key+"': GPG to '"+gpg_id_to+"' does not exist in input_peilgebieden_feature")
                if (gpg_id_from != None) and (gpg_id_to != None):
                    if (peilgebieden_dict.has_key(gpg_id_from) and peilgebieden_dict.has_key(gpg_id_to)):
                        #peilg_from -> peilg_to
                        x0 = peilgebieden_dict[gpg_id_from]['XCoord']
                        y0 = peilgebieden_dict[gpg_id_from]['YCoord']
                        x1 = peilgebieden_dict[gpg_id_to]['XCoord']
                        y1 = peilgebieden_dict[gpg_id_to]['YCoord']
                        from_ = gpg_id_from
                        from_type = options.ini['input_gpg_id']
                        to_ = gpg_id_to
                        to_type = options.ini['input_gpg_id']
                        output_table_dict, output_lines_dict = insertLineDict(x0,y0,x1,y1,ident,from_,from_type,to_,to_type,source_str,date_str,output_table_dict, output_lines_dict)
                        ident = ident + 1
                        inserted = True
            else:
                #connect peilgebieden through kw
                if not(kunstwerken_dict.has_key(kw_id)):
                    log.warning("row ["+options.ini['input_relaties_id']+"] = '"+key+"': KWK '"+kw_id+"' does not exist in input_kunstwerken_feature")
                if not(peilgebieden_dict.has_key(gpg_id_from)):
                    log.warning("row ["+options.ini['input_relaties_id']+"] = '"+key+"': GPG 'from' '"+gpg_id_from+"' does not exist in input_peilgebieden_feature")
                if not(peilgebieden_dict.has_key(gpg_id_to)):
                    log.warning("row ["+options.ini['input_relaties_id']+"] = '"+key+"': GPG 'to' '"+gpg_id_to+"' does not exist in input_peilgebieden_feature")
                if relaties_dict[key][options.ini['input_peilg_from']] != "":
                    if (kunstwerken_dict.has_key(kw_id) and peilgebieden_dict.has_key(gpg_id_from)):
                        #peilg_from -> kw
                        x0 = peilgebieden_dict[gpg_id_from]['XCoord']
                        y0 = peilgebieden_dict[gpg_id_from]['YCoord']
                        x1 = kunstwerken_dict[kw_id]['POINT_X']
                        y1 = kunstwerken_dict[kw_id]['POINT_Y']
                        from_ = gpg_id_from
                        from_type = options.ini['input_gpg_id']
                        to_ = kw_id
                        to_type = options.ini['input_kwk_id_feature']
                        #print "(peilg -> peilg) "+from_+" to "+to_
                        output_table_dict, output_lines_dict = insertLineDict(x0,y0,x1,y1,ident,from_,from_type,to_,to_type,source_str,date_str,output_table_dict, output_lines_dict)
                        ident = ident + 1
                        inserted = True
                if relaties_dict[key][options.ini['input_peilg_to']] != "":
                    if (kunstwerken_dict.has_key(kw_id) and peilgebieden_dict.has_key(gpg_id_to)):
                        #peilg_to -> kw
                        x0 = kunstwerken_dict[kw_id]['POINT_X']
                        y0 = kunstwerken_dict[kw_id]['POINT_Y']
                        x1 = peilgebieden_dict[gpg_id_to]['XCoord']
                        y1 = peilgebieden_dict[gpg_id_to]['YCoord']
                        from_ = kw_id
                        from_type = options.ini['input_kwk_id_feature']
                        to_ = gpg_id_to
                        to_type = options.ini['input_gpg_id']
                        #print "(peilg -> peilg) "+from_+" to "+to_
                        output_table_dict, output_lines_dict = insertLineDict(x0,y0,x1,y1,ident,from_,from_type,to_,to_type,source_str,date_str,output_table_dict, output_lines_dict)
                        ident = ident + 1
                        inserted = True
            if not(inserted):
                #print "Warning: row with ["+ini['input_relaties_id']+"] = '"+key+"' could not be drawn!"
                warning_count = warning_count + 1
        log.warning(" - "+str(warning_count)+" warnings occurred.")

        log.info("C-1) Checking feature class... ")
        #create feature class
        afvoerFields = [{'name': 'IDENT', 'type': 'TEXT', 'length': '30'},\
                                            {'name': 'REL_FROM', 'type': 'TEXT', 'length': '30'},\
                                            {'name': 'FROM_TYPE', 'type': 'TEXT', 'length': '30'},\
                                            {'name': 'REL_TO', 'type': 'TEXT', 'length': '30'},\
                                            {'name': 'TO_TYPE', 'type': 'TEXT', 'length': '30'},\
                                            {'name': 'Bron', 'type': 'TEXT', 'length': '50'},\
                                            {'name': 'Datum', 'type': 'DATE'}]

        mdb_name = os.path.dirname(output_feature)
        table_name = os.path.basename(output_feature)

        if gp.exists(output_feature):
            gp.delete(output_feature)

        gp.CreateFeatureclass(mdb_name, table_name, "POLYLINE")

        #check if output_table has the correct rows
        log.info("C-2) Checking fields... ")
        for field_settings in afvoerFields:
            if not turtlebase.arcgis.is_fieldname(gp, output_feature, field_settings['name']):
                if field_settings.has_key('length'):
                    gp.AddField(output_feature, field_settings['name'], field_settings['type'], '#', '#', field_settings['length'])
                else:
                    gp.AddField(output_feature, field_settings['name'], field_settings['type'])
        # ---------------------------------------------------------------------------
        #add data to file_output

        #put new data in output_table
        log.info("C-3) Inserting new records and geometry... ")

        pnt_id_counter = 1
        update_progress = {}
        #update_count,update_progress = nens.tools_gp.insertRecords(gp, output_feature, output_table_dict, update_progress)
        update_count = 0
        nsertCursor = gp.InsertCursor(output_feature)
        for key,dict_items in output_table_dict.items():
            if not(update_progress.has_key(str(key))):
                #new row
                newRow = nsertCursor.NewRow()
                ident = dict_items['IDENT']
                #shape!!
                newRow.shape, pnt_id_counter = createLine(gp, pnt_id_counter,output_lines_dict[ident]['X0'],output_lines_dict[ident]['Y0'],output_lines_dict[ident]['X1'],output_lines_dict[ident]['Y1'])
                #fields
                for field_name,value in dict_items.items():
                    newRow.SetValue(field_name,value)
                nsertCursor.InsertRow(newRow)
                update_count = update_count + 1
                update_progress[str(key)] = 1

        del newRow

        log.info(" - "+str(update_count)+" records has been inserted")

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase
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