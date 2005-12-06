from distutils.core import setup, Extension

_helpers = Extension('_helpers',
                     sources = ['helpers.c'])

setup (name = 'pyqonsole',
       version = '1.0',
       description = '',
       ext_modules = [_helpers])

