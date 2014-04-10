# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import csv
import time
import math
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis

log = logging.getLogger(__name__)

gp = mainutils.create_geoprocessor()
config = mainutils.read_config(__file__, 'turtle-settings.ini')
logfile = mainutils.log_filename(config)
logging_config = LoggingConfig(gp, logfile=logfile)
mainutils.log_header(__name__)

gpgident = config.get('GENERAL', 'gpgident').lower()
calculation_id = config.get('rrcf_waterlevel', 'calculation_point_ident').lower()
targetlevel = config.get('rrcf_waterlevel', 'field_targetlevel').lower()
maxlevel = config.get('rrcf_waterlevel', 'field_maxlevel').lower()

def calculate_waterlevel(input_hymstat, return_period_list, rekenpunten_with_levels_dict):
    '''
    input: alpha, beta, list with required x for output

    lineair function: alpha + (log(X) * beta) = Y
    X = Return period
    Y = Waterlevel
    '''
    hymstat_source = os.path.basename(input_hymstat)
    time_str = time.strftime("%d-%m-%Y %H:%M:%S")

    hymstat_list = [d for d in csv.DictReader(open(input_hymstat))]

    result = {}

    calculation_point_id = config.get('rrcf_waterlevel', 'calculation_point_ident')
    hymstat_id = config.get('rrcf_waterlevel', 'hymstat_id')
    hymstat_alpha = config.get('rrcf_waterlevel', 'hymstat_alpha')
    hymstat_beta = config.get('rrcf_waterlevel', 'hymstat_beta')
    output_targetlevel = config.get('rrcf_waterlevel', 'output_targetlevel')

    for hymstat_dict in hymstat_list:
        location = hymstat_dict[hymstat_id]
        comment = ""
        if rekenpunten_with_levels_dict.has_key(location):
            peilgebied_ident = rekenpunten_with_levels_dict[location][gpgident]
            streefpeil = rekenpunten_with_levels_dict[location][targetlevel]
            afkaphoogte = rekenpunten_with_levels_dict[location][maxlevel]

            alpha = hymstat_dict[hymstat_alpha]
            beta = hymstat_dict[hymstat_beta]
            result[location] = {calculation_point_id: location , 'date_time' : time_str, 'source': hymstat_source,
                                gpgident: peilgebied_ident, output_targetlevel: streefpeil, maxlevel: afkaphoogte}
            for return_period in return_period_list:
                if float(alpha) != -999:
                    y = float(alpha) + (float(beta) * math.log(float(return_period)))
                else:
                    y = -999

                if y > afkaphoogte:
                    y = afkaphoogte
                    if len(comment) > 0:
                        comment = comment + "; ws_%s aangepast" % return_period
                    else:
                        comment = "ws_%s aangepast" % return_period
                if y < streefpeil:
                    y = streefpeil
                    if len(comment) > 0:
                        comment = comment + "; ws_%s aangepast" % return_period
                    else:
                        comment = "ws_%s aangepast" % return_period

                result[location]["WS_%s" % return_period] = y
            result[location]['comments'] = comment
    return result


def add_field(gp, output_table, field_name, field_type):
    """
    """
    if turtlebase.arcgis.is_fieldname(gp, output_table, field_name) == False:
        log.info("create field: %s (%s)" % (field_name, field_type))
        if field_name == 'comments':
            gp.addfield_management(output_table, field_name, field_type, "#", "#", 256)
        else:
            gp.addfield_management(output_table, field_name, field_type)


def add_fields_to_output_table(output_table, fields_to_add, return_period_list):
    """
    
    """
    for field, field_type in fields_to_add.items():
        add_field(gp, output_table, field, field_type)

    for return_period in return_period_list:
        field_name = "WS_%s" % return_period
        add_field(gp, output_table, field_name, "double")

    add_field(gp, output_table, "SOURCE", "text")
    add_field(gp, output_table, "DATE_TIME", "text")
    add_field(gp, output_table, "COMMENTS", "text")


def is_key_in_dict(rekenpunten_dict, required_fields):
    """
    """
    missing_keys = []
    if rekenpunten_dict:
        first_key = rekenpunten_dict.keys()[0]
        for field in required_fields:
            if not field in rekenpunten_dict[first_key]:
                missing_keys.append(field)
    return missing_keys


def main():
    try:
        #----------------------------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 5:
            input_hymstat = sys.argv[1]
            input_rekenpunten = sys.argv[2]
            input_rr_peilgebied = sys.argv[3]
            output_table = sys.argv[4]
        else:
            log.warning("usage: <input_hymstat> <input_rekenpunten> <input_rr_peilgebied> <output_table>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # check required fields in input
        log.info("Check required fields in input data")

        missing_fields = []
        if not turtlebase.arcgis.is_fieldname(gp, input_rekenpunten, calculation_id):
            log.debug(" - missing: %s in %s" % (calculation_id, input_rekenpunten))
            missing_fields.append("%s: %s" % (input_rekenpunten, calculation_id))

        if not turtlebase.arcgis.is_fieldname(gp, input_rekenpunten, gpgident):
            log.debug(" - missing: %s in %s" % (gpgident, input_rekenpunten))
            missing_fields.append("%s: %s" % (input_rekenpunten, gpgident))

        if not turtlebase.arcgis.is_fieldname(gp, input_rr_peilgebied, gpgident):
            log.debug(" - missing: %s in %s" % (gpgident, input_rr_peilgebied))
            missing_fields.append("%s: %s" % (input_rr_peilgebied, gpgident))

        if not turtlebase.arcgis.is_fieldname(gp, input_rr_peilgebied, targetlevel):
            log.debug(" - missing: %s in %s" % (targetlevel, input_rr_peilgebied))
            missing_fields.append("%s: %s" % (input_rr_peilgebied, targetlevel))

        if not turtlebase.arcgis.is_fieldname(gp, input_rr_peilgebied, maxlevel):
            log.debug(" - missing: %s in %s" % (maxlevel, input_rr_peilgebied))
            missing_fields.append("%s: %s" % (input_rr_peilgebied, maxlevel))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        log.info("read rekenpunten table")
        rekenpunten_dict = nens.gp.get_table(gp, input_rekenpunten, primary_key=calculation_id)
        log.info("read rr_peilgebied table")
        rr_peilgebied_dict = nens.gp.get_table(gp, input_rr_peilgebied, primary_key=gpgident)

        missing_fields_in_rekenpunten = is_key_in_dict(rekenpunten_dict, [gpgident])
        if len(missing_fields_in_rekenpunten) > 0:
            log.error("missing fields in input calculation points: %s" % missing_fields_in_rekenpunten)

        missing_fields_in_rr_peilgebied = is_key_in_dict(rr_peilgebied_dict, [gpgident, targetlevel, maxlevel])
        if len(missing_fields_in_rr_peilgebied) > 0:
            log.error("missing fields in peilgebied table: %s" % missing_fields_in_rr_peilgebied)

        rekenpunten_with_levels_dict = {}
        for k, v in rekenpunten_dict.items():
            peilgebied_ident = v[gpgident]
            if rr_peilgebied_dict.has_key(peilgebied_ident):
                streefpeil = rr_peilgebied_dict[peilgebied_ident][targetlevel]
                afkaphoogte = rr_peilgebied_dict[peilgebied_ident][maxlevel]
            else:
                streefpeil = -999
                afkaphoogte = 999
            rekenpunten_with_levels_dict[k] = {gpgident: peilgebied_ident, targetlevel: streefpeil, maxlevel: afkaphoogte}

        #----------------------------------------------------------------------------------------
        return_periods = config.get('rrcf_waterlevel', 'herhalingstijden')
        return_period_list = [int(hh) for hh in return_periods.split(', ')]
        result_dict = calculate_waterlevel(input_hymstat, return_period_list, rekenpunten_with_levels_dict)

        if not gp.exists(output_table):
            gp.CreateTable_management(os.path.dirname(output_table),
                                       os.path.basename(output_table))

        fields_to_add = {calculation_id:"text", gpgident:"text", config.get('rrcf_waterlevel', 'output_targetlevel'):"double", maxlevel: "double"}
        add_fields_to_output_table(output_table, fields_to_add, return_period_list)
        turtlebase.arcgis.write_result_to_output(output_table, calculation_id, result_dict)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()

