# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
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
        entry = kt.findEntry(qt.Qt.Key_Backspace, False, True, False, False, False, False)
        self.failUnlessEqual(entry.cmd, keytrans.CMD_send)
        self.failUnlessEqual(entry.txt, '\x7f')
        entry = kt.findEntry(qt.Qt.Key_Return, False, True, False, False, False, False)
        self.failUnlessEqual(entry.cmd, keytrans.CMD_send)
        self.failUnlessEqual(entry.txt, '\r')
        
if __name__ == '__main__':
    unittest.main()
