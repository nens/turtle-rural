# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import csv
import os
import tempfile
import arcpy

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import shapefile
import nens.sobek
import time

log = logging.getLogger(__name__)
NO_DATA_VALUE = -9999

class OutputError(Exception):
    pass


def add_to_csv(output_csv, csv_data, write_or_append):
    """
    Will create a csv file when write_or_append = 'wb'. Choose binairy! Adds a
    line to an existing csv file when write_or_append = 'ab'.
    output_csv = "c:\\test\\output.csv" (output location of the csv file)
    (list with tuples, will be added to csv)
    """
    csv_file = open(output_csv, write_or_append)
    writer = csv.writer(csv_file)
    writer.writerows(csv_data)
    csv_file.close()


def create_shapefiles(gp, config, sobek_network_dict,
                      sobek_object, output_fc, profile_dict):
    '''
    creates a shapefile from a dictionary with x and y coordinates
    '''
    cross_section_type = config.get('CrossSections', 'cross_section_type')
    idfield = config.get('CrossSections', 'cross_section_id')
    difield = config.get('CrossSections', 'cross_sections_def_id')

    workspace = os.path.dirname(output_fc)
    fc_name = os.path.basename(output_fc)

    for type_name in sobek_network_dict.categorized.keys():

        if type_name == sobek_object:
            gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                                             "#", "DISABLED", "DISABLED", "#")

            gp.addfield(output_fc, idfield, "TEXT")
            gp.addfield(output_fc, difield, "TEXT")
            gp.addfield(output_fc, cross_section_type, "TEXT")

            rows = gp.InsertCursor(output_fc)
            point = gp.CreateObject("Point")

            for i, (id, x, y) in enumerate(sobek_network_dict[type_name]):
                try:
                    
                    # adding id of profile definition
                    # only if id is in both dicts
                    #locident = profile_dict[id][idfield]
                    proident = profile_dict[id][difield]
                    #add new point
                    row = rows.NewRow()
                    point = setPointAttributes(point, i, x, y)
                    row.shape = point
                    id = str(id)
                    row.SetValue(idfield, id)
                    row.SetValue(difield, str(proident))
                    row.SetValue(cross_section_type, str(sobek_object))
                    rows.InsertRow(row)
                except:
                    log.warning("failed to add %s" % id)
            del rows
            del row

def append_to_hydrobase(input_fc, output_fc):
    """
    """
    arcpy.Append_management(input_fc, output_fc, "NO_TEST")
    arcpy.CalculateField_management(output_fc, "DATE_TIME", "Now (  )", "VB")
            

def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Create workspace
        global tempfile
        workspace = config.get('GENERAL', 'location_temp')
        if workspace == "-":
            workspace = tempfile.gettempdir()

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        #---------------------------------------------------------------------
        # Input parameters
        """
        nodig voor deze tool:
        """
        if len(sys.argv) == 3:
            sbk_case = sys.argv[1]
            output_gdb = sys.argv[2]            
        else:
            log.warning("usage: <sobek_case_folder> <output_gdb>")
            sys.exit(1)

        if not os.path.isabs(output_gdb):
            log.error("%s is geen juiste outputlocatie" % output_gdb)
            raise OutputError()
        if os.path.dirname(output_gdb).endswith(".gdb"):
            log.error("%s is geen juiste outputlocatie (geodatabase in een geodatabase)" % output_gdb)
            raise OutputError()
        if not output_gdb.endswith(".gdb"):
            output_gdb = output_gdb + ".gdb"
            
        script_path = os.path.dirname(sys.argv[0])
        
        #Kopieren Hydrobase
        hydrobase_cf = os.path.join(script_path, "hydrobases", "HydroBaseCF.gdb")
        log.info(" - copy default hydrobase")
        arcpy.Copy_management(hydrobase_cf, output_gdb, "Workspace")
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_files = []

        check_files = ['network.ntw', 'boundary.dat', 'profile.dat', 'profile.def', 'struct.dat', 'struct.def', 'initial.dat', 'friction.dat', 'control.def']
        for check_file in check_files:
            if not os.path.isfile(os.path.join(sbk_case, check_file)):
                missing_files.append(check_file)

        if len(missing_files) > 0:
            log.error("missing files in sobek directory: %s" % missing_files)
            sys.exit(2)
        #---------------------------------------------------------------------
        time_str = time.strftime("%d/%m/%Y %H:%M:%S")
        log.info("Read Sobek Network file")
        sobek_network_dict = nens.sobek.Network(os.path.join(sbk_case, 'network.ntw'))

        available_types = []
        for id, x, y in sobek_network_dict['SBK_CHANNEL']:
            if x[0] not in available_types:
                available_types.append(x[0])
            if y[0] not in available_types:
                available_types.append(y[0])

        if '3B_LINK' in sobek_network_dict:
            RR_Network = True
            for id, x, y in sobek_network_dict['3B_LINK']:
                if x[0] not in available_types:
                    available_types.append(x[0])
                if y[0] not in available_types:
                    available_types.append(y[0])
        else:
            log.info(" - no RR network found")
            RR_Network = False

        network_coords = {}
        for network_type in available_types:
            for id, x, y in sobek_network_dict[network_type]:
                network_coords[id] = (x, y)

        #---------------------------------------------------------------------    
        #RR Network
        if RR_Network == True:
            log.info("Read RR Features")
            rr_nodes = shapefile.Writer(shapefile.POINT)
            rr_nodes.field('GPGIDENT')
            rr_nodes.field('SBKIDENT')
            rr_nodes.field('TYPE')

            if '3B_UNPAVED' in available_types:
                for i, (ident, x, y) in enumerate(sobek_network_dict['3B_UNPAVED']):
                        rr_nodes.point(float(x), float(y))
                        rr_nodes.record(ident, ident, '3B_UNPAVED')

            if '3B_PAVED' in available_types:
                for i, (ident, x, y) in enumerate(sobek_network_dict['3B_PAVED']):
                        rr_nodes.point(float(x), float(y))
                        rr_nodes.record(ident, ident, '3B_PAVED')
                        

            if '3B_GREENHOUSE' in available_types:
                for i, (ident, x, y) in enumerate(sobek_network_dict['3B_GREENHOUSE']):
                        rr_nodes.point(float(x), float(y))
                        rr_nodes.record(ident, ident, '3B_GREENHOUSE')

            rr_nodes_shp = os.path.join(workspace, 'rr_nodes.shp')
            rr_nodes.save(rr_nodes_shp)

            #RRCF Connection Nodes
            rrcf_connections = shapefile.Writer(shapefile.POINT)            
            rrcf_connections.field('KPIDENT')
            rrcf_connections.field('SBKIDENT')
            rrcf_connections.field('SBKTYPE')
            
            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_SBK-3B-REACH']):
                rrcf_connections.point(float(x), float(y))
                rrcf_connections.record(ident, ident, 'SBK_SBK-3B-REACH')
                
            rrcf_connections_shp = os.path.join(workspace, "rrcf_connections.shp")
            rrcf_connections.save(rrcf_connections_shp)

            # RR Network
            rr_line = shapefile.Writer(shapefile.POLYLINE)
            rr_line.field('RRIDENT')
            rr_line.field('FROM_POINT')
            rr_line.field('FROM_TYPE')
            rr_line.field('TO_POINT')
            rr_line.field('TO_TYPE')

            for i, (ident, from_node, to_node) in enumerate(sobek_network_dict['3B_LINK']):
                x1, y1 = network_coords[from_node[1]]
                x2, y2= network_coords[to_node[1]]
                rr_line.line(parts=[[[float(x1), float(y1)],[float(x2),float(y2)]]])
                rr_line.record(ident, from_node[1], from_node[0], to_node[1], to_node[0])
                
            rr_lines_shp = os.path.join(workspace, "rr_lines.shp")
            rr_line.save(rr_lines_shp)

            #append rr features
            log.info(" - append rrcf_connections to hydrobase")
            arcpy.Append_management(rrcf_connections_shp, os.path.join(output_gdb, "RR_features", "RRCF_connections"), "NO_TEST")
            log.info(" - append rr_nodes to hydrobase")
            arcpy.Append_management(rr_nodes_shp, os.path.join(output_gdb, "RR_features", "RR_nodes"), "NO_TEST")
            log.info(" - append rr_network to hydrobase")
            arcpy.Append_management(rr_lines_shp, os.path.join(output_gdb, "RR_features", "RR_network"), "NO_TEST")
        else:
            log.info(" - RR Features skipped")
        #---------------------------------------------------------------------
        #Sobek CF Database:
        log.info("Read CF Features")
        # CF Network
        # - channel
        log.info(' - copy channels')
        channel = shapefile.Writer(shapefile.POLYLINE)
        channel.field('OVKIDENT')
        channel.field('FROM_POINT')
        channel.field('FROM_TYPE')
        channel.field('TO_POINT')
        channel.field('TO_TYPE')

        for i, (ident, from_node, to_node) in enumerate(sobek_network_dict['SBK_CHANNEL']):
            x1, y1 = network_coords[from_node[1]]
            x2, y2= network_coords[to_node[1]]
            channel.line(parts=[[[float(x1), float(y1)],[float(x2),float(y2)]]])
            channel.record(ident, from_node[1], from_node[0], to_node[1], to_node[0])
            
        channel_shp = os.path.join(workspace, "channel.shp")
        channel.save(channel_shp)

        #append channels
        log.info(" - append channels to hydrobase")
        append_to_hydrobase(channel_shp, os.path.join(output_gdb, "Channel", "Channel"))
        
        #boundary_dat = nens.sobek.File(os.path.join(sbk_case, 'boundary.dat'))
        #initial_dat = nens.sobek.File(os.path.join(sbk_case, 'initial.dat'))
        #friction_dat = nens.sobek.File(os.path.join(sbk_case, 'friction.dat'))
        #control_def = nens.sobek.File(os.path.join(sbk_case, 'control.def'))
        #lateral_dat = nens.sobek.File(os.path.join(sbk_case, 'lateral.dat'))        

        profiles = {}
        log.info(' - read profile.dat')
        prof_dat = nens.sobek.File(os.path.join(sbk_case, 'profile.dat'))
        for profile in prof_dat['CRSN']:
            profiles[profile['id'][0]] = {'id': profile['id'][0], 'def_id': profile['di'][0], 'ref_level': profile['rl'][0], 'ref_surface': profile['rs'][0]}

        cross_section_definition_csv = os.path.join(workspace, "cross_section_definiton.csv")
        add_to_csv(cross_section_definition_csv, [('PROIDENT', 'TYPE', 'BED_LVL', 'BED_WDTH', 'BED_WDTH_M',
                                                    'WAT_LVL', 'WAT_WDTH', 'WAT_WDTH_M', 'SUR_LVL', 'SUR_WDTH', 'SUR_WDTH_M',
                                                    'TALUD', 'DIAMETER', 'WIDTH', 'HEIGHT', 'SOURCE', 'DATE_TIME', 'COMMENTS')], "wb")
        profiles_def = {}
        log.info(' - read profile.def')
        prof_def = nens.sobek.File(os.path.join(sbk_case, 'profile.def'))
        cross_section_yz_csv = os.path.join(workspace, "cross_section_yz.csv")
        add_to_csv(cross_section_yz_csv, [('PROIDENT', 'DIST_MID', 'BED_LVL')], "wb")
        for profile_def in prof_def['CRDS']:
            min_lvl = 9999
            talud = wat_lvl = wat_wdth = wat_wdth_m = bed_wdth = bed_wdth_m = sur_lvl = sur_wdth = sur_wdth_m = NO_DATA_VALUE
            if profile_def['ty'][0] == 1:
                proftype = 'trapezium'
                talud = profile_def['bs'][0]
                bed_wdth = profile_def['bw'][0]
                sur_wdth = profile_def['aw'][0]
            elif profile_def['ty'][0] == 10:
                proftype = 'yz profiel'
                yz_tabel = profile_def['lt yz'][0]
                
                for i in range(yz_tabel.rows()):
                    add_to_csv(cross_section_yz_csv, [(profile_def['id'][0], yz_tabel[i, 0], yz_tabel[i, 1])], "ab")
                    if yz_tabel[i, 1] < min_lvl:
                        min_lvl = yz_tabel[i, 1]
                
            elif profile_def['ty'][0] == 0:
                proftype = 'tabulated'
                lw_tabel = profile_def['lt lw'][0]
                if lw_tabel.rows() == lw_tabel.cols() == 3:
                    min_lvl = lw_tabel[0, 0]
                    bed_wdth = lw_tabel[0, 1]
                    bed_wdth_m = lw_tabel[0, 2]
                    wat_lvl = lw_tabel[1, 0]
                    wat_wdth = lw_tabel[1, 1]
                    wat_wdth_m = lw_tabel[1, 2]
                    sur_lvl = lw_tabel[2, 0]
                    sur_wdth = lw_tabel[2, 1]
                    sur_wdth_m = lw_tabel[2, 2]                    
                else:
                    for i in range(lw_tabel.rows()):
                        dist_mid = float(lw_tabel[i, 1]) / 2
                        zcoord = float(lw_tabel[i, 0])
                        add_to_csv(cross_section_yz_csv, [(profile_def['id'][0], dist_mid, zcoord)], "ab")
                        add_to_csv(cross_section_yz_csv, [(profile_def['id'][0], 0 - dist_mid, zcoord)], "ab")
                        if lw_tabel[i, 0] < min_lvl:
                            min_lvl = lw_tabel[i, 0]
                    proftype = 'yz_profiel'
            elif profile_def['ty'][0] == 4:
                proftype = 'rond'
                wat_wdth = float(profile_def['rd'][0]) * 2            
                
            else:
                proftype = 'overig: %s' % profile_def['ty'][0]

            profiles_def[profile_def['id'][0]] = {'id': profile_def['id'][0], "type": proftype, 'talud': talud,
                                                  'bed_wdth': bed_wdth, 'bed_wdth_m': bed_wdth_m, 'sur_lvl': sur_lvl, 'sur_wdth': sur_wdth, 'sur_wdth_m': sur_wdth_m,
                                                  'wat_lvl': wat_lvl, 'wat_wdth': wat_wdth, 'wat_wdth_m': wat_wdth_m, 'min_lvl': min_lvl}

        
        for profile, values in profiles.items():
            def_id = values['def_id']
            min_lvl = profiles_def[def_id]['min_lvl']
            if min_lvl != 9999:
                # cross section level shift
                bed_lvl = float(values['ref_level']) + float(min_lvl)
            else:
                bed_lvl = float(values['ref_level'])            
            
            add_to_csv(cross_section_definition_csv, [(profile, profiles_def[def_id]['type'], bed_lvl, profiles_def[def_id]['bed_wdth'], profiles_def[def_id]['bed_wdth_m'],
                                                       profiles_def[def_id]['wat_lvl'], profiles_def[def_id]['wat_wdth'], profiles_def[def_id]['wat_wdth_m'],
                                                       profiles_def[def_id]['sur_lvl'], profiles_def[def_id]['sur_wdth'], profiles_def[def_id]['sur_wdth_m'],
                                                       profiles_def[def_id]['talud'], NO_DATA_VALUE, NO_DATA_VALUE, NO_DATA_VALUE, sbk_case, time_str, "")], "ab")
            
        if 'SBK_CULVERT' in available_types:
            log.info(' - copy cross sections')
            location_shp = os.path.join(workspace, "location.shp")
            location = shapefile.Writer(shapefile.POINT)
                                        
            location_fields = ['LOCIDENT', 'PROIDENT', 'TYPE', 'X_COORD', 'Y_COORD', 'SOURCE', 'DATE_TIME', 'COMMENTS']
            for loc_field in location_fields:
                location.field(loc_field)

            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_PROFILE']):
                def_id = profiles[ident]['def_id']
                if def_id in profiles_def:
                    location.point(float(x), float(y))
                    
                    proftype = profiles_def[def_id]['type']
                    location.record(ident, ident, proftype, float(x), float(y), sbk_case, time_str, "")
                
            location.save(location_shp)        

            #append data to hydrobase
            log.info(" - append cross sections to hydrobase")
            append_to_hydrobase(location_shp, os.path.join(output_gdb, "Cross_sections", "locations"))
            log.info(" - append cross sections definitions to hydrobase")
            arcpy.Append_management(cross_section_definition_csv, os.path.join(output_gdb, "Cross_section_definition"), "NO_TEST")
            log.info(" - append cross sections yz-table to hydrobase")
            arcpy.Append_management(cross_section_yz_csv, os.path.join(output_gdb, "Cross_section_yz"), "NO_TEST")

        else:
            log.warning(" - no cross sections found ")

        # Structures
        structures = {}
        log.info(' - read structure.dat')
        struct_dat = nens.sobek.File(os.path.join(sbk_case, 'struct.dat'))
        for structure in  struct_dat['STRU']:
            structures[structure['id'][0]] = {'id': structure['id'][0], 'def_id': structure['dd'][0], 'nm': structure['nm'][0]}

        culvert_def = {}
        weir_def = {}
        pump_def = {}
        
        struct_def = nens.sobek.File(os.path.join(sbk_case, 'struct.def'))
        log.info(' - read structure.def')
        for structure_def in struct_def['STDS']:
            if structure_def['ty'][0] == 6:
                weir_def[structure_def['id'][0]] = {'id': structure_def['id'][0], 'name': structure_def['nm'][0], 'crest_lvl': structure_def['cl'][0], 'crest_wdth': structure_def['cw'][0], 'dis_coef': structure_def['ce'][0]}
            elif structure_def['ty'][0] == 9:
                pump_tble = structure_def['ct lt'][1]
                capacity = pump_tble[0,0]
                suc_start = pump_tble[0,1]
                suc_stop = pump_tble[0,2]
                prs_start = pump_tble[0,3]
                prs_stop = pump_tble[0,4]
                pump_def[structure_def['id'][0]] = {'id': structure_def['id'][0], 'name': structure_def['nm'][0], 'capacity': capacity, 'suc_start': suc_start, 'suc_stop': suc_stop, 'prs_start': prs_start, 'prs_stop': prs_stop}
            elif structure_def['ty'][0] == 10:
                culvert_def[structure_def['id'][0]] = {'id': structure_def['id'][0], 'name': structure_def['nm'][0], 'bed_lvl_1': structure_def['ll'][0], 'bed_lvl_2': structure_def['rl'][0],
                                                      'lengte': structure_def['dl'][0], 'inlet_loss': structure_def['li'][0], 'outlet_loss': structure_def['lo'][0], 'profile_ident': structure_def['si'][0]}                  

        # - culvert
        if 'SBK_CULVERT' in available_types:
            log.info(' - copy culverts')
            culvert = shapefile.Writer(shapefile.POINT)
            culvert_fields = ['KWKIDENT', 'KWK_NAAM', 'TYPE', 'DIAMETER', 'WIDTH', 'HEIGHT', 'LENGTH', 'BED_LVL_1', 'BED_LVL_2', 'FRICTION', 'INLET_LOSS', 'OUTLET_LOS', 'SOURCE']
            for c_field in culvert_fields:
                culvert.field(c_field)

            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_CULVERT']):
                width = height = diameter = NO_DATA_VALUE
                culvert_def_id = structures[ident]['def_id']
                culvert_name = culvert_def[culvert_def_id]['name']
                profile_ident = culvert_def[culvert_def_id]['profile_ident']

                if profile_ident in profiles_def:
                    culvert.point(float(x), float(y))
                    profile_type = profiles_def[profile_ident]['type']
                    if profile_type == 'tabulated':
                        culvert_type = 'rechthoek'
                        width = profiles_def[profile_ident]['bed_wdth']
                        height = profiles_def[profile_ident]['sur_lvl']
                    elif profile_type == 'rond':
                        culvert_type = 'rond'
                        diameter = profiles_def[profile_ident]['wat_wdth']
                    else:
                        culvert_type = 'onbekend'
                                
                    culvert.record(ident, culvert_name, culvert_type, diameter, width, height, culvert_def[culvert_def_id]['lengte'], culvert_def[culvert_def_id]['bed_lvl_1'],
                                   culvert_def[culvert_def_id]['bed_lvl_2'], NO_DATA_VALUE, culvert_def[culvert_def_id]['inlet_loss'],
                                   culvert_def[culvert_def_id]['outlet_loss'], sbk_case)
                else:
                    log.warning("%s heeft geen profiel" % ident)

            culvert_shp = os.path.join(workspace, "culvert.shp")
            culvert.save(culvert_shp)
            #append culverts
            log.info(" - append culverts to hydrobase")
            append_to_hydrobase(culvert_shp, os.path.join(output_gdb, "Structures", "Culvert"))
            
        else:
            log.warning(" - no culverts found ")
            
        # - weir
        if 'SBK_WEIR' in available_types:
            weir = shapefile.Writer(shapefile.POINT)
            weir_fields = ['KWKIDENT', 'KWK_NAME', 'TYPE', 'CREST_WDTH', 'CREST_LVL', 'CREST_SUM', 'CREST_WIN', 'DIS_COEF', 'SOURCE']
            for w_field in weir_fields:
                weir.field(w_field)

            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_WEIR']):
                weir_def_id = structures[ident]['def_id']
                weir_name = weir_def[weir_def_id]['name']
                weir.point(float(x), float(y))
                weir.record(ident, weir_name, "VAST", weir_def[weir_def_id]['crest_wdth'], weir_def[weir_def_id]['crest_lvl'], NO_DATA_VALUE, NO_DATA_VALUE, weir_def[weir_def_id]['dis_coef'], sbk_case)

            weir_shp = os.path.join(workspace, "weir.shp")
            weir.save(weir_shp)

            #append weirs
            log.info(" - append weirs to hydrobase")
            append_to_hydrobase(weir_shp, os.path.join(output_gdb, "Structures", "Weir"))
        else:
            log.warning(" - no weirs found ")
            
        # - pump stations
        #append pump stations
        pump_def_csv = os.path.join(workspace, "pump_def.csv")
        add_to_csv(pump_def_csv, [('KWKIDENT', 'CAPACITY', 'STAGE', 'SUC_START', 'SUC_STOP',
                                                    'PRS_START', 'PRS_STOP')], "wb")
        
        if 'SBK_PUMP' in available_types:
            pump = shapefile.Writer(shapefile.POINT)
            pump_fields = ['KWKIDENT', 'KWK_NAAM', 'CONTROLLER', 'SOURCE']
            for p_field in pump_fields:
                pump.field(p_field)
            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_PUMP']):
                pump_def_id = structures[ident]['def_id']
                pump.point(float(x), float(y))
                pump.record(ident, structures[ident]['nm'], "JAAR", sbk_case)
                capacity = (pump_def[pump_def_id]['capacity']) * 3600
                add_to_csv(pump_def_csv, [(ident, capacity, 1, pump_def[pump_def_id]['suc_start'],
                                           pump_def[pump_def_id]['suc_stop'], pump_def[pump_def_id]['prs_start'],
                                           pump_def[pump_def_id]['prs_stop'])], "ab")

            pump_shp = os.path.join(workspace, "pump.shp")              
            pump.save(pump_shp)
            
            log.info(" - append pump stations to hydrobase")        
            append_to_hydrobase(pump_shp, os.path.join(output_gdb, "Structures", "Pump_station"))
            log.info(" - append pump station definitions to hydrobase")
            arcpy.Append_management(pump_def_csv, os.path.join(output_gdb, "Pump_station_def"), "NO_TEST")
        else:
            log.warning(" - no pump stations found ")

        # - lateral flows
        if 'SBK_LATERALFLOW' in available_types:
            log.info(' - copy Lateral flow')
            lateral = shapefile.Writer(shapefile.POINT)
            lateral_fields = ['LAT_IDENT', 'LAT_TYPE', 'DISCHARGE', 'AREA', 'SEEPAGE']
            for l_field in lateral_fields:
                lateral.field(l_field)

            for i, (ident, x, y) in enumerate(sobek_network_dict['SBK_LATERALFLOW']):
                lateral.point(float(x), float(y))
                lateral.record(ident, NO_DATA_VALUE, NO_DATA_VALUE, NO_DATA_VALUE, NO_DATA_VALUE)
    
            lateral_shp = os.path.join(workspace, "lateral.shp")
            lateral.save(lateral_shp)

            #append lateral flow
            log.info(" - append lateral flow nodes to hydrobase")
            arcpy.Append_management(lateral_shp, os.path.join(output_gdb, "Model_conditions", "Lateral_Flow"), "NO_TEST")
        else:
            log.warning(" - no lateral flows found ")

        #---------------------------------------------------------------------
        mainutils.log_footer()
    except OutputError:
        sys.exit(1)
        
    except:
        log.exception("")
        sys.exit(1)

    finally:
        logging_config.cleanup()
        arcpy.CheckInExtension("DataInteroperability")
        del gp
