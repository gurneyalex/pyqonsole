"""Test pyqonsole's keytrans module.
"""
import unittest

import qt
from pyqonsole import keytrans

class ParserTC(unittest.TestCase):

    def test_parse_default_config(self):
        kt = keytrans.KeyTrans()
        kt.readConfig()


    def test_find_attr(self):
        kt = keytrans.KeyTrans()
        # key, newline, ansi, appcukeys, control, shift, alt
        entry = kt.findEntry(qt.Qt.Key_Left, False, True, False, False, False, False)
        self.failUnlessEqual(entry.cmd, keytrans.CMD_send)
        self.failUnlessEqual(entry.txt, '\033[D')
        entry = kt.findEntry(qt.Qt.Key_Tab, False, True, False, False, False, False)
        self.failUnlessEqual(entry.cmd, keytrans.CMD_send)
        self.failUnlessEqual(entry.txt, '\t')
        
if __name__ == '__main__':
    unittest.main()
