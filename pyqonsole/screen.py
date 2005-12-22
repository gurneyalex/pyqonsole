# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
""" Provide the Screen class.

The image manipulated by the emulation.

    This class implements the operations of the terminal emulation framework.
    It is a complete passive device, driven by the emulation decoder
    (EmuVT102). By this it forms in fact an ADT, that defines operations
    on a rectangular image.

    It does neither know how to display its image nor about escape sequences.
    It is further independent of the underlying toolkit. By this, one can even
    use this module for an ordinary text surface.

    Since the operations are called by a specific emulation decoder, one may
    collect their different operations here.

    The state manipulated by the operations is mainly kept in `image', though
    it is a little more complex beyond this..

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
"""

__revision__ = "$Id: screen.py,v 1.27 2005-12-22 17:39:44 syt Exp $"

from pyqonsole.ca import *
from pyqonsole.helpers import wcWidth
from pyqonsole.history import HistoryScrollBuffer

MODE_Origin  = 0
MODE_Wrap    = 1
MODE_Insert  = 2
MODE_Screen  = 3
MODE_Cursor  = 4
MODE_NewLine = 5
MODES_SCREEN = 6

BS_CLEARS = False

#REVERSE_WRAPPED_LINES = True # For debug wrapped lines
    

class Screen:
    """
    the screen is a list of lists (columns * lines), i.e. get column 4
    of line 2 with _image[3][1] (index start at 0...)
    
    coordonate are stored as 2d point (y, x)
    """
    
    def _loc(self, x, y):
        return y*self.columns+x

    
    def __init__(self, l=1, c=1):
        # Screen image
        self.lines = l
        self.columns = c
        self._image = [[DCA for j in xrange(c)] for i in xrange(l+1)]
        self._lineWrapped = [False for i in xrange(l+1)]
        # History buffer
        self.hist_cursor = 0
        self._hist = HistoryScrollBuffer(1000)
        # Cursor location
        self._cu_x = 0
        self._cu_y = 0
        # Cursor color and rendition info
        self._cu_fg = 0
        self._cu_bg = 0
        self._cu_re = 0
        # Margins top / bottom
        self._margin_t = 0
        self._margin_b = 0
        # States
        self._curr_mode = [None, None, None, None, None, None]
        self._save_mode = [None, None, None, None, None, None]
        self.__tabStops = None
        # Effective color and rendition
        self._eff_fg = 0
        self._eff_bg = 0
        self._eff_re = 0
        # Save cursor location
        self.__saCuX = 0
        self.__saCuY = 0
        # save cursor color and rendition info
        self.__saCuFg = 0
        self.__saCuBg = 0
        self.__saCuRe = 0
        # Selection
        self.busy_selecting = False # Busy making a selection
        self.clearSelection()
        #
        self.__initTabStops()
        self.reset()

    # Screen operations
    
    # The `cursor' is a location within the screen that is implicitely used in
    # many operations. The operations within this section allow to manipulate
    # the cursor explicitly and to obtain it's value.

    # The position of the cursor is guarantied to be between (including) 0 and
    # `columns-1' and `lines-1'.

    # Cursor movement
     
    def cursorUp(self, n):
        """CUU"""
        if not n:
            n = 1
        if self._cu_y < self._margin_t:
            stop = 0
        else:
            stop = self._margin_t
        self._cu_x = min(self.columns-1, self._cu_x)
        self._cu_y = max(stop, self._cu_y-n)
        
    def cursorDown(self, n):
        """CUD"""
        if not n:
            n = 1
        if self._cu_y > self._margin_t:
            stop = self.lines-1
        else:
            stop = self._margin_b
        self._cu_x = min(self.columns-1, self._cu_x)
        self._cu_y = max(stop, self._cu_y+n)
        
    def cursorLeft(self, n):
        """CUB"""
        if not n:
            n = 1
        self._cu_x = min(self.columns-1, self._cu_x)
        self._cu_x = max(0, self._cu_x-n)
        
    def cursorRight(self, n):
        """CUF"""
        if not n:
            n = 1
        self._cu_x = min(self.columns-1, self._cu_x+n)
        
    def setCursorX(self, x):
        if not x:
            x = 1
        x -= 1
        self._cu_x = max(0, min(self.columns-1, x))
        
    def setCursorY(self, y):
        if not y:
            y = 1
        y -= 1
        if self.getMode(MODE_Origin):
            dy = self._margin_t
        else:
            dy = 0
        self._cu_y = max(0, min(self.lines-1, y+dy))

    def setCursorYX(self, y, x):
        self.setCursorX(x)
        self.setCursorY(y)
    
    def setMargins(self, top, bot):
        """Set top and bottom margin"""
        if top == 0:
            top = 1
        if bot == 0:
            bot = self.lines
        top -= 1
        bot -= 1
        if not (0 <= top and top < bot and bot < self.lines):
            print "setMargins(%d, %d) : bad range" % (top, bot)
            return
        self._margin_t = top
        self._margin_b = bot
        self._cu_x = 0
        if self.getMode(MODE_Origin):
            self._cu_y = top
        else:
            self._cu_y = 0
    
    # Cursor movement with scrolling
    def newLine(self):
        """
        This behaves either as index() or as nextLine()
        depending on the NewLine Mode (LNM). This mode also
        affects the key sequence returned for newline ([CR]LF).
        """
        if self.getMode(MODE_NewLine):
            self.return_()
        self.index()
    
    def nextLine(self):
        self.return_()
        self.index()
       
    def index(self):
        """Move the cursor down one line.
        
        If cursor is on bottom margin, the region between the
        actual top and bottom margin is scrolled up instead.
        """
        if self._cu_y == self._margin_b:
            if self._margin_t == 0 and self._margin_b == self.lines-1:
                self._addHistoryLine()
            self._scrollUp(self._margin_t, 1)
        elif self._cu_y < self.lines:
            self._cu_y += 1
    
    def reverseIndex(self):
        """Move the cursor up one line.
        
        If cursor is on the top margin, the region between the
        actual top and bottom margin is scrolled down instead.
        """
        if self._cu_y == self._margin_t:
            self._scrollDown(self._margin_t, 1)
        elif self._cu_y > 0:
            self._cu_y -= 1
    
    def return_(self):
        self._cu_x = 0
        
    def tabulate(self):
        self.cursorRight(1)
        while self._cu_x < self.columns-1 and not self.__tabStops[self._cu_x]:
            self.cursorRight(1)
        
    def backSpace(self):
        """Move the cursor to left one column"""
        self._cu_x = max(0, self._cu_x-1)
        if (BS_CLEARS):
            oldca = self._image[self._cu_y][self._cu_x]
            self._image[self._cu_y][self._cu_x] = Ca(ord(' '), oldca.f, oldca.b, oldca.r)
        
    def clear(self):
        """Clear the entire screen and home the cursor"""
        self.clearEntireScreen()
        self.home()
    
    def home(self):
        """home the cursor"""
        self._cu_x = self._cu_y = 0
        
    def reset(self):
        self.setMode(MODE_Wrap)      # Wrap at end of margin
        self.saveMode(MODE_Wrap)
        self.resetMode(MODE_Origin)  # Position refere to [1,1]
        self.saveMode(MODE_Origin)
        self.resetMode(MODE_Insert)  # Overstroke
        self.saveMode(MODE_Insert)
        self.setMode(MODE_Cursor)    # Cursor visible
        self.resetMode(MODE_Screen)  # Screen not inversed
        self.resetMode(MODE_NewLine)
        self._margin_t = 0
        self._margin_b = self.lines-1
        self.setDefaultRendition()
        self.saveCursor()
        self.clear()
        
    def eraseChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self._cu_x+n-1, self.columns-1))
        self._clearImage([self._cu_y, self._cu_x], [self._cu_y, p], ' ')
        
    def deleteChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self._cu_x+n, self.columns-1))
        self._moveImage([self._cu_y, self._cu_x], [self._cu_y, p], [self._cu_y, self.columns-1])
        self._clearImage([self._cu_y, self.columns-n], [self._cu_y, self.columns-1], ' ')
        
    def insertChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self.columns-1-n, self.columns-1))
        q = max(0, min(self._cu_x+n, self.columns-1))
        self._moveImage([self._cu_y, q], [self._cu_y, self._cu_x], [self._cu_y, p])
        self._clearImage([self._cu_y, self._cu_x], [self._cu_y, q-1], ' ')
        
    def deleteLines(self, n):
        if n == 0:
            n = 1
        self._scrollUp(self._cu_y, n)
        
    def insertLines(self, n):
        if n == 0:
            n = 1
        self._scrollDown(self._cu_y, n)
        
    def clearTabStops(self):
        for i in xrange(self.columns):
            self.__tabStops[i-1] = False
            
    def changeTabStop(self, set):
        if self._cu_x >= self.columns:
            return
        self.__tabStops[self._cu_x] = set
        
    def setMode(self, m):
        self._curr_mode[m] = True
        if m == MODE_Origin:
            self._cu_x = 0
            self._cu_y = self._margin_t
            
    def resetMode(self, m):
        self._curr_mode[m] = False
        if m == MODE_Origin:
            self._cu_x = self._cu_y = 0
            
    def saveMode(self, m):
        self._save_mode[m] = self._curr_mode[m]
            
    def restoreMode(self, m):
        self._curr_mode[m] = self._save_mode[m]
            
    def saveCursor(self):
        self.__saCuX = self._cu_x
        self.__saCuY = self._cu_y
        self.__saCuRe = self._cu_re
        self.__saCuFg = self._cu_fg
        self.__saCuBg = self._cu_bg
       
    def restoreCursor(self):
        self._cu_x = min(self.__saCuX, self.columns-1)
        self._cu_y = min(self.__saCuY, self.lines-1)
        self._cu_re = self.__saCuRe
        self._cu_fg = self.__saCuFg
        self._cu_bg = self.__saCuBg
        self._effectiveRendition()
        
    def clearEntireScreen(self):
        self._clearImage([0, 0], [self.lines-1, self.columns-1], ' ')
        
    def clearToEndOfScreen(self):
        self._clearImage([self._cu_y, self._cu_x], [self.lines-1, self.columns-1], ' ')
        
    def clearToBeginOfScreen(self):
        self._clearImage([0, 0], [self._cu_y, self._cu_x], ' ')
        
    def clearEntireLine(self):
        self._clearImage([self._cu_y, 0], [self._cu_y, self.columns-1], ' ')
        
    def clearToEndOfLine(self):
        self._clearImage([self._cu_y, self._cu_x], [self._cu_y, self.columns-1], ' ')
        
    def clearToBeginOfLine(self):
        self._clearImage([self._cu_y, 0], [self._cu_y, self._cu_x], ' ')
        
    def helpAlign(self):
        self._clearImage([0, 0], [self.lines-1, self.columns-1], 'E')
        
    def setRendition(self, re):
        self._cu_re = self._cu_re | re
        self._effectiveRendition()
        
    def resetRendition(self, re):
        self._cu_re = self._cu_re & ~re
        self._effectiveRendition()
        
    def setForeColor(self, fgcolor):
        if fgcolor & 8:
            self._cu_fg = (fgcolor & 7) + 4+8
        else:
            self._cu_fg = (fgcolor & 7) + 2
        self._effectiveRendition()
            
    def setBackColor(self, bgcolor):
        if bgcolor & 8:
            self._cu_bg = (bgcolor & 7) + 4+8
        else:
            self._cu_bg = (bgcolor & 7) + 2
        self._effectiveRendition()
            
    def setDefaultRendition(self):
        self.setForeColorToDefault()
        self.setBackColorToDefault()
        self._cu_re = DEFAULT_RENDITION
        self._effectiveRendition()
        
    def setForeColorToDefault(self):
        self._cu_fg = DEFAULT_FORE_COLOR
        self._effectiveRendition()
        
    def setBackColorToDefault(self):
        self._cu_bg = DEFAULT_BACK_COLOR
        self._effectiveRendition()
        
    def getMode(self, n):
        return self._curr_mode[n]
    
    def getCursorX(self):
        return self._cu_x
    
    def getCursorY(self):
        return self._cu_y

    def showCharacter(self, c):
        #print 'screen.showcharacter', chr(c)
        w = wcWidth(c)
        if w <= 0:
            return
        if self._cu_x+w > self.columns:
            if self.getMode(MODE_Wrap):
                self._lineWrapped[self._cu_y] = True
                self.nextLine()
            else:
                self._cu_x = self.columns-w
        if self.getMode(MODE_Insert):
            self.insertChars(w)
        cpt = [self._cu_y, self._cu_x]
        self.checkSelection(cpt, cpt)
        line = self._image[self._cu_y]
        line[self._cu_x] = Ca(c, self._eff_fg, self._eff_bg, self._eff_re)
        self._cu_x += w
        for i in xrange(1, w):
            line[self._cu_x + i] = Ca(0, self._eff_fg, self._eff_bg, self._eff_re)
        
    def resizeImage(self, lines, columns):
        if lines == self.lines and columns == self.columns:
            return
        print 'screen.resize', lines, columns
        if self._cu_y > lines+1:
            self._margin_b = self.lines-1
            for i in xrange(self._cu_y-(lines-1)):
                self._addHistoryLine()
                self._scrollUp()
        # Make new image
        newimg = [[DCA for x in xrange(columns)] for y in xrange(lines+1)]
        newwrapped = [False for y in xrange(lines+1)]
        # Copy to new image
        for y in xrange(min(lines, self.lines)):
            for x in xrange(min(columns, self.columns)):
                newimg[y][x] = self._image[y][x]
            newwrapped[y] = self._lineWrapped[y]
        self._image = newimg
        self._lineWrapped = newwrapped
        self.lines = lines
        self.columns = columns
        self._cu_x = min(self._cu_x, self.columns-1)
        self._cu_y = min(self._cu_y, lines-1)
        self._margin_t = 0
        self._margin_b = self.lines - 1
        self.__initTabStops()
        self.clearSelection()
        
    def getCookedImage(self):
        #print 'cooked image', self.lines, self._hist.lines, self.hist_cursor
        image_size = self.lines * self.columns
        merged = [[DCA for x in xrange(self.columns)] for y in xrange(self.lines)]
        y = 0
        hist = self._hist
        actual_y = hist.lines - self.hist_cursor
        # get lines from history
        while y < self.lines and y < actual_y:
            yq = y + self.hist_cursor
            len_ = min(self.columns, hist.getLineLen(yq))
            merged[y][:len_] = hist.getCells(yq, 0, len_)
            for x in xrange(self.columns):
                q = [yq, x]
                if q >= self._sel_topleft and q <= self._sel_bottomright:
                    self._reverseRendition(merged, x, y)
            y += 1
        # get lines from the actual screen
        for y in xrange(actual_y, self.lines):
            yq = y + self.hist_cursor
            yr = y - actual_y
            for x in xrange(self.columns):
                q = [yq, x]
                merged[y][x] = self._image[yr][x]
                if q >= self._sel_topleft and q <= self._sel_bottomright:
                    self._reverseRendition(merged, x, y)
        # reverse rendition on screen mode
        if self.getMode(MODE_Screen):
            for y in xrange(self.lines):
                for x in xrange(self.columns):
                    self._reverseRendition(merged, x, y)
        # update cursor
        cuy = self._cu_y + actual_y
        if self.getMode(MODE_Cursor) and \
               cuy < self.lines and self._cu_x < self.columns:
            ca = merged[cuy][self._cu_x]
            merged[cuy][self._cu_x] = Ca(ca.c, ca.f, ca.b, ca.r | RE_CURSOR)
        return merged
    
    def getCookedLineWrapped(self):
        result = [False for i in xrange(self.lines)]
        actual_y = self._hist.lines - self.hist_cursor
        for y in xrange(min(self.lines, actual_y)):
            result[y] = self._hist.isWrappedLine(y+self.hist_cursor)
        for y in xrange(actual_y, self.lines):
            result[y] = self._lineWrapped[y-actual_y]
        return result
    
    def getHistLines(self):
        return self._hist.lines
    
    def setScroll(self, scroll_type):
        self.clearSelection()
        self._hist = scroll_type.getScroll(self._hist)
        self.hist_cursor = self._hist.lines
        
    def getScroll(self):
        return self._hist.getType()
    
    def hasScroll(self):
        return self._hist.hasScroll()
    
    def _clearImage(self, loca, loce, c):
        c = ord(c)
        # Clear entire selection if overlaps region to be moved
        if self._overlapSelection(loca, loce):
            self.clearSelection()
        ca = Ca(c, self._eff_fg, self._eff_bg, DEFAULT_RENDITION)
        for y in xrange(loca[0], loce[0]+1):
            for x in xrange(loca[1], loce[1]+1):
                self._image[y][x] = ca
            self._lineWrapped[y] = False
    
    def _moveImage(self, dest, loca, loce):
        #print 'move image', dest, loca, loce
        assert loce >= loca
        # XXX x coordonates are not always considered. Is it enough actually ?
        ys = loca[0]
        if dest[0] != ys:
            dy = loce[0] - ys + 1
            self._image[dest[0]:dest[0]+dy] = [lines[:] for lines in self._image[ys:ys+dy]]
            for i in xrange(dy):
                self._lineWrapped[dest[0]+i] = self._lineWrapped[ys+i]
        else:
            xs = loca[1]
            dx = loce[1] - xs + 1
            self._image[ys][dest[1]:dest[1]+dx] = self._image[ys][xs:xs+dx]
        # Adjust selection to follow scroll
        if self._sel_begin != [-1, -1]:
            beginIsSTL = (self._sel_begin == self._sel_topleft)
            diff = self._subPoints(dest, loca) # Scroll by this amount
            scr_topleft = [self._hist.lines, 0]
            srca = self._addPoints(loca, scr_topleft) # Translate index from screen to global
            srce = self._addPoints(loce, scr_topleft)
            desta = self._addPoints(srca, diff)
            deste = self._addPoints(srce, diff)
            if self._sel_topleft >= srca and self._sel_topleft <= srce:
                self._sel_topleft = self._addPoints(self._sel_topleft, diff)
            elif self._sel_topleft >= desta and self._sel_topleft <= deste:
                self._sel_bottomright = [-1, -1] # Clear selection (see below)
            if self._sel_bottomright >= srca and self._sel_bottomright <= srce:
                self._sel_bottomright = self._addPoints(self._sel_bottomright, diff)
            elif self._sel_bottomright >= desta and self._sel_bottomright <= deste:
                self._sel_bottomright = [-1, -1] # Clear selection (see below)
            if self._sel_bottomright < [0, 0]:
                self.clearSelection()
            elif self._sel_topleft < [0, 0]:
                    self._sel_topleft = [0, 0]
            if beginIsSTL:
                self._sel_begin = self._sel_topleft
            else:
                self._sel_begin = self._sel_bottomright
                
    def _scrollUp(self, from_, n):
        if n <= 0 or from_+n > self._margin_b:
            return
        self._moveImage([from_, 0], [from_+n, 0], [self._margin_b, self.columns-1])
        self._clearImage([self._margin_b-n+1, 0], [self._margin_b, self.columns-1], ' ')
        
    def _scrollDown(self, from_, n):
        if n <= 0 or from_ > self._margin_b:
            return
        if from_+n > self._margin_b:
            n = self._margin_b-from_
        self._moveImage([from_+n, 0], [from_, 0], [self._margin_b-n, self.columns-1])
        self._clearImage([from_, 0], [from_+n-1, self.columns-1], ' ')
        
    def _addHistoryLine(self):
        """Add the first image's line to history buffer
        Take care about scrolling too...
        """
        assert self.hasScroll() or self.hist_cursor == 0
        if not self.hasScroll():
            return
        end = self.columns - 1
        while end >= 0 and (self._image[0][end] is DCA or
                            self._image[0][end] == DCA) and not self._lineWrapped[0]:
            end -= 1
        oldHistLines = self._hist.lines
        self._hist.addCells(self._image[0][:end+1], self._lineWrapped[0])
        newHistLines = self._hist.lines
        # Adjust history cursor
        beginIsTL = (self._sel_begin == self._sel_topleft)
        if newHistLines > oldHistLines:
            self.hist_cursor += 1
            # Adjust selection for the new point of reference
            if self._sel_begin != [-1, -1]:
                self._sel_topleft[0] += 1
                self._sel_bottomright[0] += 1
        # Scroll up if user is looking at the history and we can scroll up
        if self.hist_cursor > 0 and (self.hist_cursor != newHistLines
                                     or self.busy_selecting):
            self.hist_cursor -= 1
        # Scroll selection in history up
        if self._sel_begin != [-1, -1]:
            topBR = [1+newHistLines, 0]
            if self._sel_topleft < topBR:
                self._sel_topleft[0] -= 1
            if self._sel_bottomright < topBR:
                self._sel_bottomright[0] -= 1
            if self._sel_bottomright < [0, 0]:
                self.clearSelection()
            elif self._sel_topleft < [0, 0]:
                self._sel_topleft = [0, 0]
            if beginIsTL:
                self._sel_begin = self._sel_topleft
            else:
                self._sel_begin = self._sel_bottomright
            
    def __initTabStops(self):
        self.__tabStops = self.columns*[False]
        for i in xrange(self.columns):
            self.__tabStops[i] = ((i % 8 == 0) and i != 0)
        
    def _effectiveRendition(self):
        self._eff_re = self._cu_re & (RE_UNDERLINE | RE_BLINK)
        if self._cu_re & RE_REVERSE:
            self._eff_fg = self._cu_bg
            self._eff_bg = self._cu_fg
        else:
            self._eff_fg = self._cu_fg
            self._eff_bg = self._cu_bg
        if self._cu_re & RE_BOLD:
            if self._eff_fg < BASE_COLORS:
                self._eff_fg += BASE_COLORS
            else:
                self._eff_fg -= BASE_COLORS
                
    def _reverseRendition(self, image, x, y):
#        image[coord] = p = image[coord].dump()
        p = image[y][x]
        image[y][x] = Ca(p.c, p.b, p.f, p.r)

    # selection handling ######################################################

    def setSelBeginXY(self, x, y):
        self._sel_begin = [y+self.hist_cursor, x]
        if x == self.columns:
            self._incPoint(self._sel_begin, -1)
        self._sel_bottomright = self._sel_begin
        self._sel_topleft = self._sel_begin
        
    def setSelExtendXY(self, x, y):
        if self._sel_begin == [-1, -1]:
            return
        l = [y+self.hist_cursor, x]
        if l < self._sel_begin:
            self._sel_topleft = l
            self._sel_bottomright = self._sel_begin
        else:
            if x == self.columns:
                self._incPoint(l, -1)
            self._sel_topleft = self._sel_begin
            self._sel_bottomright = l
            
    def testIsSelected(self, x, y):
        pos = [y+self.hist_cursor, x]
        return pos >= self._sel_topleft and pos <= self._sel_bottomright
    
    def clearSelection(self):
        self._sel_begin = [-1, -1]      # First location selected
        self._sel_topleft = [-1, -1]    # Top-left location
        self._sel_bottomright = [-1, -1]# Bottom-right location
        
    def getSelText(self, preserve_line_break):
        if self._sel_begin == [-1, -1]:
            return
        histBR = [self._hist.lines, 0]
        hY = self._sel_topleft[0]
        hX = self._sel_topleft[1]
        m = []
        s = self._sel_topleft[:]
        if preserve_line_break:
            eol_char = '\n'
        else:
            eol_char = ' '
        while s <= self._sel_bottomright:
            # XXX in the first if branch, eol is scalar while in the else branch, it's a point !
            if s < histBR:
                eol = self._hist.getLineLen(hY)
                if hY == self._sel_bottomright[0] and eol > self._sel_bottomright[1]:
                    eol = self._sel_bottomright[1] + 1
                while hX < eol:
                    c = self._hist.getCells(hY, hX, 1)[0].c
                    if c:
                        m.append(unichr(c))
                    self._incPoint(s)
                    hX += 1
                if s <= self._sel_bottomright:
                    if eol % self.columns == 0:
                        if eol == 0:
                            m.append(eol_char)
                        elif not self._hist.isWrappedLine(hY):
                            m.append(eol_char)
                    elif (eol + 1) % self.columns == 0:
                        if not self._hist.isWrappedLine(hY):
                            m.append(eol_char)
                    else:
                        m.append(eol_char)
                hY += 1
                hX = 0
                s = [hY, 0]
            else:
                eol = [s[0]+1, 0]
                self._incPoint(eol, -1)
                addNewLine = False
                if eol < self._sel_bottomright:
                    while eol > s:
                        pt = self._subPoints(eol, histBR)
                        ca = self._image[pt[0]][pt[1]]
                        if (not ca.c or ca.isSpace()) and not self._lineWrapped[pt[0]]:
                            break
                        self._incPoint(eol, -1)
                elif eol == self._sel_bottomright:
                    pt = self._subPoints(eol, histBR)
                    if not self._lineWrapped[pt[0]]:
                        addNewLine = True
                else:
                    eol = self._sel_bottomright
                while s <= eol:
                    pt = self._subPoints(s, histBR)
                    c = self._image[pt[0]][pt[1]].c
                    if c:
                        m.append(unichr(c))
                    self._incPoint(s)
                if eol < self._sel_bottomright:
                    if eol[1] +1 == self.columns: #(eol + 1) % self.columns == 0:
                        if not self._hist.isWrappedLine(eol[0]-histBR[0]):
                            m.append(eol_char)
                    else:
                        m.append(eol_char)
                elif addNewLine and preserve_line_break:
                    m.append('\n')
                s = [eol[0]+1, 0]
        # skip trailing spaces
        m = [line.rstrip() for line in ''.join(m).splitlines()]
        return '\n'.join(m)
    
    def checkSelection(self, from_, to):
        if self._sel_begin == [-1, -1]:
            return
        # Clear entire selection if overlaps region to be moved
        if self._overlapSelection(from_, to):
            self.clearSelection()

    def _overlapSelection(self, from_, to):
        assert isinstance(from_, list), from_
        assert isinstance(to, list), to
        scr_topleft = [self._hist.lines, 0]
        # Clear entire selection if overlaps region [from_, to]
        if self._sel_bottomright > self._addPoints(from_, scr_topleft) and \
               self._sel_topleft < self._addPoints(to, scr_topleft):
            return True
        return False
        

    # point manipulation ######################################################
    
    def _incPoint(self, point, inc=1):
        x = point[1] + inc
        if x < 0 or x >= self.columns:
            dy, x = divmod(x, self.columns)
            point[0] += dy
        point[1] = x
        
    def _addPoints(self, point1, point2):
        x = point1[1] + point2[1]
        y = point1[0] + point2[0]
        if x < 0 or x >= self.columns:
            dy, x = divmod(x, self.columns)
            y += dy
        return [y, x]
    
    def _subPoints(self, point1, point2):
        x = point1[1] - point2[1]
        y = point1[0] - point2[0]
        if x < 0 or x >= self.columns:
            dy, x = divmod(x, self.columns)
            y += dy
        return [y, x]
        
