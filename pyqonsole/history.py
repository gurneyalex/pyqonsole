""" Provide History classes.

An arbitrary long scroll.

   One can modify the scroll only by adding either cells
   or newlines, but access it randomly.

   The model is that of an arbitrary wide typewriter scroll
   in that the scroll is a serie of lines and each line is
   a serie of cells with no overwriting permitted.

   The implementation provides arbitrary length and numbers
   of cells and line/column indexed read access to the scroll
   at constant costs.

FIXME: some complain about the history buffer comsuming the
       memory of their machines. This problem is critical
       since the history does not behave gracefully in cases
       where the memory is used up completely.

       I put in a workaround that should handle it problem
       now gracefully. I'm not satisfied with the solution.

FIXME: Terminating the history is not properly indicated
       in the menu. We should throw a signal.

FIXME: There is noticable decrease in speed, also. Perhaps,
       there whole feature needs to be revisited therefore.
       Disadvantage of a more elaborated, say block-oriented
       scheme with wrap around would be it's complexity.

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003
@organization: CEA-Grenoble
@license: ??
"""

# Reasonable line size
LINE_SIZE = 1024


class HistoryType(object):
    """ History Type abstract base class.
    """
    def isOn(self):
        return False

    def getSize(self):
        return 0
    
    def getScroll(self):
        return HistoryScroll()
    
    
class HistoryTypeNone(HistoryType):
    """ History Type which does nothing.
    """
    def getScroll(self):
        return HistoryScrollNone()
        

class HistoryTypeBuffer(HistoryType):
    """ History Type using a buffer.
    """
    def __init__(self, nbLines):
        """ Init the History Type Buffer.
        """
        super(HistoryTypeBuffer, self).__init__()
        self.__nbLines = nbLines
        
    def getNbLines(self):
        return self.__nbLines
    
    def getSize(self):
        return self.getNbLines()
        
    #def getScroll(self):
        #return HistoryScrollBuffer()
        

class HistoryScroll(object):
    """ History Scroll abstract base class.
    """
    def __init__(self, type_):
        """ Init the History Scroll abstract base class.
        """
        self.__histType = type_
        
    def hasScroll(self):
        return True
    
    def getLines(self):
        return 0
    
    def getLineLen(self, lineno):
        return 0
    
    def getCells(self, lineno, colno, count):
        raise NotImplementedError
    
    def isWrappedLine(self, lineno):
        return False
    
    # Backward compatibility. Obsolete
    #def getCell(self, lineno, colno):
        #return self.getCells(lineno, colno, 1)[0]
    
    def addCells(self, a, count):
        raise NotImplementedError
    
    def addLine(self, previousWrapped=False):
        raise NotImplementedError
    
    def getType(self):
        return self.__histType
    
    
class HistoryScrollNone(HistoryScroll):
    """ History Scroll which does nothing.
    """
    def __init__(self):
        """ Init the History Scroll None.
        """
        super(HistoryScrollNone, self).__init__(HistoryTypeNone())
        
    def hasScroll(self):
        return False
    
    def getCells(self, lineno, colno, count):
        return None
    
    def addCells(self, a, count):
        pass
    
    def addLine(self, previousWrapped=False):
        pass
   

class HistoryScrollBuffer(HistoryScroll):
    """ History Scroll using a buffer.
    """
    def __init__(self):
        """ Init the History Scroll Buffer.
        """
        super (HistoryScrollBuffer, self).__init__(HistoryTypeBuffer())