#!/usr/bin/env python
# -*- coding: utf-8 -*-
#***********************************************************************
#*
#***********************************************************************
#*                      All rights reserved                           **
#*
#*
#*                                                                    **
#*
#*
#*
#***********************************************************************
#* Library    : the main module for RR Conversion
#*
#* Project    : various
#*
#* $Id$
#*
#* initial programmer :  Mario Frasca
#* initial date       :  2008-06-10
#**********************************************************************

__revision__ = "$Rev$"[6:-2]

import logging
if __name__ == '__main__':
    logging.basicConfig()

log = logging.getLogger('nens.trrrlib')
log.setLevel(logging.DEBUG)
log.debug('loading module (%s)' % __revision__)

import types

settings = None


def Config(filename):
    """gets the name of a windows INI file and reads the file into a ConfigParser.ConfigParser instance
    """

    from ConfigParser import ConfigParser
    config = ConfigParser()
    config.readfp(file(filename))
    return config


def kwelwegzijging(wat_is_het, waarde):
    if wat_is_het == settings.get('dictionary.peilgebied.kwel_wegzijging', 'kwel'):
        return abs(waarde)
    elif wat_is_het == settings.get('dictionary.peilgebied.kwel_wegzijging', 'wegzijging'):
        return -abs(waarde)
    return waarde


class sequential_functor(object):
    def __init__(self):
        log.debug("initializing sequential_functor")
        self.id = 0

    def __call__(self):
        self.id += 1
        return "%04d" % self.id
sequential = sequential_functor()
# ------------------------------------------------------------


def checkConstraints(obj, field_name, settings):
    """boolean function, true if all constraints hold for value

    gets value associated to field_name in obj,
    gets constraints from section 'range.<obj type>'

    returns False if the check fails on a strong constraint.
    returns True otherwise
    emits a warning if a check (strong or weak) fails.

    constraints is expected to be composed of:
    Integer
    NonNegative
    Positive
    DDMM - Integer holding a day of the year.
    MMDD - Integer holding a day of the year.
    (min, max) - either values can be a '-', which is ignored.
    W(min, max) - this is a weak constraint: logs a warning, but returns True.
    """

    import re
    pattern = re.compile(r'^([a-z]?)\(([-0-9\.]+)[ ,]+([-0-9\.]+)\)$', re.I)

    result = True

    log.debug("checkConstraints for %s" % field_name)
    # get the string representation of the value from object
    value = obj[field_name]

    try:
        fvalue = float(value)
        ivalue = int(fvalue)
    except (TypeError, ValueError):
        fvalue = ivalue = None

    log.debug("%s(%s)" % (type(value), value))

    if fvalue == float(settings.get('value.missing', 'float')):
        log.debug("replacing 'value.missing' float field '%s' in object %s with None" % (field_name, str(obj)))
        value = None

    if ivalue == int(settings.get('value.missing', 'int')):
        log.debug("replacing 'value.missing' int field '%s' in object %s with None" % (field_name, str(obj)))
        value = None

    if value is None:
        log.warning("field '%s' is not defined in object %s" % (field_name, str(obj)))
        return True

    if not isinstance(value, types.StringTypes):
        value = str(value)

    # get constraints from settings
    if isinstance(obj, Kunstwerk):
        constraints = settings.get('range.kunstwerk', field_name)
    elif isinstance(obj, Peilgebied):
        constraints = settings.get('range.peilgebied', field_name)
    else:
        log.error("can't check object %s" % str(obj))
        return False
    constraints = splitConstraints(constraints)

    # perform the check
    try:
        log.debug("checking s/f/i %s %0.6f %d, %s" % (value, fvalue, ivalue, constraints))
    except TypeError:
        log.debug("checking s/f/i %s %s %s, %s" % (value, fvalue, ivalue, constraints))
    for i in [i.lower() for i in constraints]:
        log.debug(i)
        justWarn = False
        matchedPattern = pattern.match(i)
        if i == 'boolean':
            ok = value.lower() in ['1', '0', 'true', 'false', 'yes', 'no']
        elif i == 'percent':
            ok = True
            ok &= (fvalue >= 0)
            ok &= (fvalue <= 100)
        elif i == 'integer':
            ok = (ivalue == fvalue)
        elif i == 'nonnegative':
            ok = (fvalue >= 0)
        elif i == 'positive':
            ok = (fvalue > 0)
        elif i in ['ddmm', 'mmdd']:
            if i == 'ddmm':
                day, month = ivalue / 100, ivalue % 100
            if i == 'mmdd':
                month, day = ivalue / 100, ivalue % 100
            try:
                import datetime
                datetime.datetime(2000, month, day)
                ok = True
            except ValueError:
                ok = False
        elif matchedPattern:
            justWarn, min, max = matchedPattern.groups()
            if min != '-':
                min = float(min)
            else:
                min = None
            if max != '-':
                max = float(max)
            else:
                max = None
            ok = True
            if min is not None:
                ok &= (fvalue >= min)
            if max is not None:
                ok &= (fvalue <= max)
        else:
            log.warn("unrecognized pattern '%s'" % i)
            ok = True
        if not ok:
            log.warn("value %s in field %s does not respect constraint %s" %
                     (value, field_name, i))
        if justWarn:
            ok = True
        result &= ok
    return result


def splitConstraints(s):
    '''splits the string defining the range into its components

    for example:
    splitTypeDef("NonNegative W(-,100)") ['NonNegative', 'W(-,100)']
    splitTypeDef("NonNegative W(-, 100)") ['NonNegative', 'W(-, 100)']
    splitTypeDef("Integer NonNegative W(-, 100)") ['Integer', 'NonNegative', 'W(-, 100)']
    splitTypeDef("Integer NonNegative (-, 100)") ['Integer', 'NonNegative', '(-, 100)']
    splitTypeDef("W(-, 100)") ['W(-, 100)']
    splitTypeDef("(-, 100)") ['(-, 100)']
    '''

    import re
    p = re.compile(r'^((?:[a-z]+(?:\([^\)]*\))?|(?:\([^\)]*\))))[ ]*', re.I)
    result = []
    while p.match(s):
        m = p.match(s)
        result.append(m.group(1))
        s = s[m.end():]
    return result


def createPool(output_dir='.'):
    """creates files, returns pool of open files, as a dictionary.
    """

    log.debug("writing to output - creating pool")
    retval = {}
    import os
    sep = os.sep

    # Boundaries
    retval['bound3b'] = file(sep.join([output_dir, "bound3b.3b"]), "w")

    # kassen / greenhouses
    retval['green3b'] = file(sep.join([output_dir, "greenhse.3b"]), "w")
    retval['greenrf'] = file(sep.join([output_dir, "greenhse.rf"]), "w")
    retval['greensil'] = file(sep.join([output_dir, "greenhse.sil"]), "w")

    # openwater
    retval['openw3b'] = file(sep.join([output_dir, "openwate.3b"]), "w")
    retval['openwsep'] = file(sep.join([output_dir, "openwate.sep"]), "w")
    retval['openwtbl'] = file(sep.join([output_dir, "openwate.tbl"]), "w")

    # verhard / paved
    retval['pav3b'] = file(sep.join([output_dir, "paved.3b"]), "w")
    retval['pavsto'] = file(sep.join([output_dir, "paved.sto"]), "w")
    retval['pavdwa'] = file(sep.join([output_dir, "paved.dwa"]), "w")

    # onverhard / unpaved (stedelijk/landelijk)
    retval['unp3b'] = file(sep.join([output_dir, "unpaved.3b"]), "w")
    retval['unpsto'] = file(sep.join([output_dir, "unpaved.sto"]), "w")
    retval['unpalf'] = file(sep.join([output_dir, "unpaved.alf"]), "w")
    retval['unpsep'] = file(sep.join([output_dir, "unpaved.sep"]), "w")
    retval['unpinf'] = file(sep.join([output_dir, "unpaved.inf"]), "w")
    retval['unptbl'] = file(sep.join([output_dir, "unpaved.tbl"]), "w")

    # kunstwerken
    retval['strdat'] = file(sep.join([output_dir, "struct3b.dat"]), "w")
    retval['strdef'] = file(sep.join([output_dir, "struct3b.def"]), "w")
    retval['strtbl'] = file(sep.join([output_dir, "struct3b.tbl"]), "w")
    retval['contrdef'] = file(sep.join([output_dir, "contr3b.def"]), "w")

    # zuiveringen / wastewater reatement
    retval['wwtp3b'] = file(sep.join([output_dir, "WWTP.3b"]), "w")

    # Topografie
    retval['nodetp'] = file(sep.join([output_dir, "3B_NOD.TP"]), "w")
    retval['linktp'] = file(sep.join([output_dir, "3B_LINK.TP"]), "w")

    # inlees file
    retval['netwbbb'] = file(sep.join([output_dir, "network.bbb"]), "w")

    return retval


def startupPool(pool):
    """writes to 'constant' files
    """

    log.debug("writing to output - writing constant parts to pool")
    pool['nodetp'].write("BBB2.2\n")

    pool['linktp'].write("BBB2.2\n")

    pool['greensil'].write("SILO id 'silo_uit' nm 'uit' sc 0 pc 0 silo\n")

    pool['pavdwa'].write("""\
DWA id 'alg_dwa' nm 'algemene dwa definitie' do 2 wc -999 wd %(waterusepppday)s wh 0 0 0 0 0 0 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.14 7.18 0 0 0 0 sc 0 dwa
""" % dict(settings.items('globals')))

    pool['strtbl'].write("""\
SWLV id 'onoff_outlet' nm 'uitlaat_pomp' PDIN 1 1 '365;00:00:00' pdin TBLE
 '2000/01/01;00:00:00' %(on_low)s %(off_low)s %(on_high)s %(off_high)s %(on_low)s %(off_low)s %(on_high)s %(off_high)s <
 '2000/12/31;23:59:00'  %(on_low)s %(off_low)s %(on_high)s %(off_high)s %(on_low)s %(off_low)s %(on_high)s %(off_high)s <
 tble swlv
""" % dict(settings.items('default.gemaal')))

    pool['strtbl'].write("""\
SWLV id 'onoff_inlet' nm 'inlaat_pomp ' PDIN 1 1 '365;00:00:00' pdin TBLE
 '2000/01/01;00:00:00' %(on_low)s %(off_low)s %(on_high)s %(off_high)s %(on_low)s %(off_low)s %(on_high)s %(off_high)s <
 '2000/12/31;23:59:00'  %(on_low)s %(off_low)s %(on_high)s %(off_high)s %(on_low)s %(off_low)s %(on_high)s %(off_high)s <
 tble swlv
""" % dict(settings.items('default.inlaatgemaal')))

    pool['netwbbb'].write("""\
BBB2.2
'3b_nod.tp'
'3b_link.tp'
'3bRunoff.tp'
""")
    return


def closePool(pool):
    """closes all files in the pool
    """
    log.debug("writing to output - flushing/closing pool")
    return [i.close() for i in pool.values()]

# met NX versie 0.99 vervalt XDiGraph (graphs waar men informatie bij
# een edge kan toevoegen) want het toevoegen van informatie bij een
# edge wordt bij alle graphs mogelijk.
#
# het verschil is dat 'nieuwe' edges zijn altijd 2-tuples, terwijl
# 'oude' edges waren 2-tuples bij graphs zonder extra informatie en
# 3-tuples bij graphs met extra informatie.  in beide versies kan men
# de informatie uit een edge halen door graph_object.get_edge(start,
# end) te roepen.
#
# in beide gevallen, edge[:2] bevat begin en end node.
#
import networkx

import nens.gp

# from TWiki page...  hard coded but dependent on model
required_fields = {
    'peilgebied': ['id', 'ycoord', 'xcoord', 'total_area',
                   'verhard_area', 'OnverhardSted_area', 'kas_area',
                   'grass_area', 'openwater_area', ],
    'kunstwerk': ['id', ],
    }

# ------------------------------------------------------------


class Dict(object):
    """dictionaries are not hashable, for this reason I implement the few
    relevant functions in a common 'interface'...  moreover, our
    'dictionaries' must be case insensitive...
    """

    def __init__(self, **kwargs):
        log.log(5, "initializing Dict")
        if 'init' not in kwargs:
            init = {}  # fresh new dictionary
        else:
            init = dict([(self.lowercase_key(key), value) for key, value in kwargs['init'].items()])  # clone argument
            del kwargs['init']
        for key, value in kwargs.items():
            init[self.lowercase_key(key)] = value
        self.dict = init

    def lowercase_key(self, key):
        """Custom dict implemetations are all fine and well, but they
        shouldn't break on integer keys, really... So I'm 'fixing' all the
        ``key.lower()`` methods right here.
        """
        try:
            result = key.lower()
        except:
            result = key
        return result

    def __getitem__(self, key, default=None):
        return self.dict.get(self.lowercase_key(key), default)

    def __setitem__(self, key, value):
        self.dict[self.lowercase_key(key)] = value

    def __contains__(self, key):
        return self.lowercase_key(key) in self.dict

    def update(self, d):
        for key, value in d.items():
            self.dict.setdefault(self.lowercase_key(key), value)

    def get(self, key, default=None):
        return self.dict.get(self.lowercase_key(key), default)

    def setdefault(self, key, default=None):
        return self.dict.setdefault(self.lowercase_key(key), default)

    def __repr__(self):
        return "%s(id='%s')" % (self.__class__.__name__, self['ID'])

    def as_dict(self):
        """Networkx needs us to be a dict, but we need to be able to convert back."""
        return {'real': self}


def dict_to_Dict(obj):
    """Convert a dict (from networkx) back into a Dict subclass."""
    return obj['real']
# "node" classes.  sobek keyword: NODE


# abstract base classes
class Peilgebied(Dict):
    def __init__(self, **kwargs):
        Dict.__init__(self, **kwargs)
        log.log(5, "initializing Peilgebied")
        self['peilgebied'] = self


class SobekNode(Dict):
    "sobek network node"

    def __init__(self, **kwargs):
        log.log(5, "initializing SobekNode")
        kwargs.setdefault('mt', 0)
        kwargs.setdefault('nt', 0)
        kwargs.setdefault('type_id', "-999")
        if 'peilgebied' in kwargs and kwargs['peilgebied']:
            peilgebied = kwargs['peilgebied']
            kwargs.setdefault('nm', peilgebied.get('gebiedsnaam', peilgebied['id']))
        self.__super.__init__(**kwargs)

    def write(self, pool):
        "common part called by all derived classes"

        try:
            pool['nodetp'].write("NODE id '%(ID)s' nm '%(nm)s' ri '-1' mt 1 '%(mt)i' nt %(nt)i ObID '%(type_id)s' px %(xcoord)0.0f py %(ycoord)0.0f node\n" % self)
        except TypeError:
            log.debug('node %s has no geographical information: not generating NODE entry' % self.dict)

    def handle_inbound_edge(self, edge):
        return

    def handle_outbound_edge(self, edge):
        return

SobekNode._SobekNode__super = super(SobekNode)


# concrete classes
class Zuivering(SobekNode):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing Zuivering")
        kwargs.setdefault('mt', 14)
        kwargs.setdefault('nt', 56)
        kwargs.setdefault('type_id', "3B_WWTP")
        kwargs.setdefault('id', peilgebied['zuivering'])
        kwargs['nm'] = peilgebied['zuivering']
        kwargs['xcoord'] = peilgebied['xcoord'] - 10
        kwargs['ycoord'] = peilgebied['ycoord'] - 10
        self.__super.__init__(peilgebied=peilgebied, **kwargs)

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)
        pool['wwtp3b'].write("WWTP id '%(ID)s' tb 0 wwtp\n" % self)

Zuivering._Zuivering__super = super(Zuivering)


class KoppelPunt(SobekNode):

    def __init__(self, **kwargs):
        log.log(5, "initializing KoppelPunt")
        kwargs.setdefault('id', 'koppelpunt_' + sequential())
        kwargs.setdefault('bl', "2 '%s'" % kwargs['id'])
        kwargs.setdefault('isc', 0)
        self.__super.__init__(**kwargs)

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)
        pool['bound3b'].write("BOUN id '%(ID)s' bl %(bl)s is %(isc).2f boun\n" % self)

KoppelPunt._KoppelPunt__super = super(KoppelPunt)


class Boundary(KoppelPunt):

    def __init__(self, **kwargs):
        log.log(5, "initializing Boundary")
        kwargs.setdefault('mt', 6)
        kwargs.setdefault('nt', 47)
        kwargs.setdefault('type_id', "3B_BOUNDARY")
        kwargs.setdefault('id', "bnd_" + kwargs['cause']['id'])
        kwargs.setdefault('xcoord', kwargs['cause']['xcoord'])
        kwargs.setdefault('ycoord', kwargs['cause']['ycoord'] + 75)
        self.__super.__init__(**kwargs)
        self['nm'] = self['id']

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)

Boundary._Boundary__super = super(Boundary)


class Kas(SobekNode):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing Kas")
        kwargs.setdefault('mt', 3)
        kwargs.setdefault('nt', 45)
        kwargs.setdefault('type_id', "3B_GREENHOUSE")
        kwargs.setdefault('id', peilgebied['id'] + '_gh')
        self.__super.__init__(peilgebied=peilgebied, **kwargs)
        self.update({
                'nr_areas': 10,
                'storage_area_classes': [0 for i in range(10)],
                'surface_level': peilgebied['maaiveldKassen'],
                'meteo_station': peilgebied['rainstation'],
                'roofstorage_def': "rf_" + peilgebied['ID'],
                'max_roof_berging': peilgebied['maxBergingKasDak'],
                'ini_roof_berging': peilgebied['bergingKasDakIni'],
                'ini_salt_concentration': peilgebied['iniSaltConc'],
                'xcoord': peilgebied['xcoord'] + 25,
                'ycoord': peilgebied['ycoord'],
                })
        self['storage_area_classes'][2] = int((peilgebied['kas_area'] * 10000))
        self['storage_areas'] = " ".join(['%0.1f' % float(i) for i in self['storage_area_classes']])

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)

        pool['green3b'].write("GRHS id '%(ID)s' na %(nr_areas)i ar %(storage_areas)s as 0 sl %(surface_level)0.2f ms '%(meteo_station)s' sd '%(roofstorage_def)s' si 'silo_uit' is 0 grhs\n" % self)
        pool['greenrf'].write("STDF id '%(roofstorage_def)s' nm '%(ID)s' mk %(max_roof_berging)s ik %(ini_roof_berging)s stdf\n" % self)

Kas._Kas__super = super(Kas)


class Onverhard(SobekNode):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing Onverhard")
        kwargs.setdefault('mt', 2)
        kwargs.setdefault('nt', 44)
        kwargs.setdefault('type_id', "3B_UNPAVED")
        self.__super.__init__(peilgebied=peilgebied, **kwargs)
        self.update({
                'xcoord': peilgebied['xcoord'],
                'ycoord': peilgebied['ycoord'],
                'ground_comp_type': {'ernst': 3, 'zeeuw': 1}[settings.computation],
                'scurve_def': 'su_' + self['id'],
                'storage_def': 'sd_' + self['id'],
                'storage_comp': {'ernst': 'ed', 'zeeuw': 'ad'}[settings.computation],
                'alfa_def': 'ad_' + self['id'],
                'seepage_def': "sp_%s" % self['id'],
                'infilt_cap_def': "ic_%s" % self['id'],
                'soil_type': 100 + peilgebied['grondSoortLand'],
                'ini_groundwater': peilgebied['groundwIni'],
                'groundlayer': peilgebied['dikteWatervLaag'],
                'meteo_station': peilgebied['rainstation'],
                'isc': peilgebied['iniSaltConc'],
                'kwel_resist_C': settings.getfloat('globals', 'kwelresistC'),
                'inf_cap': peilgebied['infCap'],
                'level': peilgebied['maaiveldOnv'],
                'kwel_salt_concentration': peilgebied['kwelsaltconc'],
                })

        if not(0 < self['ini_groundwater'] <= 99):
            self['ini_groundwater'] = -999.99

        self['SCurve_Level'] = peilgebied.get('maaiveldHgt', {}).items()
        self['scurve_level'].sort()
        self['scurve_table'] = ''.join([" %i %.2f <\n" % (percentage, value) for percentage, value in self['scurve_level']])

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)
        pool['unp3b'].write("UNPV id '%(id)s' na 16 ar %(area_grass)i 0 0 0 0 %(area_misc)i 0 0 0 0 0 0 0 0 0 %(area_nature)i ga %(groundw_area)i lv %(level).2f co %(ground_comp_type)i su %(use_scurve)i '%(scurve_def)s' sd '%(storage_def)s' %(storage_comp)s '%(alfa_def)s' sp '%(seepage_def)s' ic '%(infilt_cap_def)s' bt %(soil_type)i ig 0 %(ini_groundwater)s mg %(level).2f gl %(groundlayer).2f ms '%(meteo_station)s' is %(isc).2f unpv\n" % self)
        pool['unptbl'].write("SC_T id '%(scurve_def)s' nm '%(id)s' PDIN 1 0 pdin TBLE\n%(scurve_table)s tble sc_t\n" % self)
        pool['unpsto'].write("STDF id '%(storage_def)s' nm '%(id)s' ml %(land_storage).1f il %(initial_land_storage).1f stdf\n" % self)
        pool['unpsep'].write("SEEP id '%(seepage_def)s' nm '%(id)s' co 1 sp %(kwel).2f ss %(kwel_salt_concentration).2f cv %(kwel_resist_C).1f seep\n" % self)
        pool['unpinf'].write("INFC id '%(infilt_cap_def)s' nm '%(id)s' ic %(inf_cap).2f infc\n" % self)

        if settings.computation == 'ernst':
            pool['unpalf'].write("ERNS id '%(alfa_def)s' nm '%(id)s' cvi %(alfa_infiltratie).2f cvo %(ws_0).2f %(ws_1).2f %(ws_2).2f %(ws_3).2f cvs %(alfa_land).2f lv %(dp_0).1f %(dp_1).1f %(dp_2).1f erns\n" % self)
        elif settings.computation == 'zeeuw':
            pool['unpalf'].write("ALFA id '%(alfa_def)s' nm '%(id)s' af %(alfa_land).2f %(ws_0).2f %(ws_1).2f %(ws_2).2f %(ws_3).2f %(alfa_infiltratie).2f lv %(dp_0).1f %(dp_1).1f %(dp_2).1f alfa\n\n" % self)
            # ook zoiets

    def computeAlfaFields(self, peilgebied, prefix, suffix):
        """prefix is one of: ['ernst_', 'zeeuw_']
        suffix is one of: ['_uu', '_ur']
        """
        self['alfa_infiltratie'] = peilgebied[prefix + 'InfOpenwater' + suffix]
        self['alfa_land'] = peilgebied[prefix + 'OppAfvoer' + suffix]

        if peilgebied['DiepteLaaggrens34' + suffix] > 0:
            # we hebben 4 lagen
            weerstanden = (peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag2' + suffix], peilgebied[prefix + 'Laag3' + suffix], peilgebied[prefix + 'Laag4' + suffix],)
            dieptes = (peilgebied['DiepteLaaggrens12' + suffix], peilgebied['DiepteLaaggrens23' + suffix], peilgebied['DiepteLaaggrens34' + suffix],)

        elif peilgebied['DiepteLaaggrens23' + suffix] > 0:
            # we hebben 3 lagen
            weerstanden = (peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag2' + suffix], peilgebied[prefix + 'Laag3' + suffix],)
            dieptes = (0, peilgebied['DiepteLaaggrens12' + suffix], peilgebied['DiepteLaaggrens23' + suffix],)

        elif peilgebied['DiepteLaaggrens12' + suffix] > 0:
            # we hebben 2 lagen
            weerstanden = (peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag2' + suffix],)
            dieptes = (0, 0, peilgebied['DiepteLaaggrens12' + suffix],)

        else:
            # we hebben één laag
            weerstanden = (peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix], peilgebied[prefix + 'Laag1' + suffix],)
            dieptes = (0, 0, 0,)

        self['ws_0'], self['ws_1'], self['ws_2'], self['ws_3'] = weerstanden
        self['dp_0'], self['dp_1'], self['dp_2'] = dieptes

Onverhard._Onverhard__super = super(Onverhard)


class OnverhardLand(Onverhard):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing OnverhardLand")
        kwargs.setdefault('id', peilgebied['id'] + '_ur')
        self.__super.__init__(peilgebied, **kwargs)
        self['ycoord'] += 25
        self.update({
                'area_grass': int(float(peilgebied['grass_area']) * 10000),
                'area_nature': int(float(peilgebied['nature_area']) * 10000),
                'area_misc': 0,
                'area': int((float(peilgebied['grass_area']) * 10000) +
                            int(float(peilgebied['nature_area']) * 10000)),
                'groundw_area': (int(float(peilgebied['nature_area']) * 10000) +
                                  int(float(peilgebied['grass_area']) * 10000)),
                'use_scurve': settings.getfloat('globals', 'use_scurve'),
                'land_storage': peilgebied['maxBergingLand'],
                'initial_land_storage': peilgebied['bergingLandIni'],
                })
        self['kwel'] = kwelwegzijging(peilgebied['kwel_wegzijgingLand'], peilgebied['kwelstroomLand'])

        self.computeAlfaFields(peilgebied, settings.computation + '_', '_ur')

OnverhardLand._OnverhardLand__super = super(OnverhardLand)


class OnverhardSted(Onverhard):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing OnverhardSted")
        kwargs.setdefault('id', peilgebied['id'] + '_uu')
        self.__super.__init__(peilgebied, **kwargs)
        self['ycoord'] -= 25
        self.update({
                'area_grass': 0,
                'area_nature': 0,
                'area_misc': int(peilgebied['onverhardsted_area'] * 10000),
                'area': int(peilgebied['onverhardsted_area'] * 10000),
                'groundw_area': (int(float(peilgebied['onverhardsted_area']) * 10000) +
                                 int(float(peilgebied['kas_area']) * 10000) +
                                 int(float(peilgebied['verhard_area']) * 10000)),
                'use_scurve': False,
                'land_storage': peilgebied['maxBergingSted'],
                'initial_land_storage': peilgebied['bergingStedIni'],
                })
        self['kwel'] = kwelwegzijging(peilgebied['kwel_wegzijgingSted'], peilgebied['kwelstroomSted'])

        self.computeAlfaFields(peilgebied, settings.computation + '_', '_uu')

OnverhardSted._OnverhardSted__super = super(OnverhardSted)


class Verhard(SobekNode):

    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing Verhard")
        kwargs.setdefault('mt', 1)
        kwargs.setdefault('nt', 43)
        kwargs.setdefault('type_id', "3B_PAVED")
        kwargs.setdefault('id', peilgebied['id'] + '_pu')
        self.__super.__init__(peilgebied=peilgebied, **kwargs)
        self.update({
                'area': int(peilgebied['verhard_area'] * 10000),
                'level': peilgebied['maaiveldverh'],
                'storage_def': 'sd_' + peilgebied['id'],
                'meteo_station': peilgebied['rainstation'],
                'mixed_cap': peilgebied['afvoercapriool'] / 3600,
                'number_people': peilgebied['aantalInw'],
                'xcoord': peilgebied['xcoord'] - 25,
                'ycoord': peilgebied['ycoord'],
                'ini_salt_concentration': peilgebied['iniSaltConc'],
                'sewer_system_type': 0, # missing value - geen riolering
                'vgs_cap': 0,
                'sewer_storage': 0,
                'initial_sewer_storage': peilgebied['bergingRioolIni'],
                'street_storage': peilgebied['maxBergingStraat'],
                'paved_runoff_coefficient': peilgebied['paved_runoff_coefficient'],
                })

        if peilgebied['typeriool'].lower() == settings.get('dictionary.peilgebied.typeRiool', 'mixed').lower():
            self['mixed_cap'] += peilgebied['aantalinw'] * settings.getfloat('globals', 'waterusepppday') / 1000 / 10 / 3600
            self['sewer_system_type'] = 0
            self['sewer_storage'] = peilgebied['maxBergingRiool']
        elif peilgebied['typeriool'].lower() == settings.get('dictionary.peilgebied.typeRiool', 'separated').lower():
            self['vgs_cap'] = peilgebied['aantalinw'] * settings.getfloat('globals', 'waterusepppday') / 1000 / 10 / 3600
            self['sewer_system_type'] = 1
        elif peilgebied['typeriool'].lower() == settings.get('dictionary.peilgebied.typeRiool', 'impr_sep').lower():
            self['vgs_cap'] = peilgebied['aantalinw'] * settings.getfloat('globals', 'waterusepppday') / 1000 / 10 / 3600
            self['sewer_system_type'] = 2
            self['sewer_storage'] = peilgebied['maxBergingRioolVgs']
        else:
            log.warning("TypeRiool '%s' is not known for peilgebied %s.  recognized values are %s." % (peilgebied['typeriool'], peilgebied['id'], [v for (_, v) in settings.items('dictionary.peilgebied.typeRiool')]))

        # TODO 20080721 be careful here, if we add a new fictive wwtp,
        # there's no 'zuivering' field in the peilgebied, but there's
        # the fictive wwtp connected to the pu...
        if peilgebied['zuivering'] and peilgebied['zuivering'].lower() == settings.get('dictionary.peilgebied.naam', 'boundary').lower():
            self['qo'] = '0 0'
        elif peilgebied['zuivering']:
            self['qo'] = '2 2'
        else:  # openwater
            self['qo'] = '1 1'

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)
        if self.get('paved_runoff_coefficient'):
            self['runoff_spec'] = " ro 1 ru %(paved_runoff_coefficient)s qh ''" % self
        else:
            self['runoff_spec'] = ''
        pool['pav3b'].write("PAVE id '%(ID)s' ar %(area)i lv %(level).2f sd '%(storage_def)s' ss %(sewer_system_type)s qc 0 %(mixed_cap).5f %(vgs_cap).5f qo %(qo)s ms '%(meteo_station)s' is %(ini_salt_concentration).2f np %(number_people)i dw 'alg_dwa'%(runoff_spec)s pave\n" % self)

        pool['pavsto'].write("STDF id '%(storage_def)s' nm '%(id)s' ms %(street_storage).1f is 0 mr %(sewer_storage).1f 0 ir %(initial_sewer_storage).1f 0 stdf\n" % self)

Verhard._Verhard__super = super(Verhard)


class OpenWater(SobekNode):
    def __init__(self, peilgebied, **kwargs):
        log.log(5, "initializing OpenWater")
        #"create the object from peilgebied properties"

        kwargs.setdefault('mt', 4)
        kwargs.setdefault('nt', 46)
        kwargs.setdefault('type_id', "3B_OPENWATER")
        kwargs.setdefault('id', peilgebied['id'] + '_ow')
        self.__super.__init__(peilgebied=peilgebied, **kwargs)
        peilgebied['ow'] = self

        storage_level = [0 for i in range(6)]
        storage_opp = [0 for i in range(6)]

        self['min_streefpeil'] = min(peilgebied['winterPeil'], peilgebied['zomerPeil'])
        self['max_streefpeil'] = max(peilgebied['winterPeil'], peilgebied['zomerPeil'])

        waterpeilstijgingsmodel = settings.get('globals', 'waterpeilstijgingsmodel', 'taludhelling').lower()
        log.debug('waterpeilstijgingsmodel = %s' % waterpeilstijgingsmodel)
        if (waterpeilstijgingsmodel == "openwatercurve"):
            storage_level[0] = peilgebied['maaiveldhgt'][0] - 0.20
            storage_level[1] = peilgebied['maaiveldhgt'][0]
            storage_level[2] = peilgebied['maaiveldhgt'][2]
            storage_level[3] = peilgebied['maaiveldhgt'][5]
            storage_level[4] = peilgebied['maaiveldhgt'][10]
            storage_level[5] = peilgebied['maaiveldhgt'][20]

            storage_opp[0] = peilgebied['openwater_area'] * 10000
            storage_opp[1] = peilgebied['openwater_area'] * 10000
            storage_opp[2] = peilgebied['openwater_area'] * 10000 + 0.02 * (peilgebied['total_area'] - peilgebied['openwater_area']) * 10000
            storage_opp[3] = peilgebied['openwater_area'] * 10000 + 0.05 * (peilgebied['total_area'] - peilgebied['openwater_area']) * 10000
            storage_opp[4] = peilgebied['openwater_area'] * 10000 + 0.10 * (peilgebied['total_area'] - peilgebied['openwater_area']) * 10000
            storage_opp[5] = peilgebied['openwater_area'] * 10000 + 0.20 * (peilgebied['total_area'] - peilgebied['openwater_area']) * 10000

        elif (waterpeilstijgingsmodel == "taludhelling"):
            self['insteek_wg'] = peilgebied['insteek_wg']
            storage_level[0] = self['min_streefpeil'] - 0.2
            storage_level[1] = self['min_streefpeil']
            storage_level[2] = (1 * self['insteek_wg'] + 3 * self['min_streefpeil']) / 4
            storage_level[3] = (2 * self['insteek_wg'] + 2 * self['min_streefpeil']) / 4
            storage_level[4] = (3 * self['insteek_wg'] + 1 * self['min_streefpeil']) / 4
            storage_level[5] = self['insteek_wg']

            storage_opp[0] = peilgebied['openwater_area'] * 10000
            storage_opp[1] = peilgebied['openwater_area'] * 10000
            storage_opp[2] = peilgebied['openwater_area'] * 10000 + 0.25 * (self['insteek_wg'] - self['min_streefpeil']) * peilgebied['taludHelling'] / 100 * peilgebied['openwater_area'] * 10000
            storage_opp[3] = peilgebied['openwater_area'] * 10000 + 0.50 * (self['insteek_wg'] - self['min_streefpeil']) * peilgebied['taludHelling'] / 100 * peilgebied['openwater_area'] * 10000
            storage_opp[4] = peilgebied['openwater_area'] * 10000 + 0.75 * (self['insteek_wg'] - self['min_streefpeil']) * peilgebied['taludHelling'] / 100 * peilgebied['openwater_area'] * 10000
            storage_opp[5] = peilgebied['openwater_area'] * 10000 + 1.00 * (self['insteek_wg'] - self['min_streefpeil']) * peilgebied['taludHelling'] / 100 * peilgebied['openwater_area'] * 10000

        self.update({
                'bottom_level': self['min_streefpeil'] + peilgebied['waterBodemDiepte'],

                'kwel': kwelwegzijging(peilgebied['kwel_wegzijgingWater'], peilgebied['kwelstroomWater']),

                'seepage_def': "sp_%s" % peilgebied['ID'],
                'targetlevel_def': "tl_%s" % peilgebied['ID'],
                'meteo_station': peilgebied['rainstation'],

                'ini_salt_concentration': peilgebied['iniSaltConc'],
                'kwel_salt_concentration': peilgebied['kwelSaltConc'],

                'kwel_resist_C': settings.getfloat('globals', 'kwelresistC'),
                'winterpeil': peilgebied['winterPeil'],
                'zomerpeil': peilgebied['zomerPeil'],
                'date_zomwin': str(peilgebied['datumZomerWinter']),
                'date_winzom': str(peilgebied['datumWinterZomer']),
                'max_peil': peilgebied['maxPeil'],


                'overgangstijd_ZP_WP_dgn': peilgebied['overgangstijd_ZP_WP_dgn'],

                'storage_level_string': " ".join(['%0.2f' % i for i in storage_level]),
                'storage_opp_string': " ".join(['%0.0f' % i for i in storage_opp]),
                'xcoord': peilgebied['xcoord'],
                'ycoord': peilgebied['ycoord'],
                })

        if self['overgangstijd_ZP_WP_dgn'] <= 0:
            # abrupt change.  level is either constant or discontinuous. __¯¯¯___
            self['blokfunctie'] = 1
        else:
            # two levels but linear interpolation between them:  __/¯¯\__
            self['blokfunctie'] = 0

    def getNextKwkPosition(self):
        if 'nextkwkpos' not in self:
            self['nextkwkpos'] = [self['xcoord'] + 25, self['ycoord']]
        self['nextkwkpos'][1] += 25
        return self['nextkwkpos']

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)

        pool['openw3b'].write("OPWA id '%(ID)s' ml %(max_peil)0.2f rl 0 al 2 na 6 ar %(storage_opp_string)s lv %(storage_level_string)s bl %(bottom_level).2f tl 1 '%(targetlevel_def)s' sp '%(seepage_def)s' ms '%(meteo_station)s' is %(ini_salt_concentration).2f opwa\n" % self)
        pool['openwsep'].write("SEEP id '%(seepage_def)s' nm '%(ID)s' co 1 sp %(kwel).2f ss %(kwel_salt_concentration).2f cv %(kwel_resist_C).2f seep\n" % self)
        # going to write in openwtbl
        toWrite = []
        toWrite.append("OW_T id '%(targetlevel_def)s' nm '%(ID)s' PDIN %(blokfunctie)i 1 '365;00:00:00' pdin TBLE\n" % self)

        # startlevel is always 'winterpeil' and always on 2000-01-01
        toWrite.append(" '2000/01/01;00:00:00' %.2f <\n" % self['winterpeil'])

        if self['blokfunctie']:
            #  snelle overgang: dus maar drie elementen in de table:
            # yyyy-01-01_, yyyy-m1-d1^, yyyy-m2-d2_

            if settings.get('range.peilgebied', 'datumWinterZomer').lower() == 'mmdd':
                toWrite.append(" '2000/%s/%s;00:00:00' %.2f <\n" % (
                        self['date_winzom'][0:2], self['date_winzom'][2:4], self['zomerpeil']))

                toWrite.append(" '2000/%s/%s;00:00:00' %.2f <\n" % (
                        self['date_zomwin'][0:2], self['date_zomwin'][2:4], self['winterpeil']))
            else:
                toWrite.append(" '2000/%s/%s;00:00:00' %.2f <\n" % (
                        self['date_winzom'][2:4], self['date_winzom'][0:2], self['zomerpeil']))

                toWrite.append(" '2000/%s/%s;00:00:00' %.2f <\n" % (
                        self['date_zomwin'][2:4], self['date_zomwin'][0:2], self['winterpeil']))

        else:
            # langzame overgang: elke overgang begint op het gegeven
            # tijdstip maar duurt overgangstijd_ZP_WP_dgn dagen...  the
            # linear interpolation is performed by sobek, instructed with
            # the above 'blokfunctie' parameter.

            # yyyy-01-01_ yyyy-m1-d1_ yyyy-m2-d2^ yyyy-m3-d3^ yyyy-m4-d4_

            import datetime
            duur = datetime.timedelta(self['overgangstijd_ZP_WP_dgn'])
            if settings.get('range.peilgebied', 'datumWinterZomer').lower() == 'mmdd':
                maand = self['date_winzom'] / 100
                dag = self['date_winzom'] % 100
            else:
                dag = self['date_winzom'] / 100
                maand = self['date_winzom'] % 100
            overgang = datetime.date(2000, maand, dag)

            toWrite.append(" '%s;00:00:00' %.2f <\n" % (
                        overgang.isoformat().replace('-', '/'), self['winterpeil']))
            overgang += duur
            toWrite.append(" '%s;00:00:00' %.2f <\n" % (
                        overgang.isoformat().replace('-', '/'), self['zomerpeil']))

            if settings.get('range.peilgebied', 'datumWinterZomer').lower() == 'mmdd':
                maand = self['date_zomwin'] / 100
                dag = self['date_zomwin'] % 100
            else:
                dag = self['date_zomwin'] / 100
                maand = self['date_zomwin'] % 100

            overgang = datetime.date(2000, maand, dag)

            toWrite.append(" '%s;00:00:00' %.2f <\n" % (
                        overgang.isoformat().replace('-', '/'), self['zomerpeil']))
            overgang += duur
            toWrite.append(" '%s;00:00:00' %.2f <\n" % (
                        overgang.isoformat().replace('-', '/'), self['winterpeil']))

        toWrite.append(" tble ow_t\n")
        pool['openwtbl'].write(''.join(toWrite))

OpenWater._OpenWater__super = super(OpenWater)


class Kunstwerk(SobekNode):

    def __init__(self, **kwargs):
        log.log(5, "initializing Kunstwerk")
        self.__super.__init__(**kwargs)
        if 'nm' not in self:
            self['nm'] = self['id']
        self['ca_1'] = 0
        self['cj_1'] = -1

        add_defaults_from_section('kunstwerk', self, settings, 'default.kunstwerk')
        section = ('default.' + self['soort']).lower()
        add_defaults_from_section('kunstwerk (%s)' % self['soort'], self, settings, section)

    def write(self, pool):
        "writes the object to the correct files in the pool"
        log.log(5, "Kunstwerk.write... %s" % self.dict)
        log.log(5, "STDS_format: %s" % self.STDS_format)
        self.__super.write(pool)
        pool['strdat'].write("STRU id '%(id)s' dd '%(struct_def)s' ca %(ca_1)s 0 0 0 cj '%(cj_1)s' '-1' '-1' '-1' stru\n" % self)
        pool['strdef'].write(self.STDS_format % self)

Kunstwerk._Kunstwerk__super = super(Kunstwerk)


class Inlaat:
    def __init__(self, **kwargs):
        log.log(5, "initializing Inlaat")
        self['struct_def'] = "inl_%s" % self['ID']


class Uitlaat:
    def __init__(self, **kwargs):
        log.log(5, "initializing Uitlaat")
        self['struct_def'] = "outl_%s" % self['ID']


# concrete classes

class Gemaal(Kunstwerk):

    def __init__(self, **kwargs):
        log.log(5, "initializing Gemaal")
        kwargs.setdefault('mt', 8)
        kwargs.setdefault('nt', 48)
        kwargs.setdefault('type_id', "3B_PUMP")
        self.__super.__init__(**kwargs)

Gemaal._Gemaal__super = super(Gemaal)


class InlaatGemaal(Gemaal, Inlaat):

    STDS_format = "STDS id '%(struct_def)s' nm '%(id)s' ty 8 in 1 dn 2 nc 2 pc %(gem_cap_low).6f %(gem_cap_add_cap_high).6f so 'onoff_inlet' stds\n"

    def __init__(self, **kwargs):
        log.log(5, "initializing InlaatGemaal")
        Gemaal.__init__(self, **kwargs)
        Inlaat.__init__(self, **kwargs)
        self['gem_cap_low'] = self['inlet_flow']
        self['gem_cap_add_cap_high'] = 0.0


class UitlaatGemaal(Gemaal, Uitlaat):

    STDS_format = "STDS id '%(struct_def)s' nm '%(id)s' ty 8 in 0 dn 1 nc 2 pc %(gem_cap_low).6f %(gem_cap_add_cap_high).6f so 'onoff_outlet' stds\n"

    def __init__(self, **kwargs):
        log.log(5, "initializing UitlaatGemaal")
        Gemaal.__init__(self, **kwargs)
        Uitlaat.__init__(self, **kwargs)
        self['gem_cap_low'] = self['gemaalLaag'] / 3600.0
        self['gem_cap_add_cap_high'] = (self['gemaalhoog'] - self['gemaallaag']) / 3600.0


class Stuw(Kunstwerk):
    def __init__(self, **kwargs):
        log.log(5, "initializing Stuw")
        kwargs.setdefault('mt', 9)
        kwargs.setdefault('nt', 49)
        kwargs.setdefault('type_id', "3B_WEIR")
        self.__super.__init__(**kwargs)
        log.log(5, "self.dict = %s", self.dict)
        log.log(5, "kwargs = %s", kwargs)

        self['stuw_crestlevel_2'] = 999
        self['stuw_crest_width_2'] = 999
        self['controller_def'] = 'weir_' + self['id']

        if self['controlType'] == settings.get('dictionary.kunstwerk.controlType', 'trap'):
            # controller_type = 1
            self['ca_1'] = 0
            self['cj_1'] = -1
            self['stuw_crestlevel_2'] = self['kruinHoogte_trap']
            self['stuw_crest_width_2'] = self['kruinBreedte_trap']
            self['write_to_cntl'] = False

        elif self['controlType'] == settings.get('dictionary.kunstwerk.controlType', 'auto'):
            # controller_type = 2
            self['ca_1'] = 1
            self['cj_1'] = self['controller_def']
            self['write_to_cntl'] = True
            self.CNTL_format = "CNTL id '%(controller_def)s' nm '%(ID)s' ty 12 mf %(maxflow).6f mf2 %(p_mf2).6f ml %(maxpeil).2f zmin -999.99 zmax 9999 md 999 cntl\n"

        elif self['controlType'] == settings.get('dictionary.kunstwerk.controlType', 'equal'):
            # controller_type = 3
            self['ca_1'] = 1
            self['cj_1'] = self['controller_def']
            self['write_to_cntl'] = True
            self.CNTL_format = "CNTL id '%(controller_def)s' nm '%(ID)s' ty 16 mf 0.000000 mf2 %(p_mf2).6f zmin -999.99 zmax 9999 cntl\n"

        else:
            if self['controlType'] != settings.get('dictionary.kunstwerk.controlType', 'fixed'):
                log.warning('unrecognized controlType %(controlType)s - assuming fixed weir' % self)
            # controller_type = 1
            self['ca_1'] = 0
            self['cj_1'] = -1
            self['write_to_cntl'] = False

        if self['stuw_crest_width_2'] > 998.9:
            self['wt'] = 1
        else:
            self['wt'] = 3

    def handle_inbound_edge(self, edge):
        bn, en = edge[:2]
        log.debug('bovenstroomsknoop is een %s en heeft id %s' % (str(type(bn)), bn['id']))
        log.debug('bovenstroomsknoop hoort bij peilgebied %s' % bn['peilgebied']['id'])
        bspg = bn['peilgebied']
        self['maxpeil'] = bspg['maxpeil']
        log.debug('Als ik na deze regel  crash, dan betekent dat dat je de volgende kolommen met een defaultwaarde moet invullen: %r %r %r' % (bspg['AFVCAPHA'], bspg['TOTAFVOPPERVLAK'], self['deelVanAfvoer']))
        self['maxflow'] = (bspg['AFVCAPHA'] * bspg['TOTAFVOPPERVLAK'] * self['deelVanAfvoer'] / 100) / 3600
        self['p_mf2'] = 10 * self['maxflow']

    def write(self, pool):
        "writes the object to the correct files in the pool"

        self.__super.write(pool)
        if self['write_to_cntl']:
            pool['contrdef'].write(self.CNTL_format % self)

Stuw._Stuw__super = super(Stuw)


class InlaatStuw(Stuw, Inlaat):

    def __init__(self, **kwargs):
        Stuw.__init__(self, **kwargs)
        Inlaat.__init__(self, **kwargs)

    STDS_format = "STDS id '%(struct_def)s' nm '%(ID)s' ty 9 in 1 dc %(dischcoef).1f cl %(kruinhoogte).2f cl2 %(stuw_crestlevel_2).2f cw %(kruinbreedte).2f cw2 %(stuw_crest_width_2).2f cp %(powercoef).2f rt 1 wt %(wt)i fl %(inlet_flushing_flow).2f so 'onoff_inlet_stuw' stds\n"

InlaatStuw._InlaatStuw__super = super(InlaatStuw)


class UitlaatStuw(Stuw, Uitlaat):

    def __init__(self, **kwargs):
        Stuw.__init__(self, **kwargs)
        Uitlaat.__init__(self, **kwargs)

    STDS_format = "STDS id '%(struct_def)s' nm '%(ID)s' ty 9 in 0 dc %(dischcoef).1f cl %(kruinhoogte).2f cl2 %(stuw_crestlevel_2).2f cw %(kruinbreedte).2f cw2 %(stuw_crest_width_2).2f cp %(powercoef).2f rt 0 wt %(wt)i stds\n"


UitlaatStuw._UitlaatStuw__super = super(UitlaatStuw)

# ------------------------------------------------------------

# "edge" classes.  sobek keyword: BRCH (in sobek edges are called "branches")


# abstract base classes

class SobekEdge(Dict):
    def __init__(self, **kwargs):
        log.log(5, "initializing SobekEdge")
        kwargs.setdefault('mt', 0)
        kwargs.setdefault('bt', 0)
        kwargs.setdefault('type_id', "-999")
        kwargs.setdefault('tubed', '')
        self.__super.__init__(**kwargs)

    def complete_with_node_info(self, begin_node, end_node):
        self.update({'bn': begin_node['id'], 'en': end_node['id']})
        if begin_node['peilgebied'] == end_node['peilgebied']:
            if begin_node['peilgebied'] is None:
                self['id'] = '%(bn)s_%(en)s' % self
            else:
                second_half = end_node['id']
                if second_half.find('_') == -1:
                    second_half = '_' + second_half
                self['id'] = begin_node['id'] + second_half[second_half.rfind('_'):]
        else:
            if isinstance(end_node, Kunstwerk) and begin_node['peilgebied'] is not None:
                self['id'] = end_node['id'] + begin_node['id'][begin_node['id'].rfind('_'):] + '_kw'
            elif isinstance(begin_node, Kunstwerk) and end_node['peilgebied'] is not None:
                self['id'] = begin_node['id'] + '_kw' + end_node['id'][end_node['id'].rfind('_'):]
            elif isinstance(begin_node, Zuivering):
                self['id'] = begin_node['id'] + '_wwtp_boundary'
            else:
                self['id'] = begin_node['id'] + '_' + end_node['id']

        log.debug('just updated id of edge: %(id)s' % self)

    def write(self, pool):
        "common part called by all derived classes"

        pool['linktp'].write("BRCH id '%(ID)s' ri '-1' mt 1 '%(tubed)s' bt %(bt)i ObID '%(type_id)s' bn '%(bn)s' en '%(en)s' brch\n" % self)

SobekEdge._SobekEdge__super = super(SobekEdge)


class OppervlakLink(SobekEdge):
    def __init__(self, **kwargs):
        log.log(5, "initializing OppervlakLink")
        kwargs.setdefault('mt', 14)
        kwargs.setdefault('bt', 17)
        kwargs.setdefault('type_id', "3B_LINK")
        self.__super.__init__(**kwargs)
        self['tubed'] = 0

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)

OppervlakLink._OppervlakLink__super = super(OppervlakLink)


class RioolLink(SobekEdge):
    def __init__(self, **kwargs):
        log.log(5, "initializing RioolLink")
        kwargs.setdefault('mt', 14)
        kwargs.setdefault('bt', 18)
        kwargs.setdefault('type_id', "3B_LINK_RWZI")
        self.__super.__init__(**kwargs)
        self['tubed'] = 1

    def write(self, pool):
        "writes the object to the correct files in the pool"
        self.__super.write(pool)

RioolLink._RioolLink__super = super(RioolLink)


# ------------------------------------------------------------

def kunstwerkFromDict(d):
    translate = {'STUW': UitlaatStuw,
                 'GEMAAL': UitlaatGemaal,
                 'INLAATSTUW': InlaatStuw,
                 'INLAATGEMAAL': InlaatGemaal,
                 }
    return translate[d['soort'].upper()](init=d)


class HardCodedConfig:
    def __init__(self, section_name, items):
        self.content = {}
        self.content[section_name.lower()] = dict(items)

    def options(self, section_name):
        return self.content.get(section_name.lower(), {})

    def getfloat(self, section, field):
        return float(self.content[section.lower()][field.lower()])


def add_defaults_from_section(object_type, obj, config, section):
    def gettyped(config, section, field):
        try:
            return config.getfloat(section, field)
        except:
            pass
        try:
            return config.getint(section, field)
        except:
            pass
        return config.get(section, field)

    for field_name in config.options(section):
        if field_name not in obj or obj[field_name] in [None, '']:
            value = gettyped(config, section, field_name)
            if isinstance(value, types.StringTypes) and value.startswith('NO_DATA'):
                typename_of_nodata = value[len("NO_DATA."):]
                if not typename_of_nodata:
                    typename_of_nodata = "char"
                value = gettyped(config, "value.missing", typename_of_nodata)
                if value == "None":
                    value = ""
            log.debug("fixing missing value: %s(%s)['%s'] <- %s" % (object_type, obj['id'], field_name, value))
            obj[field_name] = value


# ------------------------------------------------------------

def main(options, args):

    log.debug('entering')

    log.debug("connecting to ArcView...")
    # the following three steps are necessary to connect to ArcView...
    # failing to do these, it will fail with rather obscure error messages...

    import arcgisscripting
    gp = arcgisscripting.create()
    gp.setproduct("ArcView")

    log.debug("connected to ArcView")

    # split input arguments - may raise a ValueError exception
    (peilgebieden_name, dataset, afvoer_name,
     kunstwerken_name, koppelpunten_name, inifile_name,
     output_dir, weerstand, model) = args

    log.debug("translating all '#' to None in arguments.")

    # some arguments are optional...
    if peilgebieden_name == '#':
        peilgebieden_name = None
    if afvoer_name == '#':
        kunstwerken_name = afvoer_name = None
    if kunstwerken_name == '#':
        kunstwerken_name = None
    if koppelpunten_name == '#':
        koppelpunten_name = None

    log.debug("use args: %s" % str((peilgebieden_name, dataset, afvoer_name,
                                    kunstwerken_name, koppelpunten_name,
                                    inifile_name, output_dir,
                                    weerstand, model)))

    global settings
    settings = Config(inifile_name)
    settings.computation = weerstand.lower()

    # validate the settings or die
    # RR/CF/MX (RR-puur, RR-CF-direct, combined)
    assert(model in ['RR', 'RR_CF', 'RR+RR_CF'])

    if model == 'RR_CF':
        if afvoer_name or kunstwerken_name:
            log.info("model is RR_CF: kunstwerken are only used for indirectly connected peilgebieden")
    elif model == 'RR':
        if koppelpunten_name:
            log.warning("model is RR: ignoring koppelpunten")
        koppelpunten_name = None
    else:
        assert(koppelpunten_name is not None)
        #assert(kunstwerken_name is not None)

    log.debug("going to convert using model '%s'" % model)

    check = [True, True]
    # read the peilgebied dictionary from the database
    if peilgebieden_name:
        log.info("reading geo-table %s" % nens.gp.loggable_name(peilgebieden_name))
        global peilgebieden
        peilgebieden = nens.gp.get_table(
            gp, peilgebieden_name,
            conversion=settings.items('column.peilgebied'))
        log.debug("peilgebieden table is this large: %d" % len(peilgebieden))
        log.debug("first peilgebied has %d fields now" % len(peilgebieden[0]))
        log.debug("columns are: %s" % str(peilgebieden[0].keys()))

        # complete the peilgebied information...
        for item_name in dataset.split(';'):
            log.info("joining to table '%s' on key 'id'" % nens.gp.loggable_name(item_name))

            # get the table data...
            item = nens.gp.get_table(
                gp, item_name,
                conversion=settings.items('column.peilgebied'))
            log.debug("%d rows and %d columns for table '%s'" % (len(item), len((item + [{}])[0]), item_name,))

            # join it to our data
            peilgebieden = nens.gp.join_dicts(peilgebieden, item, 'id')

            log.debug("first peilgebied has %d fields after the join" % len(peilgebieden[0]))
            log.debug("columns are: %s" % str(peilgebieden[0].keys()))

                # transform to list of case-insensitive dictionaries
        peilgebieden = [Peilgebied(init=k) for k in peilgebieden]
        peilgebieden_dict = dict([(p['id'], p) for p in peilgebieden])

        # TODO: validate the peilgebied information, generating
        # warning and stopping in case of error.  at this point
        # "validate" means assign default values and check that
        # required fields have been assigned.

        hard_coded_defaults = HardCodedConfig('default.peilgebied',
                                              {'openwater_area': 0.0,
                                               'verhard_area': 0.0,
                                               'onverhardsted_area': 0.0,
                                               'onverhardland_area': 0.0,
                                               'kas_area': 0.0,
                                               'grass_area': 0.0,
                                               'nature_area': 0.0,
                                               })

        for peilgebied in peilgebieden:
            for field_name in required_fields['peilgebied']:
                if field_name not in peilgebied:
                    log.warning("peilgebied %s misses required field %s" % (peilgebied['id'], field_name))
                    check[0] = False

            log.debug('add defaults from configuration')
            add_defaults_from_section('peilgebied', peilgebied, settings, 'default.peilgebied')
            log.debug('add hard coded defaults')
            add_defaults_from_section('peilgebied', peilgebied, hard_coded_defaults, 'default.peilgebied')

            for field_name in settings.options('range.peilgebied'):
                check[0] &= checkConstraints(peilgebied, field_name, settings)

        if not check[0]:
            log.error("peilgebieden did not pass validation. check above warnings.")

    # read the kunstwerk dictionary from the database
    if afvoer_name:
        log.info("reading afvoer table %s" % nens.gp.loggable_name(afvoer_name))
        afvoer = nens.gp.get_table(
            gp, afvoer_name,
            conversion=settings.items('column.kunstwerk'))
        log.debug("first afvoer has %d fields now" % len(afvoer[0]))
        log.debug("columns are: %s" % str(afvoer[0].keys()))

        # complete the kunstwerk information
        if kunstwerken_name:
            log.info("joining to geo-table %s on key 'id'" % nens.gp.loggable_name(kunstwerken_name))
            kunstwerken = nens.gp.get_table(
                gp, kunstwerken_name,
                conversion=settings.items('column.kunstwerk'))
            kunstwerken = nens.gp.join_dicts(afvoer, kunstwerken, 'id')
            log.debug("%d rows and %d columns for table '%s'" % (len(kunstwerken), len((kunstwerken + [{}])[0]), kunstwerken_name,))
        else:
            kunstwerken = afvoer

        log.debug("first afvoer has %d fields now" % len(afvoer[0]))
        log.debug("columns are: %s" % str(afvoer[0].keys()))

        # transform to list of case-insensitive dictionaries
        kunstwerken = [kunstwerkFromDict(k) for k in kunstwerken]

        # validate the kunstwerk information, generating warning and
        # stopping in case of error.

        for kunstwerk in kunstwerken:
            for field_name in required_fields['kunstwerk']:
                if field_name not in kunstwerk:
                    log.warning("kunstwerk %s misses required field %s" % (kunstwerk['id'], field_name))
                    check[1] = False
            for field_name in settings.options('range.kunstwerk'):
                check[1] &= checkConstraints(kunstwerk, field_name, settings)

        if not check[1]:
            log.error("kunstwerken did not pass validation. check above warnings.")
    else:
        kunstwerken = []

    if not check[0] or not check[1]:
        log.error("a fundamental check failed: aborting now.  please correct the above errors and try again.")
        return None

    # hold here all koppelpunten...  associate the name of the
    # peilgebied with the koppelpunt for external kunstwerken.
    koppelpunten = {}

    # if RR_CF: indicate a fictive 'koppelpunt' wherever we miss it.
    # we can go on as if we were in the MX case.
    if model == 'RR_CF':
        missingnode_name = 0
    else:
        missingnode_name = None

    # create a directed graph in which edges can be associated to
    # extra information
    g = networkx.DiGraph()

    # zuiveringen contains all Zuivering objects created, by name.
    zuiveringen = {}

    for peilgebied in peilgebieden:

        log.debug('examining peilgebied %s: %s' % (peilgebied['id'], peilgebied.dict,))

        openwater = OpenWater(peilgebied)
        openwater['area'] = max(peilgebied['openwater_area'],
                                settings.getfloat('threshold.peilgebied', 'openwater_area'))

        coupled_to_openwater = []
        forget_about_openwater = False
        nodes_for_peilgebied = {}

        for Type in [Kas, OnverhardLand, OnverhardSted, Verhard]:
            # couple to openwater
            type_name = Type.__name__.lower()
            # if area above threshold, create it and connect it to
            # koppelpunt or openwater, depending on whether koppelpunt
            # exists or not.
            log.debug("area of %s for %s is %s" % (type_name, peilgebied['id'], peilgebied[type_name + '_area']))
            if type_name == 'onverhardland':
                input_area = float(peilgebied['grass_area']) + float(peilgebied['nature_area'])
            else:
                input_area = float(peilgebied[type_name + '_area'])

            if (input_area >= settings.getfloat('threshold.peilgebied', type_name + '_area')):

                # koppelpunt_name is None if model is RR or if, in
                # RR+RR_CF model with cfDirect, no "knoop" has been
                # specified for this type for this peilgebied
                log.debug("evaluates cfDirect field %s(%s) to True? %s" % (type(peilgebied['cfDirect']), peilgebied['cfDirect'], bool(peilgebied['cfDirect']),))
                if peilgebied['cfDirect']:
                    koppelpunt_name = peilgebied.get(type_name + '_knoop', missingnode_name)
                    log.debug('looking into peilgebied %s for field %s, got %s(%s)' % (peilgebied['id'], type_name + '_knoop', type(koppelpunt_name), koppelpunt_name,))
                else:
                    koppelpunt_name = None

                if isinstance(koppelpunt_name, types.StringTypes):
                    if koppelpunt_name:
                        id = koppelpunt_name
                    else:
                        id = 'cf_node_' + sequential()
                    koppelpunten.setdefault(id, KoppelPunt(id=id, peilgebied=peilgebied))
                    log.debug("adding edge from %s to %s" % (type_name, id))
                    nodes_for_peilgebied[type_name] = Type(peilgebied)
                    g.add_edge(nodes_for_peilgebied[type_name],
                               koppelpunten[id],
                               OppervlakLink().as_dict())
                    # if any object is connected to koppelpunt instead of
                    # to openwater, forget about the openwater component
                    forget_about_openwater = True
                else:
                    coupled_to_openwater.append(Type(peilgebied))

        # if any object is connected to koppelpunt, create an
        # externKwkKnp, otherwise store openwater in externKwkKnp

        if forget_about_openwater:
            desc = "CF node"
            externKwkKnp = KoppelPunt(peilgebied=peilgebied)
        else:
            desc = "openwater"
            externKwkKnp = openwater
            koppelpunten[peilgebied['id']] = openwater

        for obj in coupled_to_openwater:
            type_name = obj.__class__.__name__.lower()
            log.debug("adding edge from %s to %s" % (type_name, desc))
            nodes_for_peilgebied[type_name] = obj
            g.add_edge(obj, externKwkKnp, OppervlakLink().as_dict())

        # rioolaansluitingen

        if peilgebied['typeriool']:
            if 'verhard' not in nodes_for_peilgebied:
                log.warning('settings dictate a waste water connection, but no paved area has been created')
            else:
                log.debug('creating waste water connections')
                obj = nodes_for_peilgebied['verhard']

                if peilgebied['zuivering'] and peilgebied['zuivering'] != settings.get('dictionary.peilgebied.naam', 'boundary'):
                    if peilgebied['zuivering'] not in zuiveringen:
                        log.debug("create Zuivering '%s' and connect it to Boundary via RioolLink."
                                  % peilgebied['zuivering'])
                        zuivering = Zuivering(peilgebied)
                        zuiveringen[peilgebied['zuivering']] = zuivering
                        g.add_edge(zuivering, Boundary(bl="0 0.00", isc=0, cause=zuivering), RioolLink().as_dict())
                    log.debug("connect 'verhard' object to zuivering '%s' via RioolLink."
                              % peilgebied['zuivering'])
                    zuivering = zuiveringen[peilgebied['zuivering']]
                    g.add_edge(obj, zuivering, RioolLink().as_dict())

                else:
                    log.debug("connect 'verhard' object to Boundary via RioolLink.")
                    g.add_edge(obj, Boundary(bl='0 0.00', isc=0, cause=obj), RioolLink().as_dict())

    # prepare the kunstwerk dictionary for RR/RR_CF/MX
    # if RR: zero all 'cfkoppelknoop' information

    if model == 'RR':
        for k in kunstwerken:
            k['cfkoppelknoop'] = None
    elif model == 'RR_CF' and kunstwerken:
        log.info("kunstwerken dictionary not empty while doing a RR_CF computation.  if you're not doing 'indirect', you will be warned about kunstwerken that have to be ignored (relative to a directly connected peilgebied).")

    for kunstwerk in kunstwerken:
        if model == 'RR':
            naarField = 'naarRRKnoop'
        elif model == 'RR_CF':
            naarField = 'naarCFKnoop'
        else:
            naarField = 'naar%sKnoop' % kunstwerk['typeNaarKnoop']

        vanknoop, naarknoop = kunstwerk['vanknoop'], kunstwerk[naarField]
        log.debug(("%(soort)s %(id)s: %(vanknoop)s -> %(" + naarField + ")s") % kunstwerk)

        # vanknoop and naarknoop are the names of peilgebieden or of
        # CF koppelpunten.  if it's a KoppelPunt, that's what you
        # need.  if it's a Peilgebied, use the koppelpunten dictionary
        # to get the koppelpunt of the named peilgebied (will be
        # OpenWater or again KoppelPunt.)  whichever the case, after
        # translation of the name you remain at both ends of the
        # kunstwerk with OpenWater or KoppelPunt.  notice that also
        # the case 'Boundary' is to be considered a CF KoppelPunt.

        # setting coordinates taking them from the OpenWater of
        # preferably the 'vanknoop' and otherwise the 'naarknoop'
        # peigebied.  remove the kunstwerk if no OpenWater.
        connecting = [n for n in [vanknoop, naarknoop]
                      if n in koppelpunten and isinstance(koppelpunten[n], OpenWater)]
        if len(connecting) == 0:
            log.warn("%(soort)s %(id)s is not linking any OpenWater.  not adding it to the network." % kunstwerk)
            continue

        if 'xcoord' not in kunstwerk:
            # using the first one (maybe the only one)
            log.debug('assigning fictive coordinates to %(soort)s %(id)s' % kunstwerk)
            kunstwerk['xcoord'], kunstwerk['ycoord'] = koppelpunten[connecting[0]].getNextKwkPosition()

        # here we have a geographically localized kunstwerk coupling
        # things...  we still don't know what kind of things...  let's
        # translate the names of the two extremes into
        # OpenWater/KoppelPunt/Boundary

        for extreme in [vanknoop, naarknoop]:
            # if extreme is 'boundary', create new boundary node
            if extreme == settings.get('dictionary.peilgebied.naam', 'boundary'):
                log.debug("translating %s to Boundary object" % extreme)
                koppelpunten[extreme] = Boundary(bl="0 %(boundPeil).2f" % kunstwerk,
                                                 isc=0, cause=kunstwerk)
            elif extreme not in peilgebieden_dict:
                # it's the name of a KoppelPung, which we probably must add...
                if extreme in koppelpunten:
                    log.debug("reusing already created KoppelPunt")
                else:
                    koppelpunten[extreme] = KoppelPunt(id=extreme,
                                                       peilgebied=peilgebieden_dict[connecting[0]],
                                                       xcoord=kunstwerk['xcoord'] + 25,
                                                       ycoord=kunstwerk['ycoord'])

        try:
            # add kunstwerk to graph
            g.add_edge(koppelpunten[vanknoop], kunstwerk, OppervlakLink().as_dict())
            g.add_edge(kunstwerk, koppelpunten[naarknoop], OppervlakLink().as_dict())
            log.debug("kunstwerk added to graph: %s" % kunstwerk.as_dict())
        except KeyError, e:
            kunstwerk['missing'] = e
            log.warning("kunstwerk %(soort)s %(id)s discarded: missing %(missing)s" % kunstwerk)

    log.info("spreading network information")
    for edge in g.edges():
        (begin_node, end_node) = edge[:2]
        info = g[begin_node][end_node]
        info = dict_to_Dict(info)
        info.complete_with_node_info(begin_node, end_node)
        begin_node.handle_outbound_edge(edge)
        end_node.handle_inbound_edge(edge)

    log.info('validating the network')
    for node in [item for item in g.nodes() if isinstance(item, (OpenWater, Verhard, Onverhard, Kas))]:
        # check node is not connected to any 'cf_node_' node: these
        # are fictive nodes that have been generated just to be
        # removed here...
        fictive_neighbors = [item for item in g.neighbors(node)
                             if isinstance(item, (KoppelPunt, Boundary))
                             and item['id'].startswith('cf_node_')]
        for fn in fictive_neighbors:
            log.warn('node %s has link to non existing CF node' % node['id'])
            g.remove_node(fn)

        # check that node is not directly connected to both a named CF
        # node and a boundary node.  this test can be limited to paved
        # urban nodes.

        # TODO 20080721 there must be some option so that the user can choose
        # between this warning and creating a new fictive wwtp in
        # order to connect the paved urban node to boundary via
        # sewage.
        if isinstance(node, Verhard):
            neighbors = [item for item in g.neighbors(node) if isinstance(item, (KoppelPunt, Boundary))]
            if len(neighbors) > 1:
                log.warn('node %s is directly coupled to too many Boundary nodes, removing sewage link' % (node['id'],))
                for neighbor in [item for item in neighbors if isinstance(item, Boundary)]:
                    g.remove_edge(node, neighbor)
                    if len(g.neighbors(neighbor)) == 0:
                        g.remove_node(neighbor)

    log.debug("network contains...")
    log.debug('...compact form:')
    g_nodes_id_sorted = [item['id'] for item in g.nodes()]
    g_nodes_id_sorted.sort()
    for node in g_nodes_id_sorted:
        log.debug("node (%s)" % (node,))
    for edge in g.edges():
        (bn, en) = edge[:2]
        log.debug("edge (%s)->(%s)" % (bn['id'], en['id'],))

    log.debug('...verbose form:')
    for node in g.nodes():
        log.debug("node (%s): %s" % (node['id'], node.dict,))
    for edge in g.edges():
        (bn, en) = edge[:2]
        info = g[bn][en]
        log.debug("edge (%s)->(%s): %s" % (bn['id'], en['id'], info))

    log.info("writing to output - start")
    pool = createPool(output_dir)
    startupPool(pool)
    for node in g.nodes():
        node.write(pool)
    for edge in g.edges():
        (bn, en) = edge[:2]
        info = g[bn][en]
        info = dict_to_Dict(info)
        info.write(pool)
    closePool(pool)
    log.info("output written.")


if __name__ == '__main__':
    log.warn("module loaded, no tests defined, no action taken.")
