"""Test pyqonsole's session module.
"""
import unittest
from utils import NullGui, NoScreenTC

from pyqonsole import session

class SessionTC(NoScreenTC):
    
    def setUp(self):
        NoScreenTC.setUp(self)
        self.session = session.Session(NullGui(), 'echo', ['coucou'], 'xterm')

    def test(self):
        session = self.session
        self.failUnlessEqual(session.monitor_silence, False)
    
if __name__ == '__main__':
    unittest.main()
