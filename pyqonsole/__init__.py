# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
"""pyqonsole is a python xterm, which may be used independantly or as a qt
widget
"""
__revision__ = "$Id: __init__.py,v 1.6 2006-02-15 10:24:01 alf Exp $"

_QT_VERSION=3

def require_qt(version):
    """Use this function to specify which version of Qt and PyQt you
    want to use to run pyqonsole. Supported versions are 3 and 4.

    Warning: do not change the version after qtconfig() has been
    called to query the version. Assume that any module in the
    pyqonsole package besides the __init__ module may call qtconfig
    when imported. Therefore the safe practise is to use the following
    in your code:

    >>> from pyqonsole import require_qt
    >>> require_qt(3) # or 4
    >>> from pyqonsole.widget import Widget
    """
    assert version in (3,4), "Supported versions are 3 and 4"
    global _QT_VERSION
    _QT_VERSION = version
    
def qtconfig():
    """return the current required Qt version"""
    return _QT_VERSION

def CTRL(c):
    """return the code of the given character when typed with the control
    button enabled
    """
    return ord(c) - ord("@")

class Signalable(object):
    """a class implementing a signal API similar to the qt's one"""

    def __init__(self, *args):
        print self, args
        super(Signalable, self).__init__(*args)
        self.__connected = {}
        
    def myconnect(self, signal, callback):
        """connect the given callback to the signal"""
        self.__connected.setdefault(signal, []).append(callback)
        
    def mydisconnect(self, signal, callback):
        """disconnect the given callback from the signal"""
        self.__connected[signal].remove(callback)
        
    def myemit(self, signal, args=()):
        """emit the given signal with the given arguments if any"""
        for callback in self.__connected.get(signal, []):
            try:
                callback(*args)
            except:
                import traceback
                traceback.print_exc()
