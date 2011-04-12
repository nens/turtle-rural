# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import os
import sys
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.voronoi
import turtlebase.general

log = logging.getLogger(__name__)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)
        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL','location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        #check inputfields
        log.info("Getting commandline parameters... ")
        if len(sys.argv) == 5:
            input_polygon_fc = sys.argv[1] #peilgebieden waarbinnen de afvoervakken moeten worden gezocht
            input_channel_fc = sys.argv[2] #lijnstukken waarvan het dichtsbijzijnde gebied moet worden gezocht
            output_afvoervlakken_shp = sys.argv[3] #shapefile van de gecreerde afvoervakken per lijnstuk
            use_intersect_channel = sys.argv[4] # boolean, opknippen channel: ja of nee

        else:
            log.error("Usage: python rural_genereren_afvoervlakken.py <peilgebieden shape> <waterlijnen shape> <output shape>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        if not turtlebase.arcgis.is_file_of_type(gp, input_polygon_fc, 'Polygon'):
            log.error("%s is not a %s feature class!" % (input_polygon_fc, 'Polygon'))
            geometry_check_list.append("%s -> (%s)" % (input_polygon_fc, 'Polygon'))

        if not turtlebase.arcgis.is_file_of_type(gp, input_channel_fc, 'Polyline'):
            log.error("%s is not a %s feature class!" % (input_channel_fc, 'Polyline'))
            geometry_check_list.append("%s -> (%s)" % (input_channel_fc, 'Polyline'))

        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

        #----------------------------------------------------------------------------------------
        # Check required fields
        log.info("check required fields in input data")
        missing_fields = []
        ovk_field = config.get('afvoervlakken', 'input_channel_ident')
        gpg_field = config.get('GENERAL', 'gpgident')

        if not turtlebase.arcgis.is_fieldname(gp, input_polygon_fc, gpg_field):
            log.error("missing field '%s' in %s" % (gpg_field, input_polygon_fc))
            missing_fields.append("%s: %s" % (input_polygon_fc, gpg_field))

        if not turtlebase.arcgis.is_fieldname(gp, input_channel_fc, ovk_field):
            log.error("missing field '%s' in %s" % (ovk_field, input_channel_fc))
            missing_fields.append("%s: %s" % (input_channel_fc, ovk_field))

        if len(missing_fields) > 0:
            log.error("missing fields: %s" % missing_fields)

        #----------------------------------------------------------------------------------------
        polygon_dict = nens.gp.get_table(gp, input_polygon_fc, primary_key=gpg_field.lower())

        #extract channels within polygon
        intersect_waterlijn = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Intersect_analysis(input_polygon_fc + ";" + input_channel_fc, intersect_waterlijn)

        polygon_list = []
        for k,v in polygon_dict.items():
            log.info("extract polygon %s" % k)

            huidig_peilgebied_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer(input_polygon_fc, huidig_peilgebied_lyr, "%s = '%s'" % (gpg_field, k))

            log.debug("extract polylines within %s" % k)

            huidige_waterlijn_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer(intersect_waterlijn, huidige_waterlijn_lyr, "%s = '%s'" % (gpg_field, k))

            #count records
            record_count = turtlebase.arcgis.fc_records(gp, huidige_waterlijn_lyr)
            log.debug(" - record count: %s" % record_count)

            if record_count > 1:
                log.info(" - create voronoi polygons")
                point_selection = turtlebase.voronoi.create_points(gp, huidige_waterlijn_lyr, ovk_field)

                log.info(" - create line_voronoi")
                result_dict = turtlebase.voronoi.create_line_voronoi(point_selection)

                log.info(" - create polygons")
                polygon_fc = turtlebase.voronoi.create_merged_polygons(result_dict, workspace_gdb)

                log.info(" - intersect line_voronoi polygons")
                output_intersect_fc = turtlebase.arcgis.get_random_file_name(workspace_gdb)

                gp.Intersect_analysis(huidig_peilgebied_lyr + ";" + polygon_fc, output_intersect_fc)

                polygon_list.append(output_intersect_fc)

            elif record_count == 1:
                log.debug(" - 1 watergang in peilgebied, opknippen dus niet nodig, kopieer gpg")
                output_spatial_join = turtlebase.arcgis.get_random_file_name(workspace_gdb)

                gp.SpatialJoin_analysis(huidig_peilgebied_lyr, huidige_waterlijn_lyr, output_spatial_join)
                polygon_list.append(output_spatial_join)
            else:
                log.warning(" - geen watergang aanwezig in peilgebied, peilgebied wordt in zijn geheel meegenomen")
                polygon_list.append(huidig_peilgebied_lyr)
                pass
        #----------------------------------------------------------------------------------------
        # Merge all polygons together
        merge_str = ";".join(polygon_list)

        fieldmappings = gp.createobject("FieldMappings")
        fldmap_OVK_ID = gp.createobject("FieldMap")

        for fc in polygon_list:
            try:
                fldmap_OVK_ID.AddInputField(fc, ovk_field)
            except:
                pass

        fieldmappings.AddFieldMap(fldmap_OVK_ID)

        if use_intersect_channel == 'true':
            gp.Merge_management(merge_str, output_afvoervlakken_shp, fieldmappings)
        else:
            temp_merge_fc = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.Merge_management(merge_str, temp_merge_fc, fieldmappings)
            gp.dissolve_management(temp_merge_fc, output_afvoervlakken_shp, ovk_field)


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

