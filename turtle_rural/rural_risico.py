# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import csv
import traceback
import time

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.risico
import turtlebase.general

log = logging.getLogger(__name__)


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
        # Input parameters
        if len(sys.argv) == 11:
            log.info("Reading input parameters")
            peilgebied = sys.argv[1]
            input_rr_peilgebied = sys.argv[2]
            input_rr_maaiveld = sys.argv[3]
            input_ahn = sys.argv[4]
            input_lgn = sys.argv[5]
            conversion = sys.argv[6]
            input_hymstat = sys.argv[7]
            output_risk_table = sys.argv[8]
            output_risico = sys.argv[9]
            output_risico_inundation = sys.argv[10]            
        else:
            log.error("usage: <peilgebied> <input_rr_peilgebied> <input_rr_maaiveld> <input_ahn> <input_lgn>\
                      <conversion> <input_hymstat> <output_risk_table> <output_risico> <output_risico_inundation>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)

        "<check geometry from input data, append to list if incorrect>"
        
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
                if not turtlebase.arcgis.is_fieldname(gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)
        
        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
            
        #----------------------------------------------------------------------------------------
        # Environments
        log.info("Set environments")
        temp_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Select_analysis(peilgebied, temp_peilgebieden)
        
        cellsize = gp.describe(input_ahn).MeanCellHeight  # use same cell size as AHN
        gp.extent = gp.describe(temp_peilgebieden).extent  # use extent from Peilgebieden
        gpgident = config.get('GENERAL', 'gpgident')

        #----------------------------------------------------------------------------------------
        # create ahn ascii
        log.info("Create ascii from ahn")
        
        ahn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        log.debug("ahn ascii: %s" % ahn_ascii)
        gp.RasterToASCII_conversion(input_ahn, ahn_ascii)

        #----------------------------------------------------------------------------------------
        # create lgn ascii
        log.info("Create ascii from lgn")
        #read gpgident from file
        lgn_desc = gp.describe(input_lgn)
        if lgn_desc.DataType == 'ShapeFile' or lgn_desc.DataType == 'FeatureClass':
            lgn_fieldnames = nens.gp.get_table_def(gp, input_lgn)
            if "gridcode" in lgn_fieldnames:
                gridcode = "GRIDCODE"
            elif "grid_code" in lgn_fieldnames:
                gridcode = "grid_code"
            else:
                log.error("Cannot find 'grid_code' or 'gridcode' field in input lgn file")
                
            temp_lgn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.FeatureToRaster_conversion(input_lgn, gridcode, temp_lgn, cellsize)
        elif lgn_desc.DataType == 'RasterDataset':
            temp_lgn = input_lgn
            if not lgn_desc.MeanCellHeight == cellsize:
                log.error("LGN cellsize does not match AHN cellsize (%sx%s m)" % cellsize)
                sys.exit(5)
        else:
            log.error("cannot recognize datatype of LGN, must be a fc, shapefile or a raster dataset")
            sys.exit(5)
       
        lgn_ascii = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        log.debug("lgn ascii: %s" % lgn_ascii)
        gp.RasterToASCII_conversion(temp_lgn, lgn_ascii)

        #----------------------------------------------------------------------------------------
        log.info("Create ascii from surface level areas")
        if not turtlebase.arcgis.is_fieldname(gp, temp_peilgebieden, "ID_INT"):
            gp.AddField(temp_peilgebieden, "ID_INT", "LONG")

        id_int = 1
        idint_to_peilvakid = {}
        peilvakid_to_idint = {}
        if turtlebase.arcgis.is_fieldname(gp, temp_peilgebieden, gpgident):
            rows = gp.SearchCursor(temp_peilgebieden)
            for row in nens.gp.gp_iterator(rows):
                peilvakid = row.GetValue(gpgident)
                idint_to_peilvakid[id_int] = peilvakid
                peilvakid_to_idint[peilvakid] = id_int
                id_int = id_int + 1 #each row gets a new id_int

        log.info(" - calc value ID_INT")
        rows = gp.UpdateCursor(temp_peilgebieden)
        for row in nens.gp.gp_iterator(rows):
            gpg_ident = row.GetValue(gpgident)
            id_int = peilvakid_to_idint[gpg_ident]
            row.SetValue("ID_INT", id_int)
            rows.UpdateRow(row)

        log.info("Conversion feature peilgebieden to raster")
        InField = "ID_INT"
        temp_peilgebieden_raster = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.FeatureToRaster_conversion(temp_peilgebieden, InField, temp_peilgebieden_raster, cellsize)
                
        peilgeb_asc = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        gp.RasterToASCII_conversion(temp_peilgebieden_raster, peilgeb_asc)
        
        #----------------------------------------------------------------------------------------
        # Read input tables into dictionaries
        log.info("Read input tables")
        log.info(" - read RR_Peilgebied")
        rr_peilgebied = nens.gp.get_table(gp, input_rr_peilgebied, primary_key=gpgident.lower())
        log.info(" - read RR_Maaiveld")
        rr_maaiveld = nens.gp.get_table(gp, input_rr_maaiveld,primary_key=gpgident.lower())
        log.info(" - read Conversion table")
        schadefuncties = nens.gp.get_table(gp, conversion, primary_key='lgn')
        log.info(" - read conversion table between id_int and gpgident")
        gpg_conv = nens.gp.get_table(gp, temp_peilgebieden, primary_key='id_int')

        log.info(" - read hymstat table")
        csv_dict = [d for d in csv.DictReader(open(input_hymstat))]
        hymstat = {}
        for item in csv_dict:
            hymstat[item[config.get('risico', 'hymstat_id')]] = item
            
        #----------------------------------------------------------------------------------------
        log.info("Calculate Risk")
        temp_risico = turtlebase.arcgis.get_random_file_name(workspace, "risk.asc")
        temp_risico_in = turtlebase.arcgis.get_random_file_name(workspace, ".asc")
        risico_tbl = turtlebase.risico.create_risk_grid(ahn_ascii, lgn_ascii,
                                                        peilgeb_asc, rr_peilgebied, rr_maaiveld,
                                                        hymstat, gpg_conv, schadefuncties, temp_risico,
                                                        temp_risico_in, cellsize)

        risk_result = turtlebase.risico.create_risico_dict(risico_tbl, schadefuncties, primary_key=gpgident)
        for k in risk_result.keys():
            risk_result[k]['SOURCE'] = "hymstat: %s, ahn: %s, lgn: %s" % (os.path.basename(input_hymstat),
                                                         os.path.basename(input_ahn),
                                                         os.path.basename(input_lgn))
            risk_result[k]['DATE_TIME'] = time.strftime("%d-%m-%Y, %H:%M:%S")
            
        gp.ASCIIToRaster_conversion(temp_risico, output_risico, "FLOAT")
        gp.ASCIIToRaster_conversion(temp_risico_in, output_risico_inundation, "FLOAT")

        # Schrijf de resultaten weg als een nieuwe tabel
        if not(gp.exists(output_risk_table)):
            log.info("creating table " + output_risk_table)
            gp.CreateTable(os.path.dirname(output_risk_table), os.path.basename(output_risk_table))

        risk_fields = nens.gp.get_table_def(gp, output_risk_table)
        fields_to_add = [{'fieldname': gpgident, 'fieldtype': 'text', 'length': 50},
                         {'fieldname': 'RIS_GW', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_GW_ST', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_GW_HL', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_GW_AK', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_GW_GR', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_GW_NT', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN_ST', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN_HL', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN_AK', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN_GR', 'fieldtype': 'Double'},
                         {'fieldname': 'RIS_IN_NT', 'fieldtype': 'Double'},
                         {'fieldname': 'SOURCE', 'fieldtype': 'text', 'length': 256},
                         {'fieldname': 'DATE_TIME', 'fieldtype': 'text', 'length': 25},
                         {'fieldname': 'COMMENTS', 'fieldtype': 'text', 'length': 256}]
        
        for field_to_add in fields_to_add:
            if field_to_add['fieldname'].lower() not in risk_fields:
                if 'length' in field_to_add:
                    gp.addfield_management(output_risk_table, field_to_add['fieldname'], field_to_add['fieldtype'], "#", "#", field_to_add['length'])
                else:
                    gp.addfield_management(output_risk_table, field_to_add['fieldname'], field_to_add['fieldtype'])
                         
        turtlebase.arcgis.write_result_to_output(output_risk_table, gpgident, risk_result)
        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)
            
            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        tempfiles = os.listdir(workspace)
        for tempfile in tempfiles:
            if tempfile.endswith('.asc'):
                try:
                    os.remove(os.path.join(workspace, tempfile))
                    log.debug("%s/%s removed" % (workspace, tempfile))
                except Exception, e:
                    log.debug(e)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logging_config.cleanup()
        del gp
    
