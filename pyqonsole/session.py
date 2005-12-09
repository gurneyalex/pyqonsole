# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""Provides the Session class. Sessions are combinations of PtyProcess and
Emulation.

The stuff in here does not really belong to the terminal emulation framework. It
serves it's duty by providing a single reference to TEPTy/Emulation pairs. In
fact, it is only there to demonstrate one of the abilities of the framework:
multible sessions.

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Sylvain Thenault
@copyright: 2003, 2005
@organization: Logilab
@license: CECILL
"""

__revision__ = '$Id: session.py,v 1.3 2005-12-09 18:02:14 syt Exp $'

import os

import qt

from pyqonsole import pty_, emulation, emuVt102


SILENCE_TIMEOUT = 10000 # milliseconds

class Session(qt.QObject):
    """A Session is a combination of one PTyProcess and one Emulation instances
    """

    def __init__(self, w, pgm, args, term, sessionid='session-1', cwd=None):
        super(Session, self).__init__()
        self.monitor_activity = False
        self.__monitor_silence = False # see the property below
        self.master_mode = False
        # FIXME: using the indices here is propably very bad. We should use a
        # persistent reference instead.
        self.schema_no = 0
        self.font_no = 3
        self.app_id = "qonsole"
        self.icon_name = 'openterm'
        self.icon_text = 'qonsole'
        self.state_icon_name = ''
        self.title = ''
        self.user_title = ''
        self.te = w
        self.pgm = pgm
        self.args = args
        self.term = term
        self.session_id = sessionid
        self.cwd = cwd
        
        self.sh = pty_.PtyProcess()
        self.em = emuVt102.EmuVt102(self.te)
        self.monitor_timer = qt.QTimer(self)

        self.sh.setSize(self.te.lines, self.te.columns) # not absolutely necessary
        
        self.connect(self.sh, qt.PYSIGNAL('block_in'), self.em.onRcvBlock)
        self.connect(self.em, qt.PYSIGNAL('ImageSizeChanged'), self.sh.setSize)
        self.connect(self.em, qt.PYSIGNAL('sndBlock'), self.sh.sendBytes)
        self.connect(self.em, qt.PYSIGNAL('changeTitle'), self.setUserTitle)
        self.connect(self.em, qt.PYSIGNAL('notifySessionState'), self.notifySessionState)
        self.connect(self.monitor_timer, qt.SIGNAL('timeout()'), self.monitorTimerDone)
        self.connect( self.sh, qt.PYSIGNAL('done'), self.done)

    def __del__(self):
        self.disconnect(self.sh, qt.PYSIGNAL('done'), self.done)

    def setMonitorSilence(self, monitor):
        if self.__monitor_silence == monitor:
            return
        self.__monitor_silence = monitor
        if monitor:
            self.monitor_timer.start(SILENCE_TIMEOUT, True)
        else:
            self.monitor_timer.stop()
    def getMonitorSilence(self):
        return self.__monitor_silence
    monitor_silence = property(getMonitorSilence, setMonitorSilence)

    
    def run(self):
        cwd_save = os.getcwd()
        if self.cwd:
            os.chdir(self.cwd)
        self.sh.run(self.pgm, self.args, self.term, True)
        if self.cwd:
            os.chdir(cwd_save)
        self.sh.setWriteable(False) # We are reachable via kwrited XXX not needed by pyqonsole ?


    def setUserTitle(self, what, caption):
        """
        what=0 changes title and icon
        what=1 only icon
        what=2 only title
        """
        if what in (0, 2):
            self.user_title = caption
        if what in (0, 1):
            self.icon_text = caption
        self.emit(qt.PYSIGNAL('updateTitle'), ())

    def fullTitle(self):
        if self.user_title:
            return '%s - %s' % (self.user_title, self.title)
        return self.title

    def testAndSetStateIconName(self, newname):
        if (newname != self.state_icon_name):
            self.state_icon_name = newname
            return True
        return False


    def monitorTimerDone(self):
        self.emit(qt.PYSIGNAL('notifySessionState'), (emulation.NOTIFYSILENCE,))
        self.monitor_timer.start(SILENCE_TIMEOUT, True)

    def notifySessionState(self, state):
        if state == emulation.NOTIFYACTIVITY:
            if self.monitor_silence:
                self.monitor_timer.stop()
                self.monitor_timer.start(SILENCE_TIMEOUT, True)
            if not self.monitor_activity:
                return
        self.emit(qt.PYSIGNAL('notifySessionState'), (state,))

    def done(self, status):
        self.emit(qt.PYSIGNAL('done'), (self, status,))

    def terminate(self):
        # XXX
        #del self
        pass

    def sendSignal(self, signal):
        return self.sh.kill(signal)

    def setConnect(self, connected):
        self.em.setConnect(connected)
        self.em.setListenToKeyPress(connected)

    def keymapNo(self):
        return self.em.keymapNo()

    def keymap(self):
        return self.em.keymap()

    def setKeymapNo(self, kn):
        self.em.setKeymap(kn)

    def setKeymap(self, id):
        self.em.setKeymapById(id)

    def setHistory(self, history):
        self.em.setHistory(history)

    def history(self):
        return self.em.history()
