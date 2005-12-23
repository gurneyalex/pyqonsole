# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""Provide the Emulation class.

This class acts as the controler between the Screen class (Model) and
Widget class (View). As Widget uses Qt, Emulation also depends on Qt.
But it is very easy to use another toolkit.

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
@author: Sylvain Thenault
@copyright: 2003, 2005
@organization: CEA-Grenoble
@organization: Logilab
@license: CECILL
"""

__revision__ = '$Id: emulation.py,v 1.20 2005-12-23 09:49:00 syt Exp $'

import qt

from pyqonsole import keytrans
from pyqonsole.screen import Screen


NOTIFYNORMAL = 0
NOTIFYBELL = 1
NOTIFYACTIVITY = 2
NOTIFYSILENCE = 3

BULK_TIMEOUT = 20


class Emulation(qt.QObject):
    """This class acts as the controler between the Screen class (Model) and
    Widget class (View). It's actually a common abstract base class for
    different terminal implementations, and so should be subclassed.

    It is responsible to scan the escapes sequences of the terminal
    emulation and to map it to their corresponding semantic complements.
    Thus this module knows mainly about decoding escapes sequences and
    is a stateless device w.r.t. the semantics.

    It is also responsible to refresh the Widget by certain rules.
    """
    def __init__(self, w):
        super(Emulation, self).__init__()
        self._gui = w
        # 0 = primary, 1 = alternate
        self._screen = [Screen(self._gui.lines, self._gui.columns),
                        Screen(self._gui.lines, self._gui.columns)]
        self._scr = self._screen[0]
        # communicate with widget
        self._connected = False
        # codec
        self._codec = None
        self._decoder = None
        # key translator
        self._key_trans = None
        self.setKeymap(0)
        # bulk handling
        self._bulk_timer = qt.QTimer(self)
        self._bulk_nl_cnt = 0 # bulk new line counter
        self._bulk_in_cnt = 0 # bulk counter
        self.connect(self._bulk_timer, qt.SIGNAL("timeout()"), self._showBulk)
        self.connect(self._gui, qt.PYSIGNAL("changedImageSizeSignal"), self.onImageSizeChange)
        self.connect(self._gui, qt.PYSIGNAL("changedHistoryCursor"), self.onHistoryCursorChange)
        self.connect(self._gui, qt.PYSIGNAL("keyPressedSignal"), self.onKeyPress)
        self.connect(self._gui, qt.PYSIGNAL("beginSelectionSignal"), self.onSelectionBegin)
        self.connect(self._gui, qt.PYSIGNAL("extendSelectionSignal"), self.onSelectionExtend)
        self.connect(self._gui, qt.PYSIGNAL("endSelectionSignal"), self.setSelection)
        self.connect(self._gui, qt.PYSIGNAL("clearSelectionSignal"), self.clearSelection)
        self.connect(self._gui, qt.PYSIGNAL("isBusySelecting"), self.isBusySelecting)
        self.connect(self._gui, qt.PYSIGNAL("testIsSelected"), self.testIsSelected)
        
    def __del__(self):
        self._bulk_timer.stop()
        
    def _setScreen(self, n):
        """change between primary and alternate screen"""
        old = self._scr
        self._scr = self._screen[n]
        if not self._scr is old:
            self._scr.clearSelection()
            old.busy_selecting = False
            
    def setHistory(self, history_type):
        self._screen[0].setScroll(history_type)
        if self._connected:
            self._showBulk()
        
    def history(self):
        return self._screen[0].getScroll()
    
    def setKeymap(self, no):
        self._key_trans = keytrans.find(no)
    
    def keymap(self):
        return self._key_trans
        
    # Interpreting Codes
    # This section deals with decoding the incoming character stream.
    # Decoding means here, that the stream is first seperated into `tokens'
    # which are then mapped to a `meaning' provided as operations by the
    # `Screen' class.

    def onRcvChar(self, c):
        """process application unicode input to terminal"""
        raise NotImplementedError()

    def setMode(self):
        raise NotImplementedError()
    
    def resetMode(self):
        raise NotImplementedError()
    
    def sendString(self, string):
        self.emit(qt.PYSIGNAL("sndBlock"), (s,))
           
    # Keyboard handling
    
    def onKeyPress(self, ev):
        """char received from the gui"""
        raise NotImplementedError()
            
    def onRcvBlock(self, block):
        self.emit(qt.PYSIGNAL("notifySessionState"), (NOTIFYACTIVITY,))
        self._bulkStart()
        self._bulk_in_cnt += 1
        for c in block:
            result = self._decoder.toUnicode(c , 1)
            for char in result:
                self.onRcvChar(char.at(0).unicode())
            if c == '\n':
                self._bulkNewLine()
        self._bulkEnd()
        
    def onSelectionBegin(self, x, y):
        if self._connected:
            self._scr.setSelBeginXY(x, y)
            self._showBulk()
        
    def onSelectionExtend(self, x, y):
        if self._connected:
            self._scr.setSelExtendXY(x, y)
            self._showBulk()
        
    def setSelection(self, preserve_line_break):
        if self._connected:
            text = self._scr.getSelText(preserve_line_break)
            if text is not None:
                self._gui.setSelection(text)
            
    def isBusySelecting(self, busy):
        if self._connected:
            self._scr.busy_selecting = busy
        
    def testIsSelected(self, x, y, ref):
        if self._connected:
            ref.value = self._scr.testIsSelected(x, y)
    
    def clearSelection(self):
        if self._connected:
            self._scr.clearSelection()
            self._showBulk()
    
    def setConnect(self, c):
        self._connected = c
        if self._connected:
            self.onImageSizeChange(self._gui.lines, self._gui.columns)
            self._showBulk()
        else:
            self._scr.clearSelection()
            
    def onImageSizeChange(self, lines, columns):
        """Triggered by image size change of the TEWidget `gui'.

        This event is simply propagated to the attached screens
        and to the related serial line.
        """
        if not self._connected:
            return
        print 'emulation.onImageSizeChange', lines, columns
        self._screen[0].resizeImage(lines, columns)
        self._screen[1].resizeImage(lines, columns)
        self._showBulk()
        # Propagate event to serial line
        self.emit(qt.PYSIGNAL("imageSizeChanged"), (lines, columns))
    
    def onHistoryCursorChange(self, cursor):
        if self._connected:
            self._scr.hist_cursor = cursor
            self._showBulk()
        
    def _setCodec(self, c):
        """coded number, 0=locale, 1=utf8"""
        if c:
            self._codec = qt.QTextCodec.codecForName("utf8")
        else:
            self._codec = qt.QTextCodec.codecForLocale()
        self._decoder = self._codec.makeDecoder()
        
    def _setColumns(self, columns):
        # FIXME This goes strange ways
        # Can we put this straight or explain it at least?
        # XXX moreover no one is connected to this signal...
        self.emit(qt.PYSIGNAL("changeColumns"), (columns,))
        
    def _bulkNewLine(self):
        self._bulk_nl_cnt += 1
        self._bulk_in_cnt = 0  # Reset bulk counter since 'nl' rule applies
        
    def _showBulk(self):
        self._bulk_nl_cnt = 0
        self._bulk_in_cnt = 0
        if self._connected:
            image = self._scr.getCookedImage() # Get the image
            self._gui.setImage(image, self._scr.lines, self._scr.columns) #  Actual refresh
            self._gui.setCursorPos(self._scr.getCursorX(), self._scr.getCursorY())
            # FIXME: Check that we do not trigger other draw event here
            self._gui.setLineWrapped(self._scr.getCookedLineWrapped())
            self._gui.setScroll(self._scr.hist_cursor, self._scr.getHistLines())
            
    def _bulkStart(self):
        if self._bulk_timer.isActive():
            self._bulk_timer.stop()
            
    def _bulkEnd(self):
        if self._bulk_nl_cnt > self._gui.lines or self._bulk_in_cnt > 20:
            self._showBulk()
        else:
            self._bulk_timer.start(BULK_TIMEOUT, True)
            
        
