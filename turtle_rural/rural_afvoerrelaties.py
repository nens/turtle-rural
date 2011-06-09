# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.general

log = logging.getLogger(__name__)


def draw_lines_from_dict(gp, input_dict, output_fc):
    """
    """
    log.info("Inserting new records and geometry")
    gp.CreateFeatureclass(os.path.dirname(output_fc),
                          os.path.basename(output_fc),
                          "POLYLINE")

    linearray = gp.CreateObject("ARRAY")
    point = gp.CreateObject("POINT")

    fields_to_add = ["RelationID", "ID_From", "ID_To",
                     "Structure", "Source"]
    for field in fields_to_add:
        gp.AddField(output_fc, field, "TEXT")

    rows_ic = gp.InsertCursor(output_fc)
    insect_count = 0
    for output_id, attributes in input_dict.items():
        for xy in attributes['coords']:
            point.X = float(xy[0])
            point.Y = float(xy[1])
            linearray.Add(point)
            newfeature = rows_ic.NewRow()

        newfeature.shape = linearray

        newfeature.SetValue('RelationID', output_id)
        newfeature.SetValue('ID_From', attributes['From'])
        newfeature.SetValue('ID_To', attributes['To'])
        newfeature.SetValue('Structure', attributes['Structure'])
        newfeature.SetValue('Source', attributes['Source'])

        rows_ic.InsertRow(newfeature)
        insect_count += 1
        linearray.RemoveAll()

    return insect_count


def add_centroids(gp, input_polygon):
    """
    """
    if not turtlebase.arcgis.is_fieldname(gp, input_polygon, "POINT_X"):
        gp.AddField(input_polygon, "POINT_X", "Double")
    if not turtlebase.arcgis.is_fieldname(gp, input_polygon, "POINT_Y"):
        gp.AddField(input_polygon, "POINT_Y", "Double")

    row = gp.UpdateCursor(input_polygon)
    for item in nens.gp.gp_iterator(row):
        xy = item.Shape.Centroid.split(" ")
        x = float(xy[0])
        y = float(xy[1])
        # wegschrijven naar veld
        item.setValue('POINT_X', x)
        item.setValue('POINT_Y', y)
        row.UpdateRow(item)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters")
        if len(sys.argv) == 5:
            input_peilgebieden_feature = sys.argv[1]
            input_kunstwerken_feature = sys.argv[2]
            input_afvoer_table = sys.argv[3]
            output_feature = sys.argv[4]
        else:
            log.error("Usage: python rural_afvoerrelaties.py \
            <peilgebieden feature> <kunstwerken feature> \
            <afvoerrelaties table> <output feature>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        #check input parameters
        gpgident = config.get('GENERAL', 'gpgident').lower()
        kwkident = config.get('GENERAL', 'kwkident').lower()

        log.info('Checking presence of input files')
        if not(gp.exists(input_peilgebieden_feature)):
            log.error("inputfile peilgebieden %s does not exist!" % input_peilgebieden_feature)
            sys.exit(5)

        if not(gp.exists(input_afvoer_table)):
            log.error("inputfile afvoerrelaties %s does not exist!" % input_afvoer_table)
            sys.exit(5)

        log.info('Input parameters checked')
        #----------------------------------------------------------------------------------------
        log.info("Prepare input_peilgebieden_feature")
        temp_peilgebieden_feature = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Select_analysis(input_peilgebieden_feature, temp_peilgebieden_feature)

        add_centroids(gp, temp_peilgebieden_feature)
        peilgebieden_dict = nens.gp.get_table(gp, temp_peilgebieden_feature, primary_key=gpgident)

        if input_kunstwerken_feature != '#':
            log.info("Prepare input_kunstwerken_feature")
            temp_kunstwerken_feature = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.Select_analysis(input_kunstwerken_feature, temp_kunstwerken_feature)

            gp.addxy(temp_kunstwerken_feature)
            kunstwerken_dict = nens.gp.get_table(gp, temp_kunstwerken_feature, primary_key=kwkident)
        else:
            kunstwerken_dict = {}

        log.info("Reading input_afvoer_table")
        relaties_dict = nens.gp.get_table(gp, input_afvoer_table, primary_key=kwkident)

        log.info("Calculating afvoerrelaties")
        afvoer_van = config.get('afvoerrelaties', 'input_peilg_from').lower()
        afvoer_naar = config.get('afvoerrelaties', 'input_peilg_to').lower()

        output_relations = {}
        data_source = "pg: %s, kw: %s, rel: %s" % (os.path.basename(input_peilgebieden_feature),
                                                   os.path.basename(input_kunstwerken_feature),
                                                   os.path.basename(input_afvoer_table))
        data_source = data_source[:50]

        for relation, attributes in relaties_dict.items():
            id_from = attributes[afvoer_van]
            id_to = attributes[afvoer_naar]
            item_id = "%s_%s" % (id_from, id_to)
            coords = []
            # get start coords
            x1 = peilgebieden_dict[id_from]['point_x']
            y1 = peilgebieden_dict[id_from]['point_y']
            coords.append((x1, y1))

            if relation in kunstwerken_dict:
                x2 = kunstwerken_dict[relation]['point_x']
                y2 = kunstwerken_dict[relation]['point_y']
                coords.append((x2, y2))

            if id_to in peilgebieden_dict:
                x3 = peilgebieden_dict[id_to]['point_x']
                y3 = peilgebieden_dict[id_to]['point_y']
            else:
                x3 = x1 + 10
                y3 = y1 + 10
            coords.append((x3, y3))

            output_relations[item_id] = {"Relation_id": item_id, "From": id_from, "To": id_to,
                                         "Structure": relation, "Source": data_source, "coords": coords}

        #put new data in output_table
        insert_count = draw_lines_from_dict(gp, output_relations, output_feature)
        log.info(" - %s records has been inserted" % insert_count)

        #----------------------------------------------------------------------------------------
        # Delete temporary workspace geodatabase
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

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
