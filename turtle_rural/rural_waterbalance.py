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


def max_gpg(tuples_list):
    """
    """
    main_gpg = ""
    max_area = 0
    sum_area = 0

    for peilgebied in tuples_list:
        sum_area += peilgebied[1]
        if peilgebied[1] > max_area:
            main_gpg = peilgebied[0]
            max_area = peilgebied[1]

    return main_gpg, sum_area


def sort_bodemsoorten(gp, intersect_bodem, gafident):
    """
    """
    bodem_table = nens.gp.get_table(gp, intersect_bodem)
    #log.info(bodem_table)


def weighted_average_seepage(kwelwegzijging, gafident):
    """
    """




def translate_soiltypes(bod1_int, bod2_int, bod3_int):
    """
    """
    soildict = {1: 'Veengrond met veraarde bovengrond', 2: 'Veengrond met veraarde bovengrond, zand',
                3: 'Veengrond met kleidek', 4: 'Veengrond met kleidek op zand',
                5: 'Veengrond met zanddek op zand', 6: 'Veengrond op ongerijpte klei',
                7: 'Stuifzand', 8: 'Podzol (Leemarm, fijn zand)', 9: 'Podzol (zwak lemig, fijn zand)',
                10: 'Podzol (zwak lemig, fijn zand op grof zand)', 11: 'Podzol (lemig keileem)',
                12: 'Enkeerd (zwak lemig, fijn zand)', 13: 'Beekeerd (lemig fijn zand)',
                14: 'Podzol (grof zand)', 15: 'Zavel', 16: 'Lichte klei', 17: 'Zware klei',
                18: 'Klei op veen', 19: 'Klei op zand', 20: 'Klei op grof zand', 21: 'Leem'}

    if bod1_int in range(20):

        bod1 = soildict[bod1_int]
    else:
        bod1 = bod1_int
    if bod2_int in range(20):
        bod2 = soildict[bod2_int]
    else:
        bod2 = bod2_int
    if bod3_int in range(20):
        bod3 = soildict[bod3_int]
    else:
        bod3 = bod3_int

    return bod1, bod2, bod3

def calculate_soiltypes(tuples_list):
    """
    """
    soiltypes = {}
    bod1 = ["-999", 0]
    bod2 = ["-999", 0]
    bod3 = ["-999", 0]

    for peilgebied in tuples_list:
        grondsoort = peilgebied[8]
        oppervlak = peilgebied[10]
        if grondsoort in soiltypes:
            soiltypes[grondsoort] += oppervlak
        else:
            soiltypes[grondsoort] = oppervlak

    for soiltype, area in soiltypes.items():
        if area > bod1[1]:
            bod1[0] = soiltype
            bod1[1] = area
    del soiltypes[bod1[0]]

    if len(soiltypes) >= 1:
        for soiltype, area in soiltypes.items():
            if area > bod2[1]:
                bod2[0] = soiltype
                bod2[1] = area
        del soiltypes[bod2[0]]

    if len(soiltypes) >= 1:
        for soiltype, area in soiltypes.items():
            if area > bod3[1]:
                bod3[0] = soiltype
                bod3[1] = area
        del soiltypes[bod3[0]]

    return bod1[0], bod2[0], bod3[0]


def calculate_averages(tuples_list, total_area):
    """
    calculate 
    - grondsoort
    - kwelstroom
    - stedelijk verhard
    - stedelijk onverhard
    - kassen
    - gras
    - natuur
    - water
    """
    kwelstroom = 0
    verhard_ha = 0
    onvsted_ha = 0
    kassen_ha = 0
    openwat_ha = 0
    gras_ha = 0
    natuur_ha = 0

    for peilgebied in tuples_list:
        factor = float(peilgebied[1]) / float(total_area)
        kwelstroom += (factor * peilgebied[9])
        verhard_ha += peilgebied[2]
        onvsted_ha += peilgebied[3]
        kassen_ha += peilgebied[4]
        openwat_ha += peilgebied[5]
        gras_ha += peilgebied[6]
        natuur_ha += peilgebied[7]

    return kwelstroom, verhard_ha, onvsted_ha, kassen_ha, openwat_ha, gras_ha, natuur_ha


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 5:
            hydrobase = sys.argv[1]
            input_kwelkaart = sys.argv[2]
            input_bodemkaart = sys.argv[3]
            output_waterbalance = sys.argv[4]
        else:
            log.error("usage: <hydrobase> <input_kwelkaart> <input_bodemkaart> <output_waterbalance>")
            sys.exit(1)

        peilgebieden_fc = os.path.join(hydrobase, 'RR_Features', 'PeilGebieden')
        rr_peilgebied = os.path.join(hydrobase, 'RR_Peilgebied')
        rr_grondsoort = os.path.join(hydrobase, 'RR_Grondsoort')
        rr_kwelwegzijging = os.path.join(hydrobase, 'RR_KwelWegzijging')
        rr_oppervlak = os.path.join(hydrobase, 'RR_Oppervlak')

        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        #check_fields = {}
        gpgident = config.get("general", "gpgident").lower()
        gafident = config.get("waterbalance", "gafident").lower()
        gafnaam = config.get("waterbalance", "gafnaam").lower()

        check_fields = {peilgebieden_fc: [gpgident, gafident, gafnaam],
                         rr_peilgebied: [gpgident, "zomerpeil", "winterpeil"]}
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

        nr_peilgebied = turtlebase.arcgis.fc_records(gp, rr_peilgebied)
        nr_grondsoort = turtlebase.arcgis.fc_records(gp, rr_grondsoort)
        nr_kwelwegzijging = turtlebase.arcgis.fc_records(gp, rr_kwelwegzijging)
        nr_oppervlak = turtlebase.arcgis.fc_records(gp, rr_oppervlak)

        table_cnts = {rr_peilgebied: nr_peilgebied, rr_grondsoort: nr_grondsoort,
                      rr_kwelwegzijging: nr_kwelwegzijging, rr_oppervlak: nr_oppervlak}

        for table, table_cnt in table_cnts.items():
            if not table_cnt == nr_gpg:
                log.error("%s (%s records) does not contain the same amount of records as %s (%s)" % (table, table_cnt,
                                                                                                      peilgebieden_fc, nr_gpg))
                errorcode += 1

        if errorcode > 0:
            log.error("%s errors found, see above" % errorcode)
            sys.exit(1)

        log.info("Join tables")
        log.info(" - read %s" % peilgebieden_fc)
        peilgebieden = nens.gp.get_table(gp, peilgebieden_fc, primary_key=gpgident, no_shape=True)
        log.info(" - join %s" % rr_peilgebied)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_peilgebied, gpgident)
        log.info(" - join %s" % rr_grondsoort)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_grondsoort, gpgident)
        log.info(" - join %s" % rr_kwelwegzijging)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_kwelwegzijging, gpgident)
        log.info(" - join %s" % rr_oppervlak)
        nens.gp.join_on_primary_key(gp, peilgebieden, rr_oppervlak, gpgident)

        required_keys = ["grondsoort", "verhard_ha", "onvsted_ha", "kassen_ha",
                         "openwat_ha", "gras_ha", "natuur_ha", "zomerpeil",
                         "winterpeil", "kwelstroom", "shape_area", "hectares"]


        #---------------------------------------------------------------------
        # Calculate Kwel/Wegzijging
        if input_kwelkaart == '#' == input_bodemkaart:
            pass
        else:
            workspace = config.get('GENERAL', 'location_temp')

            turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

            if not os.path.isdir(workspace):
                os.makedirs(workspace)
            workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
            if errorcode == 1:
                log.error("failed to create a file geodatabase in %s" % workspace)

            if input_kwelkaart != '#':
                # Check out Spatial Analyst extension license
                gp.CheckOutExtension("Spatial")

                kwel_table = os.path.join(workspace_gdb, 'kwel_zs_table')
                gp.ZonalStatisticsAsTable_sa(peilgebieden_fc, gpgident, input_kwelkaart, kwel_table, "NODATA")
                kwelwegzijging = nens.gp.get_table(gp, kwel_table, primary_key=gpgident, no_shape=True)

                log.info(kwelwegzijging)

            if input_bodemkaart != '#':
                temp_bodemsoort = os.path.join(workspace_gdb, "temp_bodem")
                gp.select_analysis(input_bodemkaart, temp_bodemsoort)
                temp_peilgebied = os.path.join(workspace_gdb, "temp_peilgebied")
                gp.select_analysis(peilgebieden_fc, temp_peilgebied)
                intersect_bodem = os.path.join(workspace_gdb, "intersect_bodem")
                gp.Intersect_analysis("%s;%s" % (temp_peilgebied, temp_bodemsoort), intersect_bodem)

                bodemsoorten_polders = sort_bodemsoorten(gp, intersect_bodem, gafident)

        #---------------------------------------------------------------------
        # Waterbalance
        polders = {}
        log.info("Extract data for waterbalance")
        for k, v in peilgebieden.items():
            for required_key in required_keys:
                if required_key not in v.keys():
                    log.error("Cannot find %s for gpgident: %s" % (required_key, k))
                    sys.exit(1)

            if v[gafident] in polders:
                polders[v[gafident]]["peilgebieden"].append((k, v["shape_area"], v["verhard_ha"], v["onvsted_ha"], v["kassen_ha"],
                                                             v["openwat_ha"], v["gras_ha"], v["natuur_ha"], v['grondsoort'], v['kwelstroom'], v['hectares']))
            else:
                polders[v[gafident]] = {"peilgebieden": [(k, v["shape_area"], v["verhard_ha"], v["onvsted_ha"], v["kassen_ha"],
                                                          v["openwat_ha"], v["gras_ha"], v["natuur_ha"], v['grondsoort'], v['kwelstroom'], v['hectares'])]}

        waterbalance = {}
        log.info("Calculate data for waterbalance")
        for polder, attributes in polders.items():
            main_gpg, sum_area = max_gpg(attributes['peilgebieden'])
            kwelstroom, verhard_ha, onvsted_ha, kassen_ha, openwat_ha, gras_ha, natuur_ha = calculate_averages(attributes['peilgebieden'], sum_area)
            bod1_int, bod2_int, bod3_int = calculate_soiltypes(attributes['peilgebieden'])
            bod1, bod2, bod3 = translate_soiltypes(bod1_int, bod2_int, bod3_int)
            if input_kwelkaart != '#':
                kwelstroom = kwelwegzijging[polder]['mean']

            if kwelstroom > 0:
                kwel = kwelstroom
                wegz = 0
            else:
                wegz = -1 * kwelstroom
                kwel = 0

            winterp = peilgebieden[main_gpg]['winterpeil']
            zomerp = peilgebieden[main_gpg]['zomerpeil']
            sum_ha = sum_area / 10000
            waterbalance[polder] = [("Code", polder, "TEXT"), ("Naam", polder, "TEXT"),
                                    ("Main_GPG", main_gpg, "TEXT"), ("Bodemh", -999, "DOUBLE"),
                                    ("Kwel", kwel, "DOUBLE"), ("Wegz", wegz, "DOUBLE"),
                                    ("Winterpeil", winterp, "DOUBLE"), ("Zomerpeil", zomerp, "DOUBLE"),
                                    ("Totaal_ha", sum_ha, "DOUBLE"), ("Verhard_ha", verhard_ha, "DOUBLE"),
                                    ("Onvsted_ha", onvsted_ha, "DOUBLE"), ("Kassen_ha", kassen_ha, "DOUBLE"),
                                    ("Openwat_ha", openwat_ha, "DOUBLE"), ("Gras_ha", gras_ha, "DOUBLE"),
                                    ("Natuur_ha", natuur_ha, "DOUBLE"), ("Bodem1", bod1, "TEXT"),
                                    ("Bodem2", bod2, "TEXT"), ("Bodem3", bod3, "TEXT")]

        log.info("Write output table")
        gp.CreateTable(os.path.dirname(output_waterbalance), os.path.basename(output_waterbalance))
        for key, values in waterbalance.items():
            for attribute in values:
                log.info(" - add field %s" % attribute[0])
                gp.AddField(output_waterbalance, attribute[0], attribute[2])
            break

        log.info("Inserting new records")
        update_count = 0
        nsertCursor = gp.InsertCursor(output_waterbalance)
        for key, values in waterbalance.items():
            newRow = nsertCursor.NewRow()
            for attribute in values:
                newRow.SetValue(attribute[0], attribute[1])
            nsertCursor.InsertRow(newRow)
            update_count += 1

        log.info(" - %s records have been inserted" % update_count)
        log.info("Finished")

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
