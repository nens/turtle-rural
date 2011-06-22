import random
import arcgisscripting
import sys

sys.path[0:0] = [
  'c:\\python_ontwikkeling\\turtle-rural',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\eazysvn-1.12.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\coverage-3.4-py2.6-win32.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pep8-0.6.1-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\zest.releaser-3.20-py2.6.egg',
  'c:\\python26\\arcgis10.0\\lib\\site-packages',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\turtlebase',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pkginfo-0.8-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\local_checkouts\\py-nens',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\mock-0.7.0-py2.6.egg',
  'c:\\python_ontwikkeling\\turtle-rural\\eggs\\pil-1.1.7-py2.6-win32.egg',
  ]

import nens.gp
gp = arcgisscripting.create()

input_table = sys.argv[1]
random_field = sys.argv[2]
min_int = sys.argv[3]
max_int = sys.argv[4]

rows = gp.UpdateCursor(input_table)
gp.AddMessage(rows)
for row in nens.gp.gp_iterator(rows):
    random_int = random.randint(int(min_int), int(max_int))
    gp.AddMessage(random_int)
    row.SetValue(random_field, int(random_int))
    rows.UpdateRow(row)
