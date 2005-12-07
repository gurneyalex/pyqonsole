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

import os
import fcntl
import resource
import sys

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
    
class TEPty(Process):

    def __init__(self):
        self.wsize = (0, 0)
        self.addutmp = False
        self.term = None
        #self.needGrantPty = False
        self.openPty()
        self.pending_send_jobs = []
        self.pending_send_job_timer = None
        self.connect(self, qt.SIGNAL('receivedStdout(int, int &)'), self,
                     self.slotDataReceived)
        self.connect(self, qt.SIGNAL('processExited(Process *)'), self,
                     self.slotDonePty)
        
    def run(self, pgm, args, term, addutmp):
        """start the client program
        
        having a `run' separate from the constructor allows to make
        the necessary connections to the signals and slots of the
        instance before starting the execution of the client
        """
        self.term = term
        self.addutmp = addutmp
        #self.clearArguments() # XXX not needed because of the code below
        self.arguments = [pgm] + args
        self.start(RUN_NOTIFYONEXIT, COMM_STDOUT | COMM_NOREAD)
        self.resume()

    def startPgm(self, pgm, args, term):
        """only used internally. See `run' for interface"""
        tt = self.makePty()
        # reset signal handlers for child process
        for i in range(signal.NSIG):
            signal.signal(i, signalSIG_DFL)

        # Don't know why, but his is vital for SIGHUP to find the child.
        # Could be, we get rid of the controling terminal by this.
        # getrlimit is a getdtablesize() equivalent, more portable (David Faure)
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        # We need to close all remaining fd's.
        # Especially the one used by Process.start to see if we are running ok.
        for i in range(soft):
            # FIXME: (result of merge) Check if not closing fd is OK)
            if i != tt and i != self.master_fd):
                os.close(i)

        dup2(tt, sys.stdin.fileno())
        dup2(tt, sys.stdout.fileno())
        dup2(tt, sys.stderr.fileno())

          if (tt > 2) close(tt);

          # Setup job control #################

          # This is pretty obscure stuff which makes the session
          # to be the controlling terminal of a process group.

          if (setsid() < 0) perror("failed to set process group"); # (vital for bash)

        #if defined(TIOCSCTTY)
          ioctl(0, TIOCSCTTY, 0);
        #endif

          int pgrp = getpid();                 # This sequence is necessary for
        #ifdef _AIX
          tcsetpgrp (0, pgrp);
        #else
          ioctl(0, TIOCSPGRP, (char *)&pgrp);  # event propagation. Omitting this
        #endif
          setpgid(0,0);                        # is not noticeable with all
          close(open(ttynam, O_WRONLY, 0));       # clients (bash,vi). Because bash
          setpgid(0,0);                        # heals this, use '-e' to test it.

          # without the '::' some version of HP-UX thinks, this declares
             the struct in this class, in this method, and fails to find the correct
             t[gc]etattr */
          static struct ::termios ttmode;
        #undef CTRL
        #define CTRL(c) ((c) - '@')

        #if defined (__FreeBSD__) || defined (__NetBSD__) || defined (__OpenBSD__) || defined (__bsdi__)
              ioctl(0,TIOCGETA,(char *)&ttmode);
        #else
        #   if defined (_HPUX_SOURCE) || defined(__Lynx__)
              tcgetattr(0, &ttmode);
        #   else
              ioctl(0,TCGETS,(char *)&ttmode);
        #   endif
        #endif
              ttmode.c_cc[VINTR] = CTRL('C');
              ttmode.c_cc[VQUIT] = CTRL('\\');
              ttmode.c_cc[VERASE] = 0177;
        #if defined (__FreeBSD__) || defined (__NetBSD__) || defined (__OpenBSD__) || defined (__bsdi__)
              ioctl(0,TIOCSETA,(char *)&ttmode);
        #else
        #   ifdef _HPUX_SOURCE
              tcsetattr(0, TCSANOW, &ttmode);
        #   else
              ioctl(0,TCSETS,(char *)&ttmode);
        #   endif
        #endif

          close(fd);

          # drop privileges
          setgid(getgid()); setuid(getuid()); 

          # propagate emulation
          if (term and term[0]) setenv("TERM",term,1);

          # convert QStrList into char*[]
          unsigned int i;
          char **argv = (char**)malloc(sizeof(char*)*(args.count()+1));
        #  char **argv = (char**)malloc(sizeof(char*)*(args.count()+0));
          for (i = 0; i<args.count(); i++) {
             argv[i] = strdup(args[i]);
             }

          argv[i] = 0L;

          ioctl(0,TIOCSWINSZ,(char *)&wsize);  # set screen size

          # finally, pass to the new program
          execvp(pgm, argv);
          #execvp("/bin/bash", argv);
          perror("exec failed");
          exit(1);                             # control should never come here.
        }
        
    def openPty():
        """"""
        self.master_fd, self.slave_fd = pty.openpty()
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NDELAY)
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
        mode = stat(self.ttynam)
        if writeable:
            mode.st_mode |= os.S_IWGRP
        else:
            mode.st_mode &= ~(os.S_IWGRP|os.S_IWOTH)
        os.chmod(self.ttynam, mode)
                
    def setSize(int lines, int columns):
        """Informs the client program about the actual size of the window."""
        self.wsize = (lines, columns)
        if self.master_fd is None:
            return
        # XXX: TIOCSWINSZ not available from python ?
        fcntl.ioctl(self.master_fd, TIOCSWINSZ, struct('ii', lines, columns))
        
    def setupCommunication(self):
        """overriden from Process"""
        self.out[0] = self.master_fd
        self.out[1] = dup(2) # Dummy
        self.communication = comm
        
    def _childSetupCommunication(self):
        """overriden from Process"""
        pgm = self.arguments.pop(0)
        self.startPgm(pgm, self.arguments, self.term)
        
    def sendBytes(self, string):
        """sends len bytes through the line"""
        if self.pending_send_jobs:
            self.appendSendJob(string)
        else:
            written = 0
            while writen < len(string):
                written += os.write(self.master_fd, string[writen:])
                #if ( errno==EAGAIN || errno==EINTR )
                #      appendSendJob(s,len)
                #      return

    def appendSendJob(self, string):
        """"""
        self.pending_send_jobs.append(Job(string))
        if not self.pending_send_job_timer:
            self.pending_send_job_timer = qt.QTimer()
            self.connect(self.pending_send_job_timer, qt.SIGNAL('timeout()'), self,
                         self.slotDoSendJobs)
        self.pending_send_job_timer.start(0)

    def slotDoSendJobs():
        """"""
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
            self.pending_send_job_timer->stop()

    def slotDataReceived(int, int& len):
        """indicates that a block of data is received """
        buf = os.read(self.master_fd, 4096);
        self.emit(qt.SIGNAL('block_in(char*, int)', buf, len(buf))
              
    def slotDonePty():
        """"""
        status self.exitStatus()
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
        self.emit(qt.SIGNAL('done(int)', status))



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
