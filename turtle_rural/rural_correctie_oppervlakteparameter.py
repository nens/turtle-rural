# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis

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
        log.info("Getting command parameters")
        if len(sys.argv) == 3:
            input_oppervlak = sys.argv[1]
            input_gewassen = sys.argv[2]
        else:
            log.error("Usage: python rural_correctie_oppervlakken.py <RR_Oppervlak>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        log.info("Correcting parameters")
        #check fields
        opm_correc_field = 'OPM_CORREC'
        if not turtlebase.arcgis.is_fieldname(gp, input_oppervlak, opm_correc_field):
            gp.AddField(input_oppervlak, opm_correc_field, 'TEXT', '#', '#', 50)

        gpgident_field = config.get('GENERAL', 'gpgident')
        area_field = config.get('OppervlakteParameters', 'input_oppervlak_area')
        verhard_field = config.get('OppervlakteParameters', 'input_oppervlak_verhard')
        onvsted_field = config.get('OppervlakteParameters', 'input_oppervlak_onvsted')
        onvland_field = config.get('OppervlakteParameters', 'input_oppervlak_onvland')
        kassen_field = config.get('OppervlakteParameters', 'input_oppervlak_kassen')
        openwat_field = config.get('OppervlakteParameters', 'input_oppervlak_openwat')

        input_check_bound_lower = float(config.get('OppervlakteParameters', 'input_check_bound_lower'))
        input_check_bound_upper = float(config.get('OppervlakteParameters', 'input_check_bound_upper'))

        rr_oppervlak_dict = {}
        rows = gp.UpdateCursor(input_oppervlak)    
        row = rows.next()
        while row:
            ident = row.GetValue(gpgident_field)
            area = row.GetValue(area_field)
            if area is None:
                area = 0
            verhard = row.GetValue(verhard_field)
            if verhard is None:
                verhard = 0
            onvsted = row.GetValue(onvsted_field)
            if onvsted is None:
                onvsted = 0
            onvland = row.GetValue(onvland_field)
            if onvland is None:
                onvland = 0                            
            kassen = row.GetValue(kassen_field)
            if kassen is None:
                kassen = 0
            openwat = row.GetValue(openwat_field)
            if openwat is None:
                openwat = 0
            
            opm_correc = ""

            if openwat < float(config.get('OppervlakteParameters', 'input_check_min_openwater_ha')):
                openwat = float(config.get('OppervlakteParameters', 'input_check_min_openwater_ha'))

            delta = area - (verhard + onvsted + onvland + kassen + openwat)
            if delta > input_check_bound_upper or delta < input_check_bound_lower:
                if (onvland + delta) > 0:
                    onvland = onvland + delta
                    log.info("Oppervlak %s voor peilvak %s aangepast." % (onvland_field, ident))
                    opm_correc = "Oppervlak %s voor peilvak aangepast." % (onvland_field)
                elif (onvsted + onvland + delta) > 0:
                    onvsted = onvsted + onvland + delta
                    onvland = 0
                    log.info("Oppervlak %s en %s voor peilvak %s aangepast." % (onvland_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s en %s voor peilvak aangepast." % (onvland_field, onvsted_field)

                elif (kassen + onvsted + onvland + delta) > 0:
                    kassen = kassen + onvsted + onvland + delta
                    onvland = 0
                    onvsted = 0
                    log.info("Oppervlak %s, %s en %s voor peilvak %s aangepast." % (kassen_field, onvland_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s, %s en %s voor peilvak aangepast." % (kassen_field, onvland_field, onvsted_field)
                elif (verhard + kassen + onvsted + onvland + delta) > 0:
                    verhard = verhard + kassen + onvsted + onvland + delta
                    onvland = 0
                    onvsted = 0
                    kassen = 0
                    log.info("Oppervlak %s, %s, %s en %s voor peilvak %s aangepast." % (verhard_field, kassen_field, onvland_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s, %s, %s en %s voor peilvak aangepast." % (verhard_field, kassen_field, onvland_field, onvsted_field)
                else:
                    log.info("Oppervlakken voor peilvak %s niet gecorrigeerd." % ident)
            else:
                log.info("Oppervlak %s correct." % ident)

            #write output
            #in the worst case, we only fill in opm_correc. so we always update the row
            row.SetValue(area_field, area)
            row.SetValue(onvland_field, onvland)
            row.SetValue(verhard_field, verhard)
            row.SetValue(onvsted_field, onvsted)
            row.SetValue(kassen_field, kassen)
            row.SetValue(openwat_field, openwat)
            rr_oppervlak_dict[ident] = {"onverhard stedelijk": onvsted, "onverhard landelijk": onvland}

            if len(opm_correc) > 50:
                opm_correc = opm_correc[:50]

            row.SetValue(opm_correc_field, opm_correc)
            rows.UpdateRow(row)
            row = rows.next()
            
        del rows
        del row
                
        if input_gewassen != "#":
            crop_fields = [config.get('OppervlakteParameters', 'grass_area'),
                           config.get('OppervlakteParameters', 'corn_area'),
                           config.get('OppervlakteParameters', 'potatoes_area'),
                           config.get('OppervlakteParameters', 'sugarbeet_area'),
                           config.get('OppervlakteParameters', 'grain_area'),
                           config.get('OppervlakteParameters', 'miscellaneous_area'),            
                           config.get('OppervlakteParameters', 'greenhouse_area'),
                           config.get('OppervlakteParameters', 'orchard_area'),
                           config.get('OppervlakteParameters', 'bulbous_plants_area'),
                           config.get('OppervlakteParameters', 'foliage_forest_area'),
                           config.get('OppervlakteParameters', 'pine_forest_area'),
                           config.get('OppervlakteParameters', 'nature_area'),
                           config.get('OppervlakteParameters', 'fallow_area'),
                           config.get('OppervlakteParameters', 'vegetables_area'),
                           config.get('OppervlakteParameters', 'flowers_area')]
            
            nonarab_field = config.get('OppervlakteParameters', 'nonarable_land_area')
            
            rows = gp.UpdateCursor(input_gewassen)    
            row = rows.next()
            while row:
                ident = row.GetValue(gpgident_field)
                correct_onvsted_ha = float(rr_oppervlak_dict[ident]['onverhard stedelijk'])
                correct_onvland_ha = float(rr_oppervlak_dict[ident]['onverhard landelijk'])
                
                row.SetValue(nonarab_field, correct_onvsted_ha)

                total_crop_area = 0
                for crop_field in crop_fields:
                    total_crop_area += (float(row.GetValue(crop_field)))
                                        
                percentage = correct_onvland_ha / total_crop_area
                for crop_field in crop_fields:
                    original_ha = float(row.GetValue(crop_field))
                    new_ha = original_ha * percentage
                    row.SetValue(crop_field, new_ha)
                rows.UpdateRow(row)
                row = rows.next()
                
            del rows
            del row
                
        mainutils.log_footer()

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
