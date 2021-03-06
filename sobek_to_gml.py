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


import nens.gp
import nens.turtleruralclasses as trc
import os.path


def main(options=None, args=None):
    """the function being called by the arcgis script.

    in this form so it is easy to invoke the same functionality from
    the command line.
    """

    if options is args is None:
        options, args = nens.gp.parse_arguments({1: ('arg', 0),  # input network.ntw
                                                 2: ('arg', 1),  # output path + name - extension
                                                 3: ('arg', 2),  # config file
                                                 })

    ## unpack arguments
    input_file_name, output_file_name, config_file_name = args

    trc.Base.register_configuration(config_file_name)

    trc_collection = trc.from_sobek_network(input_file_name)
    output_basedir, output_basename = os.path.split(output_file_name)

    document = trc.create_gml_document(output_basename)
    [i.add_as_element_to(document) for i in trc_collection.values()]
    out = file(output_file_name + ".gml", "w")
    document.ownerDocument.writexml(out)
    out.close()

    trc_used_classes = set(i.__class__ for i in trc_collection.values())
    if trc.Pump in trc_used_classes:
        trc_used_classes.add(trc.PumpStages)
    if trc.Profile in trc_used_classes:
        trc_used_classes.add(trc.CrossSectionYZ)
        trc_used_classes.add(trc.CrossSectionLW)
    schema = trc.create_xsd_document()
    [i.add_definition_to(schema) for i in trc_used_classes]
    out = file(output_file_name + ".xsd", "w")
    #schema.ownerDocument.writexml(out)
    out.write(schema.ownerDocument.toprettyxml(indent="  "))
    out.close()


if __name__ == "__main__":
    main()
