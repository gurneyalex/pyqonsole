"""Test pyqonsole's screen module.
"""
import unittest
from pyqonsole.screen import Screen
from pyqonsole.ca import *

class ScreenTC(unittest.TestCase):

    def setUp(self):
        self.screen = Screen(5, 10) # 5 lines 10 columns screen


    def test_init(self):
        screen = self.screen        
        self.failUnlessEqual(screen.getCursorX(), 0)
        self.failUnlessEqual(screen.getCursorY(), 0)

    def test_incPoint(self):
        screen = self.screen        
        point = [4 , 0]
        screen._incPoint(point)
        self.failUnlessEqual(point, [4, 1])
        screen._incPoint(point, -2)
        self.failUnlessEqual(point, [3, 9])
        screen._incPoint(point, 2)
        self.failUnlessEqual(point, [4, 1])
            
    def test_showCharacter(self):
        screen = self.screen
        image = screen._image
        screen.showCharacter(ord('a'))
        self.failUnlessEqual(screen.getCursorX(), 1)
        self.failUnlessEqual(screen.getCursorY(), 0)
        self.failUnlessEqual(image[0][0].c, ord('a'))
        for y in xrange(5):
            for x in xrange(10):
                if y == 0 and x == 0:
                    continue
                self.failUnlessEqual(image[y][x].c, ord(' '))

    def test_nextLine(self):
        screen = self.screen
        image = screen._image
        screen.nextLine()
        self.failUnlessEqual(screen.getCursorX(), 0)
        self.failUnlessEqual(screen.getCursorY(), 1)
        for y in xrange(5):
            for x in xrange(10):
                self.failUnlessEqual(image[y][x].c, ord(' '))
        #self.failUnlessEqual(screen._hist.hist_buffer[0], [])

    def test_getCookedImage(self):
        screen = self.screen
        screen.showCharacter(ord('a'))
        screen.nextLine()
        image = screen.getCookedImage()
        expected = [Ca(ord('a'))] + [Ca() for i in xrange(49)]
        expected[10].r |= RE_CURSOR # cursor location
        self.failUnlessEqual(image, expected)

        screen.showCharacter(ord('b'))
        screen.showCharacter(ord('c'))
        screen.nextLine()
        image = screen.getCookedImage()
        expected[10].c = ord('b')
        expected[10].r = 0
        expected[11].c = ord('c')
        expected[20].r |= RE_CURSOR # cursor location
        self.failUnlessEqual(image, expected)
        
if __name__ == '__main__':
    unittest.main()
