# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback
import tempfile

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis

log = logging.getLogger(__name__)


def check_for_landuse_types(gp, output_intersect_landuse, type_field):
    """
    """
    landuse_type_list = []
    row = gp.SearchCursor(output_intersect_landuse)
    for item in nens.gp.gp_iterator(row):
        landuse_type = item.getValue(type_field)
        if landuse_type not in landuse_type_list:
            landuse_type_list.append(landuse_type)

    return landuse_type_list


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
        result[item_id] = {"from_x": pnt_list[0][0],
                           "from_y": pnt_list[0][1],
                           "to_x": pnt_list[-1][0],
                           "to_y": pnt_list[-1][1]}

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


def remove_null_values(gp, fc, field):
    """
    """
    row = gp.UpdateCursor(fc)

    for item in nens.gp.gp_iterator(row):
        field_value = item.GetValue(field)
        if field_value is None:
            item.SetValue(field, 0)
        row.UpdateRow(item)


def calculate_area_fields(gp, fc, output_fc, ovkident, input_dict, field_rural, field_urban):
    """
    """
    fieldmappings = gp.createobject("FieldMappings")
    fldmap_OVK_ID = gp.createobject("FieldMap")
    fldmap_OVK_ID.AddInputField(fc, ovkident)
    fieldmappings.AddFieldMap(fldmap_OVK_ID)

    gp.FeatureclassToFeatureclass_conversion(fc, os.path.dirname(output_fc), os.path.basename(output_fc), "#", fieldmappings)

    #gp.addfield_management(output_fc, ovkident, "TEXT")
    gp.addfield_management(output_fc, field_urban, "DOUBLE")
    gp.addfield_management(output_fc, field_rural, "DOUBLE")

    row = gp.UpdateCursor(output_fc)

    for item in nens.gp.gp_iterator(row):
        item_id = item.GetValue(ovkident)
        if input_dict.has_key(item_id):
            urban_area = input_dict[item_id][field_urban.lower()]
            if urban_area is None:
                urban_area = 0
            rural_area = input_dict[item_id][field_rural.lower()]
            if rural_area is None:
                rural_area = 0

            item.setValue(field_rural, float(rural_area))
            item.setValue(field_urban, float(urban_area))
        else:
            item.setValue(field_rural, 0)
            item.setValue(field_urban, 0)

        row.UpdateRow(item)


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
        if workspace == "-":
            workspace = tempfile.gettempdir()

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

        if len(sys.argv) == 5:
            input_polygon_fc = sys.argv[1]
            input_channel_fc = sys.argv[2]
            input_landuse_fc = sys.argv[3]
            output_channel = sys.argv[4]
        else:
            log.warning("usage: python geo_genereren_afv_opp.py <input peilgebieden> <input watergangen> <input landgebruik> <output waterlijnen met oppervlak>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)
        gpg_obj = gp.describe(input_polygon_fc)
        if gpg_obj.ShapeType != 'Polygon':
            geometry_check_list.append("input peilgebieden does not contain polygons, it contains shapetype: %s" % gpg_obj.ShapeType)
        else:
            log.info(" - input peilgebieden is correct")

        ovk_obj = gp.describe(input_channel_fc)
        if ovk_obj.ShapeType != 'Polyline':
            geometry_check_list.append("input channel does not contain polyline, it contains shapetype: %s" % ovk_obj.ShapeType)
        else:
            log.info(" - input channel is correct")

        lu_obj = gp.describe(input_landuse_fc)
        if lu_obj.ShapeType != 'Polygon':
            geometry_check_list.append("input landuse does not contain polygons, it contains shapetype: %s" % lu_obj.ShapeType)
        else:
            log.info(" - input landuse is correct")
        #"<check geometry from input data, append to list if incorrect>"

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []
        ovk_field = config.get('general', 'ovkident')
        gpg_field = config.get('general', 'gpgident')
        landuse_type = config.get('afv_opp', 'landuse_type')

        if not turtlebase.arcgis.is_fieldname(gp, input_polygon_fc, ovk_field):
            log.error("missing field '%s' in %s" % (ovk_field, input_polygon_fc))
            missing_fields.append("%s: %s" % (input_polygon_fc, ovk_field))

        if not turtlebase.arcgis.is_fieldname(gp, input_channel_fc, ovk_field):
            log.error("missing field '%s' in %s" % (ovk_field, input_channel_fc))
            missing_fields.append("%s: %s" % (input_channel_fc, ovk_field))

        if not turtlebase.arcgis.is_fieldname(gp, input_landuse_fc, 'type'):
            log.error("missing field 'type' in %s" % input_landuse_fc)
            missing_fields.append("%s: TYPE" % (input_landuse_fc))

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Environments

        log.info(" - intersect areas with landuse")
        output_intersect_landuse = workspace_gdb + "/landuse_intersect"
        log.info(output_intersect_landuse)
        gp.intersect_analysis(input_polygon_fc + "; " + input_landuse_fc, output_intersect_landuse)

        landuse_type_list = check_for_landuse_types(gp, output_intersect_landuse, "TYPE")
        if len(landuse_type_list) == 0:
            log.error("missing landuse types 'rural' and 'urban'")
            sys.exit(3)

        #log.info(turtlebase.arcgis.is_fieldname(gp, output_intersect_landuse, 'OPP_LA'))
        if not turtlebase.arcgis.is_fieldname(gp, output_intersect_landuse, 'OPP_LA'):
            log.info("create field OPP_LA")
            gp.addfield(output_intersect_landuse, 'OPP_LA', 'Double')
        if not turtlebase.arcgis.is_fieldname(gp, output_intersect_landuse, 'OPP_ST'):
            log.info("create field OPP_ST")
            gp.addfield(output_intersect_landuse, 'OPP_ST', 'Double')

        if 'urban' in landuse_type_list:
            log.info(" - calculate urban area")
            landuse_urban_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer_management(output_intersect_landuse, landuse_urban_lyr, " TYPE = 'urban' ")
            turtlebase.arcgis.calculate_area(gp, landuse_urban_lyr, "OPP_ST")

        if 'rural' in landuse_type_list:
            log.info(" - calculate rural area")
            landuse_rural_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer_management(output_intersect_landuse, landuse_rural_lyr, " TYPE = 'rural' ")
            turtlebase.arcgis.calculate_area(gp, landuse_rural_lyr, "OPP_LA")

        output_dissolve_landuse = workspace_gdb + "/dissolve"
        #tempfiles.append(output_dissolve_landuse)
        log.info("check if output fields exist")
        field_rural = "Sum_OPP_LA"
        field_urban = "Sum_OPP_ST"
        if turtlebase.arcgis.is_fieldname(gp, output_intersect_landuse, field_rural):
            log.info(" - %s already exists, delete field" % field_rural)
            gp.deletefield_management(output_intersect_landuse, field_rural)
        if turtlebase.arcgis.is_fieldname(gp, output_intersect_landuse, field_urban):
            gp.deletefield_management(output_intersect_landuse, field_urban)

        log.info(" - dissolve rural and urban areas")
        remove_null_values(gp, output_intersect_landuse, "OPP_LA")
        remove_null_values(gp, output_intersect_landuse, "OPP_ST")

        gp.Dissolve_management(output_intersect_landuse, output_dissolve_landuse, ovk_field, "OPP_LA sum; OPP_ST sum", "MULTI_PART")

        log.info("Copy landuse area to output")
        dissolve_dict = nens.gp.get_table(gp, output_dissolve_landuse, primary_key=ovk_field.lower())
        output_channel_fc = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        calculate_area_fields(gp, input_channel_fc, output_channel_fc, ovk_field, dissolve_dict, field_rural, field_urban)

        # add from and to coordinates
        log.info("Calculate coordinates")
        update_to_and_from_coordinates(gp, output_channel_fc, ovk_field.lower())
        log.info(" - copy output")
        gp.FeatureclassToFeatureclass_conversion(output_channel_fc, os.path.dirname(output_channel), os.path.basename(output_channel))
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
