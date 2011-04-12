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

# Create the Geoprocessor object
gp = arcgisscripting.create()

# Read inifile
# Settings for all turtle tools
script_full_path = sys.argv[0] #get absolute path of running script
location_script = os.path.abspath(os.path.dirname(script_full_path))+"\\"
ini_file = location_script + 'turtle-settings.ini'

# Use configparser to read ini file
config = ConfigParser.SafeConfigParser()
config.read(ini_file)

gpg_cluster = config.get('afvoerendoppervlak', 'gpg_cluster')
gpg_source = config.get('afvoerendoppervlak', 'gpg_source')
gpg_date = config.get('afvoerendoppervlak', 'gpg_date')
gpg_opp = config.get('afvoerendoppervlak', 'gpg_opp').lower()
gpgident = config.get('GENERAL', 'gpgident').lower()
kwkident = config.get('GENERAL', 'kwkident').lower()
kwk_cap = config.get('afvoerendoppervlak', 'kwk_cap').lower()
kwk_cap_h = config.get('afvoerendoppervlak', 'kwk_cap_h').lower()
boundary_str = config.get('afvoerendoppervlak', 'boundary_str')
afvoer_van = config.get('afvoerendoppervlak', 'afvoer_van').lower()
afvoer_naar = config.get('afvoerendoppervlak', 'afvoer_naar').lower()
afvoer_percentage = config.get('afvoerendoppervlak', 'afvoer_percentage').lower()
gpg_depth = config.get('afvoerendoppervlak', 'gpg_depth')
kwk_kwerk = config.get('afvoerendoppervlak', 'kwk_kwerk').lower()
kwk_keyword_gemaal = config.get('afvoerendoppervlak', 'kwk_keyword_gemaal')
kwk_keyword_stuw = config.get('afvoerendoppervlak', 'kwk_keyword_stuw')
kwk_stuw_breedte = config.get('afvoerendoppervlak', 'kwk_stuw_breedte')
kwk_stuw_cap_per_cm = config.get('afvoerendoppervlak', 'kwk_stuw_cap_per_cm')
gpg_afvoerendoppervlak = config.get('afvoerendoppervlak', 'gpg_afvoerendoppervlak')
gpg_afvoercap_ha = config.get('afvoerendoppervlak', 'gpg_afvoercap_ha')

def calc_afv_opp_rec (gpg_ident, kwk_base, oppervlak_data, afvoer_data, pg_data_output, pg_passed, pg_route, pg_loops):
    '''
    calculate afvoerend oppervlak in a recursive way; handles cycles as well
    '''
    try:
        #the afvoerend opp has already been calculated for this pg
        pg_passed[value[afvoer_van]][kwk_base] = 1 # if this doesn't work, the key value[ini['afvoer_van']] does not exist and we go the the except part
        return pg_data_output[gpg_ident][gpg_afvoerendoppervlak]
    except:
        log.debug(" summing for "+gpg_ident)
        #we must calculate it now
        sum_from = 0
        #search for kw's from, and calc sum_from
        for kwk_ident, value in afvoer_data.items():
            if value[afvoer_naar] == gpg_ident:
                if not(pg_passed.has_key(value[afvoer_van])):
                    pg_passed[value[afvoer_van]] = {}
                #if not(pg_passed[value[ini['afvoer_van']]].has_key(kwk_base)):
                try:
                    #try to find afvoer_van in pg_route.
                    #if it succeeds, the node has been visited already and there is a cycle
                    a = pg_route.index(value[afvoer_van])
                    #uncomment this can cause almost-infinite-loop
                    log.debug(" - Warning: cycle, ignoring second time gpg_ident "+value[afvoer_van]+" on kwk_ident boundary "+kwk_base)
                    pg_loops[value[afvoer_van]] = 1
                except:
                    #this is the normal flow
                    pg_passed[value[afvoer_van]][kwk_base] = 1
                    perc = value[afvoer_percentage]
                    pg_route.append(value[afvoer_van])
                    sum_from += perc/100*calc_afv_opp_rec (value[afvoer_van], kwk_base, oppervlak_data, afvoer_data, pg_data_output, pg_passed, pg_route, pg_loops)
                    pg_route.pop() #delete last item

        opp = oppervlak_data[gpg_ident][gpg_opp] + sum_from

        pg_data_output[gpg_ident] = {gpgident: gpg_ident, gpg_afvoerendoppervlak: opp}

        return opp


def debuglogging():
    log.debug("sys.path: %s" % sys.path)
    log.debug("os.environ: %s" % os.environ)
    log.debug("path turtlebase.arcgis: %s" % turtlebase.arcgis.__file__)
    log.debug("revision turtlebase.arcgis: %s" % turtlebase.arcgis.__revision__)
    log.debug("path turtlebase.general: %s" % turtlebase.general.__file__)
    log.debug("revision turtlebase.general: %s" % turtlebase.general.__revision__)
    log.debug("path arcgisscripting: %s" % arcgisscripting.__file__)


def main():
    try:
        # Create the Geoprocessor object
        gp = arcgisscripting.create()
        gp.RefreshCatalog
        gp.OverwriteOutput = 1

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
        #check inputfields
        log.info("Getting commandline parameters")
        if len(sys.argv) == 4:
            input_oppervlak = sys.argv[1]
            input_afvoer = sys.argv[2]
            output_peilgebied = sys.argv[3]

            log.info("input oppervlak: %s" % input_oppervlak)
            log.info("input afvoer: %s" % input_afvoer)
            log.info("output peilgebied: %s" % output_peilgebied)
        else:
            log.error("Usage: python rural_afvoerendoppervlak.py <rr_oppervlak> <rr_afvoer> <output rr_peilgebied>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        log.info("A-1) Read RR_Oppervlak")
        oppervlak_data = nens.gp.get_table(gp, input_oppervlak, primary_key=gpgident)

        if len(oppervlak_data.keys()) == 0:
            log.error("RR_Oppervlak is empty! The RR_Oppervlak is required by this tool.")
            sys.exit(2)

        log.info("A-2) Read RR_Afvoer")
        afvoer_data = nens.gp.get_table(gp, input_afvoer, primary_key=kwkident)
        if len(afvoer_data.keys()) == 0:
            log.error("RR_Afvoer is empty! The RR_Afvoer is required by this tool.")
            sys.exit(2)

        log.info("B) loop boundaries")
        #check used fields for existence
        log.info(" - checking RR_Afvoer...")
        #column ini['kwk_cap'] must exist
        #column ini['kwk_cap_h'] must exist
        #take first item and check...
        #print afvoer_data.items()[0][1]
        if not turtlebase.arcgis.is_fieldname(gp, input_afvoer, kwk_cap):
            log.error("RR_Afvoer does not have column %s" % kwk_cap)
            sys.exit(3)
        if not turtlebase.arcgis.is_fieldname(gp, input_afvoer, kwk_cap_h):
            log.error("RR_Afvoer does not have column %s" % kwk_cap_h)
            sys.exit(3)

        #cluster_counter = 1
        #format: pg_passed[gpg_ident] = {kw_ident1: 1, kw_ident2: 1, kw_ident3: 1, ...}
        pg_passed = {}
        #pg_data_output has columns afv_gpg, afv_dtm, afv_bron, cp_afv_gpg, gpg_clstr, gpg_trap
        pg_data_output = {}

        #add afv_gpg, gpg_clstr, gpg_trap
        #afv_gpg = opp_current + sum(kw_perc*opp_from)
        #afv_trap = depth

        #ini['gpg_cluster']: 'cluster_'+str(cluster)

        log.info(" - calculate afv_gpg")
        pg_data_depth = {} #keep track of depth; here we insert the "starting points" for floodfill algorithm
        for kwk_ident, value in afvoer_data.items():
            if value[afvoer_naar] == boundary_str:
                #recursive function to calculate afvoerend oppervlak,
                #-track all passing peilgebieden
                #-track kwk_ident of boundaries in each passing peilgebied in pg_passed
                log.info("    boundary: %s = %s" % (kwkident, kwk_ident))
                pg_passed[value[afvoer_van]] = {}
                pg_passed[value[afvoer_van]][kwk_ident] = 1
                pg_data_depth[value[afvoer_van]] = 1
                pg_loops = {}
                calc_afv_opp_rec (value[afvoer_van], kwk_ident, oppervlak_data, afvoer_data, pg_data_output, pg_passed, [value[afvoer_van]], pg_loops)
                if len(pg_loops.keys()) > 0:
                    log.warning("    loops found: "+str(pg_loops.keys()))
                #cluster_counter += 1 #klopt nog niet igv meerdere boundaries in 1 cluster

        #calculate depth
        log.info(" - calculate gpg_trap")
        #"floodfill" from the boundaries. all pg's in in pg_data_output; done pg's in pg_data_depth
        changed = True
        while changed:
            changed = False
            for gpg_ident in pg_data_output.keys():
                #check if this gpg_ident is neighboring any pg that has already a depth
                #so loop afvoer_data to search the gpg_ident in afvoer_naar
                for kw in afvoer_data.values():
                    if kw[afvoer_naar] == gpg_ident:
                        #we found the gpg_ident == afvoer_naar
                        if pg_data_depth.has_key(kw[afvoer_naar]) and not (pg_data_depth.has_key(kw[afvoer_van])):
                            pg_data_depth[kw[afvoer_van]] = pg_data_depth[kw[afvoer_naar]] + 1
                            log.debug(gpg_ident + " -> depth " + str(pg_data_depth[kw[afvoer_naar]] + 1))
                            changed = True
        #convert pg_data_depth to str in pg_data_output
        for gpg_ident, value in pg_data_depth.items():
            pg_data_output[gpg_ident][gpg_depth] = 'trap_%s' % value

        log.debug("pg_data_output: "+str(pg_data_output))
        log.debug("afvoer_data: "+str(afvoer_data))

        log.info(" - calculate cp_afv_gpg")
        #add cp_afv_gpg. cp_afv_gpg = sum(kw_boundary)/hectares
        for gpg_ident, value in pg_passed.items():
            #sum_cap = 0
            #these kwk_idents are the boundaries
            sum_cap_per_ha = 0
            for kwk_ident in value.keys():
                if afvoer_data[kwk_ident][kwk_kwerk] == kwk_keyword_gemaal:
                    cap_single = max(afvoer_data[kwk_ident][kwk_cap],afvoer_data[kwk_ident][kwk_cap_h])
                elif afvoer_data[kwk_ident][kwk_kwerk] == kwk_keyword_stuw:
                    #log.debug(afvoer_data[kwk_ident][ini['kwk_stuw_breedte']])
                    #log.debug("ini['kwk_stuw_cap_per_cm']: "+str(ini['kwk_stuw_cap_per_cm']))
                    cap_single = 100*afvoer_data[kwk_ident][kwk_stuw_breedte]*float(kwk_stuw_cap_per_cm)
                    log.debug("  - calculate virtual capacity of stuw: "+kwk_ident+" cap "+str(cap_single))
                else:
                    #warning: what is this kind of type?
                    print " Warning: unknown type for ["+kwkident+" = "+kwk_ident+", field ["+kwk_kwerk+"] = "+afvoer_data[kwk_ident][kwk_kwerk]
                    cap_single = max(afvoer_data[kwk_ident][kwk_cap],afvoer_data[kwk_ident][kwk_cap_h])
                ha_single = pg_data_output[afvoer_data[kwk_ident][afvoer_van]][gpg_afvoerendoppervlak]
                log.debug(" cap "+kwk_ident+":"+str(cap_single))
                #sum_cap += cap_single
                log.debug(" kwk_ident:"+kwk_ident+" "+ str(cap_single)+"/"+str(ha_single))
                sum_cap_per_ha += cap_single/ha_single
            #pg_data_output[gpg_ident][ini['gpg_afvoercap_ha']] = sum_cap/pg_data_output[gpg_ident][ini['gpg_afvoerendoppervlak']]
            pg_data_output[gpg_ident][gpg_afvoercap_ha] = sum_cap_per_ha

        log.info(" - calculate clusters")

        log.debug("pg_passed: %s" % pg_passed)

        #construct cluster conversion dictionary
        cluster_conversion = {} #from old id to new id
        for value in pg_passed.values():
            #check if there is already a dictionary item for one of the elements, then pick that one, else pick first item
            for int_id in value.keys():
                if cluster_conversion.has_key(int_id):
                    new_int_id = cluster_conversion[int_id]
                    break
            else:
                #when no existing int_id has been found, we pick a new one
                new_int_id = value.keys()[0] #just pick one item, it does not matter which one
            for int_id in value.keys():
                if not(cluster_conversion.has_key(int_id)):
                    cluster_conversion[int_id] = new_int_id

        for gpg_ident in pg_passed.keys():
            pg_data_output[gpg_ident][gpg_cluster] = 'cluster_'+cluster_conversion[pg_passed[gpg_ident].keys()[0]]

        log.info(" - add date and source")
        #add adv_dtm, afv_bron (it's all the same)
        import time
        date_str = time.strftime('%x')
        source_str = "opp:"+os.path.dirname(input_oppervlak)+" afv:"+os.path.dirname(input_afvoer)
        if len(source_str) > 50:
            source_str = source_str[-50:]
        for gpg_ident in pg_data_output.keys():
            pg_data_output[gpg_ident][gpg_source] = source_str
            pg_data_output[gpg_ident][gpg_date] = date_str


        log.debug("pg_data_output: "+str(pg_data_output))
        fieldsOpp = {gpg_afvoerendoppervlak: {'type': 'Double'},\
                                gpg_cluster: {'type': 'TEXT', 'length': '50'},\
                                gpg_afvoercap_ha: {'type': 'Double'},\
                                gpg_depth: {'type': 'TEXT', 'length': '50'},\
                                gpg_source: {'type': 'TEXT', 'length': '50'},\
                                gpg_date: {'type': 'TEXT'}}

        log.info("C) writing to output")
        log.info(pg_data_output)
        for fieldname, values in fieldsOpp.items():
            if not turtlebase.arcgis.is_fieldname(gp, output_peilgebied, fieldname):
                gp.AddField_management(output_peilgebied, fieldname, values['type'])

        turtlebase.arcgis.write_result_to_output(output_peilgebied, gpgident, pg_data_output)

        log.info("*********************************************************")
        log.info("Finished")
        log.info("*********************************************************")

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
