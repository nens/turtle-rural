# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import nens.sobek
import turtlebase.arcgis
import turtlebase.general
import turtlebase.extract_from_sobek
import sobek_objects

log = logging.getLogger(__name__)


def convert_sobek_object_to_gis(gp, network_ntw, object,
                                output_fc, ident, fields_to_add):
    """
    """
    count = 0
    if object in network_ntw.categorized.keys():
        log.info(" - convert %s" % object.lower().replace('sbk_', ''))
        sbk_network = network_ntw.categorized[object]

        turtlebase.extract_from_sobek.create_empty_shapefile(gp, output_fc,
                                                             fields_to_add,
                                                             metadata=True)
        turtlebase.extract_from_sobek.convert_sobek_point_to_shp(
                                            gp, sbk_network,
                                            output_fc, ident)
    return count


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
        projection_rdnew = os.path.join(os.path.dirname(sys.argv[0]), 'RDnew.prj')

        if len(sys.argv) == 3:
            sobek_folder = sys.argv[1]
            output_hydrobase = sys.argv[2]
        else:
            log.warning("usage: <sobek_folder> <output_hydrobase>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Environments
        workspace = os.path.dirname(output_hydrobase)
        gdb_name = os.path.basename(output_hydrobase)
        gp.CreateFileGDB_management(workspace, gdb_name)

        sr = gp.CreateObject("spatialreference")
        sr.CreateFromFile(projection_rdnew)

        gp.CreateFeatureDataset_management(output_hydrobase,
                                           "Structures", sr)
        output_structures = os.path.join(output_hydrobase,
                                         "Structures")
        gp.CreateFeatureDataset_management(output_hydrobase,
                                           "Cross_sections", sr)
        output_cross_sections = os.path.join(output_hydrobase,
                                             "Cross_sections")
        gp.CreateFeatureDataset_management(output_hydrobase,
                                           "Model_conditions", sr)
        output_model_conditions = os.path.join(output_hydrobase,
                                               "Model_conditions")

        """
        Import Sobek Network
        """
        network_ntw = nens.sobek.Network(os.path.join(sobek_folder,
                                                      'network.ntw'))

        univ_weir = 'SBK_UNIWEIR'
        weir = 'SBK_WEIR'
        culvert = 'SBK_CULVERT'
        pump = 'SBK_PUMP'
        bridge = 'SBK_BRIDGE'
        calc_p = 'SBK_GRIDPOINT'
        fixed_calc_p = 'SBK_GRIDPOINTFIXED'
        connection_n = 'SBK_CHANNELCONNECTION'
        prof_loc = 'SBK_PROFILE'
        boundary = 'SBK_BOUNDARY'
        #measurement = 'SBK_MEASSTAT'
        #rrcf_connection = 'SBK_SBK-3B-REACH'
        lateral_flow = 'SBK_LATERALFLOW'
        kwkident = sobek_objects.Common.KWKIDENT

        log.info("Convert Sobek CF-Structures to Turtle Hydrobase")
        """ Bridges
        """
        output_fc = os.path.join(output_structures, 'Bridge')
        print sobek_objects.Bridge.FIELDS
        count = convert_sobek_object_to_gis(gp, network_ntw, bridge,
                                            output_fc, kwkident,
                                            sobek_objects.Bridge.FIELDS)
        log.info(" - %s objects imported" % count)

        # Nodig voor output:
        # - struct.dat
        # - friction.dat
        # - struct.def
        # - profile.def

        """ Culverts & Syphons
        """
        output_fc = os.path.join(output_structures, 'Culvert')
        count = convert_sobek_object_to_gis(gp, network_ntw, culvert,
                                            output_fc, kwkident,
                                            sobek_objects.Culvert.FIELDS)
        log.info(" - %s objects imported" % count)

        """ Pump Stations
        """
        output_fc = os.path.join(output_structures, 'Pump_station')
        count = convert_sobek_object_to_gis(gp, network_ntw, pump,
                                            output_fc, kwkident,
                                            sobek_objects.PumpStation.FIELDS)
        log.info(" - %s objects imported" % count)

        log.info("Convert Universal Weirs")
        output_fc = os.path.join(output_structures, 'Universal_weir')
        count = convert_sobek_object_to_gis(gp, network_ntw, univ_weir,
                                    output_fc, kwkident,
                                    sobek_objects.UniversalWeir.FIELDS)
        log.info(" - %s objects imported" % count)

        log.info("Convert Weirs")
        output_fc = os.path.join(output_structures, 'Weir')
        count = convert_sobek_object_to_gis(gp, network_ntw, weir,
                                            output_fc, kwkident,
                                            sobek_objects.Weir.FIELDS)
        log.info(" - %s objects imported" % count)

        log.info("Convert Cross sections")
        """Locations
        """
        output_fc = os.path.join(output_cross_sections, 'Locations')
        count = convert_sobek_object_to_gis(gp, network_ntw, prof_loc,
                                    output_fc, sobek_objects.CrossSection.LOCIDENT,
                                    sobek_objects.CrossSection.FIELDS)
        log.info(" - %s objects imported" % count)

        log.info("Convert Model Conditions")
        """Lateral flows
        """
        output_fc = os.path.join(output_model_conditions, 'Lateral_Flow')
        count = convert_sobek_object_to_gis(gp, network_ntw, lateral_flow,
                                    output_fc, sobek_objects.LateralFlow.LATIDENT,
                                    sobek_objects.LateralFlow.FIELDS)
        log.info(" - %s objects imported" % count)

        # Nodig voor output:
        # - lateral.dat

        """Boundaries
        """
        output_fc = os.path.join(output_model_conditions, 'Boundaries')
        count = convert_sobek_object_to_gis(gp, network_ntw, boundary,
                                            output_fc, sobek_objects.Boundary.BNDIDENT,
                                            sobek_objects.Boundary.FIELDS)
        log.info(" - %s objects imported" % count)


        log.info("Convert Calculation points")
        merge_list = []
        temp_fc1 = os.path.join(workspace_gdb, 'Calculation_points')
        fields_to_add = sobek_objects.CalculationPoint.FIELDS
        cpident = sobek_objects.CalculationPoint.CPIDENT
        count = convert_sobek_object_to_gis(gp, network_ntw, calc_p,
                                            temp_fc1, cpident, fields_to_add)
        log.info(" - %s objects imported" % count)
        if calc_p in network_ntw.categorized.keys():
            merge_list.append(temp_fc1)

        log.info("Convert Fixed calculation points")
        temp_fc2 = os.path.join(workspace_gdb, 'Fixed_Calculation_points')
        count = convert_sobek_object_to_gis(gp, network_ntw, fixed_calc_p,
                                            temp_fc2, cpident, fields_to_add)
        log.info(" - %s objects imported" % count)
        if fixed_calc_p in network_ntw.categorized.keys():
            merge_list.append(temp_fc2)

        log.info("Convert Connection nodes")
        temp_fc3 = os.path.join(workspace_gdb, 'Connection_nodes')
        count = convert_sobek_object_to_gis(gp, network_ntw, connection_n,
                                            temp_fc3, cpident, fields_to_add)
        log.info(" - %s objects imported" % count)
        if connection_n in network_ntw.categorized.keys():
            merge_list.append(temp_fc3)
        log.info(" - %s objects imported" % count)

        output_fc = os.path.join(output_model_conditions, 'Calculation_points')
        if len(merge_list) > 1:
            gp.Merge_management(merge_list, output_fc)
        elif len(merge_list) == 1:
            gp.Select_analysis(merge_list[0], output_fc)

        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(workspace_gdb)

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
