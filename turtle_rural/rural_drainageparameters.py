# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

# Import system modules
import sys
import os
import logging
import traceback
import ConfigParser

# Import GIS modules
import arcgisscripting
import nens.gp

# Import Turtlebase modules
import turtlebase.arcgis
import turtlebase.general
from turtlebase.logutils import LoggingConfig

log = logging.getLogger(__name__)


def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)


class ernst:
    names = []
    names.append('>0.5 mm/dag wegzijging')
    names.append('0.5 mm/dag wegzijging - 0.25 mm/dag kwel')
    names.append('0.25 mm/dag kwel - 0.75 mm/dag kwel')
    names.append('0.75 mm/dag kwel - 1.25 mm/dag kwel')
    names.append('1.25 mm/dag kwel - 1.75 mm/dag kwel')
    names.append('1.75 mm/dag kwel - 3.5 mm/dag kwel')
    names.append('>3.5 kwel')
    #[ALFA_LZ] = max(formula_a * [DL] + formula_b, 25)
    boundaries = []
    boundaries.append({'level_min': -100, 'level_max': -0.5, 'formula_a': 192.19, 'formula_b': -96.19})
    boundaries.append({'level_min': -0.5, 'level_max': 0.25, 'formula_a': 160.38, 'formula_b': -79.83})
    boundaries.append({'level_min': 0.25, 'level_max': 0.75, 'formula_a': 147.24, 'formula_b': -72.84})
    boundaries.append({'level_min': 0.75, 'level_max': 1.25, 'formula_a': 136.86, 'formula_b': -67.62})
    boundaries.append({'level_min': 1.25, 'level_max': 1.75, 'formula_a': 127.56, 'formula_b': -62.67})
    boundaries.append({'level_min': 1.75, 'level_max': 3.5 , 'formula_a': 119.36, 'formula_b': -58.41})
    boundaries.append({'level_min': 3.5,  'level_max': 100 , 'formula_a': 86    , 'formula_b': -40.99})

    #drooglegging (meters)
    def calc_dl(self, maaiveld_hoogte, winterpeil, zomerpeil):
        return maaiveld_hoogte-max(winterpeil, zomerpeil)

    #drainage (dagen)
    def calc_alfa(self, kwel, drooglegging):
        for b in self.boundaries:
            if ((kwel >= b['level_min']) and (kwel < b['level_max'])):
                return max(b['formula_a']*drooglegging+b['formula_b'], 25)
        return 25 #no match

    def name(self, class_id):
        return names[class_id]


def sort_area_rev(x,y):
    return int(y['area']-x['area']) #it sorts "roughly-correct", because we must return an int


def sum_grondsoort(l):
    total = 0
    for item in l:
        total = total + item['area']
    return total


def main():
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

        debuglogging()
        #----------------------------------------------------------------------------------------
        #create header for logfile
        log.info("*********************************************************")
        log.info(__name__)
        log.info("This python script is developed by "
                 + "Nelen & Schuurmans B.V. and is a part of 'Turtle'")
        log.info("*********************************************************")
        log.info("arguments: %s" %(sys.argv))

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
        #ernst rekenklasse
        ernst_drainage = ernst()


        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters... ")
        if len(sys.argv) == 7:
            file_input_peilgebieden_feature = sys.argv[1] #shape
            file_input_peilvakgegevens = sys.argv[2] #[ZOMERPEIL],[WINTERPEIL]
            file_input_kwelstroom = sys.argv[3] #[KWELSTROOM]
            file_input_maaiveldkarakteristiek = sys.argv[4] #[MV_HGT_50]
            file_input_bodemsoort = sys.argv[5] #shape
            file_output = sys.argv[6]
        else:
            log.error("Usage: python rural_drainageparameter.py <peilgebieden shape> <peilvakgegevens> <kwelstroom> <maaiveldkarakteristiek> <bodemsoort shape> <outputtabel HydroBase>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check geometry
        log.info("Check geometry of input parameters")
        if not turtlebase.arcgis.is_file_of_type(gp, file_input_peilgebieden_feature, 'Polygon'):
            log.error("Input %s does not contain polygons" % file_input_peilgebieden_feature)
            sys.exit(1)
        if not turtlebase.arcgis.is_file_of_type(gp, file_input_bodemsoort, 'Polygon'):
            log.error("Input %s does not contain polygons" % file_input_bodemsoort)
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check required fields
        log.info("Check required fields in input data")
        peilgebied_id = config.get('GENERAL', 'gpgident')
        pawn_code = config.get('Ernst', 'input_bodemsoort_code')

        missing_fields = []
        check_fields = {file_input_peilgebieden_feature: peilgebied_id,
                      file_input_peilvakgegevens: peilgebied_id,
                      file_input_peilvakgegevens: config.get('Ernst', 'peilvakgegevens_zomerpeil'),
                      file_input_peilvakgegevens: config.get('Ernst', 'peilvakgegevens_winterpeil'),
                      file_input_kwelstroom: peilgebied_id,
                      file_input_kwelstroom: config.get('Ernst', 'kwelstroom_kwelstroom'),
                      file_input_maaiveldkarakteristiek: peilgebied_id,
                      file_input_maaiveldkarakteristiek: config.get('Ernst', 'maaiveldkarakteristiek_value'),
                      file_input_bodemsoort: pawn_code}

        for input_file, field in check_fields.items():
            if not turtlebase.arcgis.is_fieldname(gp, input_file, field):
                log.error("Missing field %s in %s" % (field, input_file))
                missing_fields.append("missing %s in %s" % (field, input_file))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #----------------------------------------------------------------------------------------
        # Check record count
        log.info("Check records of input parameters")
        count_area = turtlebase.arcgis.fc_records(gp, file_input_peilgebieden_feature)
        count_surface_level_table = turtlebase.arcgis.fc_records(gp, file_input_peilvakgegevens)
        count_seepage = turtlebase.arcgis.fc_records(gp, file_input_kwelstroom)
        count_scurve = turtlebase.arcgis.fc_records(gp, file_input_maaiveldkarakteristiek)

        if count_surface_level_table != count_area:
            log.error("input %s (%s records) contains not the same records as %s (%s records)" % (file_input_peilvakgegevens, count_surface_level_table,
                                                                                                 file_input_peilgebieden_feature, count_area))
            sys.exit(2)
        if count_seepage != count_area:
            log.error("input %s (%s records) contains not the same records as %s (%s records)" % (file_input_kwelstroom, count_seepage,
                                                                                                 file_input_peilgebieden_feature, count_area))
            sys.exit(2)
        if count_scurve != count_area:
            log.error("input %s (%s records) contains not the same records as %s (%s records)" % (file_input_maaiveldkarakteristiek,
                                                                                                 count_scurve, file_input_peilgebieden_feature, count_area))
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        #A: bodemsoort
        log.info("A-1) Copy peilgebieden to temporary workspace")
        temp_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.select_analysis(file_input_peilgebieden_feature, temp_peilgebieden)

        log.info("A-2) Copy bodemsoort to temporary workspace")
        temp_bodemsoort = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.select_analysis(file_input_bodemsoort, temp_bodemsoort)

        log.info("A-3) Intersect bodemsoort + peilgebieden -> peilg+bodem")
        temp_intersect_bodem_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Intersect_analysis(temp_peilgebieden + "; " + temp_bodemsoort, temp_intersect_bodem_peilgebieden)

        log.info("A-4) Dissolve peilg+bodem")
        temp_dissolve_bodem_peilgebieden = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Dissolve_management (temp_intersect_bodem_peilgebieden, temp_dissolve_bodem_peilgebieden, peilgebied_id + " ;" + pawn_code, "")

        log.info("A-5) Read peilg+bodem(dissolve)")
        log.info(" - reading shape")
        peilv_grondsoort = {}
        row = gp.SearchCursor(temp_dissolve_bodem_peilgebieden)
        for item in nens.gp.gp_iterator(row):
            area_id = item.GetValue(peilgebied_id)
            soil_id = item.GetValue(pawn_code)
            area = item.Shape.Area
            data_row = {'pawn_code': soil_id, 'area': area}
            if not(peilv_grondsoort.has_key(area_id)):
                peilv_grondsoort[area_id] = {'grondsoort':[]}
            peilv_grondsoort[area_id]['grondsoort'].append(data_row)

        log.info(" - sorting")
        for key in peilv_grondsoort.keys():
            peilv_grondsoort[key]['grondsoort'].sort(sort_area_rev)
            peilv_grondsoort[key]['area'] = sum_grondsoort(peilv_grondsoort[key]['grondsoort'])

        # ---------------------------------------------------------------------------
        #B: ernst parameters
        record_count = {}

        #inlezen van shape files: [ZOMERPEIL, WINTERPEIL, KWELSTROOM, MV_HGT_50]
        log.info("B-1) Reading inputfile peilvakgegevens")
        data_set = {}

        row = gp.SearchCursor(file_input_peilvakgegevens)
        for item in nens.gp.gp_iterator(row):
            field_id = item.GetValue(peilgebied_id)
            data_set[field_id] = {}
            data_set[field_id]['zomerpeil'] = item.GetValue(config.get('Ernst', 'peilvakgegevens_zomerpeil'))
            data_set[field_id]['winterpeil'] = item.GetValue(config.get('Ernst', 'peilvakgegevens_winterpeil'))

            if (data_set[field_id]['zomerpeil'] < float(config.get('Ernst', 'validate_min_zomerpeil'))) or (data_set[field_id]['zomerpeil'] > float(config.get('Ernst', 'validate_max_zomerpeil'))):
                log.error("zomerpeil has a non-valid value of "+str(data_set[field_id]['zomerpeil']))
                sys.exit(5)
            if (data_set[field_id]['winterpeil'] < float(config.get('Ernst', 'validate_min_winterpeil'))) or (data_set[field_id]['zomerpeil'] > float(config.get('Ernst', 'validate_max_winterpeil'))):
                log.error("winterpeil has a non-valid value of "+str(data_set[field_id]['winterpeil']))
                sys.exit(5)

        #inlezen van shape files: [ZOMERPEIL, WINTERPEIL, KWELSTROOM, MV_HGT_50]
        log.info("B-2) Reading inputfile kwelstroom")
        row = gp.SearchCursor(file_input_kwelstroom)
        for item in nens.gp.gp_iterator(row):
            field_id = item.GetValue(peilgebied_id)
            if not(data_set.has_key(field_id)):
                log.error("non-matching kwelstroom and peilvakgegevens, check if peilvakgegevens has key '"+field_id+"'")
                sys.exit(9)
            data_set[field_id]['kwel'] = item.GetValue(config.get('Ernst', 'kwelstroom_kwelstroom'))

        #inlezen van shape files: [ZOMERPEIL, WINTERPEIL, KWELSTROOM, MV_HGT_50]
        log.info("B-3) Reading inputfile maaiveldkarakteristiek")
        row = gp.SearchCursor(file_input_maaiveldkarakteristiek)
        for item in nens.gp.gp_iterator(row):
            field_id = item.GetValue(peilgebied_id)
            if not(data_set.has_key(field_id)):
                log.error("non-matching maaiveldkarakteristiek and peilvakgegevens, check if peilvakgegevens has key '"+field_id+"'")
                sys.exit(9)
            data_set[field_id]['maaiveld'] = item.GetValue(config.get('Ernst', 'maaiveldkarakteristiek_value'))

        # ---------------------------------------------------------------------------
        #check input: each record should contain all fields (count: 4)
        log.info("B-4) Checking input")
        for key,value in data_set.items():
            if len(value.items()) != 4:
                log.error(key, value)
                log.error("check if inputfiles match with eachother!")
                sys.exit(6)

        # ---------------------------------------------------------------------------
        #bepaling drooglegging: [DL] = [MV_HGT_50] - max([WINTERPEIL], [ZOMERPEIL])
        #bepaling drainageweerstand [ALFA_LZ] = xx * [DL} - yy, waarbij xx, yy afhangen van de klasse
        #bepaling INF_OPWAT, OPP_AFVOER
        log.info("B-6) preparing data for output")
        data_set_output = {}
        import time
        date_str = time.strftime("%d %B %Y %H:%M:%S")
        log.info("Calculating GRONDSOORT, drooglegging, ALFA_LZ, INF_OPWAT, OPP_AFVOER... ")
        log.info(" - Datum-string: "+date_str)
        for key,item in data_set.items():
            #print key, item
            data_set[key]['drooglegging'] = ernst_drainage.calc_dl(item['maaiveld'], item['zomerpeil'], item['winterpeil'])
            data_set_output[key] = {}
            data_set_output[key][peilgebied_id] = key #important!
            data_set_output[key][config.get('Ernst', 'output_alfa_lz')] = ernst_drainage.calc_alfa(data_set[key]['kwel'],data_set[key]['drooglegging'])
            data_set_output[key][config.get('Ernst', 'output_inf_opwat')] = 250 #of dataset['key']['ALFA_LZ']*1.5
            data_set_output[key][config.get('Ernst', 'output_opp_afvoer')] = 0.5
            grondsrt_str = ""
            try:
                data_set_output[key][config.get('Ernst', 'output_grondsoort')] = peilv_grondsoort[key]['grondsoort'][0]['pawn_code']
                for idx in range(min(len(peilv_grondsoort[key]['grondsoort']), 5)):
                    grondsrt_str = grondsrt_str + str(peilv_grondsoort[key]['grondsoort'][idx]['pawn_code'])+"(" +str(int(100*peilv_grondsoort[key]['grondsoort'][idx]['area']/peilv_grondsoort[key]['area'])) + "%) "
            except Exception, e:
                log.warning(e)
                log.warning("id "+key+" has no "+config.get('Ernst', 'output_grondsoort')+" value!")
                data_set_output[key][config.get('Ernst', 'output_grondsoort')] = -1
            source_str = "grondsrt:"+grondsrt_str+"pv:"+os.path.basename(file_input_peilvakgegevens)+" kwel:"+os.path.basename(file_input_kwelstroom)+" mv:"+os.path.basename(file_input_maaiveldkarakteristiek)
            if len(source_str) > 50:
                source_str = source_str[:50]
            data_set_output[key]['SOURCE'] = source_str
            data_set_output[key]['DATE_TIME'] = date_str

        # ---------------------------------------------------------------------------
        #C: output
        #add cols [ALFA_LZ], [INF_OPWAT], [OPP_AFVOER]
        drainageFields = {peilgebied_id: {'type': 'TEXT', 'length': '30'},
                          config.get('Ernst', 'output_alfa_lz'):{'type': 'DOUBLE'},
                          config.get('Ernst', 'output_inf_opwat'):{'type': 'DOUBLE'},
                          config.get('Ernst', 'output_opp_afvoer'):{'type': 'DOUBLE'},
                          config.get('Ernst', 'output_grondsoort'):{'type': 'INTEGER'},
                          'SOURCE':{'type': 'TEXT', 'length': '256'},
                          'DATE_TIME':{'type': 'TEXT', 'length': '40'},
                          'COMMENTS':{'type': 'TEXT', 'length': '256'}}

        #check if output_table exists. if not, create with correct rows
        log.info("C-1) Checking output table... ")
        if not(gp.exists(file_output)):
            gp.CreateTable(os.path.dirname(file_output), os.path.basename(file_output))

        #check if output_table has the correct rows
        log.info("C-2) Checking fields... ")
        for field_name, field_settings in drainageFields.items():
            if field_settings.has_key('length'):
                if not turtlebase.arcgis.is_fieldname(gp, file_output, field_name):
                    gp.AddField(file_output, field_name, field_settings['type'], '#', '#', field_settings['length'])
            else:
                if not turtlebase.arcgis.is_fieldname(gp, file_output, field_name):
                    gp.AddField(file_output, field_name, field_settings['type'])

        # ---------------------------------------------------------------------------
        # Write results to output table
        log.info("Write results to output table")
        turtlebase.arcgis.write_result_to_output(file_output, peilgebied_id, data_set_output)



        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        log.info("*********************************************************")
        log.info("Finished")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
