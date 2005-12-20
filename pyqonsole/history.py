# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""Provides the History class.

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
@author: Sylvain Thenault
@copyright: 2003, 2005
@organization: CEA-Grenoble
@organization: Logilab
@license: CECILL


XXX getLineLen usefull
"""

__revision__ = '$Id: history.py,v 1.5 2005-12-20 11:03:03 alf Exp $'


class HistoryType(object):
    """ History Type abstract base class.
    """
    def isOn(self):
        return False

    def getSize(self):
        return 0
    
    def getScroll(self, old=None):
        raise NotImplementedError
    
    
class HistoryTypeNone(HistoryType):
    """ History Type which does nothing.
    """
    def getScroll(self, old=None):
        return HistoryScrollNone()
        

class HistoryTypeBuffer(HistoryType):
    """ History Type using a buffer.
    """
    def __init__(self, nb_lines):
        """ Init the History Type Buffer.
        """
        super(HistoryTypeBuffer, self).__init__()
        self.nb_lines = nb_lines
        
    def getSize(self):
        self.nb_lines
        
    def getScroll(self, old=None):
        if not old:
            return HistoryScrollBuffer(self.nb_lines)
        if isinstance(old, HistoryScrollBuffer):
            old.setMaxLines(self.nb_lines)
            return old
        scroll = HistoryScrollBuffer(self.nb_lines)
        start = 0
        if self.nb_lines < old.lines:
            start = old.lines - self.nb_lines
        for i in xrange(start, old.lines):
            scroll.addCells(old.getCells(i, 0), old.isWrappedLine(i))
        return scroll

    
class HistoryScroll(object):
    """ History Scroll abstract base class.
    """
    def __init__(self, type_):
        """ Init the History Scroll abstract base class.
        """
        self.type = type_
        self.lines = 0
        
    def hasScroll(self):
        return True
    
    def getLineLen(self, lineno):
        return 0
    
    def getCells(self, lineno, colno, count=None):
        raise NotImplementedError
    
    def isWrappedLine(self, lineno):
        return False
    
    def addCells(self, a, wrapped=False):
        raise NotImplementedError
    
    
class HistoryScrollNone(HistoryScroll):
    """ History Scroll which does nothing.
    """
    def __init__(self):
        """ Init the History Scroll None.
        """
        super(HistoryScrollNone, self).__init__(HistoryTypeNone())
        
    def hasScroll(self):
        return False
    
    def getCells(self, lineno, colno, count=None):
        return None
    
    def addCells(self, a, wrapped=False):
        pass
   

class HistoryScrollBuffer(HistoryScroll):
    """ History Scroll using a buffer.
    """
    def __init__(self, max_lines):
        """ Init the History Scroll Buffer.
        """
        super (HistoryScrollBuffer, self).__init__(HistoryTypeBuffer(max_lines))
        self.max_lines = max_lines
        self.lines = 0
        self.array_index = 0
        self.buff_filled = False
        self.hist_buffer = [None] * max_lines
        self.wrapped_line = [False] * max_lines
        
    def addCells(self, a, wrapped=False):
        """a: list(Ca())"""
        line = a[:] # XXX necessary ?
        self.hist_buffer[self.array_index] = line
        self.wrapped_line[self.array_index] = wrapped
        self.array_index += 1
        if self.array_index >= self.max_lines:
            self.array_index = 0
            self.buff_filled = True
        if self.lines < self.max_lines - 1:
            self.lines += 1

    def getLineLen(self, lineno):
        if lineno >= self.max_lines:
            return 0
        line = self.hist_buffer[self._adjustLineNo(lineno)]
        if line is not None:
            return len(line)
        return 0

    def isWrappedLine(self, lineno):
        if lineno >= self.max_lines:
            return 0
        return self.wrapped_line[self._adjustLineNo(lineno)]

    def getCells(self, lineno, colno, count=None):
        assert lineno < self.max_lines
        lineno = self._adjustLineNo(lineno)
        line = self.hist_buffer[lineno]
        assert line is not None
        assert colno < len(line), 'colno=%d, len(line)=%d'%(colno, len(line))
        if count is None:
            count = len(line)
        return line[colno:colno + count]

    def setMaxLines(self, max_lines):
        self._normalize()
        if self.max_lines > max_lines:
            start = max(0, self.array_index + 2 - max_lines)
            end = start + max_lines
            self.hist_buffer = self.hist_buffer[start:end]
            self.wrapped_line = self.wrapped_line[start:end]
            if self.array_index > max_lines:
                self.array_index = max_lines - 2
        else:
            self.hist_buffer += [None] * (max_lines - self.max_lines)
            self.wrapped_line += [False] * (max_lines - self.max_lines)
        self.max_lines = max_lines
        if self.lines > max_lines - 2:
            self.lines = max_lines - 2
        self.type = HistoryTypeBuffer(max_lines)

    def _normalize(self):
        if not self.buff_filled: # or not self.array_index:
            return
        max_lines = self.max_lines
        hist_buffer = [None] * max_lines
        wrapped_line = [False] * max_lines
        for k, i in enumerate(xrange(self.array_index - 1, self.array_index-max_lines+1, -1)):
            lineno = self._adjustLineNo(i-1)
            hist_buffer[max_lines - 3 - k] = self.hist_buffer[i]
            wrapped_line[max_lines - 3 - k] = self.wrapped_line[i]
        self.hist_buffer = hist_buffer
        self.wrapped_line = wrapped_line
        self.array_index = max_lines - 2
        self.buff_filled = False
        self.lines = max_lines - 2

    def _adjustLineNo(self, lineno):
        if self.buff_filled:
            return (lineno + self.array_index + 2) % self.max_lines
        else:
            return lineno
