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
import turtlebase.network
import turtlebase.general

log = logging.getLogger(__name__)


def create_point_file_from_polyline(gp, config, file_with_xy_points, output_file, type_of_points):
    '''
    Input: shapefile with from_x en from_y and ovkident
    output: esri point file
    type of points can be bottlenecks or terminals
    '''

    gp.CreateFeatureClass_management(os.path.dirname(output_file), os.path.basename(output_file), "POINT")
    col_ovkident = config.get('general', 'ovkident')
    gp.Addfield_management(output_file, "ovkident", "TEXT")
    rows_out = gp.InsertCursor(output_file)
    pnt = gp.CreateObject("Point")

    col_incoming = config.get('netwerkanalyse', 'incoming')
    col_examined = config.get('netwerkanalyse', 'examined')
    col_from_x = config.get('netwerkanalyse', 'from_x')
    col_from_y = config.get('netwerkanalyse', 'from_y')
    col_to_x = config.get('netwerkanalyse', 'to_x')
    col_to_y = config.get('netwerkanalyse', 'to_y')


    rows_in = gp.SearchCursor(file_with_xy_points)
    row_in = rows_in.Next()
    while row_in:
        if type_of_points == 'bottlenecks':
            #bottlenecks are recoginzed by more than 1 edge upstream and
            # not examined
            incoming = row_in.getValue(col_incoming)
            examined = row_in.getValue(col_examined)

            if incoming > 1 and examined == 0:

                pnt.X = row_in.getValue(col_from_x)
                pnt.Y = row_in.getValue(col_from_y)

                ovkident = row_in.getValue(col_ovkident)
                newfeat = rows_out.NewRow()
                newfeat.shape = pnt
                newfeat.SetValue("ovkident", ovkident)
                rows_out.InsertRow(newfeat)

            row_in = rows_in.Next()

        if type_of_points == 'terminals':
            # terminals are endpoints of the analysis. if a line is a terminal than the
            # terminal value equals 1
            terminal = row_in.getValue('terminal')
            if terminal == 1:
                pnt.X = row_in.getValue(col_to_x)
                pnt.Y = row_in.getValue(col_to_y)

                ovkident = row_in.getValue(col_ovkident)
                newfeat = rows_out.NewRow()
                newfeat.shape = pnt
                newfeat.SetValue("ovkident", ovkident)
                rows_out.InsertRow(newfeat)

            row_in = rows_in.Next()

    #Selecteren van de stelsels obv centroide
    del row_in, rows_in, rows_out


def calculate_to_and_from_point(gp, fc, ident):
    """
    calculated a 2-tuple (x, y) for the frompoint and to_point of a line fc
    """
    result = {}
    row = gp.SearchCursor(fc)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(gp.describe(fc).ShapeFieldName)
        item_id = item.GetValue(ident)
        pnt_list = [(pnt.x, pnt.y) for pnt in nens.gp.gp_iterator(feat.getpart(0))]
        result[item_id] = {"from_x": pnt_list[0][0], "from_y": pnt_list[0][1], "to_x": pnt_list[-1][0], "to_y": pnt_list[-1][1]}

    return result


def update_to_and_from_coordinates(gp, fc, ident):
    """
    """
    fields = ["from_x", "from_y", "to_x", "to_y"]
    for field in fields:
        if not turtlebase.arcgis.is_fieldname(gp, fc, field):
            gp.addfield_management(fc, field, "Double")

    coordinates_dict = calculate_to_and_from_point(gp, fc, ident)

    turtlebase.arcgis.write_result_to_output(fc, ident, coordinates_dict)

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
        tempfiles = []
        if len(sys.argv) == 5:
            input_hydrovak = sys.argv[1]
            output_shapefile = sys.argv[2]
            optional_bottleneck_points = sys.argv[3]
            optional_terminal_points = sys.argv[4]
        else:
            log.warning("usage: <input_hydrovak> <output_shapefile> <optional_bottleneck_points> <optional_terminal_points>")
            sys.exit(1)

        tolerance_points = float(config.get('netwerkanalyse', 'tolerance_points'))
        input_shapefile = turtlebase.arcgis.get_random_file_name(workspace , ".shp")
        tempfiles.append(input_shapefile)
        gp.select_analysis(input_hydrovak, input_shapefile)

        #---------------------------------------------------------------------
        # Check required fields in input data
        ovk_field = config.get('general', 'ovkident')
        missing_fields = []
        check_fields = {input_shapefile: ['Sum_OPP_LA', 'Sum_OPP_ST',
                        'ovkident', 'from_x', 'from_y', 'to_x', 'to_y']}

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
        # add from and to coordinates
        update_to_and_from_coordinates(gp, input_shapefile, 'ovkident')

        dbf_name = turtlebase.arcgis.get_random_file_name(workspace , ".dbf")
        tempfiles.append(dbf_name)
        gp.select_analysis(input_shapefile, dbf_name)

        g = turtlebase.network.import_dbf_into_graph(config, dbf_name, tolerance_points)
        turtlebase.network.let_it_stream(g)

        #create output:
        fields_to_add = [('incoming', 'SHORT'),
                         ('examined', 'SHORT'),
                         ('terminal', 'SHORT'),
                         ('som_sted', 'DOUBLE'),
                         ('som_land', 'DOUBLE'),
                         ('som_totaal', 'DOUBLE'),
                         ('bottleneck', 'SHORT'),
                         ('flip', 'SHORT')]
        gp.select_analysis(input_shapefile, output_shapefile)

        #fields_to_add = {'incoming':"SHORT",'examined':"SHORT",'terminal':"SHORT", 'cum_urban':"DOUBLE", 'cum_rural':"DOUBLE", 'bottleneck':"SHORT", 'flip':"SHORT"} #'ovkident':"TEXT",
        for field_to_add in fields_to_add:
            field_name = field_to_add[0]
            field_type = field_to_add[1]
            if turtlebase.arcgis.is_fieldname(gp, output_shapefile, field_name):
                gp.DeleteField_management(output_shapefile, field_name)
                gp.AddField_management(output_shapefile, field_name, field_type)
                log.info("Adding field %s" % field_name)
            else:
                gp.AddField_management(output_shapefile, field_name, field_type)
                log.info("Adding field %s" % field_name)

        turtlebase.network.save_result_shapefile(gp, config, g, output_shapefile)

        log.info("Recognizing bottlenecks")
        log.debug("create field to store bottlenecks")

        row = gp.UpdateCursor(output_shapefile)
        for item in nens.gp.gp_iterator(row):
            examined = item.getValue(config.get('netwerkanalyse', 'examined'))
            incoming = item.getValue(config.get('netwerkanalyse', 'incoming'))
            terminal = item.getValue(config.get('netwerkanalyse', 'terminal'))

            if terminal == 1 and examined == 0:
                item.SetValue(config.get('netwerkanalyse', 'bottleneck'), incoming)


            if incoming > 1 and examined == 0:
                item.SetValue(config.get('netwerkanalyse', 'bottleneck'), incoming)
            row.UpdateRow(item)

        # als de gebruiker heeft aangegeven de terminal points als puntenbestand te hebben
        # moeten eerst de begin x en begin y worden opgeslagen in een dictionary. daarvan
        # kan dan een puntenbestand gemaakt worden met functie
        if optional_bottleneck_points != '#':
            temp_shape = turtlebase.arcgis.get_random_file_name(workspace , ".shp")
            tempfiles.append(temp_shape)
            log.info("Creating bottleneck points file")
            create_point_file_from_polyline(gp, config, output_shapefile, temp_shape, 'bottlenecks')
            gp.Select_analysis(temp_shape, optional_bottleneck_points)
        # als de gebruiker heeft aangegeven de terminal points als puntenbestand te hebben
        # moeten eerst de begin x en begin y worden opgeslagen in een dictionary. daarvan
        # kan dan een puntenbestand gemaakt worden met functie

        if optional_terminal_points != "#":
            temp_shape2 = turtlebase.arcgis.get_random_file_name(workspace , ".shp")
            tempfiles.append(temp_shape2)
            log.info("Creating terminal points file")
            create_point_file_from_polyline(gp, config, output_shapefile, temp_shape2, 'terminals')
            gp.Select_analysis(temp_shape2, optional_terminal_points)

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)
            turtlebase.arcgis.remove_tempfiles(gp, log, tempfiles)

            log.info("workspace deleted")
        except:
            log.debug("failed to delete %s" % workspace_gdb)

        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
