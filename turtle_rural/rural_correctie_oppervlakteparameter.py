# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.filenames
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
        log.info("Getting command parameters")
        if len(sys.argv) == 2:
            input_oppervlak = sys.argv[1]
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
        area_field = config.get('controlerenoppervlakken', 'input_oppervlak_area')
        verhard_field = config.get('controlerenoppervlakken', 'input_oppervlak_verhard')
        onvsted_field = config.get('controlerenoppervlakken', 'input_oppervlak_onvsted')
        gras_field = config.get('controlerenoppervlakken', 'input_oppervlak_gras')
        natuur_field = config.get('controlerenoppervlakken', 'input_oppervlak_natuur')
        #onvland_field = config.get('controlerenoppervlakken', 'input_oppervlak_onvland')
        kassen_field = config.get('controlerenoppervlakken', 'input_oppervlak_kassen')
        openwat_field = config.get('controlerenoppervlakken', 'input_oppervlak_openwat')

        input_check_bound_lower = float(config.get('controlerenoppervlakken', 'input_check_bound_lower'))
        input_check_bound_upper = float(config.get('controlerenoppervlakken', 'input_check_bound_upper'))

        rows = gp.UpdateCursor(input_oppervlak)
        for row in nens.gp.gp_iterator(rows):
            ident = row.GetValue(gpgident_field)
            area = row.GetValue(area_field)
            verhard = row.GetValue(verhard_field)
            onvsted = row.GetValue(onvsted_field)
            gras = row.GetValue(gras_field)
            natuur = row.GetValue(natuur_field)
            #onvland = row.GetValue(onvland_field)
            kassen = row.GetValue(kassen_field)
            openwat = row.GetValue(openwat_field)

            opm_correc = ""

            if openwat < float(config.get('controlerenoppervlakken', 'input_check_min_openwater_ha')):
                openwat = float(config.get('controlerenoppervlakken', 'input_check_min_openwater_ha'))

            delta = area - (verhard + onvsted + gras + natuur + kassen + openwat)
            if delta > input_check_bound_upper or delta < input_check_bound_lower:
                if (natuur + delta) > 0:
                    natuur = natuur + delta
                    log.info("Oppervlak %s voor peilvak %s aangepast." % (natuur_field, ident))
                    opm_correc = "Oppervlak %s voor peilvak aangepast." % natuur_field
                elif (natuur + gras + delta) > 0:
                    gras = gras + natuur + delta
                    natuur = 0
                    log.info("Oppervlak %s en %s voor peilvak %s aangepast." % (gras_field, natuur_field, ident))
                    opm_correc = "Oppervlak %s en %s voor peilvak aangepast." % (natuur_field, gras_field)
                elif (onvsted + gras + natuur + delta) > 0:
                    onvsted = onvsted + gras + natuur + delta
                    gras = 0
                    natuur = 0
                    log.info("Oppervlak %s, %s en %s voor peilvak %s aangepast." % (gras_field, natuur_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s, %s en %s voor peilvak aangepast." % (natuur_field, gras_field, onvsted_field)

                elif (kassen + onvsted + gras + natuur + delta) > 0:
                    kassen = kassen + onvsted + gras + natuur + delta
                    gras = 0
                    natuur = 0
                    onvsted = 0
                    log.info("Oppervlak %s, %s, %s en %s voor peilvak %s aangepast." % (kassen_field, gras_field, natuur_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s, %s, %s en %s voor peilvak aangepast." % (kassen_field, gras_field, natuur_field, onvsted_field)
                elif (verhard + kassen + onvsted + gras + natuur + delta) > 0:
                    verhard = verhard + kassen + onvsted + gras + natuur + delta
                    gras = 0
                    natuur = 0
                    onvsted = 0
                    kassen = 0
                    log.info("Oppervlak %s, %s, %s, %s en %s voor peilvak %s aangepast." % (verhard_field, kassen_field, gras_field, natuur_field, onvsted_field, ident))
                    opm_correc = "Oppervlak %s, %s, %s, %s en %s voor peilvak aangepast." % (verhard_field, kassen_field, gras_field, natuur_field, onvsted_field)
                else:
                    log.info("Oppervlakken voor peilvak %s niet gecorrigeerd." % ident)
            else:
                log.info("Oppervlak %s correct." % ident)

            #write output
            #in the worst case, we only fill in opm_correc. so we always update the row
            row.SetValue(area_field, area)
            row.SetValue(gras_field, gras)
            row.SetValue(natuur_field, natuur)
            row.SetValue(verhard_field, verhard)
            row.SetValue(onvsted_field, onvsted)
            row.SetValue(kassen_field, kassen)
            row.SetValue(openwat_field, openwat)

            if len(opm_correc) > 50:
                opm_correc = opm_correc[:50]

            row.SetValue(opm_correc_field, opm_correc)
            rows.UpdateRow(row)
        mainutils.log_footer()

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
