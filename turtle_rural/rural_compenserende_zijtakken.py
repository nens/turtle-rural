# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-
import logging
import sys
import os
import math
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis

log = logging.getLogger(__name__)


def create_dict_stars_around_rekenpunten(gp, afvoerpunten_xy, config, output_fc):
    """
    """
    gp.CreateFeatureClass_management(os.path.dirname(output_fc), 
                                     os.path.basename(output_fc), "POLYLINE")
    linearray = gp.CreateObject("ARRAY")
    point = gp.CreateObject("POINT")
    gp.AddField(output_fc, "IDENT", "TEXT")
    
    rows = gp.InsertCursor(output_fc)
    count = 1
    for peilgebiedid, xy in afvoerpunten_xy.items():
        xcoord, ycoord = xy
        length = int(config.get('bergingstakken', 'length_of_breach'))
        aantal_takken = int(config.get('bergingstakken', 'numb_of_lines_opt_breach'))
        for i in range(aantal_takken):            
            alpha = float(i) / aantal_takken * 2 * math.pi
            dX = length * math.sin(alpha)
            point.x = float(xcoord) + float(dX)
            dY = length * math.cos(alpha)            
            point.y = float(ycoord) + float(dY)
            linearray.add(point)
            point.x = xcoord
            point.y = ycoord
            linearray.add(point)
            count = count + 1
            
            feat = rows.NewRow()
            feat.SetValue("IDENT", peilgebiedid + "_%s" % i)
            feat.Shape = linearray
            rows.InsertRow(feat)
            linearray.RemoveAll()
            
            
def calculate_xy(gp, input_fc, ident):
    output_xy = {}
    row = gp.SearchCursor(input_fc)
    for item in nens.gp.gp_iterator(row):
        key = item.getValue(ident)
        punt = item.shape.centroid
        if not output_xy.has_key(key):
            output_xy[key] = (punt.X, punt.Y)
            
    return output_xy
        
        
def add_unique_id(gp, input_fc, ident_new):
    """
    """
    count = 1
    gp.AddField(input_fc, ident_new, "TEXT")
    rows = gp.UpdateCursor(input_fc)
    row = rows.Next()
    while row:
        row.setValue(ident_new, "id_%s" % count)
        rows.UpdateRow(row)
        count += 1
        row = rows.Next()
    
    
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
        if len(sys.argv) == 5:
            afvoerpunten = sys.argv[1]
            waterlijnen = sys.argv[2]
            peilgebieden = sys.argv[3]            
            output_bergingstakken = sys.argv[4]
        else:
            log.warning("usage: <afvoerpunten> <waterlijnen> <peilgebieden>")
            sys.exit(1)

        #---------------------------------------------------------------------
        # Check geometry input parameters
        log.info("Check geometry of input parameters")
        geometry_check_list = []

        #log.debug(" - check <input >: %s" % argument1)

        #"<check geometry from input data, append to list if incorrect>"
        if gp.describe(afvoerpunten).ShapeType != 'Point':
            log.error("%s is not a point feature class!",
                      afvoerpunten)
            geometry_check_list.append(afvoerpunten + " -> (Point)")
            
        if gp.describe(waterlijnen).ShapeType != 'Polyline':
            log.error("%s is not a polyline feature class!",
                      waterlijnen)
            geometry_check_list.append(waterlijnen + " -> (Polyline)")
            
        if gp.describe(peilgebieden).ShapeType != 'Polygon':
            log.error("%s is not a polygon feature class!",
                      peilgebieden)
            geometry_check_list.append(peilgebieden + " -> (Polygon)")
        
        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)
        #---------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")

        missing_fields = []
        gpgident = config.get('Bergingstakken', 'peilgebied_id')
        verbinding = config.get('Bergingstakken', 'verbinding')
        gpg_naar = config.get('Bergingstakken', 'gpg_naar')

        #<check required fields from input data,
        #        append them to list if missing>
        check_fields = {afvoerpunten: [gpgident, verbinding, gpg_naar],
                         peilgebieden: [gpgident]}
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
        # Environments
        """
        Optioneel tertiaire bergingstakken. Wanneer deze optie wordt aangevinkt moeten ook de velden verbinindig en gpg_naar aanwezig zijn. 
        
        GPGPIDENT    VERBINDING    GPG_NAAR
        'gpg_1'        direct
        'gpg_2        indirect      'gpg_2'
        
        Wanneer de verbinding indirect is en gpg_naar is niet ingevuld dan pakt hij default de dichtsbijzijnde
        
        1. teken sterren
        2. prioritering
        3. hoe verder weg van de waterlijn, hoe hoger de prio
        4. wanneer kruising met gpg grens, lagere prio
        
        wanneer er meerdere punten op dezelfde locatie liggen dienen er meerdere zijtakken getekend te worden
        
        optioneel:
        - teken koppelpunten
        """
        afvoerpunten_xy = calculate_xy(gp, afvoerpunten, gpgident)              
        
        create_dict_stars_around_rekenpunten(gp, afvoerpunten_xy, config, output_bergingstakken)
        intersect = os.path.join(workspace_gdb, "intersect")
        gp.Intersect_analysis(output_bergingstakken + ";" + waterlijnen, intersect, "#", "#", "POINT")
        
        add_unique_id(gp, intersect, "IDENT_NEW")
        intersect_xy = calculate_xy(gp, intersect, "IDENT_NEW")
        
        log.info(len(intersect_xy))
        for ident, xy in intersect_xy.items():
            for afvoer_xy in afvoerpunten_xy.values():
                if (round(float(xy[0]), 1), round(float(xy[1]), 1)) == (round(float(afvoer_xy[0]), 1), round(float(afvoer_xy[1]), 1)):
                    
                    del(intersect_xy[ident])
        log.info(len(intersect_xy))
        pnts = intersect = os.path.join(workspace_gdb, "points")
        gp.CreateFeatureClass_management(os.path.dirname(pnts), 
                                     os.path.basename(pnts), "POINT")
        point = gp.CreateObject("POINT")
        rows = gp.InsertCursor(pnts)
        for v in intersect_xy.values():
            point.x, point.y = v
            
            feat = rows.NewRow()
            feat.Shape = point
            rows.InsertRow(feat)
        
        
        #log.info(intersect_xy)
        #spatial_join = os.path.join(workspace_gdb, "spatial_join")
        #gp.SpatialJoin_analysis(intersect,afvoerpunten,spatial_join,"JOIN_ONE_TO_ONE",
        #                        "KEEP_ALL","#","CLOSEST","100","DISTANCE")
        

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
