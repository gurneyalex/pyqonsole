import weakref

import qt
from pyqonsole import emuVt102

LOGGERS = []

def register_logger(l):
    LOGGERS.append(weakref.ref(l))
    
def reset_logs():
    for wr in LOGGERS[:]:
        logger = wr()
        if logger is None: # deleted
            LOGGERS.remove(wr)
            continue
        logger._logs = []
        
def logged(func, name):
    def wrapper(self, *args, **kwargs):
        record = (name,)
        if args:
            record += (args,)
        if kwargs:
            record += (kwargs,)
        try:
            self._logs.append(record)
        except AttributeError:
            self._logs = [record]
        return func(self, *args, **kwargs)
    return wrapper


class NullObject(object):
    def __init__(self, *args, **kwargs):
        self._logs = []
        LOGGERS.append(weakref.ref(self))
        #super(NullObject,self).__init__(*args, **kwargs)
        
    def __getattribute__(self, name):
        if name != '_logs':
            self._logs.append( ('getattr', name) )
        try:
            return super(NullObject, self).__getattribute__(name)
        except AttributeError:
            return self

    __call__ = logged(lambda *args, **kwargs: None, 'call')

        
class NullGui(NullObject, qt.QObject):
    columns = 72
    lines = 60
    def __init__(self, lines=lines, columns=columns):
        NullObject.__init__(self)
        qt.QObject.__init__(self)

    
class NullScreen(NullObject, qt.QObject):
    columns = 72
    lines = 60
    def getCursorX(self):
        return 1
    def getCursorY(self):
        return 1
    def __init__(self, lines=lines, columns=columns):
        NullObject.__init__(self)
        qt.QObject.__init__(self)

    
class MyEmuVt102(emuVt102.EmuVt102):
    def emit(self, signal, *args, **kwargs):
        try:
            self._logs.append( (signal, args) )
        except AttributeError:
            self._logs = [ (signal, args) ]
    def reportErrorToken(self, token, p, q):
        try:
            self._logs.append( ('token error', token, p, q) )
        except AttributeError:
            self._logs = [ ('token error', token, p, q) ]
            
    _setCharset = logged(emuVt102.EmuVt102._setCharset, '_setCharset')
    _useCharset = logged(emuVt102.EmuVt102._useCharset, '_useCharset')
    setMode = logged(emuVt102.EmuVt102.setMode, 'setMode')
    resetMode = logged(emuVt102.EmuVt102.resetMode, 'resetMode')
    saveMode = logged(emuVt102.EmuVt102.saveMode, 'saveMode')
    setPrinterMode = logged(emuVt102.EmuVt102.setPrinterMode, 'setPrinterMode')
            
