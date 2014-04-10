# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.network

log = logging.getLogger(__name__)

import arcgisscripting
gp = arcgisscripting.create()

def read_lines(gp, line_fc, ident=None):
    """
    """
    points = {}
    inDesc = gp.describe(line_fc)

    row = gp.SearchCursor(line_fc)
    id_int = 0
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(inDesc.ShapeFieldName)
        shape_length = feat.length
        if ident is None:
            item_id = id_int
            id_int += 1
        else:
            item_id = item.GetValue(ident)

        part = feat.getpart(0)
        pnt_list = [(float(pnt.x), float(pnt.y)) for pnt in nens.gp.gp_iterator(part)]
        points[(item_id, shape_length)] = pnt_list

    return points

def calculate_sp(percentage, max_d, lengte, points):
    x = 0
    d = float(percentage) * float(lengte)
    if float(d) > float(max_d):
        d = float(max_d)
    dist_first = turtlebase.network.distance(points[x], points[x + 1])
    while dist_first < d:
        d -= dist_first
        x += 1
        dist_first = turtlebase.network.distance(points[x], points[x + 1])

    XY = turtlebase.network.create_station_point(points[x], points[x + 1], d)
    return XY

def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 5:
            input_watergangen = sys.argv[1]
            procent = sys.argv[2]
            max_distance = sys.argv[3]
            output_profiles = sys.argv[4]
        else:
            log.warning("usage: <input_watergangen> <procent> <max_distance> <output_profiles>")
            sys.exit(1)
        
        percentage = float(procent) / 100

        gp.CreateFeatureclass_management(os.path.dirname(output_profiles), os.path.basename(output_profiles), "POINT")
        gp.AddField_management(output_profiles, "LOCIDENT", "TEXT")
        gp.AddField_management(output_profiles, "PROIDENT", "TEXT")
    
        in_rows = gp.SearchCursor(input_watergangen)
        in_row = in_rows.Next()
        out_rows = gp.InsertCursor(output_profiles)
        pnt = gp.CreateObject("Point")
        
        inDesc = gp.describe(input_watergangen)
        log.info("draw profiles")
        while in_row:
            ident = in_row.GetValue("OVKIDENT")
            log.info("- %s" % ident)
        
            feat = in_row.GetValue(inDesc.ShapeFieldName)
        
            lengte = feat.length
        
            part = feat.getpart(0)
            pnt_list = [(float(pnt.x), float(pnt.y)) for pnt in nens.gp.gp_iterator(part)]
        
            XY = calculate_sp(percentage, max_distance, lengte, pnt_list)
            pnt.X = XY[0]
            pnt.Y = XY[1]
        
            out_row = out_rows.newRow()
            out_row.shape = pnt
            out_row.setValue("PROIDENT", ident)
            out_row.setValue("LOCIDENT", "%s_a" % ident)
            out_rows.insertRow(out_row)
        
            pnt_list.reverse()
            XY = calculate_sp(percentage, max_distance, lengte, pnt_list)
            pnt.X = XY[0]
            pnt.Y = XY[1]
        
            out_row = out_rows.newRow()
            out_row.shape = pnt
            out_row.setValue("PROIDENT", ident)
            out_row.setValue("LOCIDENT", "%s_b" % ident)
            out_rows.insertRow(out_row)
            in_row = in_rows.Next()
        
        del out_rows
        del in_rows
        
        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp

