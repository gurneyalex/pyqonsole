"""Test pyqonsole's screen module.
"""
import unittest
from pyqonsole.screen import *
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
        expected = [[Ca(ord('a'))] + [Ca() for i in xrange(9)]]
        expected += [[Ca() for i in xrange(10)] for i in xrange(4)]
        expected[1][0].r |= RE_CURSOR # cursor location
        self.failUnlessEqual(image, expected)

        screen.showCharacter(ord('b'))
        screen.showCharacter(ord('c'))
        screen.nextLine()
        image = screen.getCookedImage()
        expected[1][0].c = ord('b')
        expected[1][0].r = 0
        expected[1][1].c = ord('c')
        expected[2][0].r |= RE_CURSOR # cursor location
        self.failUnlessEqual(image, expected)

    def test_modes(self):
        SCREEN_MODES = (MODE_Origin, MODE_Wrap, MODE_Insert, MODE_Screen, MODE_Cursor, MODE_NewLine)
        # reset modes so all modes are unset
        self.screen.resetMode(MODE_Wrap) 
        self.screen.resetMode(MODE_Cursor) 
        for mode in SCREEN_MODES:
            self.screen.setMode(mode)
            self.failUnless(self.screen.getMode(mode))
            for omode in SCREEN_MODES:
                if omode == mode:
                    continue
                self.failUnless(not self.screen.getMode(omode))
            self.screen.resetMode(mode)
            for omode in SCREEN_MODES:
                self.failUnless(not self.screen.getMode(omode))
        
if __name__ == '__main__':
    unittest.main()
