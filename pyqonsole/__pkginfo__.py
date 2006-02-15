# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
# pylint: disable-msg=W0622
"""pyqonsole packaging information"""

__revision__ = '$Id: __pkginfo__.py,v 1.8 2006-02-15 10:24:01 alf Exp $'

modname = "pyqonsole"
numversion = (0, 2, 0)
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
