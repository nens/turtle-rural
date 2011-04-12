# the following code is copied from / inspired by install.py from
# zc.sourcerelease at http://www.python.org/pypi/zc.sourcerelease

import os, sys

here = os.path.abspath(os.path.dirname(__file__))

sys.path[0:0] = [os.path.join(here, 'eggs', e) for e in os.listdir('eggs')]

config = os.path.join(here, 'buildout.cfg')

import zc.buildout.buildout
zc.buildout.buildout.main([

    '-Uc', config,
    'buildout:download-cache='+os.path.join(here, 'downloads'),
    'buildout:install-from-cache=true',
    ] + sys.argv[1:])
