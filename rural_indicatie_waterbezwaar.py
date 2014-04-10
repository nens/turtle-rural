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

log = logging.getLogger(__name__)


def calc_waterbezwaar(toetshoogte, ow_opp, tp_slope, winterpeil, waterstand):
    """Function to calculate waterbezwaar."""
    waterstand = float(waterstand) / 100
    ow_opp = float(ow_opp) * 10000
    tp_slope = float(tp_slope) / 100
    if toetshoogte > -100 and toetshoogte < 100:
        ow_tp = ow_opp + ((ow_opp * tp_slope) * (toetshoogte - winterpeil))
        ow_ws = ow_opp + ((ow_opp * tp_slope) * (waterstand - winterpeil))
        if waterstand > toetshoogte:
            wb_m3 = ((ow_tp * (waterstand - toetshoogte) + ((ow_ws - ow_tp) * (waterstand - toetshoogte))))
            wb_ha = wb_m3 / (toetshoogte - winterpeil) / 10000
        elif waterstand < toetshoogte:
            wb_m3 = 0
            wb_ha = 0
##            wb_m3 = ((-1 * (ow_ws * (toetshoogte - waterstand) + ((ow_tp - ow_ws) * (toetshoogte - waterstand)))))
##            wb_ha =  (-1 * (wb_m3 /(toetshoogte - winterpeil)/10000))
        else:
            wb_m3 = 0
            wb_ha = 0
        return wb_m3, wb_ha
    else:
        wb_m3 = 0
        wb_ha = 0
        return wb_m3, wb_ha


def check_items(input_dict, fields_list):
    """Functie check items uit dictonary.
    return false when field does not exist
    at least one item in fields_list is not a key in input_dict
    else return true"""
    return_list = []
    for field in fields_list:
        if not field in input_dict:
            return_list.append(field)
    return return_list


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters")
        if len(sys.argv) == 6:
            rr_peilgebieden_tbl = sys.argv[1]
            rr_oppervlak_tbl = sys.argv[2]
            rr_toetspunten_tbl = sys.argv[3]
            rr_resultaten_tbl = sys.argv[4]
            output_waterbezwaar_tbl = sys.argv[5]
        else:
            log.error("Usage: python rural_indicatie_waterbezwaar.py <rr_peilgebieden_tbl> <rr_oppervlak_tbl> <rr_toetspunten_tbl> <rr_resultaten_tbl> <output_waterbezwaar_tbl>")
            sys.exit(1)
        #----------------------------------------------------------------------------------------
        #check input parameters
        log.info('Checking presence of input files')
        if not(gp.exists(rr_peilgebieden_tbl)):
            log.error("tabel %s does not exist!" % rr_peilgebieden_tbl)
            sys.exit(5)
        if not(gp.exists(rr_oppervlak_tbl)):
            log.error("tabel %s does not exist!" % rr_oppervlak_tbl)
            sys.exit(5)
        if not(gp.exists(rr_toetspunten_tbl)):
            log.error("tabel %s does not exist!" % rr_toetspunten_tbl)
            sys.exit(5)
        if not(gp.exists(rr_resultaten_tbl)):
            log.error("tabel %s does not exist!" % rr_resultaten_tbl)
            sys.exit(5)
        log.info('input parameters checked')

        # ---------------------------------------------------------------------------
        gpgident = config.get('GENERAL', 'gpgident').lower()

        # create list from geodatabase table 
        gegevens = nens.gp.get_table(gp, rr_resultaten_tbl, primary_key=gpgident)
        nens.gp.join_on_primary_key(gp, gegevens, rr_toetspunten_tbl, gpgident)
        nens.gp.join_on_primary_key(gp, gegevens, rr_peilgebieden_tbl, gpgident)
        nens.gp.join_on_primary_key(gp, gegevens, rr_oppervlak_tbl, gpgident)

        # calculating waterbezwaar
        log.info("calculating surplus water")

        # check input fields
        check_row = gegevens.values()[0]
        check_fields = [config.get('waterbezwaar', 'toetspunt_overlast_stedelijk'),
                        config.get('waterbezwaar', 'toetspunt_overlast_hoogwlandbouw'),
                        config.get('waterbezwaar', 'toetspunt_overlast_akkerbouw'),
                        config.get('waterbezwaar', 'toetspunt_overlast_grasland'),
                        config.get('waterbezwaar', 'toetspunt_inundatie_stedelijk'),
                        config.get('waterbezwaar', 'toetspunt_inundatie_hoogwlandbouw'),
                        config.get('waterbezwaar', 'toetspunt_inundatie_akkerbouw'),
                        config.get('waterbezwaar', 'toetspunt_inundatie_grasland'),
                        config.get('waterbezwaar', 'peilgebied_winterpeil'),
                        config.get('waterbezwaar', 'peilgebied_helling'),
                        config.get('waterbezwaar', 'waterstand_inundatie_stedelijk'),
                        config.get('waterbezwaar', 'waterstand_inundatie_hoogwlandbouw'),
                        config.get('waterbezwaar', 'waterstand_inundatie_akkerbouw'),
                        config.get('waterbezwaar', 'waterstand_inundatie_grasland'),
                        config.get('waterbezwaar', 'waterstand_overlast_stedelijk'),
                        config.get('waterbezwaar', 'waterstand_overlast_hoogwlandbouw'),
                        config.get('waterbezwaar', 'waterstand_overlast_akkerbouw'),
                        config.get('waterbezwaar', 'waterstand_overlast_grasland'),
                        config.get('waterbezwaar', 'oppervlak_openwater')]
        missing_fields = check_items(check_row, check_fields)
        if missing_fields:
            log.error("at least one of the input fields is missing, check ini-file and database. %s" % (str(missing_fields)))
            sys.exit(6)

        waterbezwaar = {}
        for id, row in gegevens.items():
            if row['tldhelling'] == None:
                tp_slope = 0
            else:
                tp_slope = float(row['tldhelling'])

            if row['winterpeil'] == None:
                winterpeil = 0
            else:
                winterpeil = float(row['winterpeil'])

            if row['openwat_ha'] == None:
                ow_opp = 0
            else:
                ow_opp = float(row['openwat_ha'])

            # bereken waterbezwaar inundatie stedelijk
            toetshoogte_i_st = float(row['mtgmv_i_st'])
            if toetshoogte_i_st == winterpeil:
                toetshoogte_i_st = toetshoogte_i_st + 0.05
                log.warning("Toetspunt inundatie stedelijk is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_i_st = float(row['ws_100'])
            sted_i_wb_m3, sted_i_wb_ha = calc_waterbezwaar(toetshoogte_i_st, ow_opp, tp_slope, winterpeil, waterstand_i_st)

            # bereken waterbezwaar overlast stedelijk
            toetshoogte_o_st = float(row['mtgmv_o_st'])
            if toetshoogte_o_st == winterpeil:
                toetshoogte_o_st = toetshoogte_o_st + 0.05
                log.warning("Toetspunt overlast stedelijk is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_o_st = float(row['ws_25'])
            sted_o_wb_m3, sted_o_wb_ha = calc_waterbezwaar(toetshoogte_o_st, ow_opp, tp_slope, winterpeil, waterstand_o_st)

            # bereken waterbezwaar inundatie hoogwaardige landbouw
            toetshoogte_i_hl = float(row['mtgmv_i_hl'])
            if toetshoogte_i_hl == winterpeil:
                toetshoogte_i_hl = toetshoogte_i_hl + 0.05
                log.warning("Toetspunt inundatie hoogwaardige landbouw is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_i_hl = float(row['ws_50'])
            hoogw_i_wb_m3, hoogw_i_wb_ha = calc_waterbezwaar(toetshoogte_i_hl, ow_opp, tp_slope, winterpeil, waterstand_i_hl)

            # bereken waterbezwaar overlast hoogwaardige landbouw
            toetshoogte_o_hl = float(row['mtgmv_o_hl'])
            if toetshoogte_o_hl == winterpeil:
                toetshoogte_o_hl = toetshoogte_o_hl + 0.05
                log.warning("Toetspunt overlast hoogwaardige landbouw is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_o_hl = float(row['ws_25'])
            hoogw_o_wb_m3, hoogw_o_wb_ha = calc_waterbezwaar(toetshoogte_o_hl, ow_opp, tp_slope, winterpeil, waterstand_o_hl)

            # bereken waterbezwaar inundatie akkerbouw
            toetshoogte_i_ak = float(row['mtgmv_i_ak'])
            if toetshoogte_i_ak == winterpeil:
                toetshoogte_i_ak = toetshoogte_i_ak + 0.05
                log.warning("Toetspunt inundatie akkerbouw is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_i_ak = float(row['ws_25'])
            akker_i_wb_m3, akker_i_wb_ha = calc_waterbezwaar(toetshoogte_i_ak, ow_opp, tp_slope, winterpeil, waterstand_i_ak)

            # bereken waterbezwaar overlast akkerbouw
            toetshoogte_o_ak = float(row['mtgmv_o_ak'])
            if toetshoogte_o_ak == winterpeil:
                toetshoogte_o_ak = toetshoogte_o_ak + 0.05
                log.warning("Toetspunt overlast akkerbouw is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_o_ak = float(row['ws_15'])
            akker_o_wb_m3, akker_o_wb_ha = calc_waterbezwaar(toetshoogte_o_ak, ow_opp, tp_slope, winterpeil, waterstand_o_ak)

            # bereken waterbezwaar inundatie grasland
            toetshoogte_i_gr = float(row['mtgmv_i_gr'])
            if toetshoogte_i_gr == winterpeil:
                toetshoogte_i_gr = toetshoogte_i_gr + 0.05
                log.warning("Toetspunt inundatie grasland is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_i_gr = float(row['ws_10'])
            gras_i_wb_m3, gras_i_wb_ha = calc_waterbezwaar(toetshoogte_i_gr, ow_opp, tp_slope, winterpeil, waterstand_i_gr)

            # bereken waterbezwaar overlast grasland
            toetshoogte_o_gr = float(row['mtgmv_o_gr'])
            if toetshoogte_o_gr == winterpeil:
                toetshoogte_o_gr = toetshoogte_o_gr + 0.05
                log.warning("Toetspunt overlast grasland is gelijk aan winterpeil, toetspunt + 5cm")
            waterstand_o_gr = float(row['ws_5'])
            gras_o_wb_m3, gras_o_wb_ha = calc_waterbezwaar(toetshoogte_o_gr, ow_opp, tp_slope, winterpeil, waterstand_o_gr)

            wb_i_m3 = max(sted_i_wb_m3, hoogw_i_wb_m3, akker_i_wb_m3, gras_i_wb_m3)
            wb_o_m3 = max(sted_o_wb_m3, hoogw_o_wb_m3, akker_o_wb_m3, gras_o_wb_m3)
            wb_i_ha = max(sted_i_wb_ha, hoogw_i_wb_ha, akker_i_wb_ha, gras_i_wb_ha)
            wb_o_ha = max(sted_o_wb_ha, hoogw_o_wb_ha, akker_o_wb_ha, gras_o_wb_ha)

            waterbezwaar[id] = {'gpgident': id, 'wb_i_m3': wb_i_m3, 'wb_o_m3': wb_o_m3, 'wb_i_ha': wb_i_ha, 'wb_o_ha': wb_o_ha,
                                'wb_i_st_ha': sted_i_wb_ha, 'wb_i_hl_ha': hoogw_i_wb_ha, 'wb_i_ak_ha': akker_i_wb_ha, 'wb_i_gr_ha': gras_i_wb_ha,
                                'wb_o_st_ha': sted_o_wb_ha, 'wb_o_hl_ha': hoogw_o_wb_ha, 'wb_o_ak_ha': akker_o_wb_ha, 'wb_o_gr_ha': gras_o_wb_ha,
                                'wb_i_st_m3': sted_i_wb_m3, 'wb_i_hl_m3': hoogw_i_wb_m3, 'wb_i_ak_m3': akker_i_wb_m3, 'wb_i_gr_m3': gras_i_wb_m3,
                                'wb_o_st_m3': sted_o_wb_m3, 'wb_o_hl_m3': hoogw_o_wb_m3, 'wb_o_ak_m3': akker_o_wb_m3, 'wb_o_gr_m3': gras_o_wb_m3}

        # Schrijf de resultaten weg als een nieuwe tabel
        if not(gp.exists(output_waterbezwaar_tbl)):
            log.info("creating table " + output_waterbezwaar_tbl)
            gp.CreateTable(os.path.dirname(output_waterbezwaar_tbl), os.path.basename(output_waterbezwaar_tbl))

        wb_fields = [config.get('waterbezwaar', 'output_field_wb_i_m3'),
                    config.get('waterbezwaar', 'output_field_wb_i_ha'),
                    config.get('waterbezwaar', 'output_field_wb_o_m3'),
                    config.get('waterbezwaar', 'output_field_wb_o_ha'),
                    config.get('waterbezwaar', 'output_field_wb_i_st_ha'),
                    config.get('waterbezwaar', 'output_field_wb_i_hl_ha'),
                    config.get('waterbezwaar', 'output_field_wb_i_ak_ha'),
                    config.get('waterbezwaar', 'output_field_wb_i_gr_ha'),
                    config.get('waterbezwaar', 'output_field_wb_o_st_ha'),
                    config.get('waterbezwaar', 'output_field_wb_o_hl_ha'),
                    config.get('waterbezwaar', 'output_field_wb_o_ak_ha'),
                    config.get('waterbezwaar', 'output_field_wb_o_gr_ha'),
                    config.get('waterbezwaar', 'output_field_wb_i_st_m3'),
                    config.get('waterbezwaar', 'output_field_wb_i_hl_m3'),
                    config.get('waterbezwaar', 'output_field_wb_i_ak_m3'),
                    config.get('waterbezwaar', 'output_field_wb_i_gr_m3'),
                    config.get('waterbezwaar', 'output_field_wb_o_st_m3'),
                    config.get('waterbezwaar', 'output_field_wb_o_hl_m3'),
                    config.get('waterbezwaar', 'output_field_wb_o_ak_m3'),
                    config.get('waterbezwaar', 'output_field_wb_o_gr_m3')]

        table_def = nens.gp.get_table_def(gp, output_waterbezwaar_tbl)
        output_field_id = config.get('waterbezwaar', 'output_field_id')
        if not output_field_id in table_def:
            log.info(" - add field %s to %s" % (
                                output_field_id, os.path.basename(output_waterbezwaar_tbl)))
            gp.AddField(output_waterbezwaar_tbl, output_field_id, 'TEXT', "#", "#", 30)

        for double_field in wb_fields:
            if not double_field.lower() in table_def:
                log.info(" - add field %s to %s" % (
                                double_field, os.path.basename(output_waterbezwaar_tbl)))
                gp.AddField(output_waterbezwaar_tbl, double_field, 'DOUBLE')

        turtlebase.arcgis.write_result_to_output(output_waterbezwaar_tbl,
                                                 gpgident, waterbezwaar)
        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
