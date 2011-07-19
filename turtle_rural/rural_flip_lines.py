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


class FormatFloat:
    '''
    input float
    output rounded string with 5 decimales and a ',' when Dutch language settings
    '''
    def __init__(self):
        import locale
        lang_name, lang_code = locale.getdefaultlocale()
        if lang_name[:2] == 'nl':
            self.decimal_point = ','
        else:
            self.decimal_point = '.'

    def format(self, input):
        return ('%.5f' % input).replace('.', self.decimal_point)


def create_line_from_dict(gp, workspace, dict_with_points, fields_to_add, new_geometry, outputfile):
    """"Deze functie maakt een lijnobject aan in ArcGIS op basis van punten in een dictionary. De punten in de dictionary
    zijn met een unieke code aan elkaar gekoppeld example: ('key1':[x1 y1,x2 y])"""

    linearray = gp.CreateObject("ARRAY")
    point = gp.CreateObject("POINT")
    file = os.path.basename(outputfile)
    gp.CreateFeatureClass_management(workspace, file, "POLYLINE")

    for field_to_add in fields_to_add:
        field_name = field_to_add[0]
        field_type = field_to_add[1]
        if turtlebase.arcgis.is_fieldname(gp, outputfile, field_name):
            gp.DeleteField_management(outputfile, field_name)
            log.debug("Adding field %s" % field_name)
            gp.AddField_management(outputfile, field_name, field_type)
        else:
            log.debug("Adding field %s" % field_name)
            gp.AddField_management(outputfile, field_name, field_type)

    rows_ic = gp.InsertCursor(outputfile)
    count = 0
    for ovkident in dict_with_points.iterkeys():
        for item in dict_with_points[ovkident]:
            item_sp = item.split(' ')
            point.X = item_sp[0]
            point.Y = item_sp[1]
            linearray.Add(point)
        newfeature = rows_ic.NewRow()
        newfeature.shape = linearray

        for columns in new_geometry[ovkident].keys():
            log.info("Setting value %s: %s" % (columns, new_geometry[ovkident][columns]))
            newfeature.SetValue(columns, new_geometry[ovkident][columns])

        count += 1
        #newfeature.SetValue(leidingidkolom,key)
        rows_ic.InsertRow(newfeature)
        linearray.RemoveAll()

    return count


def flip_geometry(gp, feat, ovkident, dict_reverse_lines):
    # line moet geflipt worden

    line_array = gp.CreateObject("ARRAY")
    pnt_array = []
    float_formatter = FormatFloat() #initieren klasse ivm landsinstellingen

    partnum = 0
    partcount = feat.partcount
    while partnum < partcount:
        part = feat.getpart(partnum)
        #log.info("partnum" + str(partnum))
        part.reset()
        pnt = part.next()
        pnt_count = 0
        pnt_array = []
        while pnt:
            punt = "%s %s" % (float_formatter.format(pnt.x), float_formatter.format(pnt.y))
            pnt_array.append(punt)
            pnt_count += 1
            pnt = part.next()
        #log.info("pnt_array" + str(pnt_array))
        pnt_array.reverse()

        partnum += 1

    dict_reverse_lines[ovkident] = pnt_array
    line_array.RemoveAll()
    return dict_reverse_lines


def create_field_list(gp, shape_file):
#create a list of fields in the shapefile
    list_fields = []
    #log.info("list_field" + str(list_fields))
    fields = gp.ListFields(shape_file)
    fields.reset()
    field = fields.next()
    while field:
        fieldname = field.Name
        list_fields.append(fieldname)

        field = fields.next()
    return list_fields


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
        if len(sys.argv) == 4:
            user_input = sys.argv[1]
            flip_field = sys.argv[2].lower()
            output_shape = sys.argv[3]
        else:
            log.warning("usage: <user_input> <output_shape>")
            sys.exit(1)

        tempfiles = []
        input_shape = turtlebase.arcgis.get_random_file_name(workspace, '.shp')
        gp.Select_analysis(user_input, input_shape)
        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)
        if not turtlebase.arcgis.is_file_of_type(gp, input_shape, 'Polyline'):
            log.error("%s is not a %s feature class!" % (input_shape, 'Polyline'))
            geometry_check_list.append("%s -> (%s)" % (input_shape, 'Polyline'))

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        ovk_field = config.get('general', 'ovkident').lower()
        missing_fields = []
        check_fields = {input_shape: ['Sum_OPP_LA', 'Sum_OPP_ST',
                        ovk_field, 'from_x', 'from_y', 'to_x', 'to_y', flip_field]}

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
        #create output:
        fields_to_add = [(ovk_field, 'TEXT'),
                         ('incoming', 'SHORT'),
                         ('examined', 'SHORT'),
                         ('terminal', 'SHORT'),
                         ('som_sted', 'DOUBLE'),
                         ('som_land', 'DOUBLE'),
                         ('som_totaal', 'DOUBLE'),
                         ('bottleneck', 'SHORT'),
                         (flip_field, 'SHORT')]
        gp.select_analysis(input_shape, output_shape)

        new_feat = {}
        new_geometry = {}
        log.info("Inlezen geometrie en omdraaien van de geometrie")

        fieldnames_dict = nens.gp.get_table_def(gp, input_shape)
        log.debug(fieldnames_dict)
        desc = gp.describe(input_shape)
        count = 0
        rows = gp.SearchCursor(input_shape)
        row = rows.Next()
        while row:

            flip_boolean = row.getValue(flip_field)

            if flip_boolean == 1:
                count += 1
                #read features
                feat = row.getValue(desc.ShapeFieldName)
                ovkident = row.getValue(ovk_field)
                new_feat = flip_geometry(gp, feat, ovkident, new_feat)
                ##new_feat = feat

                #store geometry information in dictionary
                if ovkident not in new_geometry:
                    new_geometry[ovkident] = {}
                #store all information from the attribute table
                for column in fields_to_add:
                    column = column[0]

                    #columns with from en to for x and y need to be switched as well
                    if column == 'from_x':
                        lookup_column = 'to_x'
                    elif column == 'from_y':
                        lookup_column = 'to_y'
                    elif column == 'to_y':
                        lookup_column = 'from_y'
                    elif column == 'to_x':
                        lookup_column = 'from_x'
                    else:
                        # no switch needed
                        lookup_column = column

                    if column != 'opm':
                        if lookup_column in fieldnames_dict:
                            update_value = row.getValue(lookup_column)
                            try:
                                float_value = float(update_value)
                                new_geometry[ovkident][column] = float_value
                            except:
                                log.debug("geen float")
                                new_geometry[ovkident][column] = row.getValue(lookup_column)
                            log.debug(new_geometry[ovkident][column])
                #waterlijn wordt opgeslagen in dictionary
                if column == 'opm':
                    new_geometry[ovkident][column] = "Lijn is omgedraaid"
                log.info("Opslaan van waterlijn: " + str(ovkident))
            row = rows.Next()
        del row, rows
        #remove the lines that are going to be flipped

        removed_lines = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        #alleen als er inderdaad lijnen gedraaid worden moet de tempfile aangemaakt worden.
        gp.select_analysis(input_shape, removed_lines)

        #first remove lines that are going to be duplicate in the end result. lines are
        # remove from a copy of the input file.
        row = gp.UpdateCursor(removed_lines)
        log.info("Verwijder dubbele rijen")
        for item in nens.gp.gp_iterator(row):
            if item.getValue(flip_field) == 1:
                row.DeleteRow(item)

        temp_shape = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        tempfiles.append(temp_shape)

        #creates new lines in workspace with same name as output_shape
        log.info(count)
        count = create_line_from_dict(gp, workspace_gdb, new_feat, fields_to_add, new_geometry, temp_shape)
        log.info(count)

        if count == 0:
            log.warning("Er zijn geen lijnen omgedraaid")
            log.warning("Door de gebruiker is in de kolom " + str(flip_field) + " geen 1 ingevuld")
        else:
            tempfiles.append(removed_lines)

        #merge new lines with output
        gp.Merge_management(temp_shape + ";" + removed_lines, output_shape)

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
