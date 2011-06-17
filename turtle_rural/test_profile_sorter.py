import os
from pylab import *

def create_profile_graph_png(output_folder):
    """
    Create profile graph for each profile
    """
    fieldname_profile = 'PROIDENT'
    height = 'ZCOORD'
    xlabeltext = 'Profielpunt' #
    ylabeltext = 'm NAP' #
    order_field = 'NR' #'pnt_order'
    output_folder = "C:\\GISPROJECT\\Profielen Almere\\test7"
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
    
    profiles = {}
    database = r'C:\\GISTEMP\\Turtlework'
    table = '%s\\test.dbf' %database
    row = gp.SearchCursor(table)
    for item in nens.gp.gp_iterator(row):
        profile_name = item.GetValue(fieldname_profile)

        pnt_order = item.GetValue(order_field)
        
        if not profiles.has_key(profile_name):
            profiles[profile_name] = []
        y_value = item.getValue(height)
    
        profiles[profile_name].insert(pnt_order, y_value)            
        
    for profile_name in profiles.keys():
        print profile_name
        clf()
        x = []
        y = []
        for index, h in enumerate(profiles[profile_name]):
            x.append(index)
            y.append(h)
            print "X: %s, Y:%s" % (index, h)
        print x

        #finding min en max y values
        max_y = max(y)
        min_y = min(y)
        if max_y > 9000:
            max_y = 10
        if min_y < -9000:
            min_y = -10
        #SETTING PROPER extent for drawing.
        ylim( (min_y - 1, max_y + 1) )
    
        #profilename = 'TPL_BEEMSTER_BU_1280'
        plot(x,y, linewidth = 1.0, color = 'k')
        xlabel(xlabeltext)
        ylabel(ylabeltext)

##    text(top, right, 'Kruinhoogte %s' %max_y)
        #annotate('Kruinhoogte \n %s m NAP' %round(max_y,2), xy=(50, max_y) )
        #annotate('Diepte \n teensloot \n %s m NAP' %round(min_y,2), xy=(50, min_y) )

        #title('Profiel %s' %profile_name)
        title('Keerhoogtes gebied %s' %profile_name)
        grid(True)
        savefig('%s\\%s.png' % (output_folder, profile_name))
    

def setPointAttributes(point, id, x, y):
    """
    add coordinates to a Point object(CreateObject)
    id should be a unique integer
    geometry should contain a list of a x and y coordinate
    """
    point.id = id
    point.x = float(x)
    point.y = float(y)
    return point


def create_point_fc(gp, output_fc, profile_dict):
    """
    """
    workspace = os.path.dirname(output_fc)
    fc_name = os.path.basename(output_fc)
    gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                                     "#", "DISABLED", "DISABLED", "#")

    gp.addfield(output_fc, 'LOCIDENT', "TEXT")
    gp.addfield(output_fc, 'PROIDENT', "TEXT")
    gp.addfield(output_fc, 'XCOORD', "DOUBLE")
    gp.addfield(output_fc, 'YCOORD', "DOUBLE")
    gp.addfield(output_fc, 'ZCOORD', "DOUBLE")

    rows = gp.InsertCursor(output_fc)
    point = gp.CreateObject("Point")

    i = 0
    for k, v in profile_dict.items():
        i += 1
        proident = v['proident']
        x = v['xcoord']
        y = v['ycoord']
        z = v['zcoord']
        #add new point
        row = rows.NewRow()
        point = setPointAttributes(point, i, x, y)
        row.shape = point

        row.SetValue('LOCIDENT', k)
        row.SetValue('PROIDENT', proident)
        row.SetValue('XCOORD', x)
        row.SetValue('YCOORD', y)
        row.SetValue('ZCOORD', z)
        
        rows.InsertRow(row)
    del rows
    del row


def gather_xyz_points(xyzs, proident, zcoord, xcoord, ycoord):
    """
    from:
    [{'proident': profiel1}, {'proident': profiel2}]
    to:
    {proident: [[x1, y1, z1], [x2, y2, z2]]}
    """
    result = {}
    for xyz in xyzs:
        xyz_proid = xyz[proident]
        if xyz_proid in result:
            result[xyz_proid].append([xyz[xcoord], xyz[ycoord], xyz[zcoord]])
        else:
            result[xyz_proid] = [[xyz[xcoord], xyz[ycoord], xyz[zcoord]]]

    return result


def sort_xyz_profile(gp, nens_gp, geom, locations, xyz_points):
    """
    xyz_points = [[x1, y1, z1], [x2, y2, z2]]
    """
    locs = nens_gp.get_table(gp, locations, primary_key='locident')
    # [{'proident': profiel1}, {'proident': profiel2}]
    xyzs = nens_gp.get_table(gp, xyz_points)

    result = gather_xyz_points(xyzs, 'proident', 'zcoord', 'xcoord', 'ycoord')

    sorted_profiles = {}
    x = 0
    for loc, values in locs.items():
        profile = values['proident']
        sorted = geom.sort(result[profile])
        for point in sorted:
            x += 1
            sorted_profiles[x] = {'proident': profile, 'xcoord': point[0], 'ycoord': point[1], 'zcoord': point[2]}

    return sorted_profiles


import arcgisscripting
gp = arcgisscripting.create()
from nens import geom
from nens import gp as nens_gp

locations = "C:/GISPROJECT/Profielen Almere/Profielen/Locaties.shp"
xyz_points = "C:/GISPROJECT/Profielen Almere/Profielen/Profiel_punten_v5.shp"
sorted_profiles = sort_xyz_profile(gp, nens_gp, geom, locations, xyz_points)

import turtlebase.arcgis
output_points = turtlebase.arcgis.get_random_file_name(
                "c:/gistemp/turtlework", '.shp')
create_point_fc(gp, output_points, sorted_profiles)
print "fini!"


"""
Profielen tool voor gemeente Almere

Input:
Profiellocaties met per punt:
Ident (LOCIDENT)
Type (Nu ondersteund: XYZ profiel. Later ook YZ, Trapezium en Tabulated)
Profiel ident (PROIDENT)

Meetpunten XYZ
Profiel ident (PROIDENT)
XCOORD
YCOORD
ZCOORD

Sort points (using nens.geom)
Create line from points
Intersect with axislines
Calculate angle at intersection
For each point calculate the angle to the midpoint and correct the
 distance using pythagoras/gonio
Output is YZ table
Calculate waterlevel for each profile (spatial join with target level areas
Draw profiles (Profile + (summer)targetlevel -> PNG)

In de grafiek:
- Datumveld
- LOCIDENT
- Hoogte in m NAP
- X = 0 bij midpoint
- Streefpeil in grafiek
- Zachte bodem

for i in objs:
    if i.setdefault('points_2d', []):
        i['profile_shape'] = 3
    if i.get('points_3d'):
        sorted = geom.sort(i['points_3d'])
        abscissas = geom.abscissa_from_midsegment(sorted)
        i['points_2d'] = [(xx,z) for ((xx), (x,y,z)) in zip(abscissas, sorted)]
        i['profile_shape'] = 1
        del i['points_3d']
    if i['points_2d']:
        i['field_level'] = min(i['points_2d'][0][1], i['points_2d'][-1][1])
"""
