# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import time
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import nens.sobek
import turtlebase.arcgis
import turtlebase.general
import turtlebase.extract_from_sobek

log = logging.getLogger(__name__)


def convert_sobek_oject_to_gis(gp, network_ntw, object, output_fc, ident, fields_to_add):
    """
    """
    if object in network_ntw.categorized.keys():
        log.info(" - convert %s" % object.lower().replace('sbk_', ''))
        sbk_network = network_ntw.categorized[object]
        
        turtlebase.extract_from_sobek.create_empty_shapefile(gp, output_fc,
                                                             fields_to_add, metadata=True)
        turtlebase.extract_from_sobek.convert_sobek_point_to_shp(
                                            gp, sbk_network,
                                            output_fc, ident)
    
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
        sobek_folder = "C:\\Sobek212\\Turtle.lit\\2"
        time_str = time.strftime("%H%M%S")
        output_hydrobase = "C:\\GISTEMP\\Turtlework\\Hydrobase_Sobek_%s.gdb" % time_str
        projection_rdnew = os.path.join(os.path.dirname(sys.argv[0]), 'RDnew.prj')
        
        #if len(sys.argv) == "<number of arguments for this tool>":
        #    argument1 = sys.argv[1]
        #else:
        #    log.warning("usage: <argument1> <argument2>")
        #    sys.exit(1)
        date_time = time.strftime("%Y/%m/%d %H:%M:%S")
        #---------------------------------------------------------------------
        # Environments
        workspace = os.path.dirname(output_hydrobase)
        gdb_name = os.path.basename(output_hydrobase)
        gp.CreateFileGDB_management(workspace, gdb_name)

        sr = gp.CreateObject("spatialreference")
        sr.CreateFromFile(projection_rdnew)
        
        gp.CreateFeatureDataset_management(output_hydrobase, "Structures", sr)
        output_structures = os.path.join(output_hydrobase, "Structures")
        gp.CreateFeatureDataset_management(output_hydrobase, "Cross_sections", sr)
        output_cross_sections = os.path.join(output_hydrobase, "Cross_sections")
        gp.CreateFeatureDataset_management(output_hydrobase, "Model_conditions", sr)
        output_model_conditions = os.path.join(output_hydrobase, "Model_conditions")
        
        """
        Import Sobek Network
        """
        network_ntw = nens.sobek.Network(os.path.join(sobek_folder, 'network.ntw'))
        
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
        measurement = 'SBK_MEASSTAT'
        rrcf_connection = 'SBK_SBK-3B-REACH'
        lateral_flow = 'SBK_LATERALFLOW'
        kwkident = 'KWKIDENT'
        locident = 'LOCIDENT'
        proident = 'PROIDENT'

        log.info("Convert Sobek CF-Structures to Turtle Hydrobase")
        """ Bridges
        """
        fields_to_add = [(kwkident, 'TEXT'), ('KWK_NAME', 'TEXT'),
                         ('TYPE', 'TEXT'), ('LENGTH', 'DOUBLE'),
                         ('WIDTH', 'DOUBLE'), ('BED_LVL', 'DOUBLE'),
                         ('TOP_LVL', 'DOUBLE'), ('PILL_WIDTH', 'DOUBLE'),
                         ('PILL_FF', 'DOUBLE'), ('FRICTION', 'DOUBLE'),
                         ('FR_VALUE', 'DOUBLE')]
        output_fc = os.path.join(output_structures, 'Bridge')
        convert_sobek_oject_to_gis(gp, network_ntw, bridge, output_fc, kwkident, fields_to_add)
        
        """ Culverts & Syphons
        """
        fields_to_add = [(kwkident, 'TEXT'), ('KWK_NAME', 'TEXT'),
                         ('TYPE', 'TEXT'), ('DIAMETER', 'DOUBLE'),
                         ('WIDTH', 'DOUBLE'), ('HEIGHT', 'DOUBLE'),
                         ('LENGTH', 'DOUBLE'), ('BED_LVL_1', 'DOUBLE'),
                         ('BED_LVL_2', 'DOUBLE'), ('FRICTION', 'DOUBLE'),
                         ('FR_VALUE', 'DOUBLE'), ('INLET_LOSS', 'DOUBLE'),
                         ('OUTLET_LOS', 'DOUBLE'), ('BEND_LOSS', 'DOUBLE')]

        output_fc = os.path.join(output_structures, 'Culvert')
        convert_sobek_oject_to_gis(gp, network_ntw, culvert, output_fc, kwkident, fields_to_add)

        """ Pump Stations
        """
        fields_to_add = [(kwkident, 'TEXT'), ('KWK_NAME', 'TEXT'),
                         ('CONTROLLER', 'TEXT')]
        
        output_fc = os.path.join(output_structures, 'Pump_station')
        convert_sobek_oject_to_gis(gp, network_ntw, pump, output_fc, kwkident, fields_to_add)
        
        """ Universal Weir
        """
        fields_to_add = [(kwkident, 'TEXT'), ('KWK_NAME', 'TEXT'),
                         ('CONTROLLER', 'TEXT')]
        
        output_fc = os.path.join(output_structures, 'Universal_weir')
        convert_sobek_oject_to_gis(gp, network_ntw, univ_weir, output_fc, kwkident, fields_to_add)
        
        """ Weir
        """
        fields_to_add = [(kwkident, 'TEXT'), ('KWK_NAME', 'TEXT'),
                         ('PROIDENT', 'TEXT'), ('X_COORD', 'DOUBLE'),
                         ('Y_COORD', 'DOUBLE'), ('DIS_COEF', 'DOUBLE')]

        output_fc = os.path.join(output_structures, 'Weir')
        convert_sobek_oject_to_gis(gp, network_ntw, weir, output_fc, kwkident, fields_to_add)

        log.info("Convert Cross sections")
        """Locations
        """
        fields_to_add = [(locident, 'TEXT'), (proident, 'TEXT'),
                         ('TYPE', 'TEXT'), ('X_COORD', 'DOUBLE'),
                         ('Y_COORD', 'DOUBLE')]

        output_fc = os.path.join(output_cross_sections, 'Locations')
        convert_sobek_oject_to_gis(gp, network_ntw, prof_loc, output_fc, locident, fields_to_add)

        log.info("Convert Model Conditions")
        """Lateral flows
        """
        fields_to_add = [('LAT_IDENT', 'TEXT'), ('LAT_TYPE', 'TEXT'),
                         ('DISCHARGE', 'DOUBLE'), ('AREA', 'DOUBLE'),
                         ('SEEPAGE', 'DOUBLE')]

        output_fc = os.path.join(output_model_conditions, 'Lateral_Flow')
        convert_sobek_oject_to_gis(gp, network_ntw, lateral_flow, output_fc, 'LAT_IDENT', fields_to_add)

        """Boundaries
        """
        fields_to_add = [('BND_IDENT', 'TEXT'), ('BND_NAAM', 'TEXT'),
                         ('BND_TYPE', 'TEXT'), ('BND_VALUE', 'TEXT'), 
                         ('WATERLEVEL', 'DOUBLE'), ('FLOW', 'DOUBLE')]

        output_fc = os.path.join(output_model_conditions, 'Boundaries')
        convert_sobek_oject_to_gis(gp, network_ntw, boundary, output_fc, 'BND_IDENT', fields_to_add)
        
        """Calculation points
        """
        fields_to_add = [('CP_IDENT', 'TEXT')]
        merge_list = []
        temp_fc1 = os.path.join(workspace_gdb, 'Calculation_points')
        convert_sobek_oject_to_gis(gp, network_ntw, calc_p, temp_fc1, 'CP_IDENT', fields_to_add)
        if calc_p in network_ntw.categorized.keys():
            merge_list.append(temp_fc1)
        
        temp_fc2 = os.path.join(workspace_gdb, 'Fixed_Calculation_points')
        convert_sobek_oject_to_gis(gp, network_ntw, fixed_calc_p, temp_fc2, 'CP_IDENT', fields_to_add)
        if fixed_calc_p in network_ntw.categorized.keys():
            merge_list.append(temp_fc2)
        
        temp_fc3 = os.path.join(workspace_gdb, 'Connection_nodes')
        convert_sobek_oject_to_gis(gp, network_ntw, connection_n, temp_fc3, 'CP_IDENT', fields_to_add)
        if connection_n in network_ntw.categorized.keys():
            merge_list.append(temp_fc3)
        
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
