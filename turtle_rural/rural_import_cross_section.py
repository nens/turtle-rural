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
import turtlebase.general
import nens.sobek
import turtlebase.extract_from_sobek

log = logging.getLogger(__name__)


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')

        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
            gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------
        # Check input parameters
        log.info("Getting commandline parameters")
        if len(sys.argv) == 5:
            sobek_case_folder = sys.argv[1]
            output_cross_section_locations = sys.argv[2]
            output_cross_section_definition = sys.argv[3]
            output_yz_table = sys.argv[4]
        else:
            log.error("Usage: python rural_import_cross_section.py \
            <sobek case folder> <output cross_section locations> \
            <output table cross_sections definition>")
            sys.exit(1)

        # Get Sobek network file (csv file)
        input_sobek_network = os.path.join(sobek_case_folder,
            config.get('CrossSections', 'input_network_ntw'))
        if not gp.exists(input_sobek_network):
            log.error(input_sobek_network + " does not exist")
            sys.exit(1)
        log.debug("sobek network: " + input_sobek_network)

        # Get cross section data file (profile.dat)
        input_sobek_profile_dat = os.path.join(sobek_case_folder,
            config.get('CrossSections', 'input_profile_dat'))
        if not gp.exists(input_sobek_profile_dat):
            log.error(input_sobek_profile_dat + " does not exist")
            sys.exit(1)
        log.debug("sobek cross section data: " + input_sobek_profile_dat)

        # Get cross section definition file (profile.def)
        input_sobek_profile_def = os.path.join(sobek_case_folder,
            config.get('CrossSections', 'input_profile_def'))
        if not gp.exists(input_sobek_profile_def):
            log.error(input_sobek_profile_def + " does not exist")
            sys.exit(1)
        log.debug("sobek cross section defintion: " + input_sobek_profile_def)

        log.info('input parameters checked')
        # ---------------------------------------------------------------------
        '''
        input:
        - sobek map (network.ntw, profile.def, profile.dat)

        werkwijze:
        A) Profielgegevens (cross_section_definition
            A-1) lees profile.def
            A-2) schrijf de profielgegevens weg naar een tabel in
            de hydrobase (cross_section_definiton)
        B) Geometrie (locations):
            B-1) lees network.ntw
            B-2) lees profile.dat
            B-3) schrijf locaties weg naar een hydrobase (locations)

        output:
        - locations (feature class)
        - cross_section_definition (table)
        '''

        # ---------------------------------------------------------------------
        log.info("A) Read cross section definitions")

        cross_section_table, yz_table, errorcode = (
            turtlebase.extract_from_sobek.import_cross_section_definition(
                input_sobek_profile_def, config))

        if errorcode == 1:
            log.error("no cross sections found in %s" %
                      input_sobek_profile_def)
            sys.exit(1)

       # ---------------------------------------------------------------------
        log.info("B-1) Read sobek network")
        sobek_network_dict = nens.sobek.Network(input_sobek_network)

        # ---------------------------------------------------------------------
        log.info("B-2) Read cross section data")
        locident = config.get('CrossSections', 'cross_section_id')
        proident = config.get('CrossSections', 'cross_sections_def_id')
        cross_section_locations, errorcode = (
            turtlebase.extract_from_sobek.import_cross_section_data(
                input_sobek_profile_dat, locident, proident))

        # ---------------------------------------------------------------------
        log.info("C-1) Write cross section defintions to database")
        output_id = config.get('CrossSections',
                               'cross_sections_def_id').lower()
        # replace existing data in output_table
        turtlebase.arcgis.write_result_to_output(
            output_cross_section_definition, output_id, cross_section_table)

        turtlebase.extract_from_sobek.write_cross_section_yz_table(
            gp, config, yz_table, output_yz_table)

        if output_cross_section_locations != "#":
            log.info("C-2) Write cross section locations to database")
            turtlebase.extract_from_sobek.create_shapefiles(
                gp, config, sobek_network_dict, "SBK_PROFILE",
                output_cross_section_locations, cross_section_locations)

        #----------------------------------------------------------------------
        # Delete temporary workspace geodatabase & ascii files
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
