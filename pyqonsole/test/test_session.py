"""Test pyqonsole's session module.
"""
import unittest
import time
from utils import NullGui, NoScreenTC, register_logger, reset_logs
from qt import QApplication

from pyqonsole import session, emulation

session.SILENCE_TIMEOUT = 1 # milliseconds

class MySession(session.Session):
    def emit(self, signal, args):
        self._logs.append( (signal, args) )
        session.Session.emit(self, signal, args)

class SessionTC(NoScreenTC):
    
    def setUp(self):
        NoScreenTC.setUp(self)
        self.session = MySession(NullGui(), 'echo', ['coucou'], 'xterm')
        self.session._logs = []
        register_logger(self.session)

    def test_monitor_silence(self):
        app = QApplication([])
        session = self.session
        self.failUnlessEqual(session.monitor_silence, False)
        session.monitor_silence = True
        self.failUnlessEqual(session.monitor_timer.isActive(), True)
        time.sleep(2e-3 ) # 2 * SILENCE_TIMEOUT (in seconds)
        app.processEvents()
        self.failUnlessEqual(session._logs, [('9notifySessionState', (emulation.NOTIFYSILENCE,))])
        session.monitor_silence = False
        self.failUnlessEqual(session.monitor_timer.isActive(), False)

    def test_monitor_activity(self):
        session = self.session
        self.failUnlessEqual(session.monitor_activity, False)
        session.notifySessionState(emulation.NOTIFYACTIVITY)
        self.failUnlessEqual(session._logs, [])
        session.monitor_activity = True
        session.notifySessionState(emulation.NOTIFYACTIVITY)
        self.failUnlessEqual(session._logs, [('9notifySessionState', (2,))])

    def test_keymap(self):
        session = self.session
        self.failUnlessEqual(session.keymapNo(), 0)
        self.failUnlessEqual(session.keymap(), 'default')
        session.setKeymapNo(0)
        session.setKeymap('[buildin]')
        
    def test_title(self):
        session = self.session
        session.setUserTitle(0, 'bonjour')
        self.failUnlessEqual(session._logs, [('9updateTitle', ())])
        self.failUnlessEqual(session.title, '')
        self.failUnlessEqual(session.user_title, 'bonjour')
        self.failUnlessEqual(session.icon_text, 'bonjour')
        self.failUnlessEqual(session.fullTitle(), 'bonjour - ')
        reset_logs()
        session.setUserTitle(1, 'hello')
        self.failUnlessEqual(session._logs, [('9updateTitle', ())])
        self.failUnlessEqual(session.title, '')
        self.failUnlessEqual(session.user_title, 'bonjour')
        self.failUnlessEqual(session.icon_text, 'hello')
        self.failUnlessEqual(session.fullTitle(), 'bonjour - ')
        reset_logs()
        session.setUserTitle(2, 'oYe')
        self.failUnlessEqual(session._logs, [('9updateTitle', ())])
        self.failUnlessEqual(session.title, '')
        self.failUnlessEqual(session.user_title, 'oYe')
        self.failUnlessEqual(session.icon_text, 'hello')
        self.failUnlessEqual(session.fullTitle(), 'oYe - ')
        reset_logs()

    def test_icon_name(self):
        session = self.session
        self.failUnlessEqual(session.testAndSetStateIconName('bonjour'), True)
        self.failUnlessEqual(session.testAndSetStateIconName('bonjour'), False)
        self.failUnlessEqual(session.state_icon_name, 'bonjour')
        
if __name__ == '__main__':
    unittest.main()
