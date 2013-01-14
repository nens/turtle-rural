import arcgisscripting
gp = arcgisscripting.create()

#import maaiveldcurve
import sys, os
environList = os.environ['PATH'].split(';')
environList.insert(0, r'C:/Python27/ArcGIS10.1/Lib/site-packages/osgeo')
os.environ['PATH'] = ';'.join(environList)
from osgeo import ogr
gp.AddMessage(ogr.__file__)

peilgebieden = sys.argv[1]
#rr_peilgebied = sys.argv[2]
hoogtekaart = sys.argv[2]
landgebruik = sys.argv[3]
#conversietabel = sys.argv[5]
#rr_maaiveld = sys.argv[6]
kaartbladen = sys.argv[4]

#gp.AddMessage(peilgebieden)
workspace = "c:/gistemp/turtlework/"
ahn_workspace = os.path.join(workspace, "ahn_bladen")
os.makedirs(ahn_workspace)
lgn_workspace = os.path.join(workspace, "lgn_bladen")
os.makedirs(lgn_workspace)

gp.MakeFeatureLayer_management(kaartbladen, "krtbldn_lyr")
gp.MakeFeatureLayer_management(peilgebieden, "gpg_lyr")
gp.SelectLayerByLocation_management("krtbldn_lyr","INTERSECT","gpg_lyr","#","NEW_SELECTION")
kaartbladen_prj = os.path.join(ahn_workspace,"werkgebied.shp")
gp.Select_analysis("krtbldn_lyr", kaartbladen_prj)

def main():
    rows = gp.searchcursor(kaartbladen_prj)
    row = rows.next()
    while row:
        gp.Extent = row.Shape.extent
        out_ahn_raster = os.path.join(ahn_workspace, row.BLADNR)
        gp.CopyRaster_management(hoogtekaart, out_ahn_raster, "#", "#", -9999, "#", "#", "32_BIT_FLOAT")
        out_lgn_raster = os.path.join(lgn_workspace, row.BLADNR)
        gp.CopyRaster_management(landgebruik, out_lgn_raster, "#", "#", -9999, "#", "#", "32_BIT_FLOAT")
        row = rows.next()
        
    #maaiveldcurve.main(peilgebieden, kaartbladen_prj, lgn_workspace, ahn_workspace, workspace)
