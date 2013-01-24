# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import shutil
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import turtlebase.arcgis
import maaiveldcurve

log = logging.getLogger(__name__)


def create_output_table(gp, output_surface_table, area_ident, field_range):
    """
    creates a new table when the table does not exist..
    adds all fields thats are needed for writing output
    """
    if not gp.exists(output_surface_table):
        gp.CreateTable_management(os.path.dirname(
                output_surface_table), os.path.basename(output_surface_table))

    if not turtlebase.arcgis.is_fieldname(
                    gp, output_surface_table, area_ident):
        gp.addfield_management(output_surface_table,
                    area_ident, "Text", "#", "#", '50')

    for field in field_range:
        if not turtlebase.arcgis.is_fieldname(
                    gp, output_surface_table, "MV_HGT_%s" % field):
            gp.addfield_management(
                    output_surface_table, "MV_HGT_%s" % field, "Double")

    if not turtlebase.arcgis.is_fieldname(gp, output_surface_table, 'SOURCE'):
        gp.addfield_management(output_surface_table,
                        'SOURCE', "Text", "#", "#", '256')

    if not turtlebase.arcgis.is_fieldname(
                gp, output_surface_table, 'DATE_TIME'):
        gp.addfield_management(output_surface_table,
                    'DATE_TIME', "Text", "#", "#", '40')

    if not turtlebase.arcgis.is_fieldname(
                gp, output_surface_table, 'COMMENTS'):
        gp.addfield_management(output_surface_table,
                'COMMENTS', "Text", "#", "#", '256')
        

def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Create workspace
        workspace_folder = turtlebase.arcgis.get_random_layer_name()
        workspace = os.path.join(config.get('GENERAL', 'location_temp'), workspace_folder)
        os.makedirs(workspace)

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
        if len(sys.argv) == 7:
            peilgebieden = sys.argv[1]
            rr_peilgebied = sys.argv[2]
            hoogtekaart = sys.argv[3]
            landgebruik = sys.argv[4]
            conversietabel = sys.argv[5]
            rr_maaiveld = sys.argv[6]            
        else:
            log.warning("usage: <argument1> <argument2>")
            sys.exit(1)
            
        kaartbladen = os.path.join(os.path.dirname(sys.argv[0]), "kaartbladen", "kaartbladen.shp")
        gpgident = config.get('general', 'gpgident')
        mv_procent = config.get("maaiveldkarakteristiek", "mv_procent")

        #---------------------------------------------------------------------
        # Environments
        gp.MakeFeatureLayer_management(kaartbladen, "krtbldn_lyr")
        gp.MakeFeatureLayer_management(peilgebieden, "gpg_lyr")
        gp.SelectLayerByLocation_management("krtbldn_lyr","INTERSECT","gpg_lyr","#","NEW_SELECTION")
        kaartbladen_prj = turtlebase.arcgis.get_random_file_name(workspace, '.shp')
        gp.Select_analysis("krtbldn_lyr", kaartbladen_prj)

        streefpeilen = {}
        rows_gpg = gp.SearchCursor(rr_peilgebied)
        row_gpg = rows_gpg.next()
        while row_gpg:
            gpg_id = row_gpg.getValue('gpgident')
            streefpeil = row_gpg.getValue('zomerpeil')
            streefpeilen[gpg_id] = streefpeil
            row_gpg = rows_gpg.next()
            
        rows = gp.SearchCursor(peilgebieden)
        row = rows.next()
        mvcurve_dict = {}
        nbw_dict = {}
        while row:
            gpg_value = row.getValue(gpgident)
            gpg_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer_management(peilgebieden, gpg_lyr, "%s = '%s'" % ('"' + gpgident + '"', gpg_value))
            tmp_gpg = turtlebase.arcgis.get_random_file_name(workspace, '.shp')
            gp.Select_analysis(gpg_value, tmp_gpg)
        
            streefpeil = float(streefpeilen[gpg_value])
            curve = maaiveldcurve.main(tmp_gpg, kaartbladen_prj, landgebruik, hoogtekaart, streefpeil, conversietabel, workspace)
            log.info(curve)
            mvcurve_dict[gpg_value] = {gpgident: gpg_value}
            for i in mv_procent:
                mvcurve_dict[gpg_value]["MV_HGT_%s" % i] = curve[0][1][i]
            if landgebruik != '#':
                log.info("stedelijk %s" % curve[1][1][1])
                log.info("hoogwaardig %s" % curve[2][1][1])
                log.info("akkerbouw %s" % curve[3][1][1])
                log.info("gras %s" % curve[4][1][5])
                
            gp.delete(tmp_gpg)
            row = rows.next()
        
        #---------------------------------------------------------------------
        
        
        turtlebase.arcgis.write_result_to_output(rr_maaiveld, gpgident, mvcurve_dict)
        turtlebase.arcgis.write_result_to_output(rr_maaiveld, gpgident, nbw_dict)
        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        gp.delete(kaartbladen_prj)

        try:
            log.debug("delete temporary workspace: %s" % workspace_gdb)
            gp.delete(kaartbladen_prj)            
            gp.delete(workspace_gdb)
            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace_gdb)

        shutil.rmtree(workspace)
        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
