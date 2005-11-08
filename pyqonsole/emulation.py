""" Provide the Emulation class.

This class acts as the controler between the Screen class (Model) and
Widget class (View). As Widget uses Qt, Emulation also depends on Qt.
But it is very easy to use another toolkit.

Mediator between Widget and Screen.

   This class is responsible to scan the escapes sequences of the terminal
   emulation and to map it to their corresponding semantic complements.
   Thus this module knows mainly about decoding escapes sequences and
   is a stateless device w.r.t. the semantics.

   It is also responsible to refresh the Widget by certain rules.

A note on refreshing

   Although the modifications to the current screen image could immediately
   be propagated via `Widget' to the graphical surface, we have chosen
   another way here.

   The reason for doing so is twofold.

   First, experiments show that directly displaying the operation results
   in slowing down the overall performance of emulations. Displaying
   individual characters using X11 creates a lot of overhead.

   Second, by using the following refreshing method, the screen operations
   can be completely separated from the displaying. This greatly simplifies
   the programmer's task of coding and maintaining the screen operations,
   since one need not worry about differential modifications on the
   display affecting the operation of concern.

   We use a refreshing algorithm here that has been adoped from rxvt/kvt.

   By this, refreshing is driven by a timer, which is (re)started whenever
   a new bunch of data to be interpreted by the emulation arives at `onRcvBlock'.
   As soon as no more data arrive for `BULK_TIMEOUT' milliseconds, we trigger
   refresh. This rule suits both bulk display operation as done by curses as
   well as individual characters typed.
   (BULK_TIMEOUT < 1000 / max characters received from keyboard per second).

   Additionally, we trigger refreshing by newlines comming in to make visual
   snapshots of lists as produced by `cat', `ls' and likely programs, thereby
   producing the illusion of a permanent and immediate display operation.

   As a sort of catch-all needed for cases where none of the above
   conditions catch, the screen refresh is also triggered by a count
   of incoming bulks (`bulk_incnt').

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003
@organization: CEA-Grenoble
@license: ??
"""


import qt

from keytrans import KeyTrans
from screen import Screen
#from widget import Widget

NOTIFYNORMAL = 0
NOTIFYBELL = 1
NOTIFYACTIVITY = 2
NOTIFYSILENCE = 3

BULK_TIMEOUT = 20


class Emulation(qt.QObject):
    """ Emulation class.
    """
    def __init__(self, w):
        """ Init the Emulation object.
        """
        super(Emulation, self).__init__()
        self._gui = w
        self._screen = [Screen(self._gui.lines, self._gui.columns),
                        Screen(self._gui.lines, self._gui.columns)]
        self._scr = self._screen[0]
        self._connected = False
        self._listenTokenPress = False
        self._codec = None
        self._decoder = None
        self._keyTrans = KeyTrans()
        self.__bulkTimer = qt.QTimer()
        self.__bulkNlCnt = 0 # Bulk new line counter
        self.__bulkInCnt = 0 # Bulk counter
        self.__findPos = -1
        
        self.connect(self.__bulkTimer, qt.SIGNAL("timeout()"), self__showBulk)
        self.connect(self._gui, qt.SIGNAL("changedImageSizedSignal(int, int)"), self.onImageSizeChange)
        self.connect(self._gui, qt.SIGNAL("changedHistoryCursor(int)"), self.onHistoryCursorChange)
        self.connect(self._gui, qt.SIGNAL("keyPressedSignal(QKeyEvent*)"), self.onKeyPress)
        self.connect(self._gui, qt.SIGNAL("beginSelectionSignal(const int, const int)", self.onSelectionBegin))
        self.connect(self._gui, qt.SIGNAL("extendSelectionSignal(const int, const int)", self.onSelectionExtend))
        self.connect(self._gui, qt.SIGNAL("endSelectionSignal(const bool)", self.setSelection))
        self.connect(self._gui, qt.SIGNAL("clearSelectionSignal()", self.clearSelection))
        self.connect(self._gui, qt.SIGNAL("isBusySelecting(bool)", self.isBusySelecting))
        self.connect(self._gui, qt.SIGNAL("testIsSelected(const int, const int, bool &)", self.testIsSelected))
        
        self.setKeymap(0)
        
    def __del__(self):
        self.__bulkTimer.stop()
        
    def _setScreen(self, n):
        """ Change between primary and alternate screen.
        """
        old = self._scr
        scr = self._screen[n&1]
        if scr != old:
            old.setBusySelecting(False)
            
    def setHistory(self, type_):
        self._screen[0].setScroll(type_)
        if not self._connected:
            return
        self.__showBulk()
        
    def history(self):
        return self._screen[0].getScroll()
    
    def _setCodec(self, c):
        if c:
            self._codec = qt.QTextCodec.codecForName("utf8")
        else:
            self._codec = qt.QTextCodec.codecForLocale()
        self._decoder = self._codec.makeDecoder()
        
    def setKeymap(self, no):
        #self._keyTrans = KeyTrans.find(no)
        pass
        
    def setKeyMapById(self, id):
        #self._keyTrans = KeyTrans.findById(id)
        pass
    
    def keymap(self):
        return self._keyTrans.id()
    
    def keymapNo(self):
        return self._keyTrans.num()
        
    # Interpreting Codes
    # This section deals with decoding the incoming character stream.
    # Decoding means here, that the stream is first seperated into `tokens'
    # which are then mapped to a `meaning' provided as operations by the
    # `Screen' class.

    def onRcvChar(self, c):
        """ Process application unicode input to terminal.
        
        This is a trivial scanner.
        """
        c = c & 0xff
        if c == '\b':
            self._scr.backSpace()
        elif c == '\t':
            self._scr.tabulate()
        elif c == '\n':
            self._scr.newLine()
        elif c == '\r':
            self._scr.return_()
        elif ord(c) == 0x07:
            if self._connected:
                self._gui.bell()
            self.emit(qt.PYSIGNAL("notifySessionState(int)", NOTIFYBELL))
        else:
           self._scr.showCharacter()

    def setMode(self):
        raise NotImplementedError
    
    def resetMode(self):
        raise NotImplementedError
    
    def sendString(self, str_):
        raise NotImplementedError
           
    # Keyboard handling
    
    def onKeyPress(self, ev):
        if not self._listenTokenPress: # Someone else gets the keys
            return
        
        self.emit(qt.PYSIGNAL("notifySessionState(int)", NOTIFYNORMAL))
        if self._scr.getHistCursor() != self._scr.getHistLines() and not ev.text().isEmpty():
            self._scr.setHistCursor(self._scr.getHistLines())
        if not ev.text().isEmpty:
            
            # A block og text
            # Note that the text is proper unicode. We should do a conversion here,
            # but since this routine will never be used, we simply emit plain ascii.
            self.emit(qt.PYSIGNAL("sndBlock(const char*,int)"), (ev.text().ascii(), ev.text().length()))
        elif ev.ascii() > 0:
            self.emit(qt.PYSIGNAL("sndBlock(const char*,int)"), (ev.ascii(), 1))
            
    def onRcvBlock(self, s, len_):
        self.emit(qt.PYSIGNAL("notifySessionState(int)", NOTIFYACTIVITY))
        
        self.__bulkStart()
        self.__bulkInCnt += 1
        for i in xrange(len_):
            result = self._decoder.toUnicode(s[i], 1)
            for j in xrange(result.length()):
                self.onRcvChar(result[j].unicode())
            if s[i] == '\n':
                self.__bulkNewLine()
        self.__bulkEnd()
        
    def onSelectionBegin(self, x, y):
        if not self._connected:
            return
        self._scr.setSelBegin(x,y)
        self.__showBulk()
        
    def onSelectionExtend(self, x, y):
        if not self._connected:
            return
        self._scr.setSelExtendXY(x,y)
        self.__showBulk()
        
    def setSelection(self, preserveLineBreak):
        if not self._connected:
            return
        t = self._scr.getSelText(preserveLineBreak)
        if not t.isNull():
            self._gui.setSelection(t)
            
    def isBusySelecting(self, busy):
        if not self._connected:
            return
        self._scr.setBusySelecting(busy)
        
    def testIsSelected(self, x, y):
        if not self._connected:
            return
        return self._scr.testIsSelected(x, y)
    
    def clearSelection(self):
        if not self._connected:
            return
        self._scr.clearSelection()
        self.__showBulk()
        
    def streamHistory(self, stream):
        #stream << self.__scr.getHistory() # << not implemented yest. Find another solution
        pass
    
    def findTextBegin(self):
        self.__findPos = -1
        
    def findTextNext(self, str_, forward, caseSensitive):
        pos = -1
        if forward:
            if self.__findPos == -1:
                start = 0
            else:
                start = self.__finPos+1
            for i in xrange(start, self._scr.getHistLines()+self._scr.getLines()):
                string = self._scr.getHistoryLine(i)
                pos = string.find(str_, 0) #, caseSensitive)
                if pos == -1:
                    self.__findPos = i
                    if i > self._scr.getHistLines():
                        self._scr.setHistCursor(self._scr.getHistLines())
                    else:
                        self._scr.setHistCursor(i)
                    self.__showBulk()
                    return True
        else:
            if self.__findPos == -1:
                start = self._scr.getHistLines()+self._scr.getLines()
            else:
                start = self.__finPos-1
            for i in xrange(start, -1, -1):
                string = self._scr.getHistoryLine(i)
                pos = string.find(str_, 0) #, caseSensitive)
                if pos == -1:
                    self.__findPos = i
                    if i > self._scr.getHistLines():
                        self._scr.setHistCursor(self._scr.getHistLines())
                    else:
                        self._scr.setHistCursor(i)
                    self.__showBulk()
                    return True
           
        return False
    
    def __bulkNewLine(self):
        self.__bulkNlCnt += 1
        self.__bulkInCnt = 0  # Reset bulk counter since 'nl' rule applies
        
    def __showBulk(self):
        self.__bulkNlCnt = 0
        self.__bulkInCnt = 0
        if self._connected:
            image = self._scr.getCookedImage() # Get the image
            self._gui.setImage(image, self._scr.getLines(), self._scr.getColumns()) #  Actual refresh
            self._gui.setCursorPos(self._scr.getCursorX(), self._scr.getCursorY())
            
            # Check that we do not trigger other draw event here
            self._gui.setLineWrapped(self._scr.getCookedLineWrapped())
            self._gui.setScroll(self._scr.getHistCursor(), self._scr.getHistLines())
            
    def __bulkStart(self):
        if self.__bulkTimer.isActive():
            self.__bulkTimer.stop()
            
    def __bulkEnd(self):
        if self.__bulkNlCnt > self._gui.lines or self.__bulkInCnt > 20:
            self.__showBulk()
        else:
            self.__bulkTimer.start(BULK_TIMEOUT, True)
            
    def setConnect(self, c):
        self._connected = c
        if self._connected:
            self.onImageSizeChange(self._gui.lines, elf._gui.columns)
            self.__showBulk()
        else:
            self._scr.clearSelection()

    def setListenToKeyPress(self, l):
        self._listenTokenPress = l
            
    def onImageSizeChange(self, lines, columns):
        """Triggered by image size change of the TEWidget `gui'.

        This event is simply propagated to the attached screens
        and to the related serial line.
        """
        if not self._connected:
            return
        self._screen[0].resizeImage(lines, columns)
        self._screen[1].resizeImage(lines, columns)
        self.__showBulk()
        
        # Propagate event to serial line
        self.emit(qt.PYSIGNAL("imageSizeChanged(int, int)", (lines, columns)))
    
    def onHistoryCursorChange(self, cursor):
        if not self._connected:
            return
        self._scr.setHistCursor(cursor)
        self.__showBulk()
        
    def _setColumns(self, columns):
        
        # This goes strange ways
        # Can we put this straight or explain it at least?
        self.emit(qt.PYSIGNAL("changeColumns(int)", (columns)))
        
        