# pylint: disable-msg=W0622
"""pyqonsole packaging information"""

__revision__ = '$Id: __pkginfo__.py,v 1.7 2006-01-10 09:51:16 syt Exp $'

modname = "pyqonsole"
numversion = (0, 1, 0)
version = '.'.join([str(num) for num in numversion])
license = 'CeCILL'
copyright = '''Copyright (c) 2006 LOGILAB S.A. (Paris, FRANCE)
Copyright (c) 2006 CEA-Grenoble.
'''

short_desc = "console application written in Python using Qt"
long_desc = """\
 WRITEME"""

author = "Sylvain Thenault"
author_email = "sylvain.thenault@logilab.fr"
web = "http://www.logilab.org/projects/%s" % modname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname
mailinglist = "mailto://python-projects@logilab.org"

from os.path import join
scripts = [join('bin', 'pyqonsole')]

try:
    from distutils.core import Extension
    ext_modules = [Extension('pyqonsole._helpers',
                             sources = ['helpers.c'])]
except ImportError:
    pass

data_files = [('share/pyqonsole/', ['default.keytab'])]

pyversions = ['2.3', '2.4']

debian_maintainer = 'Alexandre Fayolle'
debian_maintainer_email = 'afayolle@debian.org'
