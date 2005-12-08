"""Test pyqonsole's keytrans module.
"""
import unittest

from pyqonsole import keytrans

class ParserTC(unittest.TestCase):

    def test_parse_default_config(self):
        kt = keytrans.KeyTrans()
        kt.readConfig()

    
if __name__ == '__main__':
    unittest.main()
