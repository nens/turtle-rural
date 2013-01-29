#!/usr/bin/python
# -*- coding: utf-8 -*-
#******************************************************************************
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This script is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this script.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2011 Nelen & Schuurmans
#
#******************************************************************************
#
# Initial programmer: Mario Frasca
# Initial date:       2011-10-27
# $Id: script.py 25303 2011-11-17 08:46:12Z mario.frasca $
#
#******************************************************************************

from nens.gp import parse_arguments
import os
import sys
import logging
import nens.gp
from dbfpy import dbf
import ConfigParser
from jinja2 import Environment, PackageLoader
from jinja2.utils import soft_unicode
from datetime import datetime
import turtlebase.general


def do_isknown(value):
    return value or "???"


def do_pyformat(value, format):
    """return float according to format
    """

    try:
        if value == -9999:
            return "???"
        else:
            return soft_unicode("%" + format) % value
    except TypeError:
        return "???"


def do_material(value):
    """translate numeric material or return string
    """

    try:
        return {'01': 'aluminium',
                '02': 'asbest-cement',
                '03': 'beton',
                '04': 'gegolfd plaatstaal',
                '17': 'metselwerk',
                '20': 'PVC',
                '21': 'staal',
                '99': 'overig',
                }[value]
    except (TypeError, KeyError):
        return value


def do_form(value):
    """return float according to format
    """

    try:
        return {'01': 'rond',
                '02': 'rechthoekig',
                '03': 'eivormig',
                '04': 'muil',
                '05': 'ellips',
                '06': 'heul',
                '99': 'onbekend',
                }[value]
    except (TypeError, KeyError):
        return value

def main(options=None, args=None):
    from turtlebase import mainutils
    from turtlebase.logutils import LoggingConfig

    log = logging.getLogger(__name__)
    gp = mainutils.create_geoprocessor()
    config = mainutils.read_config(__file__, 'turtle-settings.ini')
    logfile = mainutils.log_filename(config)
    logging_config = LoggingConfig(gp, logfile=logfile)
    mainutils.log_header(__name__)

    if options is args is None:
        options, args = parse_arguments({1: ('arg', 0),
                                         2: ('arg', 1),
                                         3: ('arg', 2)})

    shape_file, output_dir, settings = args

    dbf_file_name = shape_file[:-3] + 'dbf'
    table = dbf.Dbf(dbf_file_name, readOnly=True)

    resources_dir = os.path.dirname(sys.argv[0])
    log.info(resources_dir)

    config = ConfigParser.ConfigParser()
    config.read(settings)

    env = Environment(loader=PackageLoader('__main__', resources_dir))
    env.filters['pyformat'] = do_pyformat
    env.filters['filter_material'] = do_material
    env.filters['filter_isknown'] = do_isknown
    template_svg = env.get_template('duiker.svg')

    output_graphs = os.path.join(output_dir, "graph")
    log.info("output graphs: %s" % output_graphs)
    if not os.path.isdir(output_graphs):
        os.makedirs(output_graphs)

    for row in table:
        svg_info = {}
        for field in config.options('column.culvert'):
            if field == '-':
                continue
            db_field = config.get('column.culvert', field)
            if db_field == '-':
                svg_info[field] = ""
                continue
            try:
                svg_info[field] = row[db_field]
            except:
                ## column is configured but not in data, possibly
                ## using a configuration that is more than we need
                ## here.
                continue
            if svg_info[field] is None:
                svg_info[field] = ""
        if isinstance(svg_info['date'], datetime):
            svg_info['date'] = svg_info['date'].strftime('%Y-%m-%d')
        svg_info['has_diametre'] = (svg_info['profile_shape'] in ['rond'])

        svg_data = template_svg.render(svg_info)
        filename = os.path.join(output_graphs, svg_info['name'] + ".svg")
        out = file(filename, "w")
        out.write(svg_data)
        out.close()

    location_svg = output_graphs + "\\*.svg"
    log.info('%s\\batik\\convert_svg_to_png.bat %s' % (os.path.dirname(sys.argv[0]), location_svg))
    os.system('%s\\batik\\convert_svg_to_png.bat %s' % (os.path.dirname(sys.argv[0]), location_svg))

    # Create CSV files
    output_csv = os.path.join(output_dir, "csv")
    log.info("output csv: %s" % output_csv)
    if not os.path.isdir(output_csv):
        os.makedirs(output_csv)

    row = gp.SearchCursor(shape_file)
    log.info("Create CSV files")
    for item in nens.gp.gp_iterator(row):
        #log.info(" - export csv for: %s" % item.GetValue('kwk_name'))

        output_file = os.path.join(output_csv, "%s.csv" % item.GetValue(config.get('column.culvert', 'name')))
        turtlebase.general.add_to_csv(output_file, [('Location:    ', item.GetValue(config.get('column.culvert', 'name')))], "wb")
        turtlebase.general.add_to_csv(output_file, [('Vorm:        ', item.GetValue(config.get('column.culvert', 'profile_shape')))], "ab")
        turtlebase.general.add_to_csv(output_file, [('Materiaal:   ', item.GetValue(config.get('column.culvert', 'material')))], "ab")
        turtlebase.general.add_to_csv(output_file, [('Streefpeil:  ', round(item.GetValue(config.get('column.culvert', 'target_level')), 2))], "ab")
        turtlebase.general.add_to_csv(output_file, [('Diameter:    ', round(item.GetValue(config.get('column.culvert', 'diametre')), 2))], "ab")
        turtlebase.general.add_to_csv(output_file, [('Lengte:      ', round(item.GetValue(config.get('column.culvert', 'length')), 2))], "ab")
        turtlebase.general.add_to_csv(output_file, [('BOB1:        ', round(item.GetValue(config.get('column.culvert', 'bed_level_left')), 2))], "ab")
        turtlebase.general.add_to_csv(output_file, [('BOB2:        ', round(item.GetValue(config.get('column.culvert', 'bed_level_right')), 2))], "ab")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s',)

    from optparse import OptionParser
    usage = "usage: %prog [options] shape_file output_dir config"
    parser = OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    main(options, args)

