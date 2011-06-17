# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import nens.gp

logger = logging.getLogger(__name__)

try:
    import pylab
except ImportError:
    logger.error("pylab can not be imported, is matploblib installed?")
    sys.exit(1)


def create_cross_section_graph(gp, profile_yz, output_folder):
    """
    """
    fieldname_profile = 'PROIDENT'
    xfield = "DIST_MID"
    yfield = 'BED_LVL'
    streefpeil = 'TARGET_LVL'
    waterlevel_field = 'WATER_LVL'
    xlabeltext = 'Afstand tot midden (m)'
    ylabeltext = 'Hoogte (m NAP)'
    datum_data = 'januari 2011'

    profiles = {}

    row = gp.SearchCursor(profile_yz)
    for item in nens.gp.gp_iterator(row):
        profile_name = item.GetValue(fieldname_profile)

        x_value = item.GetValue(xfield)
        y_value = item.getValue(yfield)
        peil = item.GetValue(streefpeil)
        waterlevel = item.GetValue(waterlevel_field)

        if profile_name not in profiles:
            profiles[profile_name] = []

        profiles[profile_name].append((x_value, y_value, peil, waterlevel))

    for profile_name in profiles.keys():
        pylab.clf()
        profiles[profile_name].sort()

        x = [item[0] for item in profiles[profile_name]]
        y = [item[1] for item in profiles[profile_name]]
        peil_loc = profiles[profile_name][0][2]
        w_level = profiles[profile_name][0][3]

        #finding min en max y values
        max_y = max(y)
        min_y = min(y)
        if max_y > 9000:
            max_y = 10
        if min_y < -9000:
            min_y = -10
        #SETTING PROPER extent for drawing.
        pylab.ylim((min_y - 1, max_y + 1))

        #profilename = 'TPL_BEEMSTER_BU_1280'
        pylab.plot(x, y, linewidth=1.0, color='k', marker='.', label='profiel')
        target_x = [min(x), max(x)]
        target_y = [peil_loc, peil_loc]  # streefpeil
        pylab.plot(target_x, target_y, linewidth=2.0, color='b',
                   label='streefpeil')
        water_x = [min(x), max(x)]
        water_y = [w_level, w_level]  # streefpeil
        pylab.plot(water_x, water_y, linewidth=3.0, color='b',
                   linestyle='dashed', label='gemeten waterstand')

        pylab.xlabel(xlabeltext)
        pylab.ylabel(ylabeltext)
        pylab.legend(loc='upper center')

        pylab.title('ID Dwarsprofiel: %s \n Meting: %s' % (
                                    profile_name, datum_data))
        pylab.grid(True)
        pylab.savefig('%s\\%s.png' % (output_folder, profile_name))
