# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import nens.geom
import turtlebase.arcgis
import turtlebase.general

log = logging.getLogger(__name__)


def get_line_parts(gp, line_fc, line_ident):
    """reads all the lines in the line_fc and return a dict with all line parts
    """
    lineparts = {}
    line_desc = gp.describe(line_fc)
    row = gp.SearchCursor(line_fc)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(line_desc.ShapeFieldName)
        item_id = item.GetValue(line_ident)

        part = feat.getpart(0)
        pnt_list = [(round(pnt.x, 5), round(pnt.y, 5)) for pnt in
                    nens.gp.gp_iterator(part)]

        lineparts[item_id] = pnt_list
    return lineparts


def get_pointcloud(gp, point_fc, point_ident):
    """
    reads all the points in the pointcloud and return a
    dict with all points that match point_id
    """
    pointcloud = {}
    point_desc = gp.describe(point_fc)

    row = gp.SearchCursor(point_fc)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(point_desc.ShapeFieldName)
        item_id = item.GetValue(point_ident)

        pnt_xyz = (feat.Centroid.X,
                  feat.Centroid.Y,
                  float(item.GetValue('ZCOORD')))

        if item_id not in pointcloud:
            pointcloud[item_id] = [pnt_xyz]
        else:
            pointcloud[item_id].append(pnt_xyz)

    return pointcloud


def create_centroids(gp, multipoints, output_fc, mp_ident):
    """creates a centerpoint fc out of a multipoint fc
    """
    gp.AddXY_management(multipoints)

    mpoint_desc = gp.describe(multipoints)
    center_points = {}

    row = gp.SearchCursor(multipoints)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(mpoint_desc.ShapeFieldName)
        item_id = item.GetValue(mp_ident)
        xcoord = feat.Centroid.X
        ycoord = feat.Centroid.Y

        center_points[item_id] = {"xcoord": xcoord, "ycoord": ycoord}

    workspace = os.path.dirname(output_fc)
    fc_name = os.path.basename(output_fc)
    gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                                "#", "DISABLED", "DISABLED", "#")
    gp.addfield(output_fc, 'proident', "TEXT")
    gp.addfield(output_fc, 'xcoord', "DOUBLE")
    gp.addfield(output_fc, 'ycoord', "DOUBLE")

    rows = gp.InsertCursor(output_fc)
    point = gp.CreateObject("Point")

    for point_id, attributes in center_points.items():
        row = rows.NewRow()
        point.x = attributes['xcoord']
        point.y = attributes['ycoord']
        row.shape = point
        row.SetValue('proident', point_id)
        row.SetValue('xcoord', point.x)
        row.SetValue('ycoord', point.y)

        rows.InsertRow(row)
    del rows
    del row


def sort_pointcloud(gp, centerpoints_d, lineparts, pointcloud):
    profiles_xyz = {}
    profiles_yz = []
    for centerpoint_id, attributes in centerpoints_d.items():
        log.info(" - cross section: %s" % centerpoint_id)
        if 'ovkident' in attributes:
            ls = lineparts[attributes['ovkident']]
            if 'target_lvl' in attributes:
                targetlevel = attributes['target_lvl']
            else:
                targetlevel = -999
            if 'water_lvl' in attributes:
                waterlevel = attributes['water_lvl']
            else:
                waterlevel = -999
            log.debug("ls: %s" % ls)
            pc = pointcloud[centerpoint_id]

            try:
                sorted = nens.geom.sort_perpendicular_to_segment(ls, pc)
            except:
                log.warning("No intersection found, profile %s skipped",
                            centerpoint_id)
                continue
            profiles_xyz[centerpoint_id] = sorted

            sum_x = 0
            sum_y = 0
            cnt_x = 0
            cnt_y = 0
            for coords in sorted:
                sum_x += float(coords[0])
                cnt_x += 1
                sum_y += float(coords[1])
                cnt_y += 1

            avg_x = sum_x / cnt_x
            avg_y = sum_y / cnt_y

            abscissas = zip(nens.geom.abscissa_from_midsegment(sorted), sorted)
            log.debug("abscissas %s" % abscissas)

            for index, x in enumerate(abscissas):
                profiles_yz.append({"proident": centerpoint_id,
                                    "dist_mid": x[0], "bed_lvl": x[1][2],
                                    "p_order": index + 1,
                                    "target_lvl": targetlevel,
                                    "water_lvl": waterlevel,
                                    "xcoord": avg_x,
                                    "ycoord": avg_y,
                                    })
        else:
            continue

    return profiles_xyz, profiles_yz


def write_profiles_xyz(gp, profiles_xyz, output_xyz):
    """
    """
    workspace = os.path.dirname(output_xyz)
    fc_name = os.path.basename(output_xyz)
    gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                                "#", "DISABLED", "DISABLED", "#")
    gp.addfield(output_xyz, 'proident', "TEXT")
    gp.addfield(output_xyz, 'xcoord', "DOUBLE")
    gp.addfield(output_xyz, 'ycoord', "DOUBLE")
    gp.addfield(output_xyz, 'zcoord', "DOUBLE")
    gp.addfield(output_xyz, 'p_order', "SHORT")

    rows = gp.InsertCursor(output_xyz)
    point = gp.CreateObject("Point")

    for point_id, attributes in profiles_xyz.items():
        for index, point_xy in enumerate(attributes):
            row = rows.NewRow()
            point.x = point_xy[0]
            point.y = point_xy[1]
            row.shape = point
            row.SetValue('proident', point_id)
            row.SetValue('xcoord', point.x)
            row.SetValue('ycoord', point.y)
            row.SetValue('zcoord', point_xy[2])
            row.SetValue('p_order', index + 1)

            rows.InsertRow(row)
    del rows
    del row


def write_profiles_yz(gp, profiles_yz, output_yz):
    """
    """
    workspace = os.path.dirname(output_yz)
    table_name = os.path.basename(output_yz)
    gp.CreateTable_management(workspace, table_name)
    gp.addfield(output_yz, 'proident', "TEXT")
    gp.addfield(output_yz, 'dist_mid', "DOUBLE")
    gp.addfield(output_yz, 'bed_lvl', "DOUBLE")
    gp.addfield(output_yz, 'p_order', "SHORT")
    gp.addfield(output_yz, 'target_lvl', "DOUBLE")
    gp.addfield(output_yz, 'water_lvl', "DOUBLE")
    gp.addfield(output_yz, 'xcoord', "DOUBLE")
    gp.addfield(output_yz, 'ycoord', "DOUBLE")

    rows = gp.InsertCursor(output_yz)
    for attributes in profiles_yz:
        row = rows.NewRow()
        row.SetValue('proident', attributes['proident'])
        row.SetValue('dist_mid', float(attributes['dist_mid']))
        row.SetValue('bed_lvl', float(attributes['bed_lvl']))
        row.SetValue('p_order', int(attributes['p_order']))
        row.SetValue('target_lvl', float(attributes['target_lvl']))
        row.SetValue('water_lvl', float(attributes['water_lvl']))
        row.SetValue('xcoord', float(attributes['xcoord']))
        row.SetValue('ycoord', float(attributes['ycoord']))


        rows.InsertRow(row)
    del rows
    del row


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                        gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #---------------------------------------------------------------------
        # Input parameters
        """
        nodig voor deze tool:
        """
        if len(sys.argv) == 6:
            log.info("Reading input parameters")
            mpoint = sys.argv[1]
            hydroline = sys.argv[2]
            output_xyz = sys.argv[3]
            output_yz = sys.argv[4]
            output_locations = sys.argv[5]
        else:
            log.warning("usage: <hydroline> <mpoint> <output_xyz> <output_yz>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)

        #"<check geometry from input data, append to list if incorrect>"

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []

        #<check required fields from input data,
        #        append them to list if missing>
        check_fields = {}
        #check_fields = {input_1: [fieldname1, fieldname2],
        #                 input_2: [fieldname1, fieldname2]}
        for input_fc, fieldnames in check_fields.items():
            for fieldname in fieldnames:
                if not turtlebase.arcgis.is_fieldname(
                        gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (
                                    fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        multipoints = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        log.info("Dissolving pointcloud to multipoint")
        gp.Dissolve_management(mpoint, multipoints, "PROIDENT")

        if output_locations == '#':
            output_locations = (
                turtlebase.arcgis.get_random_file_name(workspace_gdb))
        log.info("Calculating coordinates of centerpoints")
        create_centroids(gp, multipoints, output_locations, 'PROIDENT')

        centerpoints_sj = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        log.info("Calculation adjacent hydrolines")
        gp.SpatialJoin_analysis(output_locations, hydroline, centerpoints_sj,
                                'JOIN_ONE_TO_ONE', "#", "#", "CLOSEST", 100)

        log.info("Reading center points")
        centerpoints_d = nens.gp.get_table(gp, centerpoints_sj,
                                           primary_key='proident')

        log.info("Reading hydrolines")
        lineparts = get_line_parts(gp, hydroline, 'ovkident')
        log.info("Reading pointcloud")
        pointcloud = get_pointcloud(gp, mpoint, 'proident')

        log.info("Sorting profiles")
        profiles_xyz, profiles_yz = sort_pointcloud(gp, centerpoints_d,
                                                    lineparts, pointcloud)
        log.info("Write xyz points to output")
        write_profiles_xyz(gp, profiles_xyz, output_xyz)
        log.info("Write yz information to output table")
        write_profiles_yz(gp, profiles_yz, output_yz)

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            #gp.delete(workspace_gdb)

            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()

    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
