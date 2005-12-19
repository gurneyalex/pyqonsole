"""Test pyqonsole's history module.
"""
import unittest

from pyqonsole.history import  *

class HistoryScrollNoneTC(unittest.TestCase):
    def setUp(self):
        self.history = HistoryScrollNone()

    def test_base(self):
        history = self.history
        self.failUnless(isinstance(history.type, HistoryTypeNone))
        self.failUnlessEqual(history.hasScroll(), False)
        self.failUnlessEqual(history.lines, 0)
        self.failUnlessEqual(history.getLineLen(1), 0)
        self.failUnlessEqual(history.isWrappedLine(1), False)
        self.failUnlessEqual(history.getCells(1, 0), None)
        
    def test_one_line(self):
        history = self.history
        history.addCells(list('bonjour'), True) # this is a list of Ca instances in the real world
        self.failUnlessEqual(history.lines, 0)
        self.failUnlessEqual(history.getLineLen(1), 0)
        self.failUnlessEqual(history.isWrappedLine(1), False)
        self.failUnlessEqual(history.getCells(1, 0), None)
        
class HistoryScrollBufferTC(unittest.TestCase):
    def setUp(self):
        self.history = HistoryScrollBuffer(5)

    def test_base(self):
        history = self.history
        self.failUnless(isinstance(history.type, HistoryTypeBuffer))
        self.failUnlessEqual(history.hasScroll(), True)
        self.failUnlessEqual(history.lines, 0)
        self.failUnlessEqual(history.getLineLen(0), 0)
        self.failUnlessEqual(history.isWrappedLine(0), False)
        #self.failUnlessEqual(history.getCells(0, 0), None)
        self.failUnlessEqual(history.buff_filled, False)
        
    def test_one_line(self):
        history = self.history
        cells = list('bonjour')
        history.addCells(cells, True) # this is a list of Ca instances in the real world
        self.failUnlessEqual(history.lines, 1)
        self.failUnlessEqual(history.getLineLen(0), len(cells))
        self.failUnlessEqual(history.isWrappedLine(0), True)
        self.failUnlessEqual(history.getCells(0, 0), cells)
        self.failUnlessEqual(history.buff_filled, False)
        
    def test_full(self):
        history = self.history
        for cells in ('1', '22', '333', '4444', '55555', '666666'):
            history.addCells(cells, True)
        self.failUnlessEqual(history.buff_filled, True)
        self.failUnlessEqual(history.hist_buffer, ['666666', '22', '333', '4444', '55555'])

    def test__normalize(self):
        history = self.history
        for cells in ('1', '22', '333', '4444', '55555', '666666'):
            history.addCells(cells, True)
        history._normalize()
        self.failUnlessEqual(history.buff_filled, False)
        self.failUnlessEqual(history.hist_buffer, ['4444', '55555', '666666', None, None])
        history.addCells('7777777')
        self.failUnlessEqual(history.hist_buffer, ['4444', '55555', '666666', '7777777', None])

    def test_change_size(self):
        history = self.history
        history.addCells('1', True)
        history.setMaxLines(4)
        self.failUnlessEqual(history.buff_filled, False)
        self.failUnlessEqual(history.hist_buffer, ['1', None, None, None])
        history.setMaxLines(5)
        self.failUnlessEqual(history.buff_filled, False)
        self.failUnlessEqual(history.hist_buffer, ['1', None, None, None, None])
        history.addCells('22')
        self.failUnlessEqual(history.hist_buffer, ['1', '22', None, None, None])
        
    def test_change_size_buff_filled(self):
        history = self.history
        for cells in ('1', '22', '333', '4444', '55555', '666666'):
            history.addCells(cells, True)
        history.setMaxLines(6)
        self.failUnlessEqual(history.buff_filled, False)
        self.failUnlessEqual(history.hist_buffer, ['4444', '55555', '666666', None, None, None])
        history.addCells('7777777')
        self.failUnlessEqual(history.hist_buffer, ['4444', '55555', '666666', '7777777', None, None])
        history.setMaxLines(3)
        self.failUnlessEqual(history.buff_filled, False)
        self.failUnlessEqual(history.hist_buffer, ['7777777', None, None])
        history.addCells('88888888')
        self.failUnlessEqual(history.hist_buffer, ['7777777', '88888888', None])
        
if __name__ == '__main__':
    unittest.main()
