# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser
from math import cos, sin, pi
from optparse import OptionParser
import logging

from turtlebase.logutils import LoggingConfig
import arcgisscripting
gp = arcgisscripting.create()
import nens.sobek
import nens.gp
import nens.geom

log = logging.getLogger(__name__)

pool = {}

nens.sobek.max_decimal_digits = 7


def getConfig(input):
    """gets the name of a windows INI file and reads the file into a ConfigParser.ConfigParser instance
    """

    config = ConfigParser()
    config.readfp(input)
    return config

## the function add_to_output adds an object to the result pool, if
## it's the first time an object with that tag and id is offered to
## the pool.  otherwise it does nothing.  the object will be further
## constructed by the software but it will not be included in the
## output.

## the function is realized as a functor because it needs static data.
class add_to_output_functor:
    def __init__(self):
        self.defined = {}
        self.destination = {'STRU': 'struct.dat',
                            'CNTL': 'control.def',
                            'STDS': 'struct.def',
                            'GLFR': 'friction.dat',
                            'STFR': 'friction.dat',
                            'CRDS': 'profile.def',
                            'CRSN': 'profile.dat',
                            'BDFR': 'friction.dat',
                            'GLIN': 'initial.dat',
                            'FLIN': 'initial.dat',
                            }
    def __call__(self, pool, obj):
        key = obj.tag + obj.id
        if self.defined.setdefault(key, obj) == obj:
            pool[self.destination[obj.tag]].addObject(obj)

add_to_output = add_to_output_functor()


def script():
    gp = arcgisscripting.create()
    logging_config = LoggingConfig(gp)
    # TODO: perhaps grab the logfile location from the config below.
    parser = OptionParser()
    (options, args) = parser.parse_args()
    main(options, args)
    logging_config.cleanup()


def main(options, args):
    log.info("CF Converter starting.")
    table_name = {}
    try:
        (output_dir_name,
         ini_file_name,
         table_name['bridge'],
         table_name['culvert'],
         table_name['syphon'],
         table_name['pump'],
         pump_stage_name,
         table_name['weir'],
         table_name['univw'],
         table_name['xsection'],
         xsection_definition,
         xsection_2dpoint,
         xsection_3dpoint,
         table_name['waterline'],) = args

    except:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s',)
        log.warning("overruling the inputs received...  for debugging...")

        if not options.debug:
            raise

        output_dir_name = "c:/Local/nens-office/Turtle/Source/Trunk/TurtleConversieCF/Voorbeelddatabase/testing"
        ini_file_name = "c:/Local/nens-office/Turtle/Source/Trunk/TurtleConversieCF/Voorbeelddatabase/settings.ini"

        dbloc = 'C:/Local/nens-office/Turtle/Source/Trunk/TurtleConversieCF/Voorbeelddatabase/testdatabase_CF.mdb/'
        table_name['bridge'] = dbloc + 'Structures/bridge'
        table_name['culvert'] = dbloc + 'Structures/culvert'
        table_name['syphon'] = dbloc + 'Structures/syphon'
        table_name['pump'] = dbloc + 'Structures/pump_station'
        pump_stage_name = dbloc + 'Pump_station_def'
        table_name['weir'] = dbloc + 'Structures/weir'

        table_name['univw'] = dbloc + 'Structures/universal_weir'

        table_name['xsection'] = dbloc + 'Cross_sections/Locations'
        xsection_definition = dbloc + 'Cross_section_definition'
        xsection_2dpoint = dbloc + 'Cross_section_yz'
        xsection_3dpoint = dbloc + 'Cross_sections/points_xyz'

        table_name['waterline'] = dbloc + 'Channel/Channel'
        pass

    output_dir_name += '/'

    config = getConfig(file(ini_file_name))

    none_values = [config.getint('global.defaults', 'none')]

    log.debug("create the file pool")
    for n in ['struct.dat', 'control.def', 'struct.def', 'friction.dat', 'profile.def', 'profile.dat', 'initial.dat']:
        f = file(output_dir_name + n, 'w')
        f.write('')
        f.close()
        pool[n] = nens.sobek.File(output_dir_name + n)

    log.debug("step 0: the default friction!")

    glfr = nens.sobek.Object(tag='GLFR', id='0')
    add_to_output(pool, glfr)

    bdfr = nens.sobek.Object(tag='BDFR', id='0')
    glfr.addObject(bdfr)

    bdfr['ci'] = '0'
    bdfr['mf'] = bdfr['sf'] = config.getint("default.global_friction","global_bed_friction_type")
    bdfr['mr cp'] = bdfr['mt cp'] = bdfr['st cp'] = [
        0, config.getint("default.global_friction","global_bed_friction_value"), 0]
    bdfr['sr cp'] = [
        0, config.getint("default.global_friction","global_bed_friction_value")]

    log.debug("step 0: the default initial!")

    glin = nens.sobek.Object(tag='GLIN', id='0')
    add_to_output(pool, glin)
    glin['fi'] = 0
    glin['fr'] = 'null'

    flin = nens.sobek.Object(tag='FLIN', id='-1')
    glin.addObject(flin)

    flin['nm'] = 'null'
    flin['ci'] = '-1'
    flin['q_ lq'] = [0, 0, ]
    flin['ty'] = 1
    flin['lv ll'] = [0, 0, ]

    for type_name in ['bridge', 'culvert', 'syphon', 'pump', 'weir', 'univw', 'xsection', 'waterline']:
        if table_name[type_name] == '#':
            log.info("%s: no input" % type_name)
            continue
        log.info("%s: reading database objects" % type_name)
        objs = nens.gp.get_table(gp, table_name[type_name],
                                 conversion=config.items('column.'+type_name),
                                 defaults=config.items('default.'+type_name),
                                 evaluate=True,
                                 dictionaries=dict([(i.split('.')[-1], config.items(i))
                                                    for i in config.sections()
                                                    if i.startswith('dictionary.'+type_name)]),
                                 nonevalues=none_values,
                                 ranges=dict(config.items('range.'+type_name)),
                                 )
        if type_name == 'univw':
            if xsection_2dpoint == '#':
                log.debug("not joining univw with '#' profile sampling table")
            else:
                nens.gp.join_on_foreign_key(
                    gp,
                    objs,
                    'profile_sampling',
                    ['x', 'z', ],
                    xsection_2dpoint,
                    'profile_id', 'profile_id',
                    conversion=config.items('column.xsection_2dpoint'),
                    defaults=config.items('default.xsection_2dpoint'),
                    evaluate=True,
                    ranges=dict(config.items('range.'+type_name)),
                    sort_on=0, nonevalues=none_values)
        elif type_name == 'pump':
            if pump_stage_name == '#':
                log.debug("not joining pump with '#' pump_stage_name table")
            else:
                nens.gp.join_on_foreign_key(
                    gp,
                    objs,
                    'stages',
                    ['stage', 'capacity', 'suc_start', 'suc_stop', 'prs_start', 'prs_stop', ],
                    pump_stage_name,
                    'id', 'id',
                    conversion=config.items('column.pump_stage'),
                    defaults=config.items('default.pump_stage'),
                    evaluate=True,
                    ranges=dict(config.items('range.'+type_name)),
                    sort_on=0, nonevalues=none_values)
        elif type_name == 'xsection':
            if xsection_definition == '#':
                log.debug("xsection: not joining with '%s' xsection_definition")
            else:
                log.debug("xsection: joining with '%s' table" % xsection_definition)
                tmp = nens.gp.get_table(gp, xsection_definition,
                                        conversion=config.items('column.xsection_definition'),
                                        defaults=config.items('default.xsection_definition'),
                                        evaluate=True,
                                        dictionaries=dict([(i.split('.')[-1], config.items(i))
                                                           for i in config.sections()
                                                           if i.startswith('dictionary.xsection_definition')]),
                                        nonevalues=none_values,
                                        ranges=dict(config.items('range.'+type_name)),
                                        )
                objs = nens.gp.join_dicts(objs, tmp, key1='profile_id', key2='profile_id')

            log.debug("for xsection type 1: joining with '%s' table" % xsection_3dpoint)
            if xsection_3dpoint == '#':
                log.debug("xsection: not joining with '%s' xsection_3dpoint")
            else:
                nens.gp.join_on_foreign_key(
                    gp, objs,
                    'points_3d',
                    ['x', 'y', 'z',],
                    xsection_3dpoint,
                    'profile_id', 'profile_id',
                    conversion=config.items('column.xsection_3dpoint'),
                    defaults=config.items('default.xsection_3dpoint'),
                    evaluate=True,
                    ranges=dict(config.items('range.'+type_name)),
                    sort_on=0 )

            if xsection_2dpoint == '#':
                log.debug("xsection: not joining with '#' xsection_2dpoint")
            else:
                log.debug("for xsection type 3: joining with '%s' table" % xsection_2dpoint)
                nens.gp.join_on_foreign_key(
                    gp, objs,
                    'points_2d',
                    ['x', 'z',],
                    xsection_2dpoint,
                    'profile_id', 'profile_id',
                    conversion=config.items('column.xsection_2dpoint'),
                    defaults=config.items('default.xsection_2dpoint'),
                    evaluate=True,
                    ranges=dict(config.items('range.'+type_name)),
                    sort_on=0 )

            for i in objs:
                if i.setdefault('points_2d', []):
                    i['profile_shape'] = 3
                if i.get('points_3d'):
                    sorted = nens.geom.sort(i['points_3d'])
                    abscissas = nens.geom.abscissa_from_midsegment(sorted)
                    i['points_2d'] = [(xx,z) for ((xx), (x,y,z)) in zip(abscissas, sorted)]
                    i['profile_shape'] = 1
                    del i['points_3d']
                if i['points_2d']:
                    i['field_level'] = min(i['points_2d'][0][1], i['points_2d'][-1][1])

        log.info("%s: translate %d database objects into SOBEK equivalent." % (type_name, len(objs), ))
        sobek_count = do_structures(type_name, objs)
        log.info("%s: added %d SOBEK objects to output files." % (type_name, sobek_count))

    log.info("CF Converter saving the SOBEK files.")
    for k,i in pool.items():
        log.debug("saving '%s' to '%s'" % (k, i.source))
        i.save()
    log.info("CF Converter done.")


def control_tble(summer_level,
                 winter_level,
                 start_year=1900, end_year=2050,
                 start_summer="0401", start_winter="1001",
                 switch_delay = 1
                 ):
    """returns an object containing the control data...
    """
    start_summer = start_summer[:2] + "/" + start_summer[2:]
    start_winter = start_winter[:2] + "/" + start_winter[2:]
    o = nens.sobek.Object(tag='TBLE')
    for y in range(start_year, end_year+1):
        o.addRow(("%s/%s;%02d:00:00" % (y, start_summer, 0), winter_level))
        o.addRow(("%s/%s;%02d:00:00" % (y, start_summer, switch_delay), summer_level))
        o.addRow(("%s/%s;%02d:00:00" % (y, start_winter, 0), summer_level))
        o.addRow(("%s/%s;%02d:00:00" % (y, start_winter, switch_delay), winter_level))
    return o

def do_structures(type_name, objs):
    """this function finally writes the data to the pool, doing all that
    is common in the common part and doing all custom parts depending
    on type_name.
    """

    sobek_count = 0
    log.debug("do_structures entering with type_name='%s'" % type_name)
    def optPut(destination, field, value):
        if value is not None:
            destination[field] = value

    for i in objs:
        try:
            log.debug("examining object '%s'" % i)
            cntl = stfr = crds = stds = crsn = bdfr = flin = None
            if type_name not in ['xsection', 'waterline']:
                log.debug("object is not a 'xsection' so it gets a STRU")
                stru = nens.sobek.Object(tag="STRU", id=i['id'])
                add_to_output(pool, stru)
                sobek_count += 1

                stru['nm'] = i.get('name', stru.id)
                stru['dd'] = 'sd_' + i['id']

                optPut(stru, 'df', i.get('damping_factor'))

            if type_name not in ['xsection', 'waterline']:
                log.debug("object is not a 'xsection' so it gets a STDS")
                stds = nens.sobek.Object(tag="STDS", id='sd_' + i['id'])
                add_to_output(pool, stds)
                sobek_count += 1

                stds['nm'] = i.get('name', stds.id)
                stds['ty'] = i['structure_type']

            if type_name in ['culvert', 'univw', 'xsection', 'syphon']:
                log.debug("object is one of '%s' so it gets a CRDS" % ['culvert', 'univw', 'xsection'])
                crds = nens.sobek.Object(tag="CRDS", id='cd_' + i['profile_id'])
                add_to_output(pool, crds)
                sobek_count += 1

            if type_name == 'xsection':
                log.debug("object is a 'xsection' so it gets a CRSN")
                crsn = nens.sobek.Object(tag="CRSN", id=i['id'])
                add_to_output(pool, crsn)
                sobek_count += 1
                crsn['di'] = crds.id
                if i['profile_shape'] not in [1, 3, 4]:
                    crsn['rl'] = i['bottom_level']
                    crsn['rs'] = i['field_level']
                else:
                    crsn['rl'] = 0
                    crsn['rs'] = 0

            if type_name == 'bridge':
                stds['tb'] = i['bridge_type']
                if i['bridge_type'] == 2:
                    optPut(stds, 'pw', i.get('tot_pillar_width'))
                    optPut(stds, 'vf', i.get('pillar_form_factor'))
                else:
                    log.debug("object is a 'bridge' and not of type '2' so it gets a CRDS")
                    crds = nens.sobek.Object(tag='CRDS', id='cd_' + i['profile_id'])
                    add_to_output(pool, crds)
                    sobek_count += 1

            if type_name == 'weir':
                i['crest_level'] = i['constant_crest_level']
                if i['winter_level'] != i['summer_level']:
                    log.debug("object is a 'weir' with two levels so it needs a controller")
                    i['crest_level'] = i['summer_level']
                    i['controller_active'] = 1

            if type_name == 'pump':
                stds['dn'] = 1
                stds['rt cr'] = [0, 1, 0]
                stds['ct lt'] = 1

                if i['period'] != 'constant':
                    log.debug("object is a 'pump' that does not stay on the whole year so it needs a controller")
                    i['controller_active'] = 1
                ## convert capacity of stages to m3/s, sum them up and
                ## store cumulative capacity in in object as capacity
                ## for the active period.
                cumulative = 0
                for stage in i['stages']:
                    stage[1] = stage[1] / 3600
                    cumulative = stage[1] = cumulative + stage[1]
                    if stage[2] == 0:
                        stds['dn'] = 2
                i[i['period'] + '_level'] = cumulative

                pass

            if type_name in ['bridge', 'culvert', 'syphon', ]:
                log.debug("object is one of '%s' so it gets a STFR" % ['bridge', 'culvert', 'syphon', ])
                stfr = nens.sobek.Object(tag="STFR", id='fr_' + i['id'])
                add_to_output(pool, stfr)
                sobek_count += 1
                stfr['ci'] = stds.id

                if type_name in ['culvert', 'syphon', ]:
                    i['has_table_of_loss_coefficient'] = 0

                stfr['mf'] = i['friction_type']
                stfr['mt cp'] = [0, i['friction_value'], 0]
                stfr['mr cp'] = [0, i['friction_value'], 0]
                stfr['s1'] = 6
                stfr['s2'] = 6
                stfr['sf'] = i['friction_type']
                stfr['st cp'] = [0, i['friction_value'], 0]
                stfr['sr cp'] = [0, i['friction_value']]
                pass

            if type_name == 'waterline':
                log.debug("object is one of '%s' so it gets a BDFR" % ['waterline', ])
                bdfr = nens.sobek.Object(tag="BDFR", id='fr_' + i['id'])
                add_to_output(pool, bdfr)
                sobek_count += 1
                bdfr['ci'] = i['id']
                bdfr['mf'] = i['friction_type']
                bdfr['mt cp'] = [0, i['friction_value'], 0, ]
                bdfr['mr cp'] = [0, i['friction_value'], 0, ]
                bdfr['s1'] = 6
                bdfr['s2'] = 6

                log.debug("object is one of '%s' so it gets a FLIN" % ['waterline', ])
                flin = nens.sobek.Object(tag="FLIN", id=i['id'])
                add_to_output(pool, flin)
                sobek_count += 1
                flin['nm'] = i.get('name', flin.id)
                flin['ci'] = i['id']
                flin['q_ lq'] = [0, i['initial_discharge'], ]
                flin['ty'] = i['initial_type']
                flin['lv ll'] = [0, i['initial_level'], ]

            if i.get('controller_active'):
                log.debug("object needs a controller so it gets a CNTL")
                cntl = nens.sobek.Object(tag='CNTL', id='cd_' + i['id'])
                add_to_output(pool, cntl)
                sobek_count += 1

                cntl['nm'] = i.get('name', cntl.id)
                cntl['ct'] = 0
                cntl['ac'] = 1
                cntl['ca'] = 3
                cntl['cf'] = 1
                cntl['mc'] = 0
                cntl['bl'] = 1
                pdin = nens.sobek.Object("PDIN pdin")
                pdin['PDIN'] = [1, 1, '365;00:00:00']
                cntl['ti tv'] = [pdin,
                                 control_tble(summer_level = i['summer_level'],
                                              winter_level = i['winter_level'],
                                              start_year=1900, end_year=1900,
                                              start_summer="0401", start_winter="1001",
                                              )
                                 ]

                stru['ca'] = 1
                stru['cj'] = cntl.id
                stru['cm'] = 0

            if stds is not None:
                optPut(stds, 'tc', i.get('type_culvert'))
                optPut(stds, 'cl', i.get('crest_level'))
                optPut(stds, 'cw', i.get('constant_crest_width'))
                optPut(stds, 'ce', i.get('discharge_coefficient'))
                optPut(stds, 'sc', i.get('lateral_contraction'))
                optPut(stds, 'sv', i.get('modular_limit'))
                optPut(stds, 'rl', i.get('bottom_level'))
                optPut(stds, 'll', i.get('bed_level_left'))
                optPut(stds, 'rl', i.get('bed_level_right'))
                optPut(stds, 'dl', i.get('length'))
                if crds is not None:
                    stds['si'] = crds.id
                optPut(stds, 'li', i.get('inlet_loss'))
                optPut(stds, 'lo', i.get('outlet_loss'))
                optPut(stds, 'lb', i.get('bend_loss'))
                optPut(stds, 'ov', i.get('initial_opening'))
                optPut(stds, 'tv', i.get('has_table_of_loss_coefficient'))
                optPut(stds, 'rt', i.get('flow_direction'))

            if type_name == 'pump':
                t = nens.sobek.Object(tag='TBLE')
                ## add stage definition but drop stage_no column, used in sorting.
                for r in i['stages']:
                    t.addRow(r[1:])
                stds['ct lt'] = [1, t]

            if crds is not None:
                crds['nm'] = i.get('name', crds.id)

                # and here the whole logic about what to do with profile definitions...

                if type_name == 'bridge':
                    i['height'] = i['top_level'] - i['bottom_level']

                    crds['ty'] = 0
                    crds['wm'] = i['width']
                    crds['w1'] = 0
                    crds['w2'] = 0
                    crds['gl'] = 0
                    crds['gu'] = 0
                    t = nens.sobek.Object(tag = 'TBLE')
                    t.addRow([0, i['width'], i['width']])
                    t.addRow([i['height'], i['width'], i['width']])
                    t.addRow([i['height'] + 0.0001, 0.0001, 0.0001])
                    crds['lt lw'] = t
                    pass
                elif (type_name in ['culvert', 'syphon']) or (type_name == 'xsection' and i['profile_shape'] in [5, 6, 7]):
                    if i['profile_shape'] == 5:
                        crds['nm'] = 'round %0.2fm' % i['diametre']
                        crds['ty'] = 4
                        crds['bl'] = 0
                        crds['rd'] = i['diametre'] / 2
                        crds['gl'] = 0
                        crds['gu'] = 0
                        pass
                    else:
                        w, h = i['width'], i['height']
                        if i['profile_shape'] == 6:
                            name_start = 'rectangular'
                            t = nens.sobek.Object(tag='TBLE')
                            t.addRow((0, w, w))
                            t.addRow((h, w, w))
                            t.addRow((h + 0.0001, 0.0001, 0.0001))
                        else:
                            name_start = 'ellipse'
                            t = nens.sobek.Object(tag='TBLE')
                            [t.addRow([h/2.0*(1-cos(x/180.0*pi)),
                                       w*sin(x/180.0*pi),
                                       w*sin(x/180.0*pi), ],
                                      decimals=7)
                             for x in range(0, 181, 9)]

                        crds['nm'] = name_start + " width = %0.2fm; height = %0.2fm" % (w, h)
                        crds['ty'] = 0
                        crds['wm'] = i['width']
                        crds['w1'] = 0
                        crds['w2'] = 0
                        crds['gl'] = 0
                        crds['gu'] = 0
                        crds['lt lw'] = t
                        pass
                elif type_name == 'univw':
                    crds['ty'] = 10
                    crds['st'] = 0
                    crds['lt sw'] = [0, i.get('storage_type',0), ]
                    crds['gl'] = i['ground_layer_depth']
                    crds['gu'] = i['ground_layer_depth'] != 0 and 1 or 0
                    t = nens.sobek.Object(tag='TBLE')
                    [t.addRow(r, decimals=3) for r in i['profile_sampling']]
                    crds['lt yz'] = t
                    i['width'] = i['profile_sampling'][-1][0] - i['profile_sampling'][0][0]
                elif type_name == 'xsection' and i['profile_shape'] in [1, 3]:
                    crds['ty'] = 10
                    crds['st'] = 0
                    crds['lt sw'] = [0, i.get('storage_type',0), ]
                    crds['gl'] = i.get('ground_layer_level', 0)
                    crds['gu'] = i.get('ground_layer_used', 0)
                    t = nens.sobek.Object(tag='TBLE')
                    [t.addRow(r, decimals=3) for r in i['points_2d']]
                    crds['lt yz'] = t
                elif type_name == 'xsection' and i['profile_shape'] == 2:
                    crds['ty'] = 1
                    crds['bw'] = i['bottom_width']
                    crds['bs'] = i['slope']
                    crds['aw'] = i['aperture_width']
                    crds['sw'] = 0
                    crds['gl'] = 0
                    crds['gu'] = 0
                elif type_name == 'xsection' and i['profile_shape'] == 4:
                    crds['ty'] = 0
                    crds['wm'] = i['max_width']
                    crds['w1'] = 0
                    crds['w2'] = 0
                    crds['sw'] = 0
                    crds['gl'] = 0
                    crds['gu'] = 0
                    t = nens.sobek.Object(tag='TBLE')
                    t.addRow([i['bottom_level'], i['main_bottom_width'], i['flow_bottom_width'], ], decimals=3)
                    t.addRow([i['water_level'], i['main_water_width'], i['flow_water_width'], ], decimals=3)
                    t.addRow([i['field_level'], i['main_field_width'], i['flow_field_width'], ], decimals=3)
                    crds['lt lw'] = t
                else:
                    log.warning("object has an empty CRDS")
        except KeyError, e:
            log.warning("%s (id='%s') has no key '%s'.  output is incomplete." % (type_name, i['id'], e))
    return sobek_count

