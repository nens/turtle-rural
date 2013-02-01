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
import turtlebase.filenames

log = logging.getLogger(__name__)


def clean_up_star(gp, shapefile, field_to_clean):
    ''' in de shapefile in het te cleanen vled staan de GPGidenten met een extra ID. Deze kan verwijderd worden.
    bijv: GPG_2__45 wordt GPG_2
    '''
    row = gp.UpdateCursor(shapefile)
    for item in nens.gp.gp_iterator(row):
        peilgebied_unieke_id = item.getValue(field_to_clean)
        peilgebied_spl = peilgebied_unieke_id.split('__')
        peilgebied_id = peilgebied_spl[0]
        #replace de oude met de nieuwe id
        item.setValue(field_to_clean, peilgebied_id)
        row.UpdateRow(item)


def remove_records_from_shapefile_not_in_list(gp, shapefile, field, remove_records):
    '''Doet een loop door de attribute tabel van een shapefile. Als er in field een waarde staat die niet voorkomt in list, wordt
    het record verwijderd.
    '''
    row = gp.UpdateCursor(shapefile)
    for item in nens.gp.gp_iterator(row):
        common_id = item.getValue(field)
        if not common_id in remove_records:
            row.DeleteRow(item)


def bepaal_ideale_punt_bergingstak(distance_dictionary):

    ''' Per peilgebied en punt zijn de afstanden opgeslagen in een dictionary als volgt:
    {' GPG_3': {98.868766987681809: '3', 99.352822005324541: '12', 101.74889490323042: '22', 102.13297406176034: '20'}
    '''
    list_with_best_point_ids = []
    for peilgebied in distance_dictionary:
        # beste punt is die met de maximal distance
        best_point = max(distance_dictionary[peilgebied])
        best_point_id = distance_dictionary[peilgebied][best_point]
        #alle beste id's in list stoppen
        peilgebied_unieke_id = str(peilgebied) + "__" + str(best_point_id)
        list_with_best_point_ids.append(peilgebied_unieke_id)
    return list_with_best_point_ids


def calculate_distance_between_points(dict_met_punten1, dict_met_punten2):
    '''Berekent de afstand tussen 2 punten, de centroide en 1 van de punten uit de waterlijnen_punten_dict.
    Bewaart het punt met de kortste afstand tussen waterlijnen en de centroide_dict

    de dictionaries zien er als volgt uit:
    dict_met_punten1 (snijpunten met de waterlijn: {' GPG_3': ['126760.70617 501257.3577'], ' GPG_2': ['126757.16122 501280.28275',
    '126673.91802 501434.71405', '126703.71162 501464.34345', '126829.46912 501449.59555']}
    dict_met_punten2: {' GPG_160__11': ['127752.39253 501294.03369'], ' GPG_410__14': ['128076.74173 503115.36159']}
    de rechterkant van key van dict_met_punten2 wordt begrensd door 'numb_of_lines_opt_breach' uit de ini-file
    '''
    output_dict = {}
    distance_dict = {}

    for peilgebied_unieke_id in dict_met_punten2.keys():
        for punten in dict_met_punten2[peilgebied_unieke_id]:
            punt_x = float(punten.split(' ')[0])
            punt_y = float(punten.split(' ')[1])
            peilgebied_spl = peilgebied_unieke_id.split('__')
            peilgebied = peilgebied_spl[0]
            peilgebieduniekeiddeel = peilgebied_spl[1]
            if dict_met_punten1.has_key(peilgebied):
                #loop over de coordinaten in de lijst in van dict1
                id_in_list = 0
                #reset de afstands dictionary
                distance_dict = {}
                for coordinaat in dict_met_punten1[peilgebied]:
                    coord_x, coord_y = coordinaat.split(' ')
                    #bereken de afstand:
                    x_kwadraat = math.pow(float(punt_x) - float(coord_x), 2)
                    y_kwadraat = math.pow(float(punt_y) - float(coord_y), 2)
                    distance = math.sqrt(x_kwadraat + y_kwadraat)
                    id_in_list = id_in_list + 1
                    distance_dict[distance] = id_in_list
                minimum_distance = min(distance_dict.keys())
                log.debug("minimum_distance %s" % minimum_distance)
                #opslaan in de dictionary:

                if not output_dict.has_key(peilgebied):
                    output_dict[peilgebied] = {}
                #geen reverse dictionary omdat er dan een risico is dat bij dezelfde distance een item overschreven wordt.
                output_dict[peilgebied][minimum_distance] = peilgebieduniekeiddeel
            else:
                # het gebied heeft geen waterlijn, dus kies random punt om de waterlijn naar toe te tekenen.
                if not output_dict.has_key(peilgebied):
                    output_dict[peilgebied] = {}
                minimum_distance = 200 # just assume the same value for min distance. it is total random which line will be there
                output_dict[peilgebied][minimum_distance] = peilgebieduniekeiddeel

    log.debug("output %s" % output_dict)
    return output_dict


def create_points_from_dict(gp, dict1, output_file, field_id):
    ''' dict1 ziet er als volgt uit:
    {' GPG_3': ['126758.56109 501357.22701', '126783.430079 501354.085326', '126806.736457 501344.857678']}
    Deze coordinaten worden omgezet naar punten
    '''
    output_filename = os.path.basename(output_file)
    workspace_gdb = os.path.dirname(output_file)
    point = gp.CreateObject("POINT")
    gp.CreateFeatureClass_management(workspace_gdb, output_filename, "POINT")
    gp.AddField(output_file, field_id, "TEXT")
    rows_ic = gp.InsertCursor(output_file)
    for key in dict1.keys():
        i = 0
        for coordinate in dict1[key]:
            i += 1
            key_pnt = str(key) + "__" + str(i)
            #coordinaten staan er altijd in met spatie ertussen
            point.X = float(coordinate.split(' ')[0])
            point.Y = float(coordinate.split(' ')[1])
            newfeature = rows_ic.NewRow()
            newfeature.shape = point
            newfeature.SetValue(field_id, key_pnt)
            rows_ic.InsertRow(newfeature)


def remove_records_from_shapefile_based_on_keys_in_dict(gp, shapefile, field, dict1):
    ''' als waarde in key voorkomt in de attribute tabel van de shapefile wordt het betreffende  record verwijderd '''
    row = gp.UpdateCursor(shapefile)
    for item in nens.gp.gp_iterator(row):
        common_id = item.getValue(field)
        if dict1.has_key(common_id):
            row.DeleteRow(item)


def remove_duplicate_values_from_dictionaries(dict1, dict2):
    ''' This dictionary removes key:item combination dict1 from dict2 if keys are the same'''
    reverse_dict1 = dict([(v, k) for (k, v) in dict1.iteritems()])
    reverse_dict2 = dict([(v, k) for (k, v) in dict2.iteritems()])

    for key in reverse_dict1.iterkeys():
        reverse_dict2.pop(key, None)
    #reverse back
    output_dict = dict([(v, k) for (k, v) in reverse_dict2.iteritems()])
    return output_dict


def join_dictionaries(dict1, dict2):
    """ Maakt een nieuwe dictionary aan obv twee dictionaries samen op basis van de key.
    dict1 bevat coordinaten paren in een list dict2 bevat coordinaten met key. de key tussen dict1 en dict2 is gelijk,
    er wordt een nieuwe dictionary aangemaakt met unieke keys waarin de coordinatenparen van dict1 een voor een gekoppeld worden aan
    de coordinaten van dict2.
    input dict1 = {key1:['x1 y1',x2 y2']} dict 2 = {key1:['x3 y3']}
    outputdict = {key2:['x3 y3', 'x1 y1'], key3:['x3 y3', 'x2 y2']} """
    outputdict = {}


    for key in dict1.keys():
        i = 0
        for itemdict1 in dict1[key]:

            if dict2.has_key(key):
                # het gaat om een 1:n relatie tussen dict1 en dict2
                i += 1
                id2 = str(key) + "__" + str(i)
                if not outputdict.has_key(id2):
                    outputdict[id2] = []
                outputdict[id2].append(itemdict1)
                outputdict[id2].append(dict2[key])

    return outputdict

def createLineFromPoints(gp, dict_with_points, leidingidkolom, outputfile):
    """"Deze functie maakt een lijnobject aan in ArcGIS op basis van punten in een dictionary. De punten in de dictionary
    zijn met een unieke code aan elkaar gekoppeld example: ('key1':[x1 y1,x2 y2])"""

    linearray = gp.CreateObject("ARRAY")
    point = gp.CreateObject("POINT")
    filename = os.path.basename(outputfile)
    workspace_gdb = os.path.dirname(outputfile)
    gp.CreateFeatureClass_management(workspace_gdb, filename, "POLYLINE")
    gp.AddField(outputfile, leidingidkolom, "TEXT")
    rows_ic = gp.InsertCursor(outputfile)
    for key in dict_with_points.iterkeys():
        for item in dict_with_points[key]:
            point.X = float(item.split(' ')[0])
            point.Y = float(item.split(' ')[1])
            linearray.Add(point)
            newfeature = rows_ic.NewRow()
        newfeature.shape = linearray
        newfeature.SetValue(leidingidkolom, key)
        rows_ic.InsertRow(newfeature)
        linearray.RemoveAll()


def create_dict_stars_around_rekenpunten(peilgebieden_list, config, rekenpunten_x_y_coordinaten):
    ''' berekent de eindpunten van de ster om de rekenpunten en retourneert deze.
    Daarnaast wordt een dictionary geretourneerd met de gpgident als key'''

    dict_points_for_star = {}

    count = 0
    
    tot = int(config.get('bergingstakken', 'numb_of_lines_opt_breach'))
    
    for peilgebiedid in peilgebieden_list.keys():
        if rekenpunten_x_y_coordinaten.has_key(peilgebiedid):
            xcoord, ycoord = rekenpunten_x_y_coordinaten[peilgebiedid].split(' ')
            #length = int(config.get('zijtakken', 'length_of_breach'))
            
            for i in range(tot):
                alpha = float(i) / tot * 2 * math.pi
                dX = int(config.get('bergingstakken', 'length_of_breach')) * math.sin(alpha)
                dY = int(config.get('bergingstakken', 'length_of_breach')) * math.cos(alpha)
                x = float(xcoord) + float(dX)
                y = float(ycoord) + float(dY)
                count = count + 1
                if not dict_points_for_star.has_key(peilgebiedid):
                    dict_points_for_star[peilgebiedid] = []
                dict_points_for_star[peilgebiedid].append(str(x) + ' ' + str(y))

    return dict_points_for_star


def bepalen_x_y_coordinaat_meerdere_punten(gp, punten_shape, field_containing_key):
    ''' leest x y coordinaten uit van meerdere punten met zelfde peilgebied en maakt unieke ID aan'''
    output_dict = {}
    row = gp.SearchCursor(punten_shape)
    for item in nens.gp.gp_iterator(row):
        key = item.getValue(field_containing_key)
        
        punt = item.shape.centroid
        punt_x, punt_y = turtlebase.arcgis.calculate_xy(gp, punt)
        #punt_spl = punt.split()
        
        punt = '%.5f' % (punt_x) + " " + '%.5f' % (punt_y)

        if not output_dict.has_key(key):
            output_dict[key] = []
        output_dict[key].append(punt)
    return output_dict


def bepalen_x_y_coordinaat(gp, punten_shape, field_containing_key):
    """Leest centroides in uit een vlakkenshape en stopt ze in een dictionary met de key uit een veld zoals meegegevens """
    output_dict = {}
    row = gp.SearchCursor(punten_shape)
    for item in nens.gp.gp_iterator(row):
        key = item.getValue(field_containing_key)
        punt = item.shape.centroid
        punt_x, punt_y = turtlebase.arcgis.calculate_xy(gp, punt)
        #punt_spl = punt.split()
        #punt_x = float(punt.X)
        #punt_y = float(punt.Y)
        punt = '%.5f' % (punt_x) + " " + '%.5f' % (punt_y)


        if not output_dict.has_key(key):
            output_dict[key] = {}
            output_dict[key] = punt
    return output_dict


def convert_ini_settings_to_dictionary(input_list_ini_settings):
    ''' de ini setting sstaan in een lijst [[key, waarde][key1 ,waarde2]]
    dit wordt omgeschreven naar een dictionary {key:waarde,key1:waarde1} '''

    output_dict = {}
    for items in input_list_ini_settings:
        for item in items:
            if not output_dict.has_key(item[0]):
                output_dict[str(item[0])] = item[1]
##            output_dict[item[0]].append(item[1])
    return output_dict


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

        #------------------------------------------------
        log.info("Reading and checking input")
        rekenpunten = sys.argv[1]
        waterlijnen = sys.argv[2]
        peilgebieden = sys.argv[3] #optioneel
        output_bergingstakken = sys.argv[4]
        gpgident = config.get('General', 'gpgident')
        if turtlebase.arcgis.is_fieldname(gp, peilgebieden, gpgident):
            peilgebieden_list = nens.gp.get_table(gp, peilgebieden, primary_key=gpgident.lower())
        else:
            log.error("field %s is missing in %s", gpgident, peilgebieden)
            sys.exit(1)

        if not turtlebase.arcgis.is_fieldname(gp, rekenpunten, gpgident):
            log.error("field %s is missing in %s", gpgident, rekenpunten)
            sys.exit(1)

        log.info("Controleer of de opgegeven bestandsnamen arcgis compatibel zijn")

        for argv in sys.argv[1:]:
            turtlebase.filenames.check_filename(argv)

        #uitlezen x en y coordinaat van de rekenpunten
        log.info("Inlezen rekenpunten")

        rekenpunten_x_y_coordinaten = bepalen_x_y_coordinaat(gp, rekenpunten, gpgident)
        log.info("Kopieer " + waterlijnen + " naar de workspace")
        waterlijnen_lokaal = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        log.debug("Kopieer de waterlijnen naar een lokale directory ")
        gp.select_analysis(waterlijnen, waterlijnen_lokaal)
        log.info("Bereken eindpunten van potentiele bergingstakken rondom rekenpunten")
        dict_stars = create_dict_stars_around_rekenpunten(peilgebieden_list, config, rekenpunten_x_y_coordinaten)

        joined_dictionaries = join_dictionaries(dict_stars, rekenpunten_x_y_coordinaten)
        star = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        log.info("Aanmaken potentiele bergingstakken vanuit rekenpunt ")

        createLineFromPoints(gp, joined_dictionaries, 'gpgident', star)
        intersect = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        log.info("Bereken kruisingen van potentiele bergingstakken met waterlijnen")
        #Buffer_analysis (in_features, out_feature_class, buffer_distance_or_field, line_side, line_end_type, dissolve_option, dissolve_field)
       
        gp.Intersect_analysis(star + ";" + waterlijnen_lokaal, intersect, "#", "#", "POINT")
        intersect_x_y_coordinaten = bepalen_x_y_coordinaat(gp, intersect, gpgident)

        remainingpoints_to_be_removed_from_star = remove_duplicate_values_from_dictionaries(rekenpunten_x_y_coordinaten, intersect_x_y_coordinaten)

        #nu remainingpoints_to_be_removed_from_star dictionary de keys vergelijken met de id in star en dan record verwijderen

        log.info("Bepaal overgebleven eindpunten van bergingstakken")
        remove_records_from_shapefile_based_on_keys_in_dict(gp, star, gpgident, remainingpoints_to_be_removed_from_star)

        star_punten = turtlebase.arcgis.get_random_file_name(workspace_gdb)

        #nu worden coordinaten uitgelezen uit de star_punten shape (lijnen)
        log.info("Bereken ideale bergingstak")
        create_points_from_dict(gp, dict_stars, star_punten, gpgident)

        intersect2 = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Intersect_analysis(star_punten + ";" + star, intersect2, "#", "#", "POINT")
        log.info("Bereken afstand potentiele bergingstakken naar waterlijn")
        log.debug("Als eerste wordt een buffer aangemaakt ")

        buffer_star = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Buffer_analysis(rekenpunten, buffer_star, int(config.get('bergingstakken', 'length_of_breach')))
        snijpunt_waterlijn = turtlebase.arcgis.get_random_file_name(workspace_gdb)

        log.debug("Nu intersect van de buffer met de waterlijnen. Deze punten worden gebruikt om de afstand naar de waterlijn te berekenen ")
        gp.Intersect_analysis(buffer_star + ";" + waterlijnen_lokaal, snijpunt_waterlijn, "#", "#", "POINT")

        log.debug("Nu wegschrijven van de coordinaten van de snijpunten met de waterlijn naar een dictionary")
        snijpunten_waterlijn_dict = bepalen_x_y_coordinaat_meerdere_punten(gp, snijpunt_waterlijn, gpgident)

        log.debug("Nu wegschrijven van de coordinaten van de overgebleven punten van de ster naar een dictionary")
        punten_star_dict = bepalen_x_y_coordinaat_meerdere_punten(gp, intersect2, gpgident)

        log.debug("Er zijn 2 of meer punten op de waterlijn waarnaar de punten van de ster een afstand hebben")
        log.debug("Berekend wordt welke de minimale afstand oplevert tussen punt van de ster en waterlijn")
        #nu afstand berekenen mbv de distance calculator uit vorige script tussen snijpunten_waterlijn_dict en intersect2
        minimaldistance_dict_star_points = calculate_distance_between_points(snijpunten_waterlijn_dict, punten_star_dict)
        log.info("Berekend wordt welk punt van de bergingstak het verst van de waterlijn verwijderd is")
        list_with_ideal_points = bepaal_ideale_punt_bergingstak(minimaldistance_dict_star_points)
        out_data = turtlebase.arcgis.get_random_file_name(workspace_gdb)
        gp.Copy_management (star, out_data)

        log.info("Selecteer de bergingstakken die loodrecht op waterlijn staan")
        remove_records_from_shapefile_not_in_list(gp, star, gpgident, list_with_ideal_points)
        #koppel de lijnen aan de RR_oppervlak tabel en neem de openwat_HA waarden over
        log.debug("De gpgident wordt weer teruggehaald ui de unieke peilgebiedid")
        clean_up_star(gp, star, gpgident)
        #intersect van star met zichzelf. als er iets overblijft dan geef een warning met de betreffende peilgebied id, mededeling
        # voor de gebruiker dat hij/zij daar even handmatig wat aan aan moet passen.
        log.info("Creeeren out_shape bergingstakken")
        log.info('%s  star' %star)
        log.info('%s  star'% output_bergingstakken)
        gp.select_analysis(star, output_bergingstakken)


        
        
        log.info("Check of er bergingstakken zijn die overlappen ")
        try:
            intersect3 = turtlebase.arcgis.get_random_file_name(workspace_gdb)
            gp.Intersect_analysis(output_bergingstakken, intersect3, "#", "#", "POINT")
            #loop door de output van de intersect en geeft de GPGident weer als deze in de attribute table staat
            row = gp.SearchCursor(intersect3)
            for item in nens.gp.gp_iterator(row):
                gpg_ident = item.getValue(gpgident)
                log.warning("In peilgebied " + str(gpg_ident) + " overlapt de bergingstak met een andere bergingstak. Pas dit handmatig aan!")
        except (RuntimeError, TypeError, NameError):
            log.info('Geen overlap aanwezig')    
            
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


