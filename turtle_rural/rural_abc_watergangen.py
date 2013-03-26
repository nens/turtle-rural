# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import turtlebase.arcgis
import networkx as nx

log = logging.getLogger(__name__)


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
            import tempfile
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
        if len(sys.argv) == 5:
            a_watergang = sys.argv[1]
            bc_watergang = sys.argv[2]
            output_fc = sys.argv[3]
            point_intersection = sys.argv[4]
        else:
            log.warning("usage: <argument1> <argument2>")
            sys.exit(1)
            
        tempfiles = []

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        if not turtlebase.arcgis.is_file_of_type(gp, bc_watergang, 'Polyline'):
            log.error("%s is not a %s feature class!" % (bc_watergang, 'Polyline'))
            geometry_check_list.append("%s -> (%s)" % (bc_watergang, 'Polyline'))
            
        if not turtlebase.arcgis.is_file_of_type(gp, a_watergang, 'Polyline'):
            log.error("%s is not a %s feature class!" % (a_watergang, 'Polyline'))
            geometry_check_list.append("%s -> (%s)" % (a_watergang, 'Polyline'))
                
        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")
        ovkident = "OVKIDENT"
        if not turtlebase.arcgis.is_fieldname(gp, a_watergang, ovkident):
            log.error("missing fields in input data: %s" % ovkident)
            sys.exit(2)
        
        bc_watergang_tmp = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Select_analysis(bc_watergang, bc_watergang_tmp)
        if turtlebase.arcgis.is_fieldname(gp, bc_watergang_tmp, ovkident):
            gp.DeleteField_management(bc_watergang_tmp, ovkident)

        #---------------------------------------------------------------------
        # Environments
        G = nx.Graph()
        
        # iterate through your feature class and build a graph
        rows = gp.SearchCursor(bc_watergang_tmp)
        row = rows.next()
        inDesc = gp.describe(bc_watergang_tmp)
        while row:
            # we need a unique representation for each edges start and end points
            feat = row.GetValue(inDesc.ShapeFieldName)
            objectid = row.GetValue(inDesc.OIDFieldName)
            
            part = feat.getpart(0)
            pnt = part.Next()
            count = 0
            while pnt:
                if count == 0:
                    start_xy = (pnt.X, pnt.Y)
                else:
                    end_xy = (pnt.X, pnt.Y)
                
                pnt = part.Next()
                count += 1
            G.add_edge(start_xy,end_xy,oid=objectid)
            row = rows.next()
        
        # get the connected components
        Components = nx.connected_components(G)
            
        point = gp.CreateObject("POINT")
        point_fc = turtlebase.arcgis.get_random_file_name(workspace, ".shp")
        tempfiles.append(point_fc)
        fc_name = os.path.basename(point_fc)
        rd_new = os.path.join(os.path.dirname(sys.argv[0]), "rdnew.prj")
        gp.AddMessage(rd_new)
        gp.CreateFeatureclass_management(os.path.dirname(point_fc), fc_name, "POINT","#","DISABLED","DISABLED", rd_new,"#", "0","0","0")
        gp.AddField_management(point_fc, ovkident, "TEXT")
        
        rows_ic = gp.InsertCursor(point_fc)
        for ident, xy in enumerate(Components):
            for pnt in xy:
                point.X = pnt[0]
                point.Y = pnt[1]
        
                newfeature = rows_ic.NewRow()
                newfeature.shape = point
                newfeature.SetValue(ovkident, "bc_%s" % ident)
                rows_ic.InsertRow(newfeature)
        
        temp_fc = turtlebase.arcgis.get_random_file_name(workspace, ".shp")
        tempfiles.append(temp_fc)
        gp.SpatialJoin_analysis(bc_watergang_tmp, point_fc, temp_fc,"JOIN_ONE_TO_ONE")
        
        output_fc_line = turtlebase.arcgis.get_random_file_name(workspace, ".shp")
        tempfiles.append(output_fc_line)
        gp.Dissolve_management(temp_fc,output_fc_line,ovkident,"#","MULTI_PART","DISSOLVE_LINES")
        
        gp.merge_management("%s;%s"% (a_watergang, output_fc_line), output_fc)
        gp.Intersect_analysis("%s #;%s #" % (a_watergang, bc_watergang_tmp), point_intersection,"ALL","#","POINT")
                
        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            for tempfile in tempfiles:
                if gp.exists(tempfile):
                    gp.delete(tempfile)
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

