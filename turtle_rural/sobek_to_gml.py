#!/usr/bin/env python
# -*- coding: utf-8 -*-
#***********************************************************************
#
# This file is part of turtle-rural.
#
# turtle-rural is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# the nens library is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the nens libraray.  If not, see
# <http://www.gnu.org/licenses/>.
#
# Copyright 2011 Nelen & Schuurmans BV
#
#***********************************************************************
#* Script     : using nens.sobek, reads a network and writes a gml
#*
#* $Id$
#*
#* initial programmer :  Mario Frasca
#* initial date       :  2011-09-06
#**********************************************************************


__revision__ = "$Rev$"[6:-2]


import nens.sobek
import nens.turtleurbanclasses as tuc
from xml.dom.minidom import Document
import uuid


class sequence_functor:
    def __call__(self):
        self.count += 1
        return self.count

    def __init__(self):
        self.count = 0


sequence = sequence_functor()


def select_from(sobek_list, field_name, field_value):
    """which element in sobek_list has field_name equal to field_value?
    """
    candidates = [i for i in sobek_list if i[field_name] == field_value]
    if len(candidates) != 1:
        return None
    return candidates[0]


def sobek_to_tuc(sobek_input, type, id):
    """create one tuc object from sobek input
    """
    result = None
    structure = sobek_input['STRUCT.DAT']['STRU', id]
    structure_def = sobek_input['STRUCT.DEF']['STDS', structure['dd'][0])
    if structure_def is not None:
        friction_dat = select_from(sobek_input['FRICTION.DAT']['STFR'], 'ci', structure_def['id'])
    control_def = sobek_input['CONTROL.DEF']['CNTL', structure['cj'][0])
    if type == "SBK_CHANNEL":
        pass
    elif type == 'SBK_WEIR':
        result = tuc.Overstort_Knoop()
    elif type == 'SBK_CULVERT':
        pass
    elif type == 'SBK_PUMP':
        result = tuc.Gemaal_Knoop()
    elif type == 'SBK_BRIDGE':
        pass
    else:
        log.warn("unhandled case '%s'" % type)
    return result

    
def sobek_network_to_objects(sobek_network_ntw):
    """read the sobek files and convert them to tuc objects.
    tuc or nens.turtleurbanclasses.
    """
    global sobek_input
    global sobek_network
    sobek_input = {}
    sobek_input['NETWORK.NTW'] = nens.sobek.Network(sobek_network_ntw)
    other_sobek_files = ['INITIAL.DAT', 'LATERAL.DAT', 'STRUCT.DAT', 
                         'CONTROL.DEF', 'FRICTION.DAT', 'PROFILE.DEF', 
                         'STRUCT.DEF', 'PROFILE.DAT', 'BOUNDARY.DAT']
    path_to_files = os.path.split(sobek_network_ntw)[0]
    sobek_input.update(dict([(i, nens.sobek.File(path_to_files + '/' + i)) 
                             for i in other_sobek_files
                             if i != "NETWORK.NTW"]))
    ## the result is a collection of tuc objects, indexed by type and id.
    tuc_collection = dict()
    ## main entry point is the channels network, but the network also
    ## defines nodes and most of these objects correspond to tuc
    ## objects that must be exported.
    sobek_network = sobek_input['NETWORK.NTW'].dict
    ## scan the network for objects (edge, node_from, node_to).
    for edge_id in sobek_network['SBK_CHANNEL']:
        (from_type, from_id), (to_type, to_id) = sobek_network['SBK_CHANNEL'][edge_id]
        tuc_collection[from_type, from_id] = sobek_to_tuc(sobek_input, 'SBK_CHANNEL', edge_id)
        if (from_type, from_id) not in tuc_collection:
            tuc_collection[from_type, from_id] = sobek_to_tuc(sobek_input, from_type, from_id)
        if (to_type, to_id) not in tuc_collection:
            tuc_collection[to_type, to_id] = sobek_to_tuc(sobek_input, to_type, to_id)
    return tuc_collection


def main(options, args):
    """the function being called by the arcgis script.

    in this form so it is easy to invoke the same functionality from
    the command line.
    """

    ## unpack arguments
    input_file_name, output_file_name = args

    ## the set of points used.  each element is a 2-tuple (type, id)
    points = set()

    o = nens.sobek.Network(input_file_name)

    ## first scan the content to compute the bounding box.
    min_x = min_y = float("inf")
    max_x = max_y = -float("inf")
    for edge_id in o.dict['SBK_CHANNEL']:
        (from_type, from_id), (to_type, to_id) = o.dict['SBK_CHANNEL'][edge_id]
        (x, y) = o.dict[from_type][from_id]
        min_x = min(min_x, float(x))
        min_y = min(min_y, float(y))
        max_x = max(max_x, float(x))
        max_y = max(max_y, float(y))
        (x, y) = o.dict[to_type][to_id]
        min_x = min(min_x, float(x))
        min_y = min(min_y, float(y))
        max_x = max(max_x, float(x))
        max_y = max(max_y, float(y))

    ## now add the features
    for edge_id in o.dict['SBK_CHANNEL']:
        (from_type, from_id), (to_type, to_id) = o.dict['SBK_CHANNEL'][edge_id]
        (from_x, from_y) = o.dict[from_type][from_id]
        (to_x, to_y) = o.dict[to_type][to_id]
        obj_id = sequence()

        ## anything we add is a featureMember
        feature_member = doc.createElement("gml:featureMember")
        feature_collection.appendChild(feature_member)

        ## first feature member is the line
        lijn = doc.createElement("fme:lijn")
        lijn.setAttribute("gml:id", "%s" % uuid.uuid4())
        feature_member.appendChild(lijn)

        ## the line has:
        ## * fme:ident
        fme_ident = doc.createElement("fme:ident")
        fme_ident.appendChild(doc.createTextNode("SBK_CHANNEL:" + edge_id))
        lijn.appendChild(fme_ident)

        ## * fme:fid
        fme_ident = doc.createElement("fme:fid")
        fme_ident.appendChild(doc.createTextNode(str(obj_id)))
        lijn.appendChild(fme_ident)

        ## * fme:objectid
        fme_ident = doc.createElement("fme:objectid")
        fme_ident.appendChild(doc.createTextNode(str(obj_id)))
        lijn.appendChild(fme_ident)

        ## * gml:curveProperties
        curve_property = doc.createElement("gml:curveProperty")
        lijn.appendChild(curve_property)

        ## the single curve property contains a lineString which
        ## contains a posList which is just the two coordinates of the
        ## two points (four numbers).
        line_string = doc.createElement("gml:LineString")
        line_string.setAttribute("srsName", "EPSG:28992")
        line_string.setAttribute("srsDimensions", "2")
        curve_property.appendChild(line_string)

        pos_list = doc.createElement("gml:posList")
        line_string.appendChild(pos_list)

        ## coordinates are as text in gml:posList
        ptext = doc.createTextNode("%0.6f %0.6f %0.6f %0.6f" % (float(from_x), float(from_y), float(to_x), float(to_y)))
        pos_list.appendChild(ptext)

        ## add pointers to the points to be used.  `points` is a set
        ## and this takes care of removing duplicates.
        points.add((from_type, from_id))
        points.add((to_type, to_id))

    for type, id in points:
        (x, y) = o.dict[type][id]
        obj_id = sequence()

        ## again, anything we add is a featureMember
        feature_member = doc.createElement("gml:featureMember")
        feature_collection.appendChild(feature_member)

        ## now adding points
        punt = doc.createElement("fme:punt")
        punt.setAttribute("gml:id", "%s" % uuid.uuid4())
        feature_member.appendChild(punt)
        
        ## the point has:
        ## * fme:ident
        fme_ident = doc.createElement("fme:ident")
        fme_ident.appendChild(doc.createTextNode(type + ":" + id))
        punt.appendChild(fme_ident)

        ## * fme:fid
        fme_ident = doc.createElement("fme:fid")
        fme_ident.appendChild(doc.createTextNode(str(obj_id)))
        punt.appendChild(fme_ident)

        ## * fme:objectid
        fme_ident = doc.createElement("fme:objectid")
        fme_ident.appendChild(doc.createTextNode(str(obj_id)))
        punt.appendChild(fme_ident)

        ## *  point properties
        point_property = doc.createElement("gml:pointProperty")
        punt.appendChild(point_property)

        ## the single point property contains a point which contains a
        ## pos which is just the two coordinates of the point.
        point = doc.createElement("gml:Point")
        point.setAttribute("srsName", "EPSG:28992")
        point.setAttribute("srsDimensions", "2")
        point_property.appendChild(point)

        pos = doc.createElement("gml:pos")
        point.appendChild(pos)

        ## coordinates are as text in gml:pos
        ptext = doc.createTextNode("%0.6f %0.6f" % (float(x), float(y)))
        pos.appendChild(ptext)

    output = file(output_file_name + ".gml", "w")
    output.write(doc.toprettyxml(indent=" "))
    output.close()

    output = file(output_file_name + ".xsd", "w")
    output.write('''\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" targetNamespace="http://www.safe.com/gml/fme" xmlns:fme="http://www.safe.com/gml/fme" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml">
  <xs:import namespace="http://www.opengis.net/gml" schemaLocation="gml.xsd"/>
  <xs:import namespace="http://www.w3.org/2001/XMLSchema-instance" schemaLocation="xsi.xsd"/>
  <xs:element name="lijn">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="fme:ident"/>
        <xs:element ref="fme:fid"/>
        <xs:element ref="fme:objectid"/>
        <xs:element ref="gml:curveProperty"/>
      </xs:sequence>
      <xs:attribute ref="gml:id" use="required"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="punt">
    <xs:complexType>
      <xs:sequence>
        <xs:element ref="fme:ident"/>
        <xs:element ref="fme:fid"/>
        <xs:element ref="fme:objectid"/>
        <xs:element ref="gml:pointProperty"/>
      </xs:sequence>
      <xs:attribute ref="gml:id" use="required"/>
    </xs:complexType>
  </xs:element>
  <xs:element name="ident" type="xs:NMTOKEN"/>
  <xs:element name="fid" type="xs:integer"/>
  <xs:element name="objectid" type="xs:integer"/>
</xs:schema>
''')
    output.close()

if __name__ == "__main__":
    import sys
    main(None, sys.argv[1:])
