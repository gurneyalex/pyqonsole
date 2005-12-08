#!/usr/bin/env python2.4

__revision__ = '$Id: test_wcwidth.py,v 1.2 2005-12-08 10:47:56 alf Exp $'

## XXX FIXME: find out if the failing tests are caused by:
##  * Errors in the test
##  * Errors in the helpers.c module
##  * Errors in the unicodedata module from stdlib

from pyqonsole.helpers import wcWidth
import unittest
import unicodedata

def makeCats():
    cats = {}
    for i in xrange(0x110000):
        char = unichr(i)
        cats.setdefault(unicodedata.category(char), []).append(i)
    return cats

CATS = makeCats()

def widths():
    """ toy function to explore the unicodedata module """
    for cat, chars in CATS.iteritems():
        print '-'*80
        print cat
        print '-'*80
        for c in chars:
            print '%06X'%c, wcWidth(c), unicodedata.east_asian_width(unichr(c))
        print

class Wcwidth_TC(unittest.TestCase):
    
    def testNullChar(self):
        self.assertEquals(wcWidth(0), 0)

    def check_range(self, codepoints, expected):
        for cp in codepoints:
            self.assertEquals(wcWidth(cp), expected,
                              'codepoint %X [%s] width %d expected %d' % \
                              (cp, unicodedata.name(unichr(cp), 'XXX Unknown Code Point'),
                               wcWidth(cp),
                               expected))
            

    def testControlChar(self):
        codepoints = [cp for cp in CATS['Cc'] if cp != 0]
        self.check_range(codepoints, -1)
            
    def testFormatChar(self):
        self.check_range(CATS['Cf'], 0)

    def testCombiningChar(self):
        self.check_range(CATS['Mn'], 0)
        self.check_range(CATS['Me'], 0)
            

    def testWideChars(self):
        codepoints = [cp for cp in xrange(0x110000)
                          if unicodedata.east_asian_width(unichr(cp)) in ('F', 'W')]
        self.check_range(codepoints, 2)

    def testHangulJame(self):
        codepoints = xrange(0x1160, 0x11FF+1)
        self.check_range(codepoints, 0)

    def testRemainingChars(self):
        # all available cats:
        # ['Ps', 'Nl', 'No', 'Lo', 'Ll', 'Lm', 'Nd', 'Pc', 'Lt', 'Lu',
        # 'Pf', 'Pd', 'Pe', 'Pi', 'Po', 'Me', 'Mc', 'Mn', 'Sk', 'So',
        # 'Sm', 'Sc', 'Zl', 'Co', 'Cn', 'Cc', 'Cf', 'Cs', 'Zp', 'Zs']

        for cat in ('Nd', 'Po', 'Lu', 'Pe', 'Ps', 'Ll', 'Lm'): # FIXME: add missing cats
            codepoints = [cp for cp in CATS[cat]
                          if unicodedata.east_asian_width(unichr(cp)) not in ('F', 'W')]
            self.check_range(codepoints, 1)
                                               

## for i in xrange(10):
##     print wcWidth(i)
if __name__ == '__main__':
#    widths()
    unittest.main()

