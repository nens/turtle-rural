# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import time
import traceback
import tempfile

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis

log = logging.getLogger(__name__)


def write_result_to_output(gp, output_table, output_ident, result_dict):
    """replace existing data in output_table
    """
    log.info("Updating existing records...")
    update_count, update_progress = update_records(
        gp, output_table, output_ident, result_dict)
    log.info(" - " + str(update_count) + " records have been updated")
    update_count = 0

    #put new data in output_table
    log.info("Inserting new records...")
    insert_count, update_progress = insert_records(
        gp, output_table, result_dict, update_progress)
    
    del update_progress
    log.info(" - " + str(insert_count) + " records have been inserted")
    insert_count = 0


def update_records(gp, table_name, field_name_id, data, update_progress={}):
    """data: {'1': {'field_name1': 'value1', 'fieldname2': 'value2'}, '2':
    {'field_name3': 'value3', 'fieldname4': 'value4'}} update_progress:
    dictionary that keeps count of the data being inserted {'1': 1, '2': 1}
    use try: except: construction when using this function
    """
    update_count = 0
    rows = gp.UpdateCursor(table_name)
    for row in nens.gp.gp_iterator(rows):
        ident = row.GetValue(field_name_id)
        #one row of data
        if str(ident) in data:
            for field_name, value in data[str(ident)].items():
                if value is not None:
                    row.SetValue(field_name, value)
            update_progress[str(ident)] = 1
            update_count = update_count + 1
            rows.UpdateRow(row)

    return update_count, update_progress


def insert_records(gp, table_name, data, update_progress={}):
    """data: {'1': {'field_name1': 'value1', 'fieldname2': 'value2'}, '2':
    {'field_name3': 'value3', 'fieldname4': 'value4'}} update_progress:
    dictionary that keeps count of the data being inserted {'1': 1, '2': 1}
    use try: except: construction when using this function
    """
    update_count = 0
    nsertCursor = gp.InsertCursor(table_name)

    for key, dict_items in data.items():
        if str(key) not in update_progress:
            #new row
            newRow = nsertCursor.NewRow()
            for field_name, value in dict_items.items():
                if value is not None:
                    newRow.SetValue(field_name, value)

            nsertCursor.InsertRow(newRow)
            update_count = update_count + 1
            update_progress[str(key)] = 1
    return update_count, update_progress


def conv_ha(conversion, lgn_id, ha, gewastype):
    '''
    converts lgn_id+area using conversion
    input:
    conversion: conversiontable, dictionary with lgn_id's as key
    lgn_id: lookup id
    ha: input for output value
    output: dictionary with 6 keys
    '''
    if lgn_id in conversion:
        verhard = ha * float(str(conversion[lgn_id]['verhard_ha']).replace(",", "."))
        onvsted = ha * float(str(conversion[lgn_id]['onvsted_ha']).replace(",", "."))
        kassen = ha * float(str(conversion[lgn_id]['kassen_ha']).replace(",", "."))
        onvland = ha * float(str(conversion[lgn_id]['onvland_ha']).replace(",", "."))
        openwat = ha * float(str(conversion[lgn_id]['openwat_ha']).replace(",", "."))
        if gewastype == 7:
            gewastype_ha = onvsted
        else:
            gewastype_ha = onvland
        hectares = ha
        error = False
    else:
        log.warning("lgncode %s not found! Check conversiontable" % lgn_id)
        verhard = 0
        onvsted = 0
        kassen = 0
        onvland = 0
        openwat = 0
        hectares = 0
        error = True
    return {'VERHRD_LGN': verhard,
            'ONVSTD_LGN': onvsted,
            'KASSEN_LGN': kassen,
            'ONVLND_LGN': onvland,
            'OPENWT_LGN': openwat,
            'HECTARES': hectares}, gewastype_ha, error


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
        if workspace == "-":
            workspace = tempfile.gettempdir()
            log.info("location temp: %s" % workspace)

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        #get argv
        log.info("Getting command parameters... ")
        if len(sys.argv) == 7:
            input_peilgebieden_feature = sys.argv[1] #from HydroBase
            input_lgn = sys.argv[2]
            input_conversiontable_dbf = sys.argv[3]
            input_watershape = sys.argv[4]
            output_table = sys.argv[5] #RR_oppervlak in HydroBase
            output_crop_table = sys.argv[6]
        else:
            log.error("Arguments: <LGN raster> <peilgebied HydroBase-table> <conversiontable dbf> <output HydroBase-table>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        lgn_desc = gp.describe(input_lgn)
        if lgn_desc.DataType == 'RasterDataset' or lgn_desc.DataType == 'RasterLayer':
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
            log.error("datatype of LGN is %s , must be a ShapeFile, FeatureClass, RasterDataset or RasterLayer" % lgn_desc.DataType)
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

        hectares = config.get('OppervlakteParameters', 'input_oppervlak_area')
        verhard_ha = config.get('OppervlakteParameters', 'input_oppervlak_verhard')
        onvsted_ha = config.get('OppervlakteParameters', 'input_oppervlak_onvsted')
        kassen_ha = config.get('OppervlakteParameters', 'input_oppervlak_kassen')
        onvland_ha = config.get('OppervlakteParameters', 'input_oppervlak_onvland')
        openwat_ha = config.get('OppervlakteParameters', 'input_oppervlak_openwat')
        lgn_id = config.get('OppervlakteParameters', 'input_field_lgncode')
        conversion_fields = [lgn_id, verhard_ha, onvsted_ha, kassen_ha, onvland_ha, openwat_ha, hectares]
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
        intersect_temp = os.path.join(workspace_gdb, 'intersect_lgn_gpg')
        gp.Union_analysis("%s;%s" % (temp_lgn_fc, peilgebieden_temp), intersect_temp)

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

        gewastypen = {1: config.get('OppervlakteParameters', 'grass_area'),
                      2: config.get('OppervlakteParameters', 'corn_area'),
                      3: config.get('OppervlakteParameters', 'potatoes_area'),
                      4: config.get('OppervlakteParameters', 'sugarbeet_area'),
                      5: config.get('OppervlakteParameters', 'grain_area'),
                      6: config.get('OppervlakteParameters', 'miscellaneous_area'),
                      7: config.get('OppervlakteParameters', 'nonarable_land_area'),
                      8: config.get('OppervlakteParameters', 'greenhouse_area'),
                      9: config.get('OppervlakteParameters', 'orchard_area'),
                      10: config.get('OppervlakteParameters', 'bulbous_plants_area'),
                      11: config.get('OppervlakteParameters', 'foliage_forest_area'),
                      12: config.get('OppervlakteParameters', 'pine_forest_area'),
                      13: config.get('OppervlakteParameters', 'nature_area'),
                      14: config.get('OppervlakteParameters', 'fallow_area'),
                      15: config.get('OppervlakteParameters', 'vegetables_area'),
                      16: config.get('OppervlakteParameters', 'flowers_area'),
                      }
        output_with_area = {}
        output_gewas_areas = {}
        unknown_lgn_codes = {}
        source_str = "lgn:" + os.path.basename(input_lgn) + " pg:" + os.path.basename(input_peilgebieden_feature)
        if len(source_str) > 50:
            source_str = source_str[:50]
        date_str = time.strftime('%x')

        calc_count = 0
        rows = gp.UpdateCursor(intersect_temp)
        for row in nens.gp.gp_iterator(rows):
            value_gpgident = row.GetValue(gpgident)
            if value_gpgident == "":
                continue
            value_gridcode = row.GetValue(gridcode)
            if value_gridcode == 0:
                if value_gpgident in output_with_area:
                    output_with_area[value_gpgident][hectares] += float(row.shape.Area) / 10000
                else:
                    output_with_area[value_gpgident] = {gpgident : value_gpgident}
                    if hectares in output_with_area[value_gpgident]:
                        output_with_area[value_gpgident][hectares] = float(row.shape.Area) / 10000
                    else:
                        output_with_area[value_gpgident] = {hectares: float(row.shape.Area) / 10000}
                continue
                    
            value_lgn_id = int(value_gridcode)
            value_peilgeb_area = float(row.shape.Area) / 10000 #Area is in m2
            
            if 'gewastype' in conversion[value_lgn_id]:
                gewastype = conversion[value_lgn_id]['gewastype']
            else:
                gewastype = 1
            #add to area
            if value_gpgident in output_with_area:
                add_to_area, gewastype_ha, error = conv_ha(conversion, value_lgn_id, float(value_peilgeb_area), gewastype)
                for key in add_to_area.keys(): #all relevant keys
                    if key in output_with_area[value_gpgident]:
                        output_with_area[value_gpgident][key] += float(add_to_area[key])
                    else:
                        output_with_area[value_gpgident][key] = float(add_to_area[key])
            else:
                output_with_area[value_gpgident], gewastype_ha, error = conv_ha(conversion, value_lgn_id, float(value_peilgeb_area), gewastype)
                output_with_area[value_gpgident][gpgident] = value_gpgident #set GPGIDENT
                if error and not(value_lgn_id in unknown_lgn_codes):
                    log.warning(" - Warning: lgncode " + str(value_lgn_id) + " not known (check conversiontable)")
                    unknown_lgn_codes[value_lgn_id] = 1
            
            if gewastype != 0:
                if value_gpgident not in output_gewas_areas:
                    output_gewas_areas[value_gpgident] = {gpgident: value_gpgident}
                    for key in gewastypen.keys():
                        output_gewas_areas[value_gpgident][gewastypen[key]] = 0
                    
                output_gewas_areas[value_gpgident][gewastypen[gewastype]] += gewastype_ha
                
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
                if peilgebied_id in watershape_areas:
                    subtotal_area = watershape_areas[peilgebied_id]['area']
                    #overwrite key with sum areas
                    watershape_areas[peilgebied_id] = {'area': subtotal_area + water_area_ha}
                else:
                    #create new key with area
                    watershape_areas[peilgebied_id] = {'area': water_area_ha}
            #update outputtable
            for peilgebied_id in output_with_area.keys():
                if peilgebied_id in watershape_areas:
                    output_with_area[peilgebied_id]['OPNWT_GBKN'] = watershape_areas[peilgebied_id]['area']
                    output_with_area[peilgebied_id]['GBKN_DATE'] = date_str
                    output_with_area[peilgebied_id]['GBKN_SOURCE'] = source_watershape

        #----------------------------------------------------------------------------------------
        # 4) put dictionary area into output_table (HydroBase)
        log.info("D) Saving results... ")

        #definition of fields
        areaFields = {gpgident: {'type': 'TEXT', 'length': '30'},
                      'VERHRD_LGN':{'type': 'DOUBLE'},
                      'ONVSTD_LGN':{'type': 'DOUBLE'},
                      'KASSEN_LGN':{'type': 'DOUBLE'},
                      'ONVLND_LGN':{'type': 'DOUBLE'},
                      'OPENWT_LGN':{'type': 'DOUBLE'},
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
            if 'length' in field_settings:
                if not turtlebase.arcgis.is_fieldname(gp, output_table, field_name):
                    gp.AddField(output_table, field_name, field_settings['type'], '#', '#', field_settings['length'])
            else:
                if not turtlebase.arcgis.is_fieldname(gp, output_table, field_name):
                    gp.AddField(output_table, field_name, field_settings['type'])

        #----------------------------------------------------------------------------------------
        #log.info(output_with_area)
        turtlebase.arcgis.write_result_to_output(output_table, gpgident.lower(), output_with_area)

        #----------------------------------------------------------------------------------------
        # 5) Calculate crop areas
        if output_crop_table != "#":
            
            
            log.info("E) Calculate crop areas... ")
            
            #definition of fields
            cropFields = {gpgident: {'type': 'TEXT', 'length': '30'},
                          'GRAS_HA':{'type': 'DOUBLE'},
                          'MAIS_HA':{'type': 'DOUBLE'},
                          'AARDAPL_HA':{'type': 'DOUBLE'},
                          'BIET_HA':{'type': 'DOUBLE'},
                          'GRAAN_HA':{'type': 'DOUBLE'},
                          'OVERIG_HA':{'type': 'DOUBLE'},
                          'NIETAGR_HA':{'type': 'DOUBLE'},
                          'GLAST_HA':{'type': 'DOUBLE'},
                          'BOOMGRD_HA':{'type': 'DOUBLE'},
                          'BOLLEN_HA':{'type': 'DOUBLE'},
                          'LOOFBOS_HA':{'type': 'DOUBLE'},
                          'NLDBOS_HA':{'type': 'DOUBLE'},
                          'NATUUR_HA':{'type': 'DOUBLE'},
                          'BRAAK_HA':{'type': 'DOUBLE'},
                          'GROENTN_HA':{'type': 'DOUBLE'},
                          'BLOEMEN_HA':{'type': 'DOUBLE'}}

            #check if output_table exists. if not, create with correct rows
            log.info("Checking table...")
            if not(gp.exists(output_crop_table)):
                try:
                    gp.CreateTable(os.path.dirname(output_crop_table), os.path.basename(output_crop_table))
                except Exception, e:
                    log.error("Error: creating table " + output_crop_table)
                    log.debug(e)
                    sys.exit(14)
            
            #check if output_table has the correct rows
            log.info("Checking fields...")
            for field_name, field_settings in cropFields.items():
                if 'length' in field_settings:
                    if not turtlebase.arcgis.is_fieldname(gp, output_crop_table, field_name):
                        gp.AddField(output_crop_table, field_name, field_settings['type'], '#', '#', field_settings['length'])
                else:
                    if not turtlebase.arcgis.is_fieldname(gp, output_crop_table, field_name):
                        gp.AddField(output_crop_table, field_name, field_settings['type'])
                        
            write_result_to_output(gp, output_crop_table, gpgident.lower(), output_gewas_areas)
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
