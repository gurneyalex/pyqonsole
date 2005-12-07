import unittest
import time

from pyqonsole import process, procctrl


class ProcessTC(unittest.TestCase):
    def setUp(self):
        self.process = p = process.Process()
        
    def test_base(self):
        p = self.process
        # process controller interaction
        self.failUnless(p in procctrl.theProcessController.process_list)
        # base attributes
        self.failUnlessEqual(p.running, False)
        self.failUnlessEqual(p.pid, None)
        self.failUnlessEqual(p.status, None)
        self.failUnlessEqual(p.run_mode, process.RUN_NOTIFYONEXIT)
        self.failUnlessEqual(p.communication, process.COMM_NOCOMMUNICATION)
    
    def test_start(self):
        p = self.process
        # XXX set arguments
        p << 'ls' << '/'
        p.start(process.RUN_NOTIFYONEXIT, process.COMM_ALL)
        time.sleep(2)
        # after execution
        self.failUnlessEqual(p.running, True) # XXX
        self.failIfEqual(p.pid, 0)
        self.failUnlessEqual(p.status, 0)
        # process controller interaction
        #self.failUnless(not p in procctrl.theProcessController.process_list)

    def test_start_then_kill(self):
        p = self.process
        # XXX set arguments
        p << 'sleep' << '11'
        p.start(process.RUN_NOTIFYONEXIT, process.COMM_ALL)
        p.kill(9)
        time.sleep(2)
        # after execution
        self.failUnlessEqual(p.running, True) # XXX
        self.failIfEqual(p.pid, 0)
        self.failUnlessEqual(p.status, 0) # XXX killed !
        # process controller interaction
        #self.failUnless(not p in procctrl.theProcessController.process_list)


class ShellProcessTC(ProcessTC):
    def setUp(self):
        self.process = p = process.ShellProcess()

    #def test_shell(self):
        
if __name__ == '__main__':
    unittest.main()
