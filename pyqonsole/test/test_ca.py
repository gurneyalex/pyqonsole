# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
import unittest
import sys
import os
sys.path.append(os.pardir)
from pyqonsole.ca import *


class CaTest(unittest.TestCase):
    """ Test of the Ca class.
    """

    def setUp(self):
        """ Setup a context before each test call.
        """
        self.c1 = Ca()
        self.c2 = Ca()

    def tearDown(self):
        """ Clear context after each test call.
        """
        del self.c1
        del self.c2

    def testInit(self):
        """ Test the __init__ method.
        """
        self.assertEqual(self.c1.c, u' ')
        self.assertEqual(self.c1.f, DEFAULT_FORE_COLOR)
        self.assertEqual(self.c1.b, DEFAULT_BACK_COLOR)
        self.assertEqual(self.c1.r, DEFAULT_RENDITION)

    def testEqual(self):
        """ Test the __eq__ method.
        """
        self.assertEqual(self.c1, self.c2)
        
    def testNotEqualC(self):
        """ Test the __ne__ method.
        """
        self.c2.c = 'a'
        self.assertNotEqual(self.c1, self.c2)
        
    def testNotEqualF(self):
        """ Test the __ne__ method.
        """
        self.c2.f = 1
        self.assertNotEqual(self.c1, self.c2)
        
        
    def testNotEqualR(self):
        """ Test the __ne__ method.
        """
        self.c2.r = 1
        self.assertNotEqual(self.c1, self.c2)


if __name__ == "__main__":
    unittest.main()
