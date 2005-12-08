#!/usr/bin/env python2.4

__revision__ = '$Id: test_wcwidth.py,v 1.4 2005-12-08 17:13:39 alf Exp $'


## http://www.cl.cam.ac.uk/~mgk25/ucs/scw-proposal.html is the right place

from pyqonsole.helpers import wcWidth
import unittest
import unicodedata as udata

def makeCats():
    cats = {}
    for i in xrange(0x110000):
        char = unichr(i)
        cats.setdefault(udata.category(char), []).append(i)
    return cats

category_names = {'Cc': 'Other, control',
                  'Cf': 'Other, format',
                  'Cn': 'Other, not assigned',
                  'Co': 'Other, private use',
                  'Cs': 'Other, surrogate',
                  'Ll': 'Letter, lowercase',
                  'Lm': 'Letter, modifier',
                  'Lo': 'Letter, other',
                  'Lt': 'Letter, titlecase',
                  'Lu': 'Letter, uppercase',
                  'Mc': 'Mark, spacing combining',
                  'Me': 'Mark, enclosing',
                  'Mn': 'Mark, non-spacing',
                  'Nd': 'Number, decimal digit',
                  'Nl': 'Number, letter',
                  'No': 'Number other',
                  'Pc': 'Punctuation, connector',
                  'Pd': 'Punctuation, dash',
                  'Pe': 'Punctuation, close',
                  'Pf': 'Punctuation, final quote',
                  'Pi': 'Puntuation, initial quote',
                  'Po': 'Punctuation, other',
                  'Ps': 'Punctuation, open',
                  'Sc': 'Symbol, currency',
                  'Sk': 'Symbol, modifier',
                  'Sm': 'Symbol, math',
                  'So': 'Symbol, other',
                  'Zl': 'Seaprator, line',
                  'Zp': 'Seaparator, paragraph',
                  'Zs': 'Separator, space',
                  }
    
CATS = makeCats()

def widths():
    """ toy function to explore the unicodedata module """
    for cat, chars in CATS.iteritems():
        print '-'*80
        print cat
        print '-'*80
        for c in chars:
            print '%06X'%c, wcWidth(c), udata.east_asian_width(unichr(c))
        print

single_width = []
double_width = []
for cp in xrange(33,0x110000):
    ch = unichr(cp)
    if (udata.category(ch) in ('Mn', 'Me',  'Cf', 'Cn') and cp != 0xAD) or \
           (0x7f<= cp < 0xa0) or \
           (0x1160 <= cp <= 0x11ff) or \
           (cp == 0x200B):
        continue
    if cp >= 0x1100 and (
        cp <= 0x115f or \
        cp in (0x2329, 0x232A) or \
        (0x2e80 <= cp < 0x303f) or \
        (0x303f < cp <= 0xa4cf) or \
        (0xac00 <= cp <= 0xd7a3) or \
        (0xf900 <= cp <= 0xfaff) or \
        (0xfe30 <= cp <= 0xfe6f) or \
        (0xff00 <= cp <= 0xff60) or \
        (0xffe0 <= cp <= 0xffe6) or \
        (0x20000 <= cp <= 0x2fffd) or \
        (0x30000 <= cp <= 0x3fffd)):
        double_width.append(cp)
    else:
        single_width.append(cp)

class Wcwidth_TC(unittest.TestCase):
    
    def testNullChar(self):
        self.assertEquals(wcWidth(0), 0)

    def check_range(self, codepoints, expected):
        failures = []
        for cp in codepoints:
            unichar = unichr(cp)
##             print cp, udata.name(unichar, 'XXX Unknown Code Point')
            if wcWidth(cp) != expected:
                failures.append('codepoint %X [%s] [cat: %s (%s)] width %d expected %d' % \
                              (cp,
                               udata.name(unichar, 'XXX Unknown Code Point'),
                               udata.category(unichar),
                               category_names[udata.category(unichar)],
                               wcWidth(cp),
                               expected))
        self.assertEquals(failures, [])
            

    def testControlChar(self):
        codepoints = range(1,32) + range(0x7f, 0xa0)
        self.check_range(codepoints, -1)
            
    def testFormatChar(self):
        # This test fails because of problems in unidata
        self.check_range(CATS['Cf'], 0)

    def testCombiningChar(self):
        self.check_range(CATS['Mn'], 0)
        self.check_range(CATS['Me'], 0)
            

    def testHangulJamo(self):
        codepoints = xrange(0x1160, 0x11FF+1)
        self.check_range(codepoints, 0)

    def testZeroWidthSpace(self):
        self.check_range([0x200B], 0)

    def testWideChars(self):
        self.check_range(double_width, 2)


    def testRemainingChars(self):
        # This test fails because of problems in unidata
        self.check_range(single_width, 1)
                                               
class UnidataErrors_TC(unittest.TestCase):
    """The tests below fail because of an error in unicodedata.

    The category mappings are not comformant with
    http://www.unicode.org/Public/UNIDATA/UnicodeData.txt maybe it is
    a version mismatch (3.2 for unicodedata, 4.X for the file above)."""
    
    def test_MongolianVowelSeparator(self):
        char = unichr(0x180E)
        self.assertEquals(udata.name(char), 'MONGOLIAN VOWEL SEPARATOR')
        self.assertEquals(udata.category(char), 'Zs')

    def test_KhmerVowelInherentAa(self):
        char = unichr(0x17B5)
        self.assertEquals(udata.name(char), 'KHMER VOWEL INHERENT AA')
        self.assertEquals(udata.category(char), 'Cf')

    def test_KhmerVowelInherentAq(self):
        char = unichr(0x17B4)
        self.assertEquals(udata.name(char), 'KHMER VOWEL INHERENT AQ')
        self.assertEquals(udata.category(char), 'Cf')

if __name__ == '__main__':
    unittest.main()

