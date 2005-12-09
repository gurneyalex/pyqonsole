__revision__ = '$Id: setup.py,v 1.2 2005-12-09 09:11:13 alf Exp $'

from distutils.core import setup, Extension

_helpers = Extension('_helpers',
                     sources = ['helpers.c'])

setup (name = 'pyqonsole',
       version = '1.0',
       description = '',
       ext_modules = [_helpers])

