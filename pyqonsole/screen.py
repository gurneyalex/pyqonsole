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
@copyright: 2003
@organization: CEA-Grenoble
@license: ??
"""

__revision__ = "$Id: screen.py,v 1.6 2005-12-15 14:57:15 syt Exp $"

import ca
from ca import Ca
from helpers import wcWidth
from history import HistoryScrollNone

MODE_Origin  = 0
MODE_Wrap    = 1
MODE_Insert  = 2
MODE_Screen  = 3
MODE_Cursor  = 4
MODE_NewLine = 5
MODES_SCREEN = 6

BS_CLEARS = False

REVERSE_WRAPPED_LINES = True # For debug wrapped lines


    

class Screen:
    """ Screen class.
    """
    def loc(self, x, y):
        return y*self.columns+x
    
    def __init__(self, l=1, c=1):
        # Screen image
        self.lines = l
        self.columns = c
        self._image = [Ca() for j in xrange(c) for i in xrange(l+1)]
        self.__lineWrapped = [False for i in xrange(l+1)]
        # History buffer
        self.__histCursor = 0
        self.__hist = HistoryScrollNone()
        # Cursor location
        self.__cuX = 0
        self.__cuY = 0
        # Cursor color and rendition info
        self.__cuFg = 0
        self.__cuBg = 0
        self.__cuRe = 0
        # Margins
        self.__tMargin = 0
        self.__bMargin = 0
        # States
        self.__currParm = {'mode': [None, None, None, None, None, None]}
        self.__tabStops = None
        # Selection
        self._sel_begin = 0    # First location selected
        self._sel_topleft = 0       # Top-left location
        self._sel_bottomright = 0       # Bottom-right location
        self.__selBusy = False # Busy making a selection
        # Effective color and rendition
        self.__efFg = 0
        self.__efBg = 0
        self.__efRe = 0
        # Save cursor location
        self.__saCuX = 0
        self.__saCuY = 0
        # save cursor color and rendition info
        self.__saCuFg = 0
        self.__saCuBg = 0
        self.__saCuRe = 0
        # Save modes
        self.__saveParm = {'mode': [None, None, None, None, None, None]}
        #
        self.__initTabStops()
        self.clearSelection()
        self.reset()

    # Screen operations
    
    # The `cursor' is a location within the screen that is implicitely used in
    # many operations. The operations within this section allow to manipulate
    # the cursor explicitly and to obtain it's value.

    # The position of the cursor is guarantied to be between (including) 0 and
    # `columns-1' and `lines-1'.

    # Cursor movement
    def cursorUp(self, n):
        """ CUU
        """
        if n == 0:
            n = 1
        if self.__cuY < self.__tMargin:
            stop = 0
        else:
            stop = self.__tMargin
        self.__cuX = min(self.columns-1, self.__cuX)
        self.__cuY = max(stop, self.__cuY-n)
        
    def cursorDown(self, n):
        """ CUD
        """
        if n == 0:
            n = 1
        if self.__cuY > self.__tMargin:
            stop = self.lines-1
        else:
            stop = self.__bMargin
        self.__cuX = min(self.columns-1, self.__cuX)
        self.__cuY = max(stop, self.__cuY+n)
        
    def cursorLeft(self, n):
        """ CUB
        """
        if n == 0:
            n = 1
        self.__cuX = min(self.columns-1, self.__cuX)
        self.__cuX = max(0, self.__cuX-n)
        
    def cursorRight(self, n):
        """ CUF
        """
        if n == 0:
            n = 1
        self.__cuX = min(self.columns-1, self.__cuX+n)
        
    def setCursorX(self, x):
        if x == 0:
            x = 1
        x -= 1
        self.__cuX = max(0, min(self.columns-1, x))
        
    def setCursorY(self, y):
        if y == 0:
            y = 1
        y -= 1
        if self.getMode(MODE_Origin):
            dy = self.__tMargin
        else:
            dy = 0
        self.__cuY = max(0, min(self.lines-1, y+dy))

    def setCursorXY(self, x, y):
        self.setCursorX(x)
        self.setCursorY(y)
    
    def setMargins(self, top, bot):
        """ Set top and bottom margin.
        """
        if top == 0:
            top = 1
        if bot == 0:
            bot = self.lines
        top -= 1
        bot -= 1
        if not ((0 <= top) and (top < bot) and (bot > self.lines)):
            raise ValueError("setMargins(%d, %d) : bad range" % (top, bot))
        self.__tMargin = top
        self.__bMargin = bot
        self.__cuX = 0
        if self.getMode(MODE_Origin):
            self.__cuY = top
        else:
            self.__cuY = 0
    
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
        """ Move the cursor down one line.
        
        If cursor is on bottom margin, the region between the
        actual top and bottom margin is scrolled up instead.
        """
        if self.__cuY == self.__bMargin:
            if self.__tMargin == 0 and self.__bMargin == self.lines-1:
                self._addHistoryLine()
            self.__scrollUp(self.__tMargin, 1)
        elif self.__cuY < self.lines:
            self.__cuY += 1
    
    def reverseIndex(self):
        """ Move the cursor up one line.
        
        If cursor is on the top margin, the region between the
        actual top and bottom margin is scrolled down instead.
        """
        if self.__cuY == self.__tMargin:
            self.__scrollDown(self.__tMargin, 1)
        elif self.__cuY > 0:
            self.__cuY -= 1
    
    def return_(self):
        self.__cuX = 0
        
    def tabulate(self):
        self.cursorRight(1)
        while self.__cuX < self.columns-1 and not self.__tabStops[self.__cuX]:
            self.cursorRight(1)
        
    def backSpace(self):
        """ Move the cursor to left one column.
        """
        self.__cuX = max(0, self.__cuX-1)
        if (BS_CLEARS):
            self._image[self.loc(self.__cuX, self.__cuY)].c = ord(' ')
        
    def clear(self):
        """ Clear the entire screen and home the cursor.
        """
        self.clearEntireScreen()
        self.home()
    
    def home(self):
        """ Home the cursor.
        """
        self.__cuX = self.__cuY = 0
        
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
        
        self.__tMargin = 0
        self.__bMargin = self.lines-1
        
        self.setDefaultRendition()
        self.saveCursor()
        
        self.clear()
        
    def eraseChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self.__cuX+n-1, self.columns-1))
        self.__clearImage(self.loc(self.__cuX, self.__cuY), self.loc(p, self.__cuY), ' ')
        
    def deleteChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self.__cuX+n, self.columns-1))
        self.__moveImage(self.loc(self.__cuX, self.__cuY), self.loc(p, self.__cuY), self.loc(self.columns-1, self.__cuY))
        self.__clearImage(self.loc(self.columns-n, self.__cuY), self.loc(self.columns-1, self.__cuY), ' ')
        
    def insertChars(self, n):
        if n == 0:
            n = 1
        p = max(0, min(self.columns-1-n, self.columns-1))
        q = max(0, min(self.__cuX+n, self.columns-1))
        self.__moveImage(self.loc(q, self.__cuY), self.loc(self.__cuX, self.__cuY), self.loc(p, self.__cuY))
        self.__clearImage(self.loc(self.__cuX, self.__cuY), self.loc(q-1, self.__cuY), ' ')
        
    def deleteLines(self, n):
        if n == 0:
            n = 1
        self.__scrollUp(self.__cuY, n)
        
    def insertLines(self, n):
        if n == 0:
            n = 1
        self.__scrollDown(self.__cuY, n)
        
    def clearTabStops(self):
        for i in xrange(self.columns):
            self.__tabStops[i-1] = False
            
    def changeTabStop(self, set):
        if self.__cuX >= self.columns:
            return
        self.__tabStops[self.__cuX] = set
        
    def setMode(self, m):
        self.__currParm['mode'][m] = True
        if m == MODE_Origin:
            self.__cuX = 0
            self.__cuY = self.__tMargin
            
    def resetMode(self, m):
        self.__currParm['mode'][m] = False
        if m == MODE_Origin:
            self.__cuX = self.__cuY = 0
            
    def saveMode(self, m):
        self.__saveParm['mode'][m] = self.__currParm['mode'][m]
            
    def restoreMode(self, m):
        self.__currParm['mode'][m] = self.__saveParm['mode'][m]
            
    def saveCursor(self):
        self.__saCuX = self.__cuX
        self.__saCuY = self.__cuY
        self.__saCuRe = self.__cuRe
        self.__saCuFg = self.__cuFg
        self.__saCuBg = self.__cuBg
       
    def restoreCursor(self):
        self.__cuX = min(self.__saCuX, self.columns-1)
        self.__cuY = min(self.__saCuY, self.lines-1)
        self.__cuRe = self.__saCuRe
        self.__cuFg = self.__saCuFg
        self.__cuBg = self.__saCuBg
        self.__effectiveRendition()
        
    def clearEntireScreen(self):
        self.__clearImage(self.loc(0, 0), self.loc(self.columns-1, self.lines-1), ' ')
        
    def clearToEndOfScreen(self):
        self.__clearImage(self.loc(self.__cuX, self.__cuY), self.loc(self.columns-1, self.lines-1), ' ')
        
    def clearToBeginOfScreen(self):
        self.__clearImage(self.loc(0, 0), self.loc(self.__cuX, self.__cuY), ' ')
        
    def clearEntireLine(self):
        self.__clearImage(self.loc(0, self.__cuY), self.loc(self.columns-1, self.__cuY), ' ')
        
    def clearToEndOfLine(self):
        self.__clearImage(self.loc(self.__cuX, self.__cuY), self.loc(self.columns-1, self.__cuY), ' ')
        
    def clearToBeginOfLine(self):
        self.__clearImage(self.loc(0, self.__cuY), self.loc(self.__cuX, self.__cuY), ' ')
        
    def helpAlign(self):
        self.__clearImage(self.loc(0, 0), self.loc(self.columns-1, self.lines-1), 'E')
        
    def setRendition(self, re):
        self.__cuRe = self.__cuRe | re
        self.__effectiveRendition()
        
    def resetRendition(self, re):
        self.__cuRe = self.__cuRe & re
        self.__effectiveRendition()
        
    def setForeColor(self, fgcolor):
        if fgcolor & 8:
            self.__cuFg = (fgcolor & 7) + 4+8
        else:
            self.__cuFg = (fgcolor & 7) + 2
            
    def setBackColor(self, bgcolor):
        if bgcolor & 8:
            self.__cuBg = (bgcolor & 7) + 4+8
        else:
            self.__cuBg = (bgcolor & 7) + 2
            
    def setDefaultRendition(self):
        self.setForeColorToDefault()
        self.setBackColorToDefault()
        self.__cuRe = ca.DEFAULT_RENDITION
        self.__effectiveRendition()
        
    def setForeColorToDefault(self):
        self.__cuFg = ca.DEFAULT_FORE_COLOR
        self.__effectiveRendition()
        
    def setBackColorToDefault(self):
        self.__cuBg = ca.DEFAULT_BACK_COLOR
        self.__effectiveRendition()
        
    def getMode(self, n):
        return self.__currParm['mode'][n]
    
    def getCursorX(self):
        return self.__cuX
    
    def getCursorY(self):
        return self.__cuY

    def showCharacter(self, c):
        print 'screen.showcharacter', c
        w = wcWidth(c)
        if w <= 0:
            return
        if self.__cuX+w > self.columns:
            if self.getMode(MODE_Wrap):
                self.__lineWrapped[self.__cuY] = True
                self.nextLine()
            else:
                self.__cuX = self.columns-w
        if self.getMode(MODE_Insert):
            self.insertChars(w)
        i = self.loc(self.__cuX, self.__cuY)
        self.checkSelection(i, i)
        self._image[i].c = c
        self._image[i].f = self.__efFg
        self._image[i].b = self.__efBg
        self._image[i].r = self.__efRe
        self.__cuX += w
        w -= 1
        while (w):
            i += 1
            self._image[i].c = 0
            self._image[i].f = self.__efFg
            self._image[i].b = self.__efBg
            self._image[i].r = self.__efRe
            w -= 1
        
    def resizeImage(self, newLines, newColumns):
        if newLines == self.lines and newColumns == self.columns:
            return
        if self.__cuY > newLines+1:
            self.__bMargin = self.lines-1
            for i in xrange(self.__cuY-(newLines-1)):
                self._addHistoryLine()
                self.__scrollUp()
        
        # Make new image
        newImg = [[Ca() for j in xrange(newColumns)] for i in xrange(newLines+1)]
        newWrapped = [False for i in xrange(newLines+1)]
        self.clearSelection()
        
        # Clear new image
        for y in xrange(newLines):
            for x in xrange(newColumns):
                newImg[y*newColumns+x].c = ord(' ')
                newImg[y*newColumns+x].f = ca.DEFAULT_FORE_COLOR
                newImg[y*newColumns+x].b = ca.DEFAULT_BACK_COLOR
                newImg[y*newColumns+x].r = ca.DEFAULT_RENDITION
            newWrapped[y] = False
        
        # Copy to new image
        cpLines = min(newLines, self.lines)
        cpColumns = min(newColumns, self.columns)
        for y in xrange(newLines):
            for x in xrange(newColumns):
                newImg[y*newColumns+x].c = self._image[self.loc(x, y)].c
                newImg[y*newColumns+x].f = self._image[self.loc(x, y)].f
                newImg[y*newColumns+x].b = self._image[self.loc(x, y)].b
                newImg[y*newColumns+x].r = self._image[self.loc(x, y)].r
            newWrapped[y] = self.__lineWrapped[y]
        
        self._image = newImg
        self.__lineWrapped = newWrapped
        self.lines = newLines
        self.columns = newColumns
        self.__cuX = min(self.__cuX, self.columns-1)
        self.__cuY = min(self.__cuY, lines-1)
        self.__tMargin = 0
        self.__bMargin = self.lines
        self.__initTabStops()
        self.clearSelection()
        
    def getCookedImage(self):
        merged = self.lines*self.columns*[None]
        dft = Ca()
        
        y = 0
        while y < self.lines and y < (self.__hist.getLines()-self.__histCursor):
            len_ = min(self.columns, self.__hist.getLineLen(y,self.__histCursor))
            yp = y*self.columns
            yq = (y+self.__histCursor)*self.columns
            #self.__hist.getCells(y+self.__histCursor, 0, len_, merged, yp)
            try:
                merged[yp:yp+len_] = self.__hist.getCells(y+self.__histCursor, 0, len_)
            except TypeError:
                pass
            for x in xrange(len_, self.columns):
                merged[yp+x] = dft
            for x in xrange(self.columns):
                p = x+yp
                q = x+yq
                if REVERSE_WRAPPED_LINES: # Debug mode
                    if self.__hist.isWrappedLine(y+self.__histCursor):
                        self.__reverseRendition(merged, p)
                if q >= self._sel_topleft and q <= self._sel_bottomright:
                    self.__reverseRendition(merged, p)
                    
        if self.lines >= (self.__hist.getLines()-self.__histCursor):
            for y in xrange(self.__hist.getLines(), self.lines):
                yp = y*self.columns
                yq = (y+self.__histCursor)*self.columns
                yr = (y-self.__hist.getLines()+self.__histCursor)*self.columns
                for x in xrange(self.columns):
                    p = x+yp
                    q = x+yq
                    r = x+yr
                    merged[p] = self._image[r]
                    if REVERSE_WRAPPED_LINES: # Debug mode
                        if self.__lineWrapped[y+-self.__hist.getLines()+self.__histCursor]:
                            self.__reverseRendition(merged, p)
        
        if self.getMode(MODE_Screen):
            for i in xrange(self.lines*self.columns):
                self.__reverseRendition(merged, i)
        
        loc_ = self.loc(self.__cuX, self.__cuY+self.__hist.getLines()-self.__histCursor)
        if self.getMode(MODE_Cursor) and loc_ < self.columns*self.lines:
            merged[loc_].r = merged[loc_].r | ca.RE_CURSOR
        print merged
        return merged
    
    def getCookedLineWrapped(self):
        result = [False for i in xrange(self.lines)]
        
        y = 0
        while y < self.lines and y < (self.__hist.getLines()-self.__histCursor):
            result[y] = self.__hist.isWrappedLine(y+self.__histCursor)
        if self.lines >= (self.__hist.getLines()-self.__histCursor):
            
            for y in xrange(self.__hist.getLines()-self.__histCursor, self.lines):
                result[y] = self.__lineWrapped[y-self.__hist.getLines()+self.__histCursor]
                
        return result
    
    def setHistCursor(self, cursor):
        self.__histCursor = cursor
        
    def getHistCursor(self):
        return self.__histCursor
    
    def getHistLines(self):
        return self.__hist.getLines()
    
    def setScroll(self, t):
        self.clearSelection()
        self.__hist = t.getScroll(self.__hist)
        self.__histCursor = self.__hist.getLines()
        
    def getScroll(self):
        return self.__hist.getType()
    
    def hasScroll(self):
        return self.__hist.hasScroll()
    
    def setSelBeginXY(self, x, y):
        self._sel_begin = self.loc(x, y+self.__histCursor)
        if x == self.columns:
            self._sel_begin -= 1
        self._sel_bottomright = self._sel_begin
        self._sel_topleft = self._sel_begin
        
    def setSelExtentXY(self, x, y):
        if self._sel_begin == -1:
            return
        l = self.loc(x, y+self.__histCursor)
        if l < self._sel_begin:
            self._sel_topleft = l
            self._sel_bottomright = self._sel_begin
        else:
            if x == self.columns:
                l -= 1
            self._sel_topleft = self._sel_begin
            self._sel_bottomright = l
            
    def testIsSelected(self, x, y):
        pos = self.loc(x, y+self.__histCursor)
        return (pos >= self._sel_topleft and pos <= self._sel_bottomright)
    
    def clearSelection(self):
        self._sel_bottomright = -1
        self._sel_topleft = -1
        self._sel_begin = -1
        
    def setBusySelecting(self, busy):
        self.__selBusy = busy
        
    def getSelText(self, preserveLineBreak):
        if self._sel_begin == -1:
            return
        histBR = self.loc(0, self.__hist.getLines())
        hY = self._sel_topleft / self.columns
        hX = self._sel_topleft % self.columns
        s = self._sel_topleft
        d = (self._sel_bottomright - self.__selfTL) / self.columns + 1
        m = (d* (self.columns + 1) + 2) * [None]
        d = 0
        
        while s <= self._sel_bottomright:
            if s < histBR:
                eol = self.__hist.getLineLen(hY)
                if hY == (self._sel_bottomright / self.columns) and eol > (self._sel_bottomright % self.columns):
                    eol = self._sel_bottomright % self.columns + 1
                while hX < eol:
                    c = self.__hist.getCell(hY, hX).c
                    hX += 1
                    if c:
                        m[d] = c
                        d += 1
                    s += 1
                if s <= self._sel_bottomright:
                    if eol % self.columns == 0:
                        if eol == 0:
                            if preserveLineBreak:
                                m[d] = '\n'
                            else:
                                m[d] = ' '
                            d += 1
                        else:
                            if not self.__hist.isWrappedLine(hY):
                                if preserveLineBreak:
                                    m[d] = '\n'
                                else:
                                    m[d] = ' '
                                d += 1
                    elif (eol + 1) % self.columns == 0:
                        if not self.__hist.isWrappedLine(hY):
                            if preserveLineBreak:
                                m[d] = '\n'
                            else:
                                m[d] = ' '
                            d += 1
                    else:
                        if preserveLineBreak:
                            m[d] = '\n'
                        else:
                            m[d] = ' '
                            d += 1
                hY += 1
                hX = 0
                s = hY * self.columns
            else:
                eol = (s/self.columns+1)*self.columns-1
                addNewLine = False
                if eol < self._sel_bottomright:
                    while eol > s and \
                    (not self._image[eol-histBR].c or self._image[eol-histBR].c in (' ', '\t', '\f', '\n', '\r')) \
                    and not self.__lineWrapped[(eol-histBR)/self.columns]:
                        eol -= 1
                elif eol == self._sel_bottomright:
                    if not self.__lineWrapped[(eol-histBR)/self.columns]:
                        addNewLine = True
                else:
                    eol = self._sel_bottomright
                    
                while s < eol:
                    c = self._image[s-histBR].c
                    s += 1
                    if c:
                        m[d] = c
                        d += 1
                        
                if eol < self._sel_bottomright:
                    if (eol + 1) % self.columns == 0:
                        if not self.__hist.isWrappedLine((eol-histBR)/self.columns):
                            if preserveLineBreak:
                                m[d] = '\n'
                            else:
                                m[d] = ' '
                            d += 1
                    else:
                        if preserveLineBreak:
                            m[d] = '\n'
                        else:
                            m[d] = ' '
                            d += 1
                elif addNewLine and preserveLineBreak:
                    m[d] = '\n'
                    d += 1

                s = (eol/self.columns+1)*self.columns

        qc = d*[None]
        lastSpace = -1
        j = 0
        for i in xrange(d):
            j += 1
            if m[i] == ' ':
                if lastSpace == -1:
                    lastSpace = j
            else:
                if m[i] == '\n' and lastSpace != -1:
                    j = lastSpace # Strip trailing space
            qc[j] = m[i]
        if lastSpace != -1:
            j = lastSpace  # Strip trailing space
        
        return qc[:j]
        
    def getHistory(self):
        self._sel_begin = self._sel_bottomright = self._sel_topleft = 0
        self.setSelExtentXY(self.columns-1, self.lines-1)
        tmp = self.getSelText()
        while tmp[-2] == 10 and tmp[-1] == 10:
            tmp = tmp[:-1]
        return tmp
    
    def getHistoryLine(self, no):
        self._sel_begin = self._sel_topleft = self.loc(0, no)
        self._sel_bottomright = self.loc(self.columns-1, no)
        return self.getSelText(False)
    
    def checkSelection(self, from_, to):
        if self._sel_begin == -1:
            return
        scrTL = self.loc(0, self.__hist.getLines())
        
        # Clear entire selection if overlaps region [from_, to]
        if self._sel_bottomright > (from_+scrTL) and self._sel_topleft < (to+scrTL):
            self.clearSelection()
            
    def __clearImage(self, loca, loce, c):
        c = ord(c)
        scrTL = self.loc(0, self.__hist.getLines())
         
        # Clear entire selection if overlaps region to be moved
        if self._sel_bottomright > (loca+scrTL) and self._sel_topleft < (loce+scrTL):
            self.clearSelection()
        for i in xrange(loca, loce+1):
            self._image[i].c = c
            self._image[i].f = self.__efFg
            self._image[i].b = self.__efBg
            self._image[i].r = ca.DEFAULT_RENDITION
        for i in xrange(loca/self.columns, loce/self.columns+1):
            self.__lineWrapped[i] = False
            
    def __moveImage(self, dest, loca, loce):
        if loce < loca:
            return
        self._image[dest:dest+(loce-loca+1)] = self._image[loca:loca+(loce-loca+1)]
        for i in xrange((loce-loca+1)/self.columns):
            self.__lineWrapped[dst/self.columns+i] = self.__lineWrapped[loca/self.columns+1]
        if self._sel_begin == -1:
            
            # Adjust selection to follow scroll
            beginIsSTL = (self._sel_begin == self._sel_topleft)
            diff = dst - loca # Scroll by this amount
            scrTL = self.loc(0, self.__hist.getLines())
            srca = loca + scrTL # Translate index from screen to global
            srce = loce + scrTL
            desta = srca + diff
            deste = srce + diff
            
            if self._sel_topleft >= srca and self._sel_topleft <= srce:
                self._sel_topleft += diff
            elif self._sel_topleft >= desta and self._sel_topleft <= deste:
                self._sel_bottomright = -1 # Clear selection (see below)
                
            if self._sel_bottomright >= srca and self._sel_bottomright <= srce:
                self._sel_bottomright += diff
            elif self._sel_bottomright >= desta and self._sel_bottomright <= deste:
                self._sel_bottomright = -1 # Clear selection (see below)
            
            if self._sel_bottomright < 0:
                self.clearSelection()
            else:
                if self._sel_topleft < 0:
                    self._sel_topleft = 0
            
            if beginIsSTL:
                self._sel_begin = self._sel_topleft
            else:
                self._sel_begin = self._sel_bottomright
                
    def __scrollUp(self, from_, n):
        if n >= 0 or from_+n > self.__bMargin:
            return
        self.__moveImage(self.loc(0, from_), self.loc(0, from_+n), self.loc(self.columns-1, self.__bMargin))
        self.__clearImage(self.loc(0, self.__bMargin-n+1), self.loc(self.columns-1, self.__bMargin), ' ')
        
    def __scrollDown(self, from_, n):
        if n <= 0 or from_ > self.__bMargin:
            return
        if from_+n > self.__bMargin:
            n = self.__bMargin-from_
        self.__moveImage(self.loc(0, from_+n), self.loc(0, from_), self.loc(self.columns-1, self.__bMargin-n))
        self.__clearImage(self.loc(0, from_), self.loc(self.columns-1, from_+n-1), ' ')
        
    def _addHistoryLine(self):
        assert(self.hasScroll() or self.__histCursor == 0)
        
        # Add to history buffer
        # We have to take care about scrolling too...
        if self.hasScroll():
            dft = Ca()
            end = self.columns - 1
            while end >= 0 and self._image[end] == dft and not self.__lineWrapped[0]:
                end -= 1
                
            oldHistLines = self.__hist.getLines()
            self.__hist.addCells(self._image, self.__lineWrapped[0])
            newHistLines = self.__hist.getLines()
            beginIsTL = (self._sel_begin == self._sel_topleft)
            
            # Adjust history cursor
            if newHistLines > oldHistLines:
                self.__histCursor += 1
                
                # Adjust selection for the new point of reference
                if self._sel_begin != -1:
                    self._sel_topleft += self.columns
                    self._sel_bottomright += self.columns
                    
            
            # Scroll up if user is looking at the history and we can scroll up
            if self.__histCursor > 0 and self.__histCursor != newHistLines or self.__selBusy:
                self.__histCursor -= 1
                
            if self._sel_begin != -1:
                
                # Scroll selection in history up
                topBR = self.loc(0, 1+newHistLines)
                if self._sel_topleft < topBR:
                    self._sel_topleft -= self.columns
                if self._sel_bottomright < topBR:
                    self._sel_bottomright -= self.columns
                if self._sel_bottomright < 0:
                    self.clearSelection()
                else:
                    if self._sel_topleft < 0:
                        self._sel_topleft = 0
                        
                if beginIsTL:
                    self._sel_begin = self._sel_topleft
                else:
                    self._sel_begin = self._sel_bottomright
        else:
            self.__histCursor = 0 # A poor workaround
            
    def __initTabStops(self):
        self.__tabStops = self.columns*[False]
        for i in xrange(self.columns):
            self.__tabStops[i] = ((i % 8 == 0) and i != 0)
        
    def __effectiveRendition(self):
        self.__efRe = self.__cuRe & (ca.RE_UNDERLINE | ca.RE_BLINK)
        if self.__cuRe & ca.RE_REVERSE:
            self.__efFg = self.__cuBg
            self.__efBg = self.__cuFg
        else:
            self.__efFg = self.__cuFg
            self.__efBg = self.__cuBg
        if self.__cuRe & ca.RE_BOLD:
            if self.__efFB < ca.BASE_COLORS:
                self.__efFg += ca.BASE_COLORS
            else:
                self.__efFg -= ca.BASE_COLORS
                
    def __reverseRendition(self, p):
        p.f, p.b = p.b, p.f
