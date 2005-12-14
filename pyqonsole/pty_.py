"""Pseudo Terminal Device
                                                               
---------------------------------------------------------------
Copyright (c) 1997,1998 by Lars Doelle <lars.doelle@on-line.de>
                                                               
This file is part of Konsole - an X terminal for KDE           
---------------------------------------------------------------

TEPty

    Ptys provide a pseudo terminal connection to a program.

    Although closely related to pipes, these pseudo terminal connections have
    some ability, that makes it nessesary to uses them. Most importent, they
    know about changing screen sizes and UNIX job control.

    Within the terminal emulation framework, this class represents the
    host side of the terminal together with the connecting serial line.

    One can create many instances of this class within a program.
    As a side effect of using this class, a signal(2) handler is
    installed on SIGCHLD.


    FIXME

    [NOTE: much of the technical stuff below will be replaced by forkpty.]

    publish the SIGCHLD signal if not related to an instance.

    clearify TEPty::done vs. TEPty::~TEPty semantics.
    check if pty is restartable via run after done.


    Pseudo terminals

    Pseudo terminals are a unique feature of UNIX, and always come in form of
    pairs of devices (/dev/ptyXX and /dev/ttyXX), which are connected to each
    other by the operating system. One may think of them as two serial devices
    linked by a null-modem cable. Being based on devices the number of
    simultanous instances of this class is (globally) limited by the number of
    those device pairs, which is 256.

    Another technic are UNIX 98 PTY's. These are supported also, and prefered
    over the (obsolete) predecessor.

    There's a sinister ioctl(2), signal(2) and job control stuff
    nessesary to make everything work as it should.

    Much of the stuff can be simplified by using openpty from glibc2.
    Compatibility issues with obsolete installations and other unixes
    may prevent this.

XXX  signals:

    /*! emitted when the client program terminates.
        \param status the wait(2) status code of the terminated client program.
    */
    void done(int status)

    /*! emitted when a new block of data comes in.
        \param s - the data
        \param len - the length of the block
    */
    void block_in(const char* s, int len)

"""
__revision__ = '$Id: pty_.py,v 1.6 2005-12-14 12:59:03 syt Exp $'

import os
import sys
from pty import openpty
from struct import pack
from fcntl import ioctl, fcntl, F_SETFL
from resource import getrlimit, RLIMIT_NOFILE
from termios import tcgetattr, tcsetattr, VINTR, VQUIT, VERASE, \
     TIOCSPGRP, TCSANOW, TIOCSWINSZ, TIOCSCTTY
import signal

import qt

from pyqonsole.process import Process, RUN_BLOCK, RUN_NOTIFYONEXIT, \
     COMM_STDOUT, COMM_NOREAD

HAVE_UTEMPTER = os.path.exists("/usr/sbin/utempter")


class UtmpProcess(Process):

    def __init__(self, fd, option, ttyname):
        super(UtmpProcess, self).__init__()
        self.cmd_fd = fd
        assert option in ('-a', '-q')
        self << "/usr/sbin/utempter" << option << ttyname

    def _childSetupCommunication(self):
        os.dup2(self.cmd_fd, 0)   
        os.dup2(self.cmd_fd, 1)   
        os.dup2(self.cmd_fd, 3)
        return 1


class Job:
    def __init__(self, string):
        self.start = 0
        self.string = string
        self.length = len(string)

    def finished(self):
        return self.start == len(self.string)

    
class PtyProcess(Process):
    """fork a process using a controlling terminal
    """

    def __init__(self):
        super(PtyProcess, self).__init__()
        self.wsize = (0, 0)
        self.addutmp = False
        self.term = None
        #self.needGrantPty = False
        self.openPty()
        self.pending_send_jobs = []
        self.pending_send_job_timer = None
        self.connect(self, qt.PYSIGNAL('receivedStdout'), self.dataReceived)
        self.connect(self, qt.PYSIGNAL('processExited'),  self.donePty)
        
    def run(self, pgm, args, term, addutmp):
        """start the client program
        
        having a `run' separate from the constructor allows to make
        the necessary connections to the signals and slots of the
        instance before starting the execution of the client
        """
        self.term = term
        self.addutmp = addutmp
        #self.clearArguments() # XXX not needed because of the code below
        self._arguments = [pgm] + args
        self.start(RUN_NOTIFYONEXIT, COMM_STDOUT | COMM_NOREAD)
        self.resume()

    def startPgm(self, pgm, args, term):
        """only used internally. See `run' for interface"""
        tt = self.makePty() # slave_fd
        # reset signal handlers for child process
        for i in range(signal.NSIG):
            signal.signal(i, signal.SIG_DFL)

        # Don't know why, but his is vital for SIGHUP to find the child.
        # Could be, we get rid of the controling terminal by this.
        soft, hard = getrlimit(RLIMIT_NOFILE)
        # We need to close all remaining fd's.
        # Especially the one used by Process.start to see if we are running ok.
        for i in range(soft):
            # FIXME: (result of merge) Check if (not) closing fd is OK)
            if i != tt:# and i != self.master_fd):
                try:
                    os.close(i)
                except OSError:
                    continue
        os.dup2(tt, sys.stdin.fileno())
        os.dup2(tt, sys.stdout.fileno())
        os.dup2(tt, sys.stderr.fileno())

        if tt > 2:
            os.close(tt)

        # Setup job control #################

        # This is pretty obscure stuff which makes the session
        # to be the controlling terminal of a process group.
        os.setsid()

        ioctl(0, TIOCSCTTY, '')
        # This sequence is necessary for event propagation. Omitting this
        # is not noticeable with all clients (bash,vi). Because bash
        # heals this, use '-e' to test it.
        pgrp = os.getpid()                          
        ioctl(0, TIOCSPGRP, pack('i', pgrp))
        os.setpgid(0, 0)
        os.close(os.open(os.ttyname(tt), os.O_WRONLY))
        os.setpgid(0, 0)

        tty_attrs = tcgetattr(0)
        tty_attrs[-1][VINTR] = CTRL('C')
        tty_attrs[-1][VQUIT] = CTRL('\\')
        tty_attrs[-1][VERASE] = 0177
        tcsetattr(0, TCSANOW, tty_attrs);

        #os.close(self.master_fd)

        # drop privileges
        os.setgid(os.getgid())
        os.setuid(os.getuid())

        # propagate emulation
        if self.term:
            os.environ['TERM'] = term
        ioctl(0, TIOCSWINSZ, pack('ii', *self.wsize))

        # finally, pass to the new program
        os.execvp(pgm, args)
        #execvp("/bin/bash", argv);
        sys.exit(1) # control should never come here.
        
    def openPty(self):
        """"""
        self.master_fd, self.slave_fd = openpty()
        fcntl(self.master_fd, F_SETFL, os.O_NDELAY)
        return self.master_fd
        
    def makePty(self):
        """"""
        # XXX: is master_fd already unlocked? Is it a problem if yes?
        #ifdef HAVE_UNLOCKPT
        #unlockpt(fd)
        #endif
        # Stamp utmp/wtmp if we have and want them
        if HAVE_UTEMPTER and self.addutmp:
            utmp = UtmpProcess(self.master_fd, '-a', os.ttyname(self.slave_fd))
            utmp.start(process.RUN_BLOCK)
        #ifdef USE_LOGIN
        #  char *str_ptr
        #  struct utmp l_struct
        #  memset(&l_struct, 0, sizeof(struct utmp))
        #  if (! (str_ptr=getlogin()) ) {
        #    if ( ! (str_ptr=getenv("LOGNAME"))) {
        #      abort()
        #    }
        #  }
        #  strncpy(l_struct.ut_name, str_ptr, UT_NAMESIZE)
        #  if (gethostname(l_struct.ut_host, UT_HOSTSIZE) == -1) {
        #     if (errno != ENOMEM)
        #        abort()
        #     l_struct.ut_host[UT_HOSTSIZE]=0
        #  }
        #  if (! (str_ptr=ttyname(tt)) ) {
        #    abort()
        #  }
        #  if (strncmp(str_ptr, "/dev/", 5) == 0)
        #       str_ptr += 5
        #  strncpy(l_struct.ut_line, str_ptr, UT_LINESIZE)
        #  time(&l_struct.ut_time) 
        #  login(&l_struct)
        #endif
        return self.slave_fd

            
    def setWriteable(self, writeable):
        """set the slave pty writable"""
        ttyname = os.ttyname(self.slave_fd)
        mode = stat(ttyname)
        if writeable:
            mode.st_mode |= os.S_IWGRP
        else:
            mode.st_mode &= ~(os.S_IWGRP|os.S_IWOTH)
        os.chmod(ttyname, mode)
                
    def setSize(self, lines, columns):
        """Informs the client program about the actual size of the window."""
        self.wsize = (lines, columns)
        if self.master_fd is None:
            return
        ioctl(self.master_fd, TIOCSWINSZ, pack('ii', lines, columns))
        
    def setupCommunication(self, comm):
        """overriden from Process"""
        self.out[0] = self.master_fd
        self.out[1] = os.dup(2) # Dummy
        self.communication = comm
        
    def _childSetupCommunication(self):
        """overriden from Process"""
        pgm = self._arguments.pop(0)
        self.startPgm(pgm, self._arguments, self.term)
        
    def sendBytes(self, string):
        """sends len bytes through the line"""
        if self.pending_send_jobs:
            self.appendSendJob(string)
        else:
            written = 0
            while written < len(string):
                written += os.write(self.master_fd, string[written:])
                #if ( errno==EAGAIN || errno==EINTR )
                #      appendSendJob(s,len)
                #      return

    def appendSendJob(self, string):
        """"""
        self.pending_send_jobs.append(Job(string))
        if not self.pending_send_job_timer:
            self.pending_send_job_timer = qt.QTimer()
            self.connect(self.pending_send_job_timer, qt.SIGNAL('timeout()'),
                         self.doSendJobs)
        self.pending_send_job_timer.start(0)

    def doSendJobs(self):
        """qt slot"""
        written = 0
        while pending_send_jobs:
            job = pending_send_jobs[0]
            job.start += os.write(self.master_fd, job.string[job.start:])
            #if ( errno!=EAGAIN and errno!=EINTR )
            #   pending_send_jobs.remove(pending_send_jobs.begin())
            #   return
            if job.finished():
                pending_send_jobs.remove(job)
        if self.pending_send_job_timer:
            self.pending_send_job_timer.stop()

    def dataReceived(self):
        """qt slot: indicates that a block of data is received """
        buf = os.read(self.master_fd, 4096);
        self.emit(qt.PYSIGNAL('block_in'), (buf,))
              
    def donePty(self):
        """qt slot"""
        if HAVE_UTEMPTER:
            utmp = UtmpProcess(self.master_fd, '-d', os.ttyname(self.slave_fd))
            utmp.start(RUN_BLOCK)
        #elif defined(USE_LOGIN)
        #  char *tty_name=ttyname(0)
        #  if (tty_name)
        #  {
        #        if (strncmp(tty_name, "/dev/", 5) == 0)
        #            tty_name += 5
        #        logout(tty_name)
        #  }
        #endif
        #if (needGrantPty) chownpty(fd,False)
        self.emit(qt.PYSIGNAL('done', (self.exitStatus(),)))



## #define PTY_FILENO 3
## #define BASE_CHOWN "qonsole_grantpty"

## int chownpty(int fd, int grant)
## # param fd: the fd of a master pty.
## # param grant: 1 to grant, 0 to revoke
## # returns 1 on success 0 on fail
## {
##   struct sigaction newsa, oldsa;
##   newsa.sa_handler = SIG_DFL;
##   newsa.sa_mask = sigset_t();
##   newsa.sa_flags = 0;
##   sigaction(SIGCHLD, &newsa, &oldsa);

##   pid_t pid = fork();
##   if (pid < 0)
##   {
##     # restore previous SIGCHLD handler
##     sigaction(SIGCHLD, &oldsa, NULL);

##     return 0;
##   }
##   if (pid == 0)
##   {
##     # We pass the master pseudo terminal as file descriptor PTY_FILENO. */
##     if (fd != PTY_FILENO and dup2(fd, PTY_FILENO) < 0) exit(1);
## #    QString path = locate("exe", BASE_CHOWN);
##     QString path = BASE_CHOWN;
##     execle(path.ascii(), BASE_CHOWN, grant?"--grant":"--revoke", NULL, NULL);
##     exit(1); # should not be reached
##   }

##   if (pid > 0) {
##     int w;
## retry:
##     int rc = waitpid (pid, &w, 0);
##     if ((rc == -1) and (errno == EINTR))
##       goto retry;

##     # restore previous SIGCHLD handler
##     sigaction(SIGCHLD, &oldsa, NULL);

##     return (rc != -1 and WIFEXITED(w) and WEXITSTATUS(w) == 0);
##   }

##   return 0; #dummy.
## }
