# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import shutil
import math
import traceback

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import turtlebase.arcgis
import maaiveldcurve

log = logging.getLogger(__name__)
NODATA = -9999


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


def get_layer_full_path(gp, layer):
    desc = gp.Describe(layer)
    path = desc.path
    filename = desc.File
    full_path = os.path.join(path, filename)
    
    return full_path


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #---------------------------------------------------------------------
        # Create workspace
        workspace = os.path.join(config.get('GENERAL', 'location_temp'))
        workspace_folder = turtlebase.arcgis.get_random_layer_name()
        workspace_shp = os.path.join(workspace, workspace_folder)
        os.makedirs(workspace_shp)

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                        gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #---------------------------------------------------------------------
        # Input parameters
        if len(sys.argv) == 8:
            peilgebieden = get_layer_full_path(gp, sys.argv[1])
            rr_peilgebied = get_layer_full_path(gp, sys.argv[2])
            hoogtekaart = get_layer_full_path(gp, sys.argv[3])
            rr_maaiveld = get_layer_full_path(gp, sys.argv[4])
            """Optional arguments for NBW analysis
            """
            if sys.argv[5] != '#':
                landgebruik = get_layer_full_path(gp, sys.argv[5])
            else:
                landgebruik = '#'
        
            if sys.argv[6] != '#':
                conversietabel = get_layer_full_path(gp, sys.argv[6])
            else:
                conversietabel = '#'
            
            if sys.argv[7] != '#':
                rr_toetspunten = get_layer_full_path(gp, sys.argv[7])
            else:
                rr_toetspunten = '#'
        else:
            log.warning("usage: <peilgebieden> <rr_peilgebied> <hoogtekaart> <rr_maaiveld> {landgebruik} {conversietabel} {rr_toetspunten}")
            sys.exit(1)
            
        kaartbladen = os.path.join(os.path.dirname(sys.argv[0]), "kaartbladen", "kaartbladen.shp")
        gpgident = config.get('general', 'gpgident')
        mv_procent = config.get("maaiveldkarakteristiek", "mv_procent")
        lgn_code = config.get('maaiveldkarakteristiek', 'lgn_code')
        nbw_klasse = config.get('maaiveldkarakteristiek', 'nbw_klasse')
        
        if landgebruik != '#':
            if conversietabel == '#':
                log.error("When you use a landuse map, a conversion table is required!")
                sys.exit(2)
            if rr_toetspunten == '#':
                rr_toetspunten = os.path.join(workspace_gdb, "rr_toetspunten")
                log.warning("You did not specify a output table for the RR_TOETSPUNTEN")
                log.warning(" - output will be written to %s" % rr_toetspunten)
                gp.CreateTable_management(os.path.dirname(rr_toetspunten), os.path.basename(rr_toetspunten))
        
        #---------------------------------------------------------------------
        # Environments
        geometry_check_list = []
        if gp.describe(hoogtekaart).PixelType[0] not in ['F']:
            log.info(gp.describe(hoogtekaart).PixelType)
            log.error("Input AHN is an integer raster, for this script a float is required")
            geometry_check_list.append(hoogtekaart + " -> (Float)")
            
        if landgebruik != '#':
            if gp.describe(landgebruik).PixelType[0] in ['F']:
                log.info(gp.describe(landgebruik).PixelType)
                log.error("Input landgebruik is a float raster, for this script a integer is required")
                geometry_check_list.append(hoogtekaart + " -> (Float)")
            
            cellsize_ahn = gp.describe(hoogtekaart).MeanCellHeight
            cellsize_landgebruik = gp.describe(landgebruik).MeanCellHeight
            if not cellsize_ahn == cellsize_landgebruik:
                log.error("The cellsize of input AHN2 is %s, the cellsize of landuse is %s. They should be the same" % (
                                                                                                                       cellsize_ahn,
                                                                                                                       cellsize_landgebruik))
                geometry_check_list.append("Change cellsize of %s" % landgebruik)
        
        if len(geometry_check_list) > 0:
            log.error("check input: %s" % geometry_check_list)
            sys.exit(2)

            
        gp.MakeFeatureLayer_management(kaartbladen, "krtbldn_lyr")
        gp.MakeFeatureLayer_management(peilgebieden, "gpg_lyr")
        gp.SelectLayerByLocation_management("krtbldn_lyr","INTERSECT","gpg_lyr","#","NEW_SELECTION")
        kaartbladen_prj = turtlebase.arcgis.get_random_file_name(workspace_shp, '.shp')
        gp.Select_analysis("krtbldn_lyr", kaartbladen_prj)
        peilgebieden_shp = turtlebase.arcgis.get_random_file_name(workspace_shp, '.shp')
        gp.Select_analysis("gpg_lyr", peilgebieden_shp)

        streefpeilen = {}
        rows_gpg = gp.SearchCursor(rr_peilgebied)
        row_gpg = rows_gpg.next()
        while row_gpg:
            gpg_id = row_gpg.getValue('gpgident')
            streefpeil = row_gpg.getValue('zomerpeil')
            streefpeilen[gpg_id] = streefpeil
            row_gpg = rows_gpg.next()
            
        conversion = {}
        if conversietabel != '#':
            rows_conv = gp.SearchCursor(conversietabel)
            row_conv = rows_conv.next()
            while row_conv:
                lgn = row_conv.GetValue(lgn_code)
                nbw = row_conv.GetValue(nbw_klasse)
                conversion[lgn] = nbw
                row_conv = rows_conv.next()
                
        rows = gp.SearchCursor(peilgebieden)
        row = rows.next()
        mvcurve_dict = {}        
        maxpeil = float(config.get('maaiveldkarakteristiek', 'max_hoogte'))
        
        if landgebruik != '#':
            nbw_dict = {}
            nbw_stedelijk = int(config.get('maaiveldkarakteristiek', 'nbw_stedelijk'))
            stedelijk_procent = int(config.get('maaiveldkarakteristiek', 'stedelijk_procent'))
            nbw_hoogwaardig = int(config.get('maaiveldkarakteristiek', 'nbw_hoogwaardig'))
            hoogwaardig_procent = int(config.get('maaiveldkarakteristiek', 'hoogwaardig_procent'))
            nbw_akkerbouw = int(config.get('maaiveldkarakteristiek', 'nbw_akkerbouw'))
            akkerbouw_procent = int(config.get('maaiveldkarakteristiek', 'akkerbouw_procent'))
            nbw_grasland = int(config.get('maaiveldkarakteristiek', 'nbw_grasland'))
            grasland_procent = int(config.get('maaiveldkarakteristiek', 'grasland_procent'))

        while row:
            gpg_value = row.getValue(gpgident)
            log.info(" - processing area %s" %  gpg_value)
            gpg_lyr = turtlebase.arcgis.get_random_layer_name()
            gp.MakeFeatureLayer_management(peilgebieden_shp, gpg_lyr, "%s = '%s'" % ('"' + gpgident + '"', gpg_value))
            tmp_gpg = turtlebase.arcgis.get_random_file_name(workspace_shp, '.shp')
            gp.Select_analysis(gpg_lyr, tmp_gpg)
        
            streefpeil = float(streefpeilen[gpg_value])
            curve, curve_per_landuse = maaiveldcurve.main(tmp_gpg, kaartbladen_prj, landgebruik, hoogtekaart, streefpeil, maxpeil, conversion, workspace_shp)
            mvcurve_dict[gpg_value] = {gpgident: gpg_value}
            
            for i in mv_procent.split(', '):
                v = curve[0][1][int(i)]
                mvcurve_dict[gpg_value]["MV_HGT_%s" % i] = math.ceil(v*100)/100
            
            if landgebruik != '#':
                nbw_dict[gpg_value] = {gpgident: gpg_value}
                
                if nbw_stedelijk in curve_per_landuse:
                    nbw_dict[gpg_value]['DFLT_I_ST'] = curve_per_landuse[nbw_stedelijk][1][stedelijk_procent]
                    nbw_dict[gpg_value]['DFLT_O_ST'] = (curve_per_landuse[nbw_stedelijk][1][10] + streefpeil) / 2
                else:
                    nbw_dict[gpg_value]['DFLT_I_ST'] = NODATA
                    nbw_dict[gpg_value]['DFLT_O_ST'] = NODATA
                    
                if nbw_hoogwaardig in curve_per_landuse:
                    nbw_dict[gpg_value]['DFLT_I_HL'] = curve_per_landuse[nbw_hoogwaardig][1][hoogwaardig_procent]
                    nbw_dict[gpg_value]['DFLT_O_HL'] = (curve_per_landuse[nbw_hoogwaardig][1][10] + streefpeil) / 2
                else:
                    nbw_dict[gpg_value]['DFLT_I_HL'] = NODATA
                    nbw_dict[gpg_value]['DFLT_O_HL'] = NODATA
                    
                if nbw_akkerbouw in curve_per_landuse:
                    nbw_dict[gpg_value]['DFLT_I_AK'] = curve_per_landuse[nbw_akkerbouw][1][akkerbouw_procent]
                    nbw_dict[gpg_value]['DFLT_O_AK'] = (curve_per_landuse[nbw_akkerbouw][1][10] + streefpeil) / 2
                else:
                    nbw_dict[gpg_value]['DFLT_I_AK'] = NODATA
                    nbw_dict[gpg_value]['DFLT_O_AK'] = NODATA
                    
                if nbw_grasland in curve_per_landuse:
                    nbw_dict[gpg_value]['DFLT_I_GR'] = curve_per_landuse[nbw_grasland][1][grasland_procent]
                    nbw_dict[gpg_value]['DFLT_O_GR'] = (curve_per_landuse[nbw_grasland][1][10] + streefpeil) / 2
                else:
                    nbw_dict[gpg_value]['DFLT_I_GR'] = NODATA
                    nbw_dict[gpg_value]['DFLT_O_GR'] = NODATA
                
            gp.delete(tmp_gpg)
            row = rows.next()
            
        if landgebruik != '#':
            tp_fields = ["GPGIDENT", "DFLT_I_ST", "DFLT_I_HL", "DFLT_I_AK", "DFLT_I_GR",
                         "DFLT_O_ST", "DFLT_O_HL", "DFLT_O_AK", "DFLT_O_GR",
                         "MTGMV_I_ST", "MTGMV_I_HL", "MTGMV_I_AK", "MTGMV_I_GR", 
                         "MTGMV_O_ST", "MTGMV_O_HL", "MTGMV_O_AK", "MTGMV_O_GR"]
            for tp_field in tp_fields:
                if not turtlebase.arcgis.is_fieldname(gp, rr_toetspunten, tp_field):
                    gp.addfield_management(tp_field, "TEXT")
        #---------------------------------------------------------------------
        turtlebase.arcgis.write_result_to_output(rr_maaiveld, gpgident, mvcurve_dict)
        if landgebruik != '#':
            turtlebase.arcgis.write_result_to_output(rr_toetspunten, gpgident, nbw_dict)
        
        #---------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
        try:
            log.info("delete temporary folder: %s" % workspace_shp)
            shutil.rmtree(workspace_shp)
            log.info("workspace deleted")
        except:
            log.warning("failed to delete %s" % workspace)
       
        mainutils.log_footer()
    except:
        log.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
