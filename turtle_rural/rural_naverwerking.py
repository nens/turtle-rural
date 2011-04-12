# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import shutil
import os
import csv
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
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
        #check inputfields
        log.info("Getting commandline parameters... ")
        use_onderbemalingen = False
        if len(sys.argv) == 6:
            input_peilgebiedgegevens = sys.argv[1]
            input_toetspunten = sys.argv[2]
            input_resultaten = sys.argv[3]
            output_table = sys.argv[4]
            output_csv = sys.argv[5]
            use_csv = not(output_csv == '#')
        else:
            log.error("Usage: python rural_naverwerking.py <peilvakgegevens table> <toetspunten_table> <resultaten_csv> <output_table> <output_csv>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        #check input parameters
        log.info('Checking presence of input files... ')
        if not(use_csv):
            log.warning("no output has been defined, output will be written to temp workspace")
        if not(gp.exists(input_toetspunten)):
            log.error("input_toetspunten "+input_toetspunten+" does not exist!")
            sys.exit(5)
        if not(gp.exists(input_resultaten)):
            log.error("input_resultaten "+input_resultaten+" does not exist!")
            sys.exit(5)

        log.info('input parameters checked... ')

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
        log.info("A-1) Reading peilgebiedgegevens... ")
        gpgident = config.get('GENERAL', 'gpgident')
        peilgebied_dict = nens.gp.get_table(gp, input_peilgebiedgegevens, primary_key=gpgident.lower())

        log.info("A-2) Converting toetspunten to csv")
        toetspunten_csv = os.path.join(workspace, "nav_toets.csv")
        nav_toetspunten = nens.gp.join_on_primary_key(gp, peilgebied_dict, input_toetspunten, gpgident.lower())

        turtlebase.arcgis.convert_dict_to_csv(nav_toetspunten, toetspunten_csv)

        log.info("A-3) Preparing hymstat csv")
        hymstat_csv = os.path.join(workspace, "nav_hym.csv")
        #turtlebase.arcgis.convert_table_to_csv(gp, input_resultaten, hymstat_csv)
        shutil.copyfile(input_resultaten, hymstat_csv)

        #prepare naverwerking ini file
        log.info("B-1) Reading naverwerkingstool.ini... ")
        location_script = os.path.dirname(sys.argv[0])
        nav_config = mainutils.read_config(__file__, config.get('GENERAL', 'filename_naverwerking_ini'))
        configfilename = os.path.join(location_script, config.get('GENERAL', 'filename_naverwerking_ini'))

        nav_config.set('GENERAL', 'CSVTOETSPUNTEN', toetspunten_csv) #input_toetspunten
        nav_config.set('GENERAL', 'CSVINPUT1', hymstat_csv)

        #image output of naverkingstool will go to the same outputdir as the csv!! So if csv output is selected,
        #we MUST use that output-csv as the intermediate csv too
        if use_csv:
            log.info(" - using csv")
            if not output_csv.endswith('.csv'):
                output_csv += '.csv'
            nav_config.set('GENERAL', 'CSVOUTPUT1', output_csv)
        else:
            log.info(" - not using csv")
            output_csv = os.path.join(workspace, "nav_output.csv")
            nav_config.set('GENERAL', 'CSVOUTPUT1', output_csv)

        nav_config.set('GENERAL', 'CSVINPUT2', '')
        nav_config.set('GENERAL', 'CSVOUTPUT2', '')
        configfile = open(configfilename, "wb")
        nav_config.write(configfile)
        configfile.close()

        #----------------------------------------------------------------------------------------
        #call naverwerkingstool
        arguments = ""

        #change working path to exe directory
        os.chdir(location_script)

        #execute external program gridbewerking
        log.info("Naverwerking calculation")

        import subprocess
        naverwerking_exe = config.get('GENERAL', 'filename_naverwerking_exe')
        child = subprocess.Popen(os.path.join(location_script, naverwerking_exe) + arguments)
        child.wait()
        log.info("naverwerking.exe succesfully executed")

        """
        HIERONDER ALLES HERSCHRIJVEN
        """
        #----------------------------------------------------------------------------------------
        #post: write to database, table and/or csv
        log.info("C-1) Reading output csv")
        data_set = csv.DictReader(file(output_csv))

        #name is same as key is nothing is given; key is columnname from csv
        #alle velden die niet hier voorkomen, hoeven niet van naam worden veranderd en zijn van het type "long", precision 10, scale 5
        naverwerkingFields = {\
            gpgident: {"NAME": gpgident, "TYPE": "TEXT", "PRECISION": "10", "SCALE": "5", "LENGTH": "50"},\
            "X0": {"NAME": "X0", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "B": {"NAME": "B", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_2": {"NAME": "WS_2", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_5": {"NAME": "WS_5", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_10": {"NAME": "WS_10", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_15": {"NAME": "WS_15", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_20": {"NAME": "WS_20", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_25": {"NAME": "WS_25", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_50": {"NAME": "WS_50", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "WS_100": {"NAME": "WS_100", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_I_S": {"NAME": "STA_TP_I_ST", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_I_H": {"NAME": "STA_TP_I_HL", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_I_A": {"NAME": "STA_TP_I_AK", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_I_G": {"NAME": "STA_TP_I_GR", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_O_S": {"NAME": "STA_TP_O_ST", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_O_H": {"NAME": "STA_TP_O_HL", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_O_A": {"NAME": "STA_TP_O_AK", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "STA_TP_O_G": {"NAME": "STA_TP_O_GR", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "T_I": {"NAME": "T_I", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "T_O": {"NAME": "T_O", "TYPE": "DOUBLE", "PRECISION": "10", "SCALE": "5"},\
            "RSLT_Bron": {"NAME": "RSLT_Bron", "TYPE": "TEXT", "LENGTH": "50", "PRECISION": "10", "SCALE": "5"},\
            "RSLT_Datum": {"NAME": "RSLT_Datum", "TYPE": "DATE", "PRECISION": "10", "SCALE": "5"},\
            }

        #convert columnnames in data_set
        data_set_converted = {}
        source_str = "hymstat: %s" % os.path.basename(input_resultaten)
        if len(source_str) > 50:
            source_str = source_str[:50]
        import time
        date_str = time.strftime('%x')

        for row in data_set:
            peilgebied_id = row['PEILVAKID']
            data_set_converted[peilgebied_id] = {gpgident: peilgebied_id}
            for key in row.keys():
                if key in naverwerkingFields:
                    data_set_converted[peilgebied_id][naverwerkingFields[key]["NAME"]] = row[key]

            data_set_converted[peilgebied_id]["RSLT_Bron"] = source_str
            data_set_converted[peilgebied_id]["RSLT_Datum"] = date_str

        #----------------------------------------------------------------------------------------
        #check if output_table exists. if not, create with correct rows
        log.info("C-2) Checking output table... ")
        if not(gp.exists(output_table)):
            gp.CreateTable(os.path.dirname(output_table), os.path.basename(output_table))

        #----------------------------------------------------------------------------------------
        #for key,row in naverwerkingFields.items():
        #	print row["NAME"]+" "+row["TYPE"]+" "+row["PRECISION"]+" "+row["SCALE"]
        #check if output_table has the correct rows
        log.info("C-3) Checking fields")
        for field_name, field_settings in naverwerkingFields.items():
            if not turtlebase.arcgis.is_fieldname(gp, output_table, field_settings['NAME']):
                if field_settings['TYPE'] == 'DOUBLE':
                    gp.AddField(output_table, field_settings['NAME'], field_settings['TYPE'], field_settings['PRECISION'], field_settings['SCALE'])
                elif field_settings['TYPE'] == 'TEXT':
                    gp.AddField(output_table, field_settings['NAME'], field_settings['TYPE'], '#', '#', field_settings['LENGTH'])
                else:
                    gp.AddField(output_table, field_settings['NAME'], field_settings['TYPE'], field_settings['PRECISION'], field_settings['SCALE'])

        # ---------------------------------------------------------------------------
        #add data to file_output
        turtlebase.arcgis.write_result_to_output(output_table, gpgident, data_set_converted)

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        if os.path.isfile(toetspunten_csv):
            os.remove(toetspunten_csv)
        if os.path.isfile(hymstat_csv):
            os.remove(hymstat_csv)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
