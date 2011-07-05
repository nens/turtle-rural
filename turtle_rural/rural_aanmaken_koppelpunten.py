# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

# Import system modules
import sys
import os
import logging
import traceback
import math

# Import GIS modules
import nens.gp

# Import Turtlebase modules
import turtlebase.arcgis
import turtlebase.general
from turtlebase import mainutils
from turtlebase.logutils import LoggingConfig

log = logging.getLogger(__name__)


def reading_line_feature_nodes_to_dict_according_to_peilgebied(gp, point_shape, field_containing_key):
    ''' leest de coordinaten van een puntenshapefile in en schrijft deze naar een dictionary obv een id_field
    output_dict ziet er als volgt uit : {gpg_id:{count:coordinates}}
    '''
    output_dict = {}

    rows = gp.SearchCursor(point_shape)
    count = 0
    for row in nens.gp.gp_iterator(rows):
        key = row.getValue(field_containing_key)
        centroid = row.shape.centroid
        if not output_dict.has_key(key):
            output_dict[key] = {}
            count += 1
            output_dict[key][count] = centroid
    return output_dict


def create_point_file_from_dict(gp, centroid_dict, output_centroid_file, peilgebied_id):
    '''Creeert een punten_shape obv een dictionary met centroides  daarnaast voegt het de peilgebiedid toe aan de file'''
    output_centroid_filename = os.path.basename(output_centroid_file)
    workspace_gdb = os.path.dirname(output_centroid_file)
    log.info("The centroid file %s wordt aangemaakt" % output_centroid_file)

    gp.CreateFeatureClass_management(workspace_gdb, output_centroid_filename, "POINT")
    gp.Addfield_management(output_centroid_file, peilgebied_id, "TEXT")
    rows_out = gp.InsertCursor(output_centroid_file)
    pnt = gp.CreateObject("Point")
    for peilgebied in centroid_dict:
        newfeat = rows_out.NewRow()
        punt = centroid_dict[peilgebied].split(' ')
        pnt.X = float(punt[0].replace(",", "."))
        pnt.Y = float(punt[1].replace(",", "."))
        newfeat.shape = pnt
        newfeat.SetValue(peilgebied_id, peilgebied)
        rows_out.InsertRow(newfeat)
    del rows_out


def read_coordinates_from_string(coord_string):
    ''' the coordinates are in a string as follows: 'x y'
        returns de x en y as floating point
        '''
    coord_spl = coord_string.split(' ')
    x = float(coord_spl[0].replace(",", "."))
    y = float(coord_spl[1].replace(",", "."))
    return x, y


def calculate_distance(x1, y1, x2, y2):
    ''' berekent de afstand tussen x1 y1 en x2 y2. input zijn de coordinaten als floating point '''
    x_kwadraat = math.pow((x1 - x2), 2)
    y_kwadraat = math.pow((y1 - y2), 2)
    distance = math.sqrt(x_kwadraat + y_kwadraat)
    return distance


def calculate_minimal_distance_between_points(peilgebieden_centroides_dict, waterlijnen_punten_dict, waterlijnen_vertex_dict):
    '''Berekent de afstand tussen 2 punten, de centroide en 1 van de punten uit de waterlijnen_punten_dict.
    Bewaart het punt met de kortste afstand tussen waterlijnen en de centroide_dict
    '''
    output_dict = {}

    for peilgebied in peilgebieden_centroides_dict.keys():
        if waterlijnen_punten_dict.has_key(peilgebied):
            distance_dict = {}
            for punt_op_waterlijn in waterlijnen_punten_dict[peilgebied].keys():
                punt_x, punt_y = read_coordinates_from_string(waterlijnen_punten_dict[peilgebied][punt_op_waterlijn])
                centroid_x, centroid_y = read_coordinates_from_string(peilgebieden_centroides_dict[peilgebied]['centroid'])
                #calculate_distance
                distance = calculate_distance(punt_x, punt_y, centroid_x, centroid_y)
                distance_dict[distance] = punt_op_waterlijn
            minimum_distance = min(distance_dict.keys())
            knoopnummer = distance_dict[minimum_distance]
            nearest_point_to_centroid = waterlijnen_punten_dict[peilgebied][knoopnummer]
            output_dict[peilgebied] = nearest_point_to_centroid

        #else functie voor als er geen waterlijn in het peilgebied is
        elif waterlijnen_vertex_dict.has_key(peilgebied):

            distance_dict = {}
            for punt_op_waterlijn in waterlijnen_vertex_dict[peilgebied].keys():
                punt_x, punt_y = read_coordinates_from_string(waterlijnen_vertex_dict[peilgebied][punt_op_waterlijn])
                centroid_x, centroid_y = read_coordinates_from_string(peilgebieden_centroides_dict[peilgebied]['centroid'])
                #calculate_distance
                distance = calculate_distance(punt_x, punt_y, centroid_x, centroid_y)
                distance_dict[distance] = punt_op_waterlijn
            minimum_distance = min(distance_dict.keys())
            knoopnummer = distance_dict[minimum_distance]
            nearest_point_to_centroid = waterlijnen_vertex_dict[peilgebied][knoopnummer]
            output_dict[peilgebied] = nearest_point_to_centroid
        else:

            log.warning("Peilgebied " + peilgebied + " heeft geen waterlijn. De centroide wordt als rekenpunt aangemaakt")
            output_dict[peilgebied] = peilgebieden_centroides_dict[peilgebied]['centroid']
    return output_dict


def reading_line_features_nodes(gp, inputFC):
    nodes_dict = {}
    ''' leest de nodes van een line feature in en plaatst de coordinaten in een dictionary.'''
    inDesc = gp.describe(inputFC)
    inRows = gp.searchcursor(inputFC)
    inRow = inRows.next()
    temp_dict = {}

    row_id = 0
    while inRow:
        feat = inRow.GetValue(inDesc.ShapeFieldName)
        row_id += 1
        partnum = 0
        partcount = feat.partcount
        while partnum < partcount:
            part = feat.getpart(partnum)
            part.reset()
            pnt = part.next()
            pnt_count = 0
            while pnt:
                key = str(row_id) + "__" + str(pnt_count)
##                if not nodes_dict.has_key(row_id):
##                        nodes_dict[row_id] = {}
##                nodes_dict[row_id][pnt_count] = str(pnt.x) + " " + str(pnt.y)
                key_coord = '%.5f' % (pnt.x) + " " + '%.5f' % (pnt.y)
                if temp_dict.has_key(key_coord):
                    nodes_dict[key] = key_coord
                temp_dict[key_coord] = key

                pnt = part.next()
                pnt_count += 1

            partnum += 1
        inRow = inRows.next()

    return nodes_dict


def reading_line_features_vertices(gp, inputFC, field_peilgebied_id, peilgebieden_centroides_dict):
    ''' leest de vertices van een line feature en plaatst de coordinaten in een dictionary. per peilgebied worden de knopen afzonderlijk
    opgeslagen:
    outputdictionary = { GPGIDENT: {1:'x1 y1',2:x2 y2'}}
    '''
    vertex_dict = {}

    inDesc = gp.describe(inputFC)
    inRows = gp.searchcursor(inputFC)
    inRow = inRows.next()

    while inRow:
        peilgebied_shapefile = inRow.getValue(field_peilgebied_id)
        if peilgebieden_centroides_dict.has_key(peilgebied_shapefile):
            #de gpgident uit de waterlijnenshape komt voor in de dictionary peilgebieden met centroides
            feat = inRow.GetValue(inDesc.ShapeFieldName)
            partnum = 0
            partcount = feat.partcount
            while partnum < partcount:
                part = feat.getpart(partnum)
                part.reset()
                pnt = part.next()
                pnt_count = 0
                while pnt:
                    if not vertex_dict.has_key(peilgebied_shapefile):
                        vertex_dict[peilgebied_shapefile] = {}
                    vertex_dict[peilgebied_shapefile][pnt_count] = str(pnt.x) + " " + str(pnt.y)
                    pnt = part.next()
                    pnt_count += 1

                partnum += 1
        inRow = inRows.next()

    return vertex_dict


def bepalen_centroides(gp, polygon_shape, field_containing_key):
    """Leest centroides in uit een vlakkenshape en stopt ze in een dictionary met de key uit een veld zoals meegegevens """
    dict = {}
    row = gp.SearchCursor(polygon_shape)
    for item in nens.gp.gp_iterator(row):
        key = item.getValue(field_containing_key)
        centroid = item.shape.centroid
        if not dict.has_key(key):
            dict[key] = {}
            dict[key]['centroid'] = centroid
    return dict


def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)

        #----------------------------------------------------------------------------------------
        # Create workspace
        workspace = config.get('GENERAL', 'location_temp')
        turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

        if not os.path.isdir(workspace):
            os.makedirs(workspace)
        workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(gp, workspace)
        if errorcode == 1:
            log.error("failed to create a file geodatabase in %s" % workspace)

        #----------------------------------------------------------------------------------------
        if len(sys.argv) == 4:
            log.info("Reading and checking input")
            waterlijnen = sys.argv[1]
            peilgebieden = sys.argv[2]
            output_file = sys.argv[3]
        else:
            log.error("usage: <waterlijnen> <peilgebieden> <output_file>")
            sys.exit(1)

        #----------------------------------------------------------------------------------------
        # Check required fields in input data
        log.info("Check required fields in input data")
        missing_fields = []

        #<check required fields from input data, append them to list if missing>"
        gpgident = config.get('GENERAL', 'gpgident')
        check_fields = {peilgebieden: [gpgident]}
        for input_fc, fieldnames in check_fields.items():
            for fieldname in fieldnames:
                if not turtlebase.arcgis.is_fieldname(gp, input_fc, fieldname):
                    errormsg = "fieldname %s not available in %s" % (fieldname, input_fc)
                    log.error(errormsg)
                    missing_fields.append(errormsg)

        if len(missing_fields) > 0:
            log.error("missing fields in input data: %s" % missing_fields)
            sys.exit(2)
        #----------------------------------------------------------------------------------------

        try:
            #bepaald centroide van peilvakken en stop in dictionary
            #dict wordt {<gpgident>:[centroid:<centroid>]}
            peilgebieden_centroides_dict = bepalen_centroides(gp, peilgebieden, gpgident)
            # Eerst een intersect van de peilgebiden met de waterlijnen
            #extract de shapefiles uit de geodatabase
            log.info("Kopieer " + waterlijnen + " naar de workspace")
            waterlijnen_lokaal = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            log.debug("Kopieer de waterlijnen naar een lokale directory")
            gp.select_analysis(waterlijnen, waterlijnen_lokaal)

            intersect = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.Intersect_analysis(waterlijnen_lokaal + ";" + peilgebieden, intersect)

            log.info("Reading line features")
            #nu uitlezen van de nodes van de waterlijnen
            waterlijnen_nodes_dict = reading_line_features_nodes(gp, waterlijnen_lokaal)

            nodes = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            create_point_file_from_dict(gp, waterlijnen_nodes_dict, nodes, "nodes_id")
            #nu koppel de nodes aan de peilgebieden dmv een spatial join
            spat_jn_nodes = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.SpatialJoin_analysis(nodes, peilgebieden, spat_jn_nodes)

            #uitlezen van de nodes van de waterlijnen inclusief gpgident
            waterlijnen_nodes_dict = reading_line_feature_nodes_to_dict_according_to_peilgebied(gp, spat_jn_nodes, gpgident)

            #uitlezen van de vertices van de waterlijnen
            waterlijnen_vertex_dict = reading_line_features_vertices(gp, intersect, gpgident, peilgebieden_centroides_dict)

            #bereken het punt het dichtst bij de centroide van een peilgebied. Kijk eerst naar de nodes, dan naar vertices en indien geen waterlijn aanwezig maak dan
            # centroide punt aan van het peilgebied

            dictionary_with_closest_point_to_centroid_on_waterlijn = calculate_minimal_distance_between_points(peilgebieden_centroides_dict, waterlijnen_nodes_dict, waterlijnen_vertex_dict)


            output_centroid_file = turtlebase.arcgis.get_random_file_name(workspace_gdb)

            create_point_file_from_dict(gp, dictionary_with_closest_point_to_centroid_on_waterlijn, output_centroid_file, gpgident)
            gp.select_analysis(output_centroid_file, output_file)

        except Exception, e:
            errormsg = traceback.extract_tb(sys.exc_traceback)
            log.error(errormsg)
            log.error(e)
            sys.exit(1)

        #----------------------------------------------------------------------------------------
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
