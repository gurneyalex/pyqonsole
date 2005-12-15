"""Test pyqonsole's screen module.
"""
import unittest
from pyqonsole.screen import Screen


class ScreenTC(unittest.TestCase):

    def setUp(self):
        self.screen = Screen(5, 10) # 5 lines 10 columns screen


    def test_init(self):
        screen = self.screen        
        self.failUnlessEqual(screen.getCursorX(), 0)
        self.failUnlessEqual(screen.getCursorY(), 0)

        
    def test_showCharacter(self):
        screen = self.screen
        image = screen._image
        screen.showCharacter(ord('a'))
        self.failUnlessEqual(screen.getCursorX(), 1)
        self.failUnlessEqual(screen.getCursorY(), 0)
        self.failUnlessEqual(image[0].c, ord('a'))
        for i in xrange(1, len(image)):
            self.failUnlessEqual(image[i].c, ord(' '))

    def test_nextLine(self):
        screen = self.screen
        image = screen._image
        screen.nextLine()
        self.failUnlessEqual(screen.getCursorX(), 0)
        self.failUnlessEqual(screen.getCursorY(), 1)
        self.failUnlessEqual(image[0].c, ord(' '))
        for i in xrange(1, len(image)):
            self.failUnlessEqual(image[i].c, ord(' '))
        
if __name__ == '__main__':
    unittest.main()
