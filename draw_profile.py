import sys
import os
sys.path[0:0] = [
  'c:\\python_ontwikkeling\\turtle-rural',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\eazysvn-1.12.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\coverage-3.4-py2.6-win32.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pep8-0.6.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\zest.releaser-3.20-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\setuptools-0.6c11-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\turtlebase',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pkginfo-0.8-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\py-nens',
  'c:\\python26\\arcgis10.0\\lib\\site-packages',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\mock-0.7.0-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pil-1.1.7-py2.6-win32.egg',
  ]
import traceback
import arcgisscripting
gp = arcgisscripting.create()
import nens.gp
# genereer profieldoorsnede

try:

    fieldname_profile = 'PROIDENT'
    height = 'BED_LVL'
    xlabeltext = 'Profielpunt' #
    ylabeltext = 'm NAP' #
    order_field = 'PNT_ORDERb' #'pnt_order'
    output_folder = "C:\\GISPROJECT\\Vecht\\profiel110"
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
    
    profiles = {}
    from pylab import *
    database = r'C:\\GISPROJECT\\Vecht'
    table = '%s\\profiel110.dbf' %database
    row = gp.SearchCursor(table)
    for item in nens.gp.gp_iterator(row):
        profile_name = item.GetValue(fieldname_profile)

        dist_mid = item.GetValue(order_field)
        
        if not profiles.has_key(profile_name):
            profiles[profile_name] = []
        y_value = item.getValue(height)
    
        profiles[profile_name].append((dist_mid, y_value))    
                
        
    print profiles
    for profile_name in profiles.keys():
        print profile_name
        clf()
        x = []
        y = []
        print profiles[profile_name]
        for dist_mid, y_value in profiles[profile_name]:
            x.append(dist_mid)
            y.append(y_value)
            print "X: %s, Y:%s" % (dist_mid, y_value)
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
        print ylim
    
        #profilename = 'TPL_BEEMSTER_BU_1280'
        plot(x, y, linewidth = 1.0, color = 'k')
        water_x = [min(x), max(x)]
        water_y = [1, 1]  # streefpeil
        plot(water_x, water_y, linewidth = 2.0, color = 'b')
        
        xlabel(xlabeltext)
        ylabel(ylabeltext)

##    text(top, right, 'Kruinhoogte %s' %max_y)
        #annotate('Kruinhoogte \n %s m NAP' %round(max_y,2), xy=(50, max_y) )
        #annotate('Diepte \n teensloot \n %s m NAP' %round(min_y,2), xy=(50, min_y) )

        #title('Profiel %s' %profile_name)
        title('Dwarsprofiel %s' % profile_name)
        grid(True)
        savefig('%s\\%s.png' % (output_folder, profile_name))


except:
    print traceback.format_exc()