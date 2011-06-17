import nens.geom
import nens.gp
import turtlebase.arcgis
import os
import time


hydroline = "c:/gisproject/profielen almere/testdata/hydroline.shp"
mpoint = "c:/gisproject/profielen almere/testdata/pointcloud.shp"
output_sorted = "c:/gisproject/profielen almere/testdata/output/output_%s.shp" % time.strftime("%H%M%S")
output_yz = "c:/gisproject/profielen almere/testdata/output/output_yz_%s.dbf" % time.strftime("%H%M%S")

import arcgisscripting
gp = arcgisscripting.create()

"""
- dissolve pointcloud
- Calculate centroid of pointcloud multipoint
- spatial join (kijk voor iedere puntenwolk welke watergang het dichtsbij de centroid ligt
- read lines
- read pointclouds
- for each pointcloud:
    sort perpendicular to segment
- create output:
    xyz points
    yz table
"""


#def calculate_multipoint_centroid(point_collection, dissolve_id):
#    """
#    creates a fc with centre points of a point collection
#    """
#    gp.dissolve
#    gp.addxy
#    create points from xy
#    return centroid_fc

# Create workspace
workspace = "c:/gistemp/turtlework"
turtlebase.arcgis.delete_old_workspace_gdb(gp, workspace)

if not os.path.isdir(workspace):
    os.makedirs(workspace)
workspace_gdb, errorcode = turtlebase.arcgis.create_temp_geodatabase(
                                gp, workspace)
if errorcode == 1:
    log.error("failed to create a file geodatabase in %s" % workspace)
            
#hydroline_points = create_points(gp, hydroline, "ID")
#pointscloud = create_points(gp, mpoint, "PROIDENT")

multipoints = turtlebase.arcgis.get_random_file_name(workspace_gdb)

gp.Dissolve_management(mpoint, multipoints, "PROIDENT")


def create_centroids(multipoints, output_fc, mp_ident):
    """creates a centrepoint fc out of a multipoint fc
    
    """
    gp.AddXY_management(multipoints)
    
    mpoint_desc = gp.describe(multipoints)
    centre_points = {}

    row = gp.SearchCursor(multipoints)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(mpoint_desc.ShapeFieldName)
        item_id = item.GetValue(mp_ident)
        xcoord = float(feat.Centroid.split(' ')[0])
        ycoord = float(feat.Centroid.split(' ')[1])
       
        centre_points[item_id] = {"XCOORD": xcoord, "YCOORD": ycoord}
     
    workspace = os.path.dirname(output_fc)
    fc_name = os.path.basename(output_fc)
    gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                                "#", "DISABLED", "DISABLED", "#")
    gp.addfield(output_fc, 'PROIDENT', "TEXT")
    gp.addfield(output_fc, 'XCOORD', "DOUBLE")
    gp.addfield(output_fc, 'YCOORD', "DOUBLE")
    
    rows = gp.InsertCursor(output_fc)
    point = gp.CreateObject("Point")
    
    for point_id, attributes in centre_points.items():
        row = rows.NewRow()
        point.x = attributes['XCOORD']
        point.y = attributes['YCOORD']
        row.shape = point

        row.SetValue('PROIDENT', point_id)
        row.SetValue('XCOORD', point.x)
        row.SetValue('YCOORD', point.y)
        
        rows.InsertRow(row)
    del rows
    del row


  
centrepoints = turtlebase.arcgis.get_random_file_name(workspace_gdb)
create_centroids(multipoints, centrepoints, 'PROIDENT')

centrepoints_sj = turtlebase.arcgis.get_random_file_name(workspace_gdb)
gp.SpatialJoin_analysis(centrepoints, hydroline, centrepoints_sj, 'JOIN_ONE_TO_ONE',
                        "#", "#", "CLOSEST", 100)

gp.AddXY_management(centrepoints_sj)
centrepoints_d = nens.gp.get_table(gp, centrepoints_sj, primary_key='proident')

def get_line_parts(line_fc, line_ident):
    """reads all the lines in the line_fc and return a dict with all line parts
    
    """
    lineparts = {}
    hydroline_desc = gp.describe(hydroline)
    row = gp.SearchCursor(hydroline)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(hydroline_desc.ShapeFieldName)
        item_id = item.GetValue(line_ident)
        
        part = feat.getpart(0)
        pnt_list = [(round(pnt.x, 5), round(pnt.y, 5)) for pnt in
                    nens.gp.gp_iterator(part)]

        lineparts[item_id] = pnt_list
    return lineparts


def get_pointcloud(point_fc, point_ident):
    """
    reads all the points in the pointcloud and return a dict with all points that match point_id
    """
    pointcloud = {}
    point_desc = gp.describe(point_fc)
    
    row = gp.SearchCursor(point_fc)
    for item in nens.gp.gp_iterator(row):
        feat = item.GetValue(point_desc.ShapeFieldName)
        item_id = item.GetValue(point_ident)
        
        pnt_xyz = (round(float(feat.Centroid.split(' ')[0]), 5),
                  round(float(feat.Centroid.split(' ')[1]), 5),
                  float(item.GetValue('ZCOORD')))

        if item_id not in pointcloud:
            pointcloud[item_id] = [pnt_xyz]
        else:
            pointcloud[item_id].append(pnt_xyz)
            
    return pointcloud
    
    
lineparts = get_line_parts(hydroline, 'ovkident')
pointcloud = get_pointcloud(mpoint, 'proident')

sorted_profiles = {}
profiles_yz = {}
for centrepoint_id, attributes in centrepoints_d.items():
    """
    >>> ls = [(0, 0), (30, 40), (30, 10)]
    >>> pc = [(10, 10), (9, 11), (7, 12), (6, 13)]
    """
    print "ID: %s" % centrepoint_id
    ls = lineparts[attributes['ovkident']]
    print "ls: %s" % ls
    pc = pointcloud[centrepoint_id]
    print "pc_unsorted: %s" % pc
    print "pc_sorted: %s" % nens.geom.sort(pc)
    
    try:
        sorted = nens.geom.sort_perpendicular_to_segment(ls, nens.geom.sort(pc))
    except:
        continue
    sorted_profiles[centrepoint_id] = sorted
    print "sorted: %s" % sorted
    abscissas = nens.geom.abscissa_from_midsegment(sorted)
    print "abscissas %s" % abscissas
    
    profile_order = 0
    for x in abscissas:
        zcoord = sorted[profile_order][2]
        #zcoord = 0
        profile_order += 1
        profiles_yz["%s_%s" % (centrepoint_id, profile_order)] = {"proident": centrepoint_id, "dist_mid": x, "bed_lvl": zcoord, "p_order": profile_order}
        

workspace = os.path.dirname(output_sorted)
fc_name = os.path.basename(output_sorted)
gp.CreateFeatureClass_management(workspace, fc_name, "Point",
                            "#", "DISABLED", "DISABLED", "#")
gp.addfield(output_sorted, 'PROIDENT', "TEXT")
gp.addfield(output_sorted, 'XCOORD', "DOUBLE")
gp.addfield(output_sorted, 'YCOORD', "DOUBLE")
gp.addfield(output_sorted, 'ZCOORD', "DOUBLE")

rows = gp.InsertCursor(output_sorted)
point = gp.CreateObject("Point")

for point_id, attributes in sorted_profiles.items():
    for point_xy in attributes:
        row = rows.NewRow()
        point.x = point_xy[0]
        point.y = point_xy[1]
        row.shape = point

        row.SetValue('PROIDENT', point_id)
        row.SetValue('XCOORD', point.x)
        row.SetValue('YCOORD', point.y)
        row.SetValue('ZCOORD', point_xy[2])

        
        rows.InsertRow(row)
del rows
del row

workspace = os.path.dirname(output_yz)
table_name = os.path.basename(output_yz)
gp.CreateTable_management(workspace, table_name)

gp.addfield(output_yz, 'PROIDENT', "TEXT")
gp.addfield(output_yz, 'DIST_MID', "DOUBLE")
gp.addfield(output_yz, 'BED_LVL', "DOUBLE")
gp.addfield(output_yz, 'P_ORDER', "SHORT")

rows = gp.InsertCursor(output_yz)
for point_id, attributes in profiles_yz.items():
    row = rows.NewRow()
    row.SetValue('PROIDENT', attributes['proident'])
    row.SetValue('DIST_MID', float(attributes['dist_mid']))
    row.SetValue('BED_LVL', float(attributes['bed_lvl']))
    row.SetValue('P_ORDER', int(attributes['p_order']))
    
    rows.InsertRow(row)
del rows
del row

    
print "Finished!"

















