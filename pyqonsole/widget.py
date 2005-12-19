""" Provide the Widget class.

Visible screen contents

   This class is responsible to map the `image' of a terminal emulation to the
   display. All the dependency of the emulation to a specific GUI or toolkit is
   localized here. Further, this widget has no knowledge about being part of an
   emulation, it simply work within the terminal emulation framework by exposing
   size and key events and by being ordered to show a new image.

   - The internal image has the size of the widget (evtl. rounded up)
   - The external image used in setImage can have any size.
   - (internally) the external image is simply copied to the internal
     when a setImage happens. During a resizeEvent no painting is done
     a paintEvent is expected to follow anyway.

FIXME:
   - 'image' may also be used uninitialized (it isn't in fact) in resizeEvent
   - 'font_a' not used in mouse events
   - add destructor

TODO
   - evtl. be sensitive to `paletteChange' while using default colors.
   - set different 'rounding' styles? I.e. have a mode to show clipped chars?

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003
@organization: CEA-Grenoble
@license: ??



## signals:
##     void keyPressedSignal(QKeyEvent *e)
##     void mouseSignal(int cb, int cx, int cy)
##     void changedImageSizeSignal(int lines, int columns)
##     void changedHistoryCursor(int value)
##     void configureRequest( TEWidget*, int state, int x, int y )

##     void clearSelectionSignal()
##     void beginSelectionSignal( const int x, const int y )
##     void extendSelectionSignal( const int x, const int y )
##     void endSelectionSignal(const bool preserve_line_breaks)
##     void isBusySelecting(bool)
##     void testIsSelected(const int x, const int y, bool &selected /* result */)
"""

__revision__ = '$Id: widget.py,v 1.20 2005-12-19 22:13:31 syt Exp $'

import qt

from pyqonsole.screen import Screen
from pyqonsole.ca import *

# FIXME: the rim should normally be 1, 0 only when running in full screen mode.
rimX = 0 # left/right rim width
rimY = 0 # top/bottom rim high

# width of the scrollbar
SCRWIDTH = 16

SCRNONE = 0
SCRLEFT = 1
SCRRIGHT = 2

# scroll increment used when dragging selection at top/bottom of window.
yMouseScroll = 1

BELLNONE = 0
BELLSYSTEM = 1
BELLVISUAL = 2

#extern unsigned short vt100_graphics[32]

# Dnd
diNone = 0
diPending = 1
diDragging = 2

class dragInfo:
##     def __init__(self, state, start, dragObject):
##       self.state = state
##       self.start = start
##       self.dragObject = dragObject
    state = None
    start = None
    dragObject = None

# Colors ######################################################################

#FIXME: the default color table is in session.C now.
#       We need a way to get rid of this one, here.
BASE_COLOR_TABLE = [
    # The following are almost IBM standard color codes, with some slight
    # gamma correction for the dim colors to compensate for bright X screens.
    # It contains the 8 ansiterm/xterm colors in 2 intensities.
    # Fixme: could add faint colors here, also.
    # normal
    ColorEntry(qt.QColor(0x00,0x00,0x00), 0, 0 ), ColorEntry( qt.QColor(0xB2,0xB2,0xB2), 1, 0 ), # Dfore, Dback
    ColorEntry(qt.QColor(0x00,0x00,0x00), 0, 0 ), ColorEntry( qt.QColor(0xB2,0x18,0x18), 0, 0 ), # Black, Red
    ColorEntry(qt.QColor(0x18,0xB2,0x18), 0, 0 ), ColorEntry( qt.QColor(0xB2,0x68,0x18), 0, 0 ), # Green, Yellow
    ColorEntry(qt.QColor(0x18,0x18,0xB2), 0, 0 ), ColorEntry( qt.QColor(0xB2,0x18,0xB2), 0, 0 ), # Blue,  Magenta
    ColorEntry(qt.QColor(0x18,0xB2,0xB2), 0, 0 ), ColorEntry( qt.QColor(0xB2,0xB2,0xB2), 0, 0 ), # Cyan,  White
    # intensiv
    ColorEntry(qt.QColor(0x00,0x00,0x00), 0, 1 ), ColorEntry( qt.QColor(0xFF,0xFF,0xFF), 1, 0 ),
    ColorEntry(qt.QColor(0x68,0x68,0x68), 0, 0 ), ColorEntry( qt.QColor(0xFF,0x54,0x54), 0, 0 ),
    ColorEntry(qt.QColor(0x54,0xFF,0x54), 0, 0 ), ColorEntry( qt.QColor(0xFF,0xFF,0x54), 0, 0 ),
    ColorEntry(qt.QColor(0x54,0x54,0xFF), 0, 0 ), ColorEntry( qt.QColor(0xFF,0x54,0xFF), 0, 0 ),
    ColorEntry(qt.QColor(0x54,0xFF,0xFF), 0, 0 ), ColorEntry( qt.QColor(0xFF,0xFF,0xFF), 0, 0 )
]

# Note that we use ANSI color order (bgr), while IBMPC color order is (rgb)
#
#   Code        0       1       2       3       4       5       6       7
#   ----------- ------- ------- ------- ------- ------- ------- ------- -------
#   ANSI  (bgr) Black   Red     Green   Yellow  Blue    Magenta Cyan    White
#   IBMPC (rgb) Black   Blue    Green   Cyan    Red     Magenta Yellow  White


# Font ########################################################################

#   The VT100 has 32 special graphical characters. The usual vt100 extended
#   xterm fonts have these at 0x00..0x1f.
#
#   QT's iso mapping leaves 0x00..0x7f without any changes. But the graphicals
#   come in here as proper unicode characters.
#
#   We treat non-iso10646 fonts as VT100 extended and do the requiered mapping
#   from unicode to 0x00..0x1f. The remaining translation is then left to the
#   QCodec.

# assert for i in [0..31] : vt100extended(vt100_graphics[i]) == i.

VT100_GRAPHICS = [
    # 0/8     1/9    2/10    3/11    4/12    5/13    6/14    7/15
    0x0020, 0x25C6, 0x2592, 0x2409, 0x240c, 0x240d, 0x240a, 0x00b0,
    0x00b1, 0x2424, 0x240b, 0x2518, 0x2510, 0x250c, 0x2514, 0x253c,
    0xF800, 0xF801, 0x2500, 0xF803, 0xF804, 0x251c, 0x2524, 0x2534,
    0x252c, 0x2502, 0x2264, 0x2265, 0x03C0, 0x2260, 0x00A3, 0x00b7,
]

## def identicalMap(c):
##     return c

import sys


class Widget(qt.QFrame):
    """a widget representing attributed text"""

    def _print_image(self):
        """debug"""
        print 'begin image ***********'
        for y in xrange(self.lines):
            for x in xrange(self.columns):
                sys.stdout.write(unichr(self.image[self._loc(x, y)].c))
            sys.stdout.write('\n')
        print 'end image ***********'
                
    def _loc(self, x, y):
        return y * self.columns + x
    
    def __init__(self, qapp, parent=None, name=''):
        super(Widget, self).__init__(parent, name)
        # application object
        self._qapp = qapp
        # current session in this widget
        self.current_session = None
        # has blinking cursor enabled
        self.has_blinking_cursor = False
        # hide text in paintEvent
        self.blinking = False
        # has characters to blink
        self.has_blinker = False
        # hide cursor in paintEvent
        self.cursor_blinking = False
        self.blink_t = qt.QTimer(self)        # active when self.has_blinker
        self.blink_cursor_t = qt.QTimer(self) # active when self.has_blinking_cursor        
        # require Ctrl key for drag
        self.ctrldrag = False
        # do we antialias or not
        self.antialias = False
        #self.fixed_font # has fixed pitch
        # height, width, ascend
        self.font_h = self.font_w = self.font_a = 1
        # The offsets are not yet calculated. 
        # Do not calculate these too often to be more smoothly when resizing
        # pyqonsole in opaque mode.
        self.bX = self.bY = 0
        # widget size
        self.lines, self.columns = 1, 1
        self.image = None  # [lines][columns]
        self.image_size = 1 # lines * columns
        
        self.line_wrapped = [] # QBitArray

        self.color_table = [None] * TABLE_COLORS

        self.resizing = False
        self.terminal_size_hint = False
        self.terminal_size_startup = True
        self.mouse_marks = False
  
        self.i_pnt_sel = None # initial selection point
        self.pnt_sel = None   # current selection point
        self.act_sel = 0      # selection state
        self.word_selection_mode = False
        self.line_selection_mode = False
        self.preserve_line_breaks = True
        self.scroll_loc = SCRNONE
        self.word_characters = ":@-./_~"
        self.bell_mode = BELLSYSTEM
        # is set in mouseDoubleClickEvent and deleted
        # after QApplication::doubleClickInterval() delay
        self.possible_triple_click = False
        
        self.m_resize_widget = None # QFrame
        self.m_resize_label = None # QLabel
        self.m_resize_timer = None # QTimer
        self.m_line_spacing = 0

        self.cb = qt.QApplication.clipboard() # QClipboard
        
        self.scrollbar = qt.QScrollBar(self)
        self.scrollbar.setCursor(self.arrowCursor)

        self.drop_text = ''
        self.cursor_rect = None #for quick changing of cursor

        self.connect(self.cb, qt.SIGNAL('selectionChanged()'), self.onClearSelection)
        self.connect(self.scrollbar, qt.SIGNAL('valueChanged(int)'), self.scrollChanged)
        self.connect(self.blink_t, qt.SIGNAL('timeout()'), self.blinkEvent)
        self.connect(self.blink_cursor_t, qt.SIGNAL('timeout()'), self.blinkCursorEvent)

        self.setMouseMarks(True)
        self.setVTFont(qt.QFont("fixed"))
        self.setColorTable(BASE_COLOR_TABLE) # init color table
        self._qapp.installEventFilter(self) #FIXME: see below
        #  QCursor::setAutoHideCursor( self, True )

        # Init DnD ################################
        self.setAcceptDrops(True) # attempt
        dragInfo.state = diNone

        self.setFocusPolicy(self.WheelFocus)

        # We're just a big pixmap, no need to have a background 
        # Speeds up redraws
        self.setBackgroundMode(self.NoBackground)


##     def __del__(self):
##         # FIXME: make proper destructor
##         self._qapp.removeEventFilter( self )
##         #if self.image:
##         #    free(self.image)
                
    def getDefaultBackColor(self):
        return self.color_table[DEFAULT_BACK_COLOR].color

    def getColorTable(self):
        return self.color_table
    def setColorTable(self, table):
        for i in xrange(TABLE_COLORS):
            self.color_table[i] = table[i]
        pm = self.paletteBackgroundPixmap() 
        if not pm:
            self.setPaletteBackgroundColor(self.color_table[DEFAULT_BACK_COLOR].color)
        self.update()

    # FIXME: add backgroundPixmapChanged.

    def setScrollbarLocation(self, loc):
        if self.scroll_loc == loc:
            return # quickly
        self.bY = self.bX = 1
        self.scroll_loc = loc
        self.propagateSize()
        self.update()

    def setScroll(self, cursor, lines):
        self.disconnect(self.scrollbar, qt.PYSIGNAL('valueChanged(int)'), self.scrollChanged)
        self.scrollbar.setRange(0,lines)
        self.scrollbar.setSteps(1, self.lines)
        self.scrollbar.setValue(cursor)
        self.connect(self.scrollbar, qt.PYSIGNAL('valueChanged(int)'), self.scrollChanged)

    def doScroll(self, lines):
        self.scrollbar.setValue(self.scrollbar.value()+lines)

    def blinkingCursor(self):
        return self.has_blinking_cursor
    def setBlinkingCursor(self, blink):
        """Display operation"""
        self.has_blinking_cursor = blink
        if blink and not self.blink_cursor_t.isActive():
            self.blink_cursor_t.start(1000)
        if not blink and self.blink_cursor_t.isActive():
            self.blink_cursor_t.stop()
            if self.cursor_blinking:
                self.blinkCursorEvent()
            else:
                self.cursor_blinking = False
        
    def setCtrlDrag(self, enable):
        self.ctrldrag = enable
        
    def setLineSpacing(self, i):
        self.m_line_spacing = i
        self.setVTFont(self.font()) # Trigger an update.
        
    def lineSpacing(self):
        return self.m_line_spacing


    def emitSelection(self, useXselection, appendReturn):
        """Paste Clipboard by simulating keypress events"""
        qt.QApplication.clipboard().setSelectionMode(useXselection)
        text = qt.QApplication.clipboard().text()
        if appendReturn:
            text.append("\r")
        if not text.isEmpty():
            text.replace(qt.QRegExp("\n"), "\r")
        ev = qt.QKeyEvent(qt.QEvent.KeyPress, 0, -1, 0, text)
        self.emit(qt.PYSIGNAL('keyPressedSignal'), (ev,)) # expose as a big fat keypress event
        self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())
        qt.QApplication.clipboard().setSelectionMode(False)
  
    def emitText(self,  text):
        if not text.isEmpty():
            ev = qt.QKeyEvent(qt.QEvent.KeyPress, 0, -1, 0, text)
            self.emit(qt.PYSIGNAL('keyPressedSignal'), (ev,)) # expose as a big fat keypress event

    def setImage(self, newimg, lines, columns):
        """Display Operation - The image can only be set completely.

        The size of the new image may or may not match the size of the widget.
        """
        pm = self.paletteBackgroundPixmap()
        self.setUpdatesEnabled(False)
        paint = qt.QPainter()
        paint.begin(self)
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        self.has_blinker = False
        cf = cb = cr  = -1 # undefined
        lins = min(self.lines,  max(0, lines))
        cols = min(self.columns,max(0, columns))
        #print 'setimage', lins, cols, self.lines, self.columns, len(self.image), len(newimg)
        for y in xrange(lins):
            if self.resizing: # while resizing, we're expecting a paintEvent
                break
            x = 0
            while x < cols:
                ca = newimg[y*columns + x]
                self.has_blinker |= ca.r & RE_BLINK
                # XXX "is" to be more effective than "==", but depends on screen implementation
                if ca is self.image[self._loc(x, y)]:
                    x += 1
                    continue
                c = ca.c
                if not c:
                    x += 1
                    continue
                disstrU = [c]
                cr = ca.r
                cb = ca.b
                if ca.f != cf:
                    cf = ca.f
                lln = cols - x
                xlen = 1
                for xlen in xrange(1, lln):
                    cal = newimg[y*columns + x + xlen]
                    c = cal.c
                    if not c:
                        continue # Skip trailing part of multi-col chars.
                    if (cal.f != cf or cal.b != cb or cal.r != cr or
                        cal == self.image[self._loc(x + xlen, y)]):
                        break
                    disstrU.append(c)
                unistr = qt.QString(''.join([unichr(i) for i in disstrU]))
                self.drawAttrStr(paint,
                                 qt.QRect(self.bX+tLx+self.font_w*x, self.bY+tLy+self.font_h*y, self.font_w*xlen, self.font_h),
                                 unistr, ca, pm != None, True)
                x += xlen
        self.image = newimg
        self.drawFrame(paint)
        paint.end()
        self.setUpdatesEnabled(True)
        if (self.has_blinker and not self.blink_t.isActive()):
            self.blink_t.start(1000) # 1000 ms
        if (not self.has_blinker and self.blink_t.isActive()):
            self.blink_t.stop()
            self.blinking = False

        if self.resizing and self.terminal_size_hint:
            if self.terminal_size_startup:
                self.terminal_size_startup = False
                return
            if not self.m_resize_widget:
                self.m_resize_widget = qt.QFrame(self)
                f = self.m_resize_widget.font()
                f.setPointSize(f.pointSize()*2)
                f.setBold(True)
                self.m_resize_widget.setFont(f)
                self.m_resize_widget.setFrameShape(self.Raised)
                self.m_resize_widget.setMidLineWidth(4)
                l = qt.QVBoxLayout( self.m_resize_widget, 10)
                self.m_resize_label = qt.QLabel("Size: XXX x XXX", self.m_resize_widget)
                l.addWidget(self.m_resize_label, 1, AlignCenter)
                self.m_resize_widget.setMinimumWidth(self.m_resize_label.fontMetrics().width("Size: XXX x XXX")+20)
                self.m_resize_widget.setMinimumHeight(self.m_resize_label.sizeHint().height()+20)
                self.m_resize_timer = qt.QTimer(self)
                self.connect(self.m_resize_timer, SIGNAL('timeout()'), self.m_resize_widget.hide)
            sizeStr = qt.QString("Size: %1 x %2").arg(columns).arg(lines)
            self.m_resize_label.setText(sizeStr)
            self.m_resize_widget.move((width()-self.m_resize_widget.width())/2,
                                      (height()-self.m_resize_widget.height())/2)
            self.m_resize_widget.show()
            self.m_resize_timer.start(1000, True)

    def setLineWrapped(self, line_wrapped):
        self.line_wrapped = line_wrapped

    def setCursorPos(self, curx, cury):
        """Display Operation - Set XIM Position"""
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        ypos = self.bY + tLy + self.font_h*(cury-1) + self.font_a
        xpos = self.bX + tLx + self.font_w*curx
        self.setMicroFocusHint(xpos, ypos, 0, self.font_h)

    def calcGeometry(self):
        # FIXME: set rimX == rimY == 0 when running in full screen mode.
        self.scrollbar.resize(qt.QApplication.style().pixelMetric(qt.QStyle.PM_ScrollBarExtent),
                              self.contentsRect().height())
        if self.scroll_loc == SCRNONE:
           self.bX = 1
           self.columns = (self.contentsRect().width() - 2 * rimX) / self.font_w
           self.scrollbar.hide()
        elif self.scroll_loc == SCRLEFT:
           self.bX = 1+self.scrollbar.width()
           self.columns = (self.contentsRect().width() - 2 * rimX - self.scrollbar.width()) / self.font_w
           self.scrollbar.move(self.contentsRect().topLeft())
           self.scrollbar.show()
        elif self.scroll_loc ==  SCRRIGHT:
           self.bX = 1
           self.columns = (self.contentsRect().width()  - 2 * rimX - self.scrollbar.width()) / self.font_w
           self.scrollbar.move(self.contentsRect().topRight() - qt.QPoint(self.scrollbar.width()-1,0))
           self.scrollbar.show()
        if self.columns < 1:
            self.columns = 1
        # FIXME: support 'rounding' styles
        self.lines = (self.contentsRect().height() - 2 * rimY ) / self.font_h
  
    def propagateSize(self):
        oldimg = self.image
        oldlin = self.lines
        oldcol = self.columns
        self.makeImage()
        # we copy the old image to reduce flicker
        lins = min(oldlin, self.lines)
        cols = min(oldcol, self.columns)
        if oldimg:
            for lin in xrange(lins):
                self.image[self.columns*lin] = oldimg[oldcol*lin]
        else:
            self.clearImage()
        # NOTE: control flows from the back through the chest right into the eye.
        #      `emu' will call back via `setImage'.
        self.resizing = True
        self.emit(qt.PYSIGNAL('changedImageSizeSignal'), (self.lines, self.columns)) # expose resizeEvent
        self.resizing = False

    def calcSize(self, cols, lins):        
        """calculate the needed size for the widget to get a cols*lins
        characters terminal
        """
        frw = self.width() - self.contentsRect().width()
        frh = self.height() - self.contentsRect().height()
        if self.scroll_loc == SCRNONE:
            scw = 0
        else:
            scw = self.scrollbar.width()
        return qt.QSize(self.font_w*cols + 2*rimX + frw + scw + 2, self.font_h*lins + 2*rimY + frh + 2)


    def sizeHint(self):
        return self.size()

    def setWordCharacters(self, wc):
        self.word_characters = wc

    def setBellMode(self, mode):
        self.bell_mode = mode
    
    def bell(self):
        if self.bell_mode == BELLSYSTEM:
            qt.QApplication.beep()
        if self.bell_mode==BELLVISUAL:
            self.swapColorTable()
            qt.QTimer.singleShot(200, self.swapColorTable)


    def setSelection(self, t):
        # Disconnect signal while WE set the clipboard
        self.cb = qt.QApplication.clipboard()
        self.disconnect(self.cb, qt.SIGNAL('selectionChanged()'), self.onClearSelection)
        self.cb.setSelectionMode(True)
        qt.QApplication.clipboard().setText(t)
        self.cb.setSelectionMode(False)
        qt.QApplication.clipboard().setText(t)
        self.connect(self.cb, qt.SIGNAL('selectionChanged()'), self.onClearSelection)


    def setFont(self, font):
        # ignore font change request if not coming from konsole itself
        pass
    def setVTFont(self, font):
        if not self.antialias:
            font.setStyleStrategy(qt.QFont.NoAntialias)
        qt.QFrame.setFont(self, font)
        self.fontChange(font)

    def setMouseMarks(self, on):
        self.mouse_marks = on
        self.setCursor(on and self.ibeamCursor or self.arrowCursor)

    def setTerminalSizeHint(self, on):
        self.terminal_size_hint = on

    def pasteClipboard(self):
        self.emitSelection(False, False)

    def onClearSelection(self):
        self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())


    # protected ###############################################################

    def styleChange(self, style):
        self.propagateSize()


    def eventFilter(self, obj, e):
        """Keyboard

        FIXME: an `eventFilter' has been installed instead of a `keyPressEvent'
               due to a bug in `QT' or the ignorance of the author to prevent
               repaint events being self.emitted to the screen whenever one leaves
               or reenters the screen to/from another application.
      
         Troll says one needs to change focusInEvent() and focusOutEvent(),
         which would also let you have an in-focus cursor and an out-focus
         cursor like xterm does.

        for the auto-hide cursor feature, I added empty focusInEvent() and
        focusOutEvent() so that update() isn't called.
        For auto-hide, we need to get keypress-events, but we only get them when
        we have focus.
        """
        if (e.type() == qt.QEvent.Accel or
            e.type() == qt.QEvent.AccelAvailable) and self._qapp.focusWidget() == self:
            e.ignore()
            return True
        if obj != self and obj != self.parent(): # when embedded / when standalone
            return False # not us
        if e.type() == qt.QEvent.Wheel:
            qt.QApplication.sendEvent(self.scrollbar, e)
        if e.type() == qt.QEvent.KeyPress:
            self.act_sel = 0 # Key stroke implies a screen update, so TEWidget won't
                             # know where the current selection is.
            if self.has_blinking_cursor:
                self.blink_cursor_t.start(1000)
            if self.cursor_blinking:
                self.blinkCursorEvent()
            else:
                self.cursor_blinking = False
            self.emit(qt.PYSIGNAL('keyPressedSignal'), (e,)) # expose
            # in Qt2 when key events were propagated up the tree 
            # (unhandled? . parent widget) they passed the event filter only once at
            # the beginning. in qt3 self has changed, that is, the event filter is 
            # called each time the event is sent (see loop in qt.QApplication.notify,
            # when internalNotify() is called for KeyPress, whereas internalNotify
            # activates also the global event filter) . That's why we stop propagation
            # here.
            return True
        composeLength = 0
        if e.type() == qt.QEvent.IMStart:
            composeLength = 0
            e.accept()
            return False
        if e.type() == qt.QEvent.IMCompose:
            text = qt.QString()
            if composeLength:
                text.setLength(composeLength)
                for i in xrange(composeLength):
                    text[i] = '\010'
            composeLength = e.text().length()
            text += e.text()
            if not text.isEmpty():
                ke = qt.QKeyEvent(qt.QEvent.KeyPress, 0,-1,0, text)
                self.emit(qt.PYSIGNAL('keyPressedSignal'), (ke,))
            e.accept()
            return False
        if e.type() == qt.QEvent.IMEnd:
            text = qt.QString()
            if composeLength:
                text.setLength(composeLength)
                for i in xrange(composeLength):
                    text[i] = '\010'
            text += e.text()
            if not text.isEmpty():
                ke = qt.QKeyEvent(qt.QEvent.KeyPress, 0,-1,0, text)
                self.emit(qt.PYSIGNAL('keyPressedSignal'), (ke,))
            e.accept()
            return False
        if e.type() == qt.QEvent.Enter:
            self.disconnect(self.cb, qt.PYSIGNAL('dataChanged()'), self.onClearSelection)
        if e.type() == qt.QEvent.Leave:
            self.connect(self.cb, qt.PYSIGNAL('dataChanged()'), self.onClearSelection)
        return qt.QFrame.eventFilter(self,obj, e)

    def drawAttrStr(self, paint, rect, str, attr, pm, clear):
        """Display Operation - attributed string draw primitive"""
        if (attr.r & RE_CURSOR) and self.hasFocus() and (not self.has_blinking_cursor or not self.cursor_blinking):
            fColor = self.color_table[attr.b].color
            bColor = self.color_table[attr.f].color
        else:
            fColor = self.color_table[attr.f].color
            bColor = self.color_table[attr.b].color
        if attr.r & RE_CURSOR:
            self.cursor_rect = rect
        if pm and self.color_table[attr.b].transparent and (not (attr.r & RE_CURSOR) or self.cursor_blinking):
            paint.setBackgroundMode(self.TransparentMode)
            if clear:
                self.erase(rect)
        else:
            if self.blinking:
                paint.fillRect(rect, bColor)
            else:
                paint.setBackgroundMode(self.OpaqueMode)
                paint.setBackgroundColor(bColor)
        if not (self.blinking and (attr.r & RE_BLINK)):
            if (attr.r and RE_CURSOR) and self.cursor_blinking:
                self.erase(rect)
            paint.setPen(fColor)
            paint.drawText(rect.x(),rect.y()+self.font_a, str)
            if (attr.r & RE_UNDERLINE) or self.color_table[attr.f].bold:
                paint.setClipRect(rect)
                if self.color_table[attr.f].bold:
                    paint.setBackgroundMode(self.TransparentMode)
                    paint.drawText(rect.x()+1,rect.y()+self.font_a, str) # second stroke
                if attr.r & RE_UNDERLINE:
                    paint.drawLine(rect.left(), rect.y()+self.font_a+1,
                                   rect.right(),rect.y()+self.font_a+1)
                paint.setClipping(False)
        if (attr.r & RE_CURSOR) and not self.hasFocus():
            if pm and self.color_table[attr.b].transparent:
                self.erase(rect)
                paint.setBackgroundMode(self.TransparentMode)
                paint.drawText(rect.x(),rect.y()+self.font_a, str)
            paint.setClipRect(rect)
            paint.drawRect(rect.x(), rect.y(), rect.width(), rect.height()-self.m_line_spacing)
            paint.setClipping(False)

    def paintEvent(self, pe):
        """
        The difference of this routine vs. the `setImage' is, that the drawing
        does not include a difference analysis between the old and the new
        image. Instead, the internal image is used and the painting bound by the
        PaintEvent box.
        """
        pm = self.paletteBackgroundPixmap()
        self.setUpdatesEnabled(False)
        paint = qt.QPainter()
        paint.begin(self)
        paint.setBackgroundMode(self.TransparentMode)
        # Note that the actual widget size can be slightly larger
        # that the image (the size is truncated towards the smaller
        # number of characters in `resizeEvent'. The paint rectangle
        # can thus be larger than the image, but less then the size
        # of one character.
        rect = pe.rect().intersect(self.contentsRect())
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        lux = min(self.columns-1, max(0, (rect.left()   - tLx - self.bX) / self.font_w))
        luy = min(self.lines-1,   max(0, (rect.top()    - tLy - self.bY) / self.font_h))
        rlx = min(self.columns-1, max(0, (rect.right()  - tLx - self.bX) / self.font_w))
        rly = min(self.lines-1,   max(0, (rect.bottom() - tLy - self.bY) / self.font_h))
        #  if (pm != NULL and self.color_table[image.b].transparent)
        #  self.erase(rect)
        # BL: I have no idea why we need this, and it breaks the refresh.
        #print 'paintEvent', lux, rlx, luy, rly, self.lines, self.columns, len(self.image)
        #self._print_image()
        assert rlx < self.columns, str((rlx, self.columns))
        assert rly < self.lines, str((rly, self.lines))
        for y in xrange(luy, rly+1):
            c = self.image[self._loc(lux, y)].c
            x = lux
            if not c and x:
                x -= 1 # Search for start of multi-col char
            while x <= rlx:
                disstrU = []
                ca = self.image[self._loc(x,y)]
                c = ca.c
                if c:
                    disstrU.append(c)
                cf = ca.f
                cb = ca.b
                cr = ca.r
                xlen = 1
                while (x+xlen <= rlx and
                       self.image[self._loc(x+xlen,y)].f == cf and
                       self.image[self._loc(x+xlen,y)].b == cb and
                       self.image[self._loc(x+xlen,y)].r == cr ):
                    c = self.image[self._loc(x+xlen,y)].c
                    if c:
                        disstrU.append(c)
                    xlen += 1
                if (x+xlen < self.columns) and (not self.image[self._loc(x+xlen,y)].c):
                    xlen += 1 # Adjust for trailing part of multi-column char
                unistr = qt.QString(''.join([unichr(i) for i in disstrU]))
                self.drawAttrStr(paint,
                                 qt.QRect(self.bX+tLx+self.font_w*x, self.bY+tLy+self.font_h*y, self.font_w*xlen, self.font_h),
                                 unistr, ca, pm != None, False)
                x += xlen
        self.drawFrame(paint)
        paint.end()
        self.setUpdatesEnabled(True)

    def resizeEvent(self, ev):
        # see comment in `paintEvent' concerning the rounding.
        # FIXME: could make a routine here; check width(),height()
        assert ev.size().width() == self.width()
        assert ev.size().height() == self.height()
        self.propagateSize()


    def fontChange(self, font):
        fm = qt.QFontMetrics(font) # QFontMetrics fm(font())
        self.font_h = fm.height() + self.m_line_spacing
        # waba TEWidget 1.123:
        # "Base character width on widest ASCII character. Self prevents too wide
        #  characters in the presence of double wide (e.g. Japanese) characters."
        self.font_w = 1
        for i in xrange(128):
            i = chr(i)
            if not i.isalnum():
                continue
            fw = fm.width(i)
            if self.font_w < fw:
                self.font_w = fw
        if self.font_w > 200: # don't trust unrealistic value, fallback to QFontMetrics::maxWidth()
            self.font_w = fm.maxWidth()
        if self.font_w < 1:
            self.font_w = 1
        self.font_a = fm.ascent()
        self.propagateSize()
        self.update()
        
    def frameChanged(self):
        self.propagateSize()
        self.update()


    # Mouse ###################################################################

    #    Three different operations can be performed using the mouse, and the
    #    routines in self section serve all of them:
    #
    #    1) The press/release events are exposed to the application
    #    2) Marking (press and move left button) and Pasting (press middle button)
    #    3) The right mouse button is used from the configuration menu
    #
    #    NOTE: During the marking process we attempt to keep the cursor within
    #    the bounds of the text as being displayed by setting the mouse position
    #    whenever the mouse has left the text area.
    #
    #    Two reasons to do so:
    #    1) QT does not allow the `grabMouse' to confine-to the TEWidget.
    #       Thus a `XGrapPointer' would have to be used instead.
    #    2) Even if so, self would not help too much, since the text area
    #       of the TEWidget is normally not identical with it's bounds.
    #
    #    The disadvantage of the current handling is, that the mouse can visibly
    #    leave the bounds of the widget and is then moved back. Because of the
    #    current construction, and the reasons mentioned above, we cannot do better
    #    without changing the overall construction.
    
    def mouseDoubleClickEvent(self, ev):
        if ev.button() != self.LeftButton:
            return
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        pos = qt.QPoint((ev.x()-tLx-self.bX)/self.font_w,(ev.y()-tLy-self.bY)/self.font_h)
        # pass on double click as two clicks.
        if not self.mouse_marks and not (ev.state() & self.ShiftButton):
            # Send just _ONE_ click event, since the first click of the double click
            # was already sent by the click handler!
            self.emit(qt.PYSIGNAL('mouseSignal'), (0, pos.x()+1, pos.y()+1)) # left button
            return
        self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())
        bgnSel = pos
        endSel = pos
        i = self._loc(bgnSel.x(),bgnSel.y())
        self.i_pnt_sel = bgnSel
        self.i_pnt_sel.setY(bgnSel.y() + self.scrollbar.value())
        self.word_selection_mode = True
        # find word boundaries...
        selClass = self.charClass(self.image[i].c)
        # set the start...
        x = bgnSel.x()
        while ((x>0) or (bgnSel.y()>0 and self.line_wrapped[bgnSel.y()-1])) and self.charClass(self.image[i-1].c) == selClass:
            i -= 1
            if x > 0:
                x -= 1
            else:
                x = self.columns-1
                bgnSel.setY(bgnSel.y() - 1)
        bgnSel.setX(x)
        self.emit(qt.PYSIGNAL('beginSelectionSignal'), (bgnSel.x(), bgnSel.y()))
        # set the end...
        i = self._loc(endSel.x(), endSel.y())
        x = endSel.x()
        while ((x<self.columns-1) or (endSel.y()<self.lines-1 and self.line_wrapped[endSel.y()])) and self.charClass(self.image[i+1].c) == selClass:
            i += 1
            if x < self.columns-1:
                x += 1
            else:
                x = 0
                endSel.setYb(endSel.y() + 1)
        endSel.setX(x)
        self.act_sel = 2 # within selection
        self.emit(qt.PYSIGNAL('extendSelectionSignal'), (endSel.x(), endSel.y()))
        self.emit(qt.PYSIGNAL('endSelectionSignal'), (self.preserve_line_breaks,))
        self.possible_triple_click=True
        qt.QTimer.singleShot(qt.QApplication.doubleClickInterval(), self.tripleClickTimeout)
    
    def mousePressEvent(self, ev):
        if self.possible_triple_click and ev.button() == self.LeftButton:
            self.mouseTripleClickEvent(ev)
            return
        if not self.contentsRect().contains(ev.pos()):
            return
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        self.line_selection_mode = False
        self.word_selection_mode = False
        pos = qt.QPoint((ev.x()-tLx-self.bX+(self.font_w/2))/self.font_w,(ev.y()-tLy-self.bY)/self.font_h)
        if ev.button() == self.LeftButton:
            self.emit(qt.PYSIGNAL('isBusySelecting'), (True,)) # Keep it steady...
            # Drag only when the Control key is hold
            selected = False
            # The receiver of the testIsSelected() signal will adjust 
            # 'selected' accordingly.
            self.emit(qt.PYSIGNAL('testIsSelected'), (pos.x(), pos.y(), selected))
            if (not self.ctrldrag or ev.state() & self.ControlButton) and selected:
                # The user clicked inside selected text
                dragInfo.state = diPending
                dragInfo.start = ev.pos()
            else:
                # No reason to ever start a drag event
                dragInfo.state = diNone
                self.preserve_line_breaks = not (ev.state() & self.ControlButton)
                if self.mouse_marks or (ev.state() & self.ShiftButton):
                    self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())
                    pos.setY(pos.y() + self.scrollbar.value())
                    self.i_pnt_sel = self.pnt_sel = pos
                    self.act_sel = 1 # left mouse button pressed but nothing selected yet.
                    self.grabMouse() # handle with care!
                else:
                    self.emit(qt.PYSIGNAL('mouseSignal'), ( 0, (ev.x()-tLx-self.bX)/self.font_w +1, (ev.y()-tLy-self.bY)/self.font_h +1)) # Left button
        elif ev.button() == self.MidButton:
            if self.mouse_marks or (not self.mouse_marks and (ev.state() & self.ShiftButton)):
                self.emitSelection(True, ev.state() & self.ControlButton)
            else:
                self.emit(qt.PYSIGNAL('mouseSignal'), (1, (ev.x()-tLx-self.bX)/self.font_w +1, (ev.y()-tLy-self.bY)/self.font_h +1))
        elif ev.button() == self.RightButton:
            if self.mouse_marks or (ev.state() & self.ShiftButton):
                self.emit(qt.PYSIGNAL('configureRequest'), (self, ev.state()&(self.ShiftButton|self.ControlButton), ev.x(), ev.y()))
            else:
                self.emit(qt.PYSIGNAL('mouseSignal'), (2, (ev.x()-tLx-self.bX)/self.font_w +1, (ev.y()-tLy-self.bY)/self.font_h +1))

    def mouseReleaseEvent(self, ev):
        if ev.button() == self.LeftButton:
            self.emit(qt.PYSIGNAL('isBusySelecting'), (False,)) # Ok.. we can breath again.
            if dragInfo.state == diPending:
                # We had a drag event pending but never confirmed.  Kill selection
                self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())
            else:
                if self.act_sel > 1:
                    self.emit(qt.PYSIGNAL('endSelectionSignal'), (self.preserve_line_breaks,))
                self.act_sel = 0
                #FIXME: emits a release event even if the mouse is
                #       outside the range. The procedure used in `mouseMoveEvent'
                #       applies here, too.
                tL  = self.contentsRect().topLeft()
                tLx = tL.x()
                tLy = tL.y()
                if not self.mouse_marks and not (ev.state() & self.ShiftButton):
                    self.emit(qt.PYSIGNAL('mouseSignal'), (3, # release
                                                           (ev.x()-tLx-self.bX)/self.font_w + 1,
                                                           (ev.y()-tLy-self.bY)/self.font_h + 1))
                self.releaseMouse()
            dragInfo.state = diNone
        if not self.mouse_marks and ((ev.button() == self.RightButton and not (ev.state() & self.ShiftButton))
                                     or ev.button() == self.MidButton):
            tL  = self.contentsRect().topLeft()
            tLx = tL.x()
            tLy = tL.y()
            self.emit(qt.PYSIGNAL('mouseSignal'), (3, (ev.x()-tLx-self.bX)/self.font_w +1, (ev.y()-tLy-self.bY)/self.font_h +1))
            self.releaseMouse()
    
    def mouseMoveEvent(self, QMouseEvent):
        # for auto-hiding the cursor, we need mouseTracking
        ev = QMouseEvent
        if ev.state() == self.NoButton:
            return
        if dragInfo.state == diPending:
            # we had a mouse down, but haven't confirmed a drag yet
            # if the mouse has moved sufficiently, we will confirm
        #   int distance = KGlobalSettings::dndEventDelay();
        #   int distance = 0; # FIXME
        #   if ( ev.x() > dragInfo.start.x() + distance or ev.x() < dragInfo.start.x() - distance or
        #        ev.y() > dragInfo.start.y() + distance or ev.y() < dragInfo.start.y() - distance) {
              # we've left the drag square, we can start a real drag operation now
        #      emit isBusySelecting(False); # Ok.. we can breath again.
        #      emit clearSelectionSignal();
        #      doDrag();
        #    }
            return
        elif dragInfo.state == diDragging:
            # self isn't technically needed because mouseMoveEvent is suppressed during
            # Qt drag operations, replaced by dragMoveEvent
            return
        if self.act_sel == 0:
            return
        # don't extend selection while pasting
        if ev.state() & self.MidButton:
            return
        #if ( not self.contentsRect().contains(ev.pos()) ) return;
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        scroll = self.scrollbar.value()
        # we're in the process of moving the mouse with the left button pressed
        # the mouse cursor will kept catched within the bounds of the text in
        # self widget.
        # Adjust position within text area bounds. See FIXME above.
        pos = ev.pos()
        if pos.x() < tLx+self.bX:
            pos.setX(tLx+self.bX)
        if pos.x() > tLx+self.bX+self.columns*self.font_w-1:
            pos.setX(tLx+self.bX+self.columns*self.font_w)
        if pos.y() < tLy+self.bY:
            pos.setY(tLy+self.bY)
        if pos.y() > tLy+self.bY+self.lines*self.font_h-1:
            pos.setY(tLy+self.bY+self.lines*self.font_h-1)
        # check if we produce a mouse move event by self
        if pos != ev.pos():
            cursor().setPos(mapToGlobal(pos))
        if pos.y() == tLy+self.bY+self.lines*self.font_h-1:
            self.scrollbar.setValue(self.scrollbar.value()+yMouseScroll) # scrollforward
        if pos.y() == tLy+self.bY:
            self.scrollbar.setValue(self.scrollbar.value()-yMouseScroll) # scrollback
        here = qt.QPoint((pos.x()-tLx-self.bX+(self.font_w/2))/self.font_w,(pos.y()-tLy-self.bY)/self.font_h)
        self.i_pnt_selCorr = self.i_pnt_sel
        self.i_pnt_selCorr.setY(self.i_pnt_selCorr.y() - self.scrollbar.value())
        self.pnt_selCorr = self.pnt_sel
        self.pnt_selCorr.setY(self.pnt_selCorr.y() - self.scrollbar.value())
        swapping = False
        if self.word_selection_mode:
            # Extend to word boundaries
            left_not_right = (here.y() < self.i_pnt_selCorr.y() or
                              here.y() == self.i_pnt_selCorr.y() and here.x() < self.i_pnt_selCorr.x())
            old_left_not_right = (self.pnt_selCorr.y() < self.i_pnt_selCorr.y() or
                                  self.pnt_selCorr.y() == self.i_pnt_selCorr.y() and self.pnt_selCorr.x() < self.i_pnt_selCorr.x())
            swapping = left_not_right != old_left_not_right
            # Find left (left_not_right ? from here : from start)
            left = left_not_right and here or self.i_pnt_selCorr
            i = self._loc(left.x(),left.y())
            if i >= 0 and i <= self.image_size:
                selClass = self.charClass(self.image[i].c)
                while ((left.x()>0) or (left.y()>0 and self.line_wrapped[left.y()-1])) and self.charClass(self.image[i-1].c) == selClass:
                    i -= 1
                    if left.x() > 0:
                        left.setX(left.x() - 1)
                    else:
                        left.setX(self.columns-1)
                        left.setY(left.y() - 1)
            # Find left (left_not_right ? from start : from here)
            right = left_not_right and self.i_pnt_selCorr or here
            i = self._loc(right.x(),right.y())
            if i >= 0 and i <= self.image_size:
                selClass = self.charClass(self.image[i].c)
                while ((right.x()<self.columns-1) or (right.y()<self.lines-1 and self.line_wrapped[right.y()])) and self.charClass(self.image[i+1].c) == selClass:
                    i += 1
                    if right.x() < self.columns-1:
                        right.setX(right.x() + 1)
                    else:
                        right.setX(0)
                        right.setY(right.y() + 1)
            # Pick which is start (ohere) and which is extension (here)
            if left_not_right:
                here, ohere = left, right
            else:
                here, ohere = right, left
            ohere.setX(ohere.x() + 1)
        if self.line_selection_mode:
            # Extend to complete line
            above_not_below = here.y() < self.i_pnt_selCorr.y()
            #    bool old_above_not_below = ( self.pnt_selCorr.y() < self.i_pnt_selCorr.y() )
            swapping = True # triple click maybe selected a wrapped line
            above = above_not_below and here or self.i_pnt_selCorr
            below = above_not_below and self.i_pnt_selCorr or here
            while above.y() > 0 and self.line_wrapped[above.y()-1]:
                above.setY(above.y() - 1)
            while below.y() < self.lines-1 and self.line_wrapped[below.y()]:
                below.setY(below.y() + 1)
            above.setX(0)
            below.setX(self.columns-1)
            # Pick which is start (ohere) and which is extension (here)
            if above_not_below:
                here, ohere = above, below
            else:
                here, ohere = below, above
            ohere.setX(ohere.x() + 1)
        offset = 0
        if not self.word_selection_mode and not self.line_selection_mode:
            left_not_right = (here.y() < self.i_pnt_selCorr.y() or
                              here.y() == self.i_pnt_selCorr.y() and here.x() < self.i_pnt_selCorr.x())
            old_left_not_right = (self.pnt_selCorr.y() < self.i_pnt_selCorr.y() or
                                  self.pnt_selCorr.y() == self.i_pnt_selCorr.y() and self.pnt_selCorr.x() < self.i_pnt_selCorr.x())
            swapping = left_not_right != old_left_not_right
            # Find left (left_not_right ? from here : from start)
            left = left_not_right and here or self.i_pnt_selCorr
            # Find left (left_not_right ? from start : from here)
            right = left_not_right and self.i_pnt_selCorr or here
            if right.x() > 0:
                i = self._loc(right.x(),right.y())
                if i >= 0 and i <= self.image_size:
                    selClass = self.charClass(self.image[i-1].c)
                    if selClass == ' ':
                        while (right.x() < self.columns-1 and self.charClass(self.image[i+1].c) == selClass and (right.y()<self.lines-1) and not self.line_wrapped[right.y()]):
                            i += 1
                            right.setX(right.x() + 1)
                        if right.x() < self.columns-1:
                            right = left_not_right and self.i_pnt_selCorr or here
                        else:
                            # will be balanced later because of offset=-1
                            right.setX(right.x() + 1)
            # Pick which is start (ohere) and which is extension (here)
            if left_not_right:
                here, ohere = left, right
                offset = 0
            else:
                here, ohere = right, left
                offset = -1
        if here == self.pnt_selCorr and scroll == self.scrollbar.value():
            return # not moved
        if here == ohere:
            return # It's not left, it's not right.
        if self.act_sel < 2 or swapping:
            self.emit(qt.PYSIGNAL('beginSelectionSignal'), (ohere.x()-1-offset, ohere.y()))
        self.act_sel = 2 # within selection
        self.pnt_sel = here
        self.pnt_sel.setY(self.pnt_sel.y() + self.scrollbar.value())
        self.emit(qt.PYSIGNAL('extendSelectionSignal'), (here.x() + offset, here.y()))
        
    def mouseTripleClickEvent(self, ev):
        tL  = self.contentsRect().topLeft()
        tLx = tL.x()
        tLy = tL.y()
        self.i_pnt_sel = qt.QPoint((ev.x()-tLx-self.bX)/self.font_w,(ev.y()-tLy-self.bY)/self.font_h)
        self.emit(qt.PYSIGNAL('clearSelectionSignal'), ())
        self.line_selection_mode = True
        self.word_selection_mode = False
        self.act_sel = 2 # within selection
        while self.i_pnt_sel.y()>0 and self.line_wrapped[self.i_pnt_sel.y()-1]:
            self.i_pnt_sel.setY(self.i_pnt_sel.y() - 1)
        self.emit(qt.PYSIGNAL('beginSelectionSignal'), (0, self.i_pnt_sel.y()))
        while self.i_pnt_sel.y()<self.lines-1 and self.line_wrapped[self.i_pnt_sel.y()]:
            self.i_pnt_sel.setY(self.i_pnt_sel.y() + 1)
        self.emit(qt.PYSIGNAL('extendSelectionSignal'), (self.columns-1, self.i_pnt_sel.y()))
        self.emit(qt.PYSIGNAL('endSelectionSignal'), (self.preserve_line_breaks,))
        self.i_pnt_sel.setY(self.i_pnt_sel.y() + self.scrollbar.value())


    def focusInEvent(self, ev):
        """*do* erase area, to get rid of the hollow cursor rectangle"""
        self.repaint(self.cursor_rect, True)
        
    def focusOutEvent(self, ev):
        """don't erase area"""
        self.repaint(self.cursor_rect, False)

    def focusNextPrevChild(self, next):
        if next:
            return False # Self disables changing the active part in konqueror
                         # when pressing Tab
        return qt.QFrame.focusNextPrevChild(self, next)


    def charClass(self, ch):
        qch = qt.QChar(ch)
        if qch.isSpace(): return ' '
        if qch.isLetterOrNumber() or self.word_characters.contains(qch, False):
            return 'a'
        # Everything else is weird
        return 1

    def clearImage(self):
        """initialize the image, for internal use only"""
        for y in xrange(self.lines):
            for x in xrange(self.columns):
                self.image[self._loc(x,y)].c = 0xff #' '
                self.image[self._loc(x,y)].f = 0xff #DEFAULT_FORE_COLOR
                self.image[self._loc(x,y)].b = 0xff #DEFAULT_BACK_COLOR
                self.image[self._loc(x,y)].r = 0xff #DEFAULT_RENDITION

    def scrollChanged(self, value):
        self.emit(qt.PYSIGNAL('changedHistoryCursor'), (self.scrollbar.value(),)) # expose

    def blinkEvent(self):
        """Display operation"""
        self.blinking = not self.blinking
        self.repaint(False)

    def blinkCursorEvent(self):
        self.cursor_blinking = not self.cursor_blinking
        self.repaint(self.cursor_rect, False)

    # private #################################################################

    def makeImage(self):
        # FIXME: rename 'calcGeometry?
        self.calcGeometry()
        self.image = [Ca() for i in xrange(self.lines * self.columns)]
        self.image_size = self.lines*self.columns;
        #self.clearImage() not needed due to default values of Ca()

    def swapColorTable(self):
        color = self.color_table[1]
        self.color_table[1] = self.color_table[0]
        self.color_table[0]= color
        self.update()
    
    def tripleClickTimeout(self):
        """resets self.possible_triple_click"""
        self.possible_triple_click = False
