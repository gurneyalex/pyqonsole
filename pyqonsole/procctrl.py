# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""KPROCESSCONTROLLER -- A helper class for KProcess


using a struct which contains both the pid and the status makes it
easier to write and read the data into the pipe.
especially this solves a problem which appeared on my box where
slotDoHouseKeeping() received only 4 bytes (with some debug output
around the write()'s it received all 8 bytes). don't know why this
happened, but when writing all 8 bytes at once it works here, aleXXX

struct waitdata
{
  pid_t pid
  int status
}

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Sylvain Thenault
@copyright: 2003, 2005
@organization: CEA-Grenoble
@organization: Logilab
@license: CECILL

XXX review singleton aspect
"""
__revision__ = '$Id: procctrl.py,v 1.8 2005-12-27 16:53:22 syt Exp $'

import os
import errno
import fcntl
import select
import signal
import struct
import sys

import qt

def waitChildren():
    """wait for all children process, yield (pid, status) each time one
    is existing
    """
    while 1:
        try:
            yield os.waitpid(-1, os.WNOHANG)
        except OSError, ex:
            if ex.errno == errno.ECHILD:
                break
            raise

theProcessController = None

class ProcessController(qt.QObject):
    """ A class for internal use by Process only. -- Exactly one instance
    of this class is generated by the first instance of Process that is
    created (a pointer to it gets stored in @ref theProcessController ).
    
    This class takes care of the actual (UN*X) signal handling.
    """

    def __init__(self):
        super(ProcessController, self).__init__()        
        global theProcessController
        assert theProcessController is None
        self.old_sigCHLDHandler = None
        self.handler_set = False
        self.process_list = []
        self.fd = os.pipe()
        # delayed children cleanup timer
        self._dcc_timer = qt.QTimer()
        fcntl.fcntl(self.fd[0], fcntl.F_SETFL, os.O_NONBLOCK)
        notifier = qt.QSocketNotifier(self.fd[0], qt.QSocketNotifier.Read, self)
        self.connect(notifier, qt.SIGNAL('activated(int)'),
                     self.slotDoHousekeeping)
        self.connect(self._dcc_timer, qt.SIGNAL('timeout()'),
                                self.delayedChildrenCleanup)
        theProcessController = self
        self.setupHandlers()

##     def __del__(self):
##         global theProcessController
##         assert theProcessController is self
##         self.resetHandlers()
##         self.notifier.setEnabled(False)
##         os.close(self.fd[0])
##         os.close(self.fd[1])
##         del self.notifier
##         theProcessController = None

    def setupHandlers(self):
        if self.handler_set:
            return
        self.old_sigCHLDHandler = signal.getsignal(signal.SIGCHLD)
        signal.signal(signal.SIGCHLD, self.sigCHLDHandler)
        #sigaction( SIGCHLD, &act, &self.old_sigCHLDHandler )
        #act.sa_handler=SIG_IGN
        #sigemptyset(&(act.sa_mask))
        #sigaddset(&(act.sa_mask), SIGPIPE)
        #act.sa_flags = 0
        #sigaction( SIGPIPE, &act, 0L)
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        self.handler_set = True

    def resetHandlers(self):
        if not self.handler_set:
            return
        signal.signal(signal.SIGCHLD, self.old_sigCHLDHandler)
        # there should be no problem with SIGPIPE staying SIG_IGN
        self.handler_set = False

    def addProcess(self, process):
        # XXX block SIGCHLD handler, because it accesses self.process_list
        #sigset_t newset, oldset
        #sigemptyset( &newset )
        #sigaddset( &newset, SIGCHLD )
        #sigprocmask( SIG_BLOCK, &newset, &oldset )
        self.process_list.append(process)
        #sigprocmask( SIG_SETMASK, &oldset, 0 )

    def removeProcess(self, process):
        # XXX block SIGCHLD handler, because it accesses self.process_list
        #sigset_t newset, oldset
        #sigemptyset( &newset )
        #sigaddset( &newset, SIGCHLD )
        #sigprocmask( SIG_BLOCK, &newset, &oldset )
        self.process_list.remove(process)
        #sigprocmask( SIG_SETMASK, &oldset, 0 )


    def sigCHLDHandler(self, signal, frame):
        """SIGCHLD handler
        
        :signal: int
        :frame: frame object

        Automatically called upon SIGCHLD.
        
        Normally you do not need to do anything with this function but
        if your application needs to disable SIGCHLD for some time for
        reasons beyond your control, you should call this function afterwards
        to make sure that no SIGCHLDs where missed.
        """
        found = False
        # iterating the list doesn't perform any system call
        for process in self.process_list:
            if not process.running:
                continue
            try:
                wpid, status = os.waitpid(process.pid, os.WNOHANG)
            except OSError:
                # [Errno 10] No child processes
                # XXX: bug in process.py ?
                continue
            if wpid > 0:
                os.write(self.fd[1], struct.pack('II', wpid, status))
                found = True
        if (not found and
            not self.old_sigCHLDHandler in (signal.SIG_IGN, signal.SIG_DFL)):
            self.old_sigCHLDHandler(signal) # call the old handler
        # handle the rest
        # XXX
        os.write(self.fd[1], struct.pack('II', 0, 0)) # delayed waitpid()

    def slotDoHousekeeping(self, _):
        """NOTE: It can happen that QSocketNotifier fires while
        we have already read from the socket. Deal with it.
        
        read pid and status from the pipe.
        """
        bytes_read = ''
        while not bytes_read:
            try:
                bytes_read = os.read(self.fd[0], struct.calcsize('II'))
            except OSError, ex:
                if ex.errno == errno.EAGAIN:
                    return
                if ex.errno == errno.EINTR:
                    msg = ("Error: pipe read returned errno=%d "
                           "in ProcessController::slotDoHousekeeping")
                    print >> sys.stderr, msg % ex.errno
                    return
        if len(bytes_read) != struct.calcsize('II'):
            msg = "Error: Could not read info from signal handler %d <> %d!"
            print >> sys.stderr, msg % (len(bytes_read), struct.calcsize('II'))
            return
        pid, status = struct.unpack('II', bytes_read)
        if pid == 0:
            self._dcc_timer.start(100, True)
            return
        for process in self.process_list:
            if process.pid == pid:
                process.processHasExited(status)
                return

    def delayedChildrenCleanup(self):
        """this is needed e.g. for popen(), which calls waitpid() checking
        // for its forked child, if we did waitpid() directly in the SIGCHLD
        // handler, popen()'s waitpid() call would fail
        """
        for wpid, status in waitChildren():
            for process in self.process_list:
                if not process.running or process.pid != wpid:
                    continue
                # it's Process, handle it
                os.write(self.fd[1], struct.pack('II', wpid, status))
                break

    def waitForProcessExit(self, timeout):
        """
        * Wait for any process to exit and handle their exit without
        * starting an event loop.
        * This function may cause Process to emit any of its signals.
        *
        * return True if a process exited, False if no process exited within
          @p timeout seconds.
        // Due to a race condition the signal handler may have
        // failed to detect that a pid belonged to a Process
        // and defered handling to delayedChildrenCleanup()
        // Make sure to handle that first.
        """
        if self._dcc_timer.isActive():
            self._dcc_timer.stop()
            self.delayedChildrenCleanup()
        while True:
            rlist, wlist, xlist  = select.select([self.fd[0]], [], [], timeout)
            if not rlist:
                return False
            else:
                self.slotDoHousekeeping(self.fd[0])
                break
        return True


theProcessController = ProcessController()
