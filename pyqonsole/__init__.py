"""pyqonsole is a python xterm, which may be used independantly or as a qt
widget
"""
__revision__ = "$Id: __init__.py,v 1.5 2005-12-27 14:47:47 syt Exp $"

def CTRL(c):
    """return the code of the given character when typed with the control
    button enabled
    """
    return ord(c) - ord("@")

class Signalable(object):
    """a class implementing a signal API similar to the qt's one"""

    def __init__(self, *args):
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
