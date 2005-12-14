# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""Process

A class for handling child processes in without having to take care
of Un*x specific implementation details

// This file is a translation of konsole/.kprocess.[h/cpp]
//  version 0.3.1, Jan, 8th 1998
//  (C) Christian Czezatke e9025461@student.tuwien.ac.at

XXX signals:
  /**
   * Emitted after the process has terminated when
   * the process was run in the @p RUN_NOTIFYONEXIT  (==default option to
   * @ref start()) or the @ref RUN_BLOCK mode.
   **/
  void processExited(Process *proc)

  /**
   * Emitted, when output from the child process has
   * been received on stdout.
   *
   *  To actually get
   * these signals, the respective communication link (stdout/stderr)
   * has to be turned on in @ref start().
   *
   * @param buffer The data received.
   * @param buflen The number of bytes that are available.
   *
   * You should copy the information contained in @p buffer to your private
   * data structures before returning from this slot.
   **/
  void receivedStdout(Process *proc, char *buffer, int buflen)

  /**
   * Emitted when output from the child process has
   * been received on stdout.
   *
   * To actually get these signals, the respective communications link 
   * (stdout/stderr) has to be turned on in @ref start() and the 
   * @p COMM_NOREAD flag should have been passed.
   *
   * You will need to explicitly call resume() after your call to start()
   * to begin processing data from the child process's stdout.  This is
   * to ensure that this signal is not emitted when no one is connected
   * to it, otherwise this signal will not be emitted.
   * 
   * The data still has to be read from file descriptor @p fd.
   **/
  void receivedStdout(int fd, int &len)

  /**
   * Emitted, when output from the child process has
   * been received on stderr.
   * To actually get
   * these signals, the respective communication link (stdout/stderr)
   * has to be turned on in @ref start().
   *
   * @param buffer The data received.
   * @param buflen The number of bytes that are available.
   *
   * You should copy the information contained in @p buffer to your private
   * data structures before returning from this slot.
  */
  void receivedStderr(Process *proc, char *buffer, int buflen)

  /**
   * Emitted after all the data that has been
   * specified by a prior call to @ref writeStdin() has actually been
   * written to the child process.
   **/
  void wroteStdin(Process *proc)
"""
__revision__ = '$Id: process.py,v 1.8 2005-12-14 14:22:18 alf Exp $'


import os
import pwd
import grp
import fcntl
import select
import signal
import socket
import struct
import stat
import sys

import qt


def initgroups(user, group):
    """The  initgroups()  function initializes the group access list by
    reading the group database /etc/group and using all groups of which
    user is a member.  The additional group group is also added to the
    list."""
    raise NotImplementedError


## Modes in which the communication channel can be opened.
#
# If communication for more than one channel is required,
# the values have to be or'ed together, for example to get
# communication with stdout as well as with stdin, you would
# specify @p Stdin @p | @p Stdout
#
# If @p COMM_NOREAD is specified in conjunction with @p Stdout,
# no data is actually read from @p Stdout but only
# the signal @ref childOutput(int fd) is emitted.
#
COMM_NOCOMMUNICATION = 0
COMM_STDIN           = 1
COMM_STDOUT          = 2
COMM_STDERR          = 4
COMM_ALLOUTPUT       = 6
COMM_ALL             = 7
COMM_NOREAD          = 8

## Run-modes for a child process.
#
# The application does not receive notifications from the subprocess when
# it is finished or aborted.
RUN_DONTCARE = 0
# The application is notified when the subprocess dies.
RUN_NOTIFYONEXIT = 1
# The application is suspended until the started process is finished.
RUN_BLOCK = 2

class ProcessEnv:
    def __init__(self):
        self.wd = None
        self.env = {}


class Process(qt.QObject):
    """Child process invocation, monitoring and control.
 
    @sect General usage and features

    This class allows a KDE application to start child processes without having
    to worry about UN*X signal handling issues and zombie process reaping.

    @see ProcIO

    Basically, this class distinguishes three different ways of running
    child processes:

    *  Process::RUN_DONTCARE -- The child process is invoked and both the child
    process and the parent process continue concurrently.

    Starting a  RUN_DONTCARE child process means that the application is
    not interested in any notification to determine whether the
    child process has already exited or not.

    *  Process::RUN_NOTIFYONEXIT -- The child process is invoked both the
    child and the parent process run concurrently.

    When the child process exits, the Process instance
    corresponding to it emits the Qt signal @ref processExited().

    Since this signal is @em not emitted from within a UN*X
    signal handler, arbitrary function calls can be made.

    Be aware: When the Process objects gets destructed, the child
    process will be killed if it is still running!
    This means in particular, that you cannot use a Process on the stack
    with Process::RUN_NOTIFYONEXIT.

    *  Process::RUN_BLOCK -- The child process starts and the parent process
    is suspended until the child process exits. (@em Really not recommended
    for programs with a GUI.)

    Process also provides several functions for determining the exit status
    and the pid of the child process it represents.

    Furthermore it is possible to supply command-line arguments to the process
    in a clean fashion (no null -- terminated stringlists and such...)

    A small usage example:
    <pre>
    Process *proc = new Process;

    *proc << "my_executable";
    *proc << "These" << "are" << "the" << "command" << "line" << "args";
    QApplication::connect(proc, SIGNAL(processExited(Process *)),
                          pointer_to_my_object, SLOT(my_objects_slot(Process *)));
    proc.start();
    </pre>

    This will start "my_executable" with the commandline arguments "These"...

    When the child process exits, the respective Qt signal will be emitted.

    @sect Communication with the child process

    Process supports communication with the child process through
    stdin/stdout/stderr.

    The following functions are provided for getting data from the child
    process or sending data to the child's stdin (For more information,
    have a look at the documentation of each function):

    * bool @ref writeStdin(char  *buffer, int  buflen);
    *  -- Transmit data to the child process's stdin.

    * bool @ref closeStdin();
    * -- Closes the child process's stdin (which causes it to see an  feof(stdin)).
    Returns False if you try to close stdin for a process that has been started
    without a communication channel to stdin.

    * bool @ref closeStdout();
    * -- Closes the child process's stdout.
    Returns False if you try to close stdout for a process that has been started
    without a communication channel to stdout.

    * bool @ref closeStderr();
    * -- Closes the child process's stderr.
    Returns False if you try to close stderr for a process that has been started
    without a communication channel to stderr.


    @sect QT signals:

    * void @ref receivedStdout(Process  *proc, char  *buffer, int  buflen);
    *  void @ref receivedStderr(Process  *proc, char  *buffer, int  buflen);
    *  -- Indicates that new data has arrived from either the
    child process's stdout or stderr.

    *  void @ref wroteStdin(Process  *proc);
    *  -- Indicates that all data that has been sent to the child process
    by a prior call to @ref writeStdin() has actually been transmitted to the
    client .
    """

    def __init__(self): 
        """
        RunMode self.run_mode
          How to run the process (RUN_BLOCK, RUN_NOTIFYONEXIT, RUN_DONTCARE). You should
          not modify this data member directly from derived classes.
          
        bool running
          True if the process is currently running.
          
        pid_t pid
          Returns the process id of the process.
          If it is called after the process has exited, it returns the process
          id of the last child process that was created by this instance of
          Process.
          Calling it before any child process has been started by this
          Process instance causes pid to be 0.
          
        int status        
          The process' exit status as returned by "waitpid". You should not
          modify the value of this data member from derived classes. You should
          rather use @ref exitStatus than accessing this data member directly
          since it will probably be made private in further versions of
          Process.
          
        bool run_privileged
          Controls whether the started process should drop any setuid/segid
          privileges or whether it should keep them. The default is @p False :
          drop privileges

        Communication communication
          Lists the communication links that are activated for the child
          process.  Should not be modified from derived classes.
          
        const char *input_data  // the buffer holding the data
        int input_sent          // # of bytes already transmitted
          information about the data that has to be sent to the child:

        ProcessEnv d
          process environment
          
        QValueList<QCString> arguments
          The list of the process' command line arguments. The first entry
          in this list is the executable itself.
        """
        super(Process, self).__init__()
        self.pid = None
        self.status = None
        self.running = False
        self.run_privileged = False
        self.run_mode = RUN_NOTIFYONEXIT
        self.communication = COMM_NOCOMMUNICATION
        self._input_data = ''
        self._input_sent = 0
        self.d = ProcessEnv()
        # the socket descriptors for stdin/stdout/stderr
        self.in_ = [-1, -1]
        self.out = [-1, -1]
        self.err = [-1, -1]
        # the socket notifiers for the above socket descriptors
        self._innot = None
        self._outnot = None
        self._errnot = None
        procctrl.theProcessController.addProcess(self)
        self._arguments = []
        
    def XXX__del__(self):
        # destroying the Process instance sends a SIGKILL to the
        # child process (if it is running) after removing it from the
        # list of valid processes (if the process is not started as
        # "RUN_DONTCARE")
        procctrl.theProcessController.removeProcess(self)
        # this must happen before we kill the child
        # TODO: block the signal while removing the current process from the process list
        if self.running and self.run_mode != RUN_DONTCARE:
            self.kill(signal.SIGKILL)
        # Clean up open fd's and socket notifiers.
        self.closeStdin()
        self.closeStdout()
        self.closeStderr()
        # TODO: restore SIGCHLD and SIGPIPE handler if this is the last Process

    def detach(self):
        """Detaches Process from child process. All communication is closed.
        
        No exit notification is emitted any more for the child process.
        Deleting the Process will no longer kill the child process.
        Note that the current process remains the parent process of the child
        process.
        """
        procctrl.theProcessController.removeProcess(self)
        self.running = False
        self.pid = 0
        # clean up open fd's and socket notifiers.
        self.closeStdin()
        self.closeStdout()
        self.closeStderr()

    def closeStdin(self):
        """This causes the stdin file descriptor of the child process to be
        closed indicating an "EOF" to the child.
   
        @return @p False if no communication to the process's stdin
        had been specified in the call to @ref start().
        """
        if self.communication & COMM_STDIN:
            self.communication = self.communication & ~COMM_STDIN
            self._innot = None
            self.in_[1].close()
            return True
        return False

    def closeStdout(self):
        """This causes the stdout file descriptor of the child process to be
        closed.
   
        @return @p False if no communication to the process's stdout
        had been specified in the call to @ref start().
        """
        if self.communication & COMM_STDOUT:
            self.communication = self.communication & ~COMM_STDOUT
            self._outnot = None
            self.out[0].close()
            return True
        return False

    def closeStderr(self):
        """This causes the stderr file descriptor of the child process to be
        closed.

        @return @p False if no communication to the process's stderr
        had been specified in the call to @ref start().
        """
        if self.communication & COMM_STDERR:
            self.communication = self.communication & ~COMM_STDERR
            self._errnot = None
            self.err[0].close()
            return True
        return False

    def normalExit(self):
        """@return @p True if the process has already finished and has exited
        "voluntarily", ie: it has not been killed by a signal.
   
        Note that you should check @ref Process::exitStatus() to determine
        whether the process completed its task successful or not.
        """
        return self.pid and not self.running and os.WIFEXITED(self.status)
    
    def exitStatus(self):
        """Returns the exit status of the process.
   
        Please use @ref Process::normalExit() to check whether the process has
        exited cleanly (i.e., @ref Process::normalExit() returns @p True)
        before calling this function because if the process did not exit
        normally, it does not have a valid exit status.
        """
        return os.WEXITSTATUS(self.status)
    
    def processHasExited(self, state):
        """Immediately called after a process has exited. This function normally
        calls commClose to close all open communication channels to this
        process and emits the "processExited" signal (if the process was
        not running in the "RUN_DONTCARE" mode).
        """
        if self.running:
            self.running = False
            self.status = state
        self.commClose()
        # also emit a signal if the process was run Blocking
        if RUN_DONTCARE != self.run_mode:
            self.emit(qt.PYSIGNAL('processExited(Process*)'), self)

    def childOutput(self, fdno):
        """Called by "slotChildOutput" this function copies data arriving from the
        child process's stdout to the respective buffer and emits the signal
        "@ref receivedStderr".
        """
        if self.communication & COMM_NOREAD:
            len_ = -1
            # XXX We have a problem here: the slot is supposed to change the value of len_
            # at least, dataReceived does it in the c++ version
            # Don't know how to do this in Python. 
            self.emit(qt.PYSIGNAL("receivedStdout(int, int&)"), fdno, len_)
        else:
            buffer = os.read(fdno, 1024)
            len_ = len(buffer)
            if buffer:
                self.emit(qt.PYSIGNAL("receivedStdout(Process*, char*, int)"), self, buffer, len_)
        return len_

    def childError(self, fdno):
        """Called by "slotChildError" this function copies data arriving from the
        child process's stdout to the respective buffer and emits the signal
        "@ref receivedStderr"
        """
        buffer = os.read(fdno, 1024)
        len_ = len(buffer)
        if buffer:
            self.emit(qt.PYSIGNAL("receivedStderr(Process*, char*, int)"), self, buffer, len_)
        return len_

    # Functions for setting up the sockets for communication:
    #
    # - setupCommunication is called from "start" before "fork"ing.
    # - parentSetupCommunication completes communication socket setup in the parent
    # - childSetupCommunication completes communication setup in the child process
    # - commClose frees all allocated communication resources in the parent
    #   after the process has exited
    
    def setupCommunication(self, comm):
        """ This function is called from "Process::start" right before a "fork"
        takes place. According to the "comm" parameter this function has to
        initialize the "in", "out" and "err" data member of Process.

        This function should return 0 if setting the needed communication channels
        was successful.

        The default implementation is to create UNIX STREAM sockets for the communication,
        but you could overload this function and establish a TCP/IP communication for
        network communication, for example.
        """
        if comm & COMM_STDIN:
            self.in_ = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        if comm & COMM_STDOUT:
            self.out = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        if comm & COMM_STDERR:
            self.err = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        self.communication = comm

    def _childSetupCommunication(self):
        """
        Called right after a (successful) fork, but before an "exec" on the
        child process' side. It usually just closes the unused communication
        ends of "in", "out" and "err" (like the writing end of the "in"
        communication channel).

        see "man 7 socket" for explanation on SO_LINGER. Here it disabled so
        that the "close" call returns immediately and the closing is done in
        the background.
        """
        if self.communication & COMM_STDIN:
            self.in_[1].close()
        if self.communication & COMM_STDOUT:
            self.out[0].close()
        if self.communication & COMM_STDERR:
            self.err[0].close()
        # stdin
        if self.communication & COMM_STDIN:
            os.dup2(self.in_[0].fileno(), sys.stdin.fileno())
        else:
            null_fd = os.open( "/dev/null", os.O_RDONLY)
            os.dup2(null_fd, sys.stdin.fileno())
            os.close(null_fd)
        # stdout
        if self.communication & COMM_STDOUT:
            os.dup2(self.out[1].fileno(), sys.stdout.fileno())
            self.out[1].setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                   struct.pack('ii', 0, 0))
        else:
            null_fd = os.open( "/dev/null", os.O_WRONLY)
            os.dup2(null_fd, sys.stdout.fileno())
            os.close(null_fd)
        # stderr
        if self.communication & COMM_STDERR:
            os.dup2(self.err[1].fileno(), sys.stderr.fileno())
            self.err[1].setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                   struct.pack('ii', 0, 0))
        else:
            null_fd = os.open( "/dev/null", os.O_WRONLY)
            os.dup2(null_fd, sys.stderr.fileno())
            os.close(null_fd)

    def _parentSetupCommunication(self):
        """Called right after a (successful) fork on the parent side. This function
        will usually do some communications cleanup, like closing the reading end
        of the "stdin" communication channel.
   
        Furthermore, it must also create the QSocketNotifiers "innot", "outnot" and
        "errnot" and connect their Qt slots to the respective Process member functions.
        """
        if self.communication != COMM_NOCOMMUNICATION:
            if self.communication & COMM_STDIN:
                os.close(self.in_[0])
            if self.communication & COMM_STDOUT:
                os.close(self.out[1])
            if self.communication & COMM_STDERR:
                os.close(self.err[1])
        # Don't create socket notifiers and set the sockets non-blocking if
        # blocking is requested.
        if self.run_mode == RUN_BLOCK:
            return
        if self.communication & COMM_STDIN:
            # fcntl(in_[1], F_SETFL, O_NONBLOCK))
            self._innot = qt.QSocketNotifier(self.in_[1], qt.QSocketNotifier.Write)
            self._innot.setEnabled(False) # will be enabled when data has to be sent
            self.connect(self._innot, qt.SIGNAL('activated(int)'), self.slotSendData)
        if self.communication & COMM_STDOUT:
            # fcntl(out[0], F_SETFL, O_NONBLOCK))
            self._outnot = qt.QSocketNotifier(self.out[0], qt.QSocketNotifier.Read)
            self.connect(self._outnot, qt.SIGNAL('activated(int)'), self.slotChildOutput)
            if self.communication & COMM_NOREAD:
                self.suspend()
        if self.communication & COMM_STDERR:
            # fcntl(err[0], F_SETFL, O_NONBLOCK))
            self._errnot = qt.QSocketNotifier(self.err[0], qt.QSocketNotifier.Read)
            self.connect(self._outnot, qt.SIGNAL('activated(int)'), self.slotChildError)

    def commClose(self):
        """Should clean up the communication links to the child after it has
        exited. Should be called from "processHasExited".
        """
        if COMM_NOCOMMUNICATION == self.communication:
            return
        b_in = self.communication & COMM_STDIN
        b_out = self.communication & COMM_STDOUT
        b_err = self.communication & COMM_STDERR
        if b_in:
            self._innot = None

        if b_out or b_err:
            # If both channels are being read we need to make sure that one socket buffer
            # doesn't fill up whilst we are waiting for data on the other (causing a deadlock).
            # Hence we need to use select.
            # Once one or other of the channels has reached EOF (or given an error) go back
            # to the usual mechanism.
            if b_out:
                fcntl.fcntl(self.out[0].fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
                self._outnot = None
            if b_err:
                fcntl.fcntl(self.err[0].fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
                self._errnot = None
            while b_out or b_err:
                # * If the process is still running we block until we
                # receive data. (p_timeout = 0, no timeout)
                # * If the process has already exited, we only check
                # the available data, we don't wait for more.
                # (p_timeout = &timeout, timeout immediately)
                if self.running:
                    timeout = None
                else:
                    timeout = 0
                rfds = []
                if b_out:
                    rfds.append(self.out[0])
                if b_err:
                    rfds.append(self.err[0])
                rlist, wlist, xlist = select.select(rfds, [], [], p_timeout)
                if not rlist:
                    break
                if b_out and self.out[0] in rlist:
                    ret = 1
                    while ret > 0:
                        ret = self.childOutput(self.out[0].fileno())
                    if (ret == -1 and errno != EAGAIN) or ret == 0:
                        b_out = False
                if b_err and self.err[0] in rlist:
                    ret = 1
                    while ret > 0:
                        ret = self.childError(err[0].fileno())
                    if (ret == -1 and errno != EAGAIN) or ret == 0:
                        b_err = False
        if self.communication & COMM_STDIN:
            self.communication = self.communication & ~COMM_STDIN
            self.in_[1].close()
        if self.communication & COMM_STDOUT:
            self.communication = self.communication & ~COMM_STDOUT
            self.out[0].close()
        if self.communication & COMM_STDERR:
            self.communication = self.communication & ~COMM_STDERR
            self.err[0].close()

    def _childSetupEnvironment(self):
        """Sets up the environment according to the data passed via
        setEnvironment(...)
        
        * Modifies the environment of the process to be started.
        * This function must be called before starting the process.        
        """
        for key, val in self.d.env.items():
            os.environ[key] = val
        if self.d.wd:
            os.chdir(self.d.wd)

    def start(self, runmode=None, comm=None):
        """Starts the process.
        
        For a detailed description of the various run modes and communication
        semantics, have a look at the general description of the Process class.
        
        The following problems could cause this function to raise an exception:
   
        * The process is already running.
        * The command line argument list is empty.
        * The starting of the process failed (could not fork).
        * The executable was not found.
   
        @param comm  Specifies which communication links should be
        established to the child process (stdin/stdout/stderr). By default,
        no communication takes place and the respective communication
        signals will never get emitted.
   
        @return True on success, False on error
        (see above for error conditions)
        """
        uid, gid = self._startInit(runmode, comm)
        fd = os.pipe()
        # note that we use fork() and not vfork() because vfork() has unclear
        # semantics and is not standardized.
        self.pid = os.fork()
        if 0 == self.pid:
            self._childStart(uid, gid, fd, self._arguments)            
        else:
            self._parentStart(fd)

    def _startInit(self, runmode, comm):
        """initialisation part of the start method"""
        if self.running:
            raise Exception('cannot start a process that is already running')
        if not self._arguments:
            raise Exception('no executable has been assigned')
        if runmode is None:
            runmode = self.run_mode
        if comm is None:
            comm = self.communication
        self.run_mode = runmode
        self.status = 0
        self.setupCommunication(comm)
        # We do this in the parent because if we do it in the child process
        # gdb gets confused when the application runs from gdb.
        uid = os.getuid()
        gid = os.getgid()
        # get password entry to know user name / default group
        #pw_entry = pwd.getpwuid(uid)
        self.running = True
        #QApplication::flushX()
        return uid, gid
    
    def _childStart(self, uid, gid, fd, arguments):
        """parent process part of the start method"""
        if fd[0]:
            os.close(fd[0])
        if not self.run_privileged:
            os.setgid(gid)
            # XXX implement initgroups (cf pw_entry above for necessary information) 
            #if defined( HAVE_INITGROUPS)
            # if(pw)
            #    initgroups(pw.pw_name, pw.pw_gid)
            #endif
            os.setuid(uid)
        self._childSetupCommunication()
        self._childSetupEnvironment()
        # Matthias
        if self.run_mode == RUN_DONTCARE:
            os.setpgid(0, 0)
        # restore default SIGPIPE handler (Harri)
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        # We set the close on exec flag.
        # Closing of fd[1] indicates that the execvp succeeded!
        if fd[1]:
            fcntl.fcntl(fd[1], fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        os.execvp(arguments[0], arguments)
        # somethings went wrong... XXX cant be there in python
        if fd[1]:
            os.write(fd[1], chr(1))
        sys.exit(-1)
        
    def _parentStart(self, fd):
        """parent process part of the start method"""
        if fd[1]:
            os.close(fd[1])
        # Discard any data for stdin that might still be there
        self._input_data = ''
        # Check whether client could be started.
        if fd[0]:
            while True:
                resultByte = os.read(fd[0], 1)
                if not resultByte:
                    break # success
                if ord(resultByte) == 1:
                    # Error
                    self.running = False
                    os.close(fd[0])
                    self.pid = 0
                    return False
                #if not resultByte:
                #    # if ((errno == ECHILD) or (errno == EINTR))
                #    continue # Ignore
                break # success
        if fd[0]:
            os.close(fd[0])
        self._parentSetupCommunication()
        if self.run_mode == RUN_BLOCK:
            self.commClose()
            # The SIGCHLD handler of the process controller will catch
            # the exit and set the status
            while self.running: # XXX
                procctrl.theProcessController.waitForProcessExit(10)
            self.emit(qt.PYSIGNAL("processExited(Process*)"), self)
        
    def kill(self, signo):
        """Stop the process (by sending it a signal).
        
        @param signo	The signal to send. The default is SIGTERM.
        @return @p True if the signal was delivered successfully.
        """
        os.kill(self.pid, signo)

    def suspend(self):
        """Suspend processing of data from stdout of the child process.
        """
        if (self.communication & COMM_STDOUT) and self._outnot:
            self._outnot.setEnabled(False)

    def resume(self):
        """Resume processing of data from stdout of the child process.
        """
        if (self.communication & COMM_STDOUT) and self._outnot:
            self._outnot.setEnabled(True)

    def setEnvironment(self, name, value):
        self.d.env[name] = value
        
    def setWorkingDirectory(self, directory):
        """Changes the current working directory (CWD) of the process to be
        started. This function must be called before starting the process.
        """
        self.d.wd = directory

    def setExecutable(self, proc):
        """The use of this function is now deprecated. -- Please use the
        "operator<<" instead of "setExecutable".
        Sets the executable to be started with this Process object.
        Returns False if the process is currently running (in that
        case the executable remains unchanged.)
        """
        if self.running: return False
        if not proc: return False
        self._arguments = [proc]
        return True

    def __lshift__(self, arg):
        """Sets the executable and the command line argument list for this process.
   
        For example, doing an "ls -l /usr/local/bin" can be achieved by:
        
        Process p
        ...
        p << "ls" << "-l" << "/usr/local/bin"
        """
        self._arguments.append(arg)
        return self

    def clearArguments(self):
        """Clear a command line argument list that has been set by using
        the "operator<<".
        """
        self._arguments = []

    def writeStdin(self, string):
        """Transmit data to the child process's stdin.
   
        it may return False in the following cases:
   
        * The process is not currently running.
        * Communication to stdin has not been requested in the @ref start() call.
        * Transmission of data to the child process by a previous call to
        
        @ref writeStdin() is still in progress.
   
        Please note that the data is sent to the client asynchronously,
        so when this function returns, the data might not have been
        processed by the child process.
   
        If all the data has been sent to the client, the signal
        @ref wroteStdin() will be emitted.
   
        Please note that you must not call @ref writeStdin()
        again until either a @ref wroteStdin() signal indicates that the
        data has been sent or a @ref processHasExited() signal shows that
        the child process is no longer alive...
        """
        # if there is still data pending, writing new data
        # to stdout is not allowed (since it could also confuse
        # process...
        if not self._input_data:
            return False

        if self.running and self.communication & COMM_STDIN:
            self._input_data = string
            self._input_sent = 0
            self.slotSendData(0)
            self._innot.setEnabled(True)
            return True
        return False

    def slotChildOutput(self, fdno):
        """This slot gets activated when data from the child's stdout arrives.
        It usually calls "childOutput"
        """
        if not self.childOutput(fdno):
            self.closeStdout()

    def slotChildError(self, fdno):
        """This slot gets activated when data from the child's stderr arrives.
        It usually calls "childError"
        """
        if not self.childError(fdno):
            self.closeStderr()

    def slotSendData(self, int):
        """Called when another bulk of data can be sent to the child's
        stdin. If there is no more data to be sent to stdin currently
        available, this function must disable the QSocketNotifier "innot".
        """
        if self._input_sent == len(self._input_data):
            self._innot.setEnabled(False)
            self._input_data = ''
            self._input_sent = 0
            self.emit(qt.SIGNAL("wroteStdin(Process*)"), self)
        else:
            self._input_sent += os.write(self.in_[1].fileno(),
                                         self._input_data[self._input_sent:])

from pyqonsole import procctrl
