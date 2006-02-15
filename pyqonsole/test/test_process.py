# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
import unittest
import time

from pyqonsole import pty_, procctrl


class ProcessTC(unittest.TestCase):
    def setUp(self):
        self.process = p = pty_.PtyProcess()
        
    def test_base(self):
        p = self.process
        # process controller interaction
        self.failUnless(p in procctrl.theProcessController.process_list)
        # base attributes
        self.failUnlessEqual(p.running, False)
        self.failUnlessEqual(p.pid, None)
        self.failUnlessEqual(p.status, None)
    
    def test_start(self):
        p = self.process
        p.run('ls', ['/'], 'xterm', False)
        time.sleep(2)
        # after execution
        self.failUnlessEqual(p.running, True) # XXX
        self.failIfEqual(p.pid, 0)
        self.failUnlessEqual(p.status, 0)
        # process controller interaction
        #self.failUnless(not p in procctrl.theProcessController.process_list)

    def test_start_then_kill(self):
        p = self.process
        p.run('sleep', ['11'], 'xterm', False)
        p.kill(9)
        time.sleep(2)
        # after execution
        self.failUnlessEqual(p.running, True) # XXX
        self.failIfEqual(p.pid, 0)
        self.failUnlessEqual(p.status, 0) # XXX killed !
        # process controller interaction
        #self.failUnless(not p in procctrl.theProcessController.process_list)

        
if __name__ == '__main__':
    unittest.main()
