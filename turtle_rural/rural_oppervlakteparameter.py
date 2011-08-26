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

def conv_ha(conversion, lgn_id, ha):
    '''
    converts lgn_id+area using conversion
    input:
    conversion: conversiontable, dictionary with lgn_id's as key
    lgn_id: lookup id
    ha: input for output value
    output: dictionary with 6 keys
    '''
    if lgn_id in conversion:
        verhard = ha * float(conversion[lgn_id]['verhard_ha'])
        onvsted = ha * float(conversion[lgn_id]['onvsted_ha'])
        kassen = ha * float(conversion[lgn_id]['kassen_ha'])
        gras = ha * float(conversion[lgn_id]['gras_ha'])
        natuur = ha * float(conversion[lgn_id]['natuur_ha'])
        openwat = ha * float(conversion[lgn_id]['openwat_ha'])
        hectares = ha
        error = False
    else:
        log.warning("lgncode %s not found! Check conversiontable" % lgn_id)
        verhard = 0
        onvsted = 0
        kassen = 0
        gras = 0
        natuur = 0
        openwat = 0
        hectares = 0
        error = True
    return {'VERHARD_LGN': verhard,
            'ONVSTED_LGN': onvsted,
            'KASSEN_LGN': kassen,
            'GRAS_LGN': gras,
            'NATUUR_LGN': natuur,
            'OPENWAT_LGN': openwat,
            'HECTARES': hectares}, error


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)
        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        #get argv
        log.info("Getting command parameters... ")
        if len(sys.argv) == 6:
            input_peilgebieden_feature = sys.argv[1] #from HydroBase
            input_lgn = sys.argv[2]
            input_conversiontable_dbf = sys.argv[3]
            input_watershape = sys.argv[4]
            output_table = sys.argv[5] #RR_oppervlak in HydroBase
        else:
            log.error("Arguments: <LGN raster> <peilgebied HydroBase-table> <conversiontable dbf> <output HydroBase-table>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        lgn_desc = gp.describe(input_lgn)
        if lgn_desc.DataType == 'RasterDataset':
            if lgn_desc.PixelType[0] not in ["S", "U"]:
                errormsg = "input %s is not an integer raster!" % input_lgn
                log.error(errormsg)
                geometry_check_list.append(errormsg)
                # Create shapefile from input raster
            else:
                log.info("Input LGN is a raster, convert to feature class")
                temp_lgn_fc = turtlebase.arcgis.get_random_file_name(workspace_gdb)
                gp.RasterToPolygon_conversion(input_lgn, temp_lgn_fc, "NO_SIMPLIFY")
        elif lgn_desc.DataType == 'ShapeFile' or lgn_desc.DataType == 'FeatureClass':
            if lgn_desc.ShapeType != 'Polygon':
                errormsg = "input %s is not an integer raster!" % input_lgn
                log.error(errormsg)
                geometry_check_list.append(errormsg)
            else:
                # Copy shapefile to workspace
                log.info("Input LGN is a feature class, copy to workspace")
                temp_lgn_fc = turtlebase.arcgis.get_random_file_name(workspace_gdb)
                gp.Select_analysis(input_lgn, temp_lgn_fc)
        else:
            log.error("cannot recognize datatype of LGN, must be a fc, shapefile or a raster dataset")
            sys.exit(5)

        if not(gp.exists(input_peilgebieden_feature)):
            errormsg = "input %s does not exist!" % input_peilgebieden_feature
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if not(gp.exists(input_conversiontable_dbf)):
            errormsg = "input %s does not exist!" % input_conversiontable_dbf
            log.error(errormsg)
            geometry_check_list.append(errormsg)

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        "<check required fields from input data, append them to list if missing>"
        gpgident = config.get('GENERAL', 'gpgident')
        if not turtlebase.arcgis.is_fieldname(gp, input_peilgebieden_feature, gpgident):
            log.debug(" - missing: %s in %s" % (gpgident, input_peilgebieden_feature))
            missing_fields.append("%s: %s" % (input_peilgebieden_feature, gpgident))

        lgn_id = config.get('OppervlakteParameters', 'input_field_lgncode')
        conversion_fields = [lgn_id, "verhard_ha", "onvsted_ha", "kassen_ha", "gras_ha", "natuur_ha", "openwat_ha"]
        for conversion_field in conversion_fields:
            if not turtlebase.arcgis.is_fieldname(gp, input_conversiontable_dbf, conversion_field):
                log.debug(" - missing: %s in %s" % (conversion_field, input_conversiontable_dbf))
                missing_fields.append("%s: %s" % (input_conversiontable_dbf, conversion_field))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        # 2a) copy input targetlevel areas to workspace
        log.info("A) Create feature class input_peilgebieden_feature -> tempfile_peilgebied")
        peilgebieden_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.select_analysis(input_peilgebieden_feature, peilgebieden_temp)

        # 2b) intersect(lgn+peilgebieden)
        log.info("B) Intersect lgn_shape + tempfile_peilgebied -> lgn_peilgebieden")
        intersect_temp = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Intersect_analysis("%s;%s" % (temp_lgn_fc, peilgebieden_temp), intersect_temp)

        # 3a) Read conversiontable into memory"
        log.info("C-1) Read conversiontable into memory")
        conversion = nens.gp.get_table(gp, input_conversiontable_dbf, primary_key=lgn_id.lower())

        # 3b) calculate areas for lgn_id
        log.info("C-2) Calculate areas for tempfile_LGN_peilgebied using conversiontable")

        #read gpgident from file
        lgn_fieldnames = nens.gp.get_table_def(gp, temp_lgn_fc)
        if "gridcode" in lgn_fieldnames:
            gridcode = "GRIDCODE"
        elif "grid_code" in lgn_fieldnames:
            gridcode = "grid_code"
        else:
            log.error("Cannot find 'grid_code' or 'gridcode' field in input lgn file")

        output_with_area = {}
        unknown_lgn_codes = {}
        source_str = "lgn:" + os.path.basename(input_lgn) + " pg:" + os.path.basename(input_peilgebieden_feature)
        if len(source_str) > 50:
            source_str = source_str[:50]
        date_str = time.strftime('%x')

        calc_count = 0
        rows = gp.UpdateCursor(intersect_temp)
        for row in nens.gp.gp_iterator(rows):
            value_gpgident = row.GetValue(gpgident)
            value_gridcode = row.GetValue(gridcode)
            value_lgn_id = int(value_gridcode)
            value_peilgeb_area = float(row.shape.Area) / 10000 #Area is in m2
            #add to area
            if output_with_area.has_key(value_gpgident):
                add_to_area, error = conv_ha(conversion, value_lgn_id, float(value_peilgeb_area))
                for key, value in add_to_area.items(): #all relevant keys
                    output_with_area[value_gpgident][key] = float(output_with_area[value_gpgident][key]) + float(add_to_area[key])
            else:
                output_with_area[value_gpgident], error = conv_ha(conversion, value_lgn_id, float(value_peilgeb_area))
                output_with_area[value_gpgident][gpgident] = value_gpgident #set GPGIDENT
                if error and not(unknown_lgn_codes.has_key(value_lgn_id)):
                    log.warning(" - Warning: lgncode " + str(value_lgn_id) + " not known (check conversiontable)")
                    unknown_lgn_codes[value_lgn_id] = 1
            output_with_area[value_gpgident]['LGN_SOURCE'] = source_str
            output_with_area[value_gpgident]['LGN_DATE'] = date_str
            calc_count = calc_count + 1
            if calc_count % 100 == 0:
                log.info("Calculating field nr " + str(calc_count))

        #----------------------------------------------------------------------------------------
        if input_watershape != "#":
            log.info("C-3) Calculate open water from watershape")

            # 1) intersect(watershape+peilgebieden)
            log.info("- intersect water_shape + tempfile_peilgebied -> watershape_peilgebieden")
            watershape_intersect = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.Intersect_analysis("%s;%s" % (input_watershape, peilgebieden_temp), watershape_intersect)

            source_watershape = os.path.basename(input_watershape)
            if len(source_watershape) > 50:
                source_watershape = source_watershape[:50]

            watershape_areas = {}
            rows = gp.SearchCursor(watershape_intersect)
            for row in nens.gp.gp_iterator(rows):
                water_area_ha = float(row.shape.Area) / 10000 #Area is in m2
                peilgebied_id = row.GetValue(gpgident)
                if watershape_areas.has_key(peilgebied_id):
                    subtotal_area = watershape_areas[peilgebied_id]['area']
                    #overwrite key with sum areas
                    watershape_areas[peilgebied_id] = {'area': subtotal_area + water_area_ha}
                else:
                    #create new key with area
                    watershape_areas[peilgebied_id] = {'area': water_area_ha}
            #update outputtable
            for peilgebied_id, values in output_with_area.items():
                if watershape_areas.has_key(peilgebied_id):
                    output_with_area[peilgebied_id]['OPNWT_GBKN'] = watershape_areas[peilgebied_id]['area']
                    output_with_area[peilgebied_id]['GBKN_DATE'] = date_str
                    output_with_area[peilgebied_id]['GBKN_SOURCE'] = source_watershape

        #----------------------------------------------------------------------------------------
        # 4) put dictionary area into output_table (HydroBase)
        log.info("D) Saving results... ")

        #definition of fields
        areaFields = {}
        areaFields = {gpgident: {'type': 'TEXT', 'length': '30'},
                      'VERHARD_LGN':{'type': 'DOUBLE'},
                      'ONVSTED_LGN':{'type': 'DOUBLE'},
                      'KASSEN_LGN':{'type': 'DOUBLE'},
                      'GRAS_LGN':{'type': 'DOUBLE'},
                      'NATUUR_LGN':{'type': 'DOUBLE'},
                      'OPENWAT_LGN':{'type': 'DOUBLE'},
                      'HECTARES':{'type': 'DOUBLE'},
                      'OPNWT_GBKN':{'type': 'DOUBLE'},
                      'LGN_SOURCE':{'type': 'TEXT', 'length': '50'},
                      'LGN_DATE':{'type': 'TEXT', 'length': '50'},
                      'GBKN_DATE':{'type': 'TEXT', 'length': '50'},
                      'GBKN_SOURCE':{'type': 'TEXT', 'length': '50'}}

        #check if output_table exists. if not, create with correct rows
        log.info("Checking table...")
        if not(gp.exists(output_table)):
            try:
                gp.CreateTable(os.path.dirname(output_table), os.path.basename(output_table))
            except Exception, e:
                log.error("Error: creating table " + output_table)
                log.debug(e)
                sys.exit(14)

        #check if output_table has the correct rows
        log.info("Checking fields...")
        for field_name, field_settings in areaFields.items():
            if field_settings.has_key('length'):
                if not turtlebase.arcgis.is_fieldname(gp, output_table, field_name):
                    gp.AddField(output_table, field_name, field_settings['type'], '#', '#', field_settings['length'])
            else:
                if not turtlebase.arcgis.is_fieldname(gp, output_table, field_name):
                    gp.AddField(output_table, field_name, field_settings['type'])

        #----------------------------------------------------------------------------------------
        turtlebase.arcgis.write_result_to_output(output_table, gpgident.lower(), output_with_area)

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.debug("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
