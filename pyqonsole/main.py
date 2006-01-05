# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
"""module used to launch pyqonsole independantly

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Sylvain Thenault
@copyright: 2003, 2005
@organization: CEA-Grenoble
@organization: Logilab
@license: CECILL
"""

__revision__ = '$Id: main.py,v 1.16 2006-01-05 13:22:37 alf Exp $'

import sys
import signal
import os
import pwd

import qt

from pyqonsole.widget import Widget
from pyqonsole.session import Session
from pyqonsole.history import HistoryTypeBuffer

FONTS = [
    "13",
    "7",   # tiny font, never used
    "10",  # small font
    "13",  # medium
    "15",  # large
    "20",  # huge
    "-misc-console-medium-r-normal--16-160-72-72-c-160-iso10646-1", # "Linux"
    "-misc-fixed-medium-r-normal--15-140-75-75-c-90-iso10646-1",    # "Unicode"
    ]

#define TOPFONT (sizeof(fonts)/sizeof(char*))
#define DEFAULTFONT TOPFONT
TOPFONT = 0

def setFont(te, fontno):
    f = qt.QFont()
    if FONTS[fontno][0] == '-':
        f.setRawName(FONTS[fontno])
        if not f.exactMatch():
            return
    else:
        f.setFamily("fixed")
        f.setFixedPitch(True)
        f.setPixelSize(int(FONTS[fontno]))
    te.setVTFont(f)


def findExecutablePath(progname):
    if os.path.isabs(progname):
        return progname
    for dirname in os.getenv('PATH').split(os.pathsep):
        fullname = os.path.join(dirname, progname)
        if os.path.isfile(fullname) and os.access(fullname, os.X_OK):
            return fullname
    raise ValueError('%s not found in PATH' % progname)

def main(argv):
    appli = qt.QApplication(argv)
    te = Widget(appli)
    te.setScrollbarLocation(2)
    te.setMinimumSize(150, 70)
    te.setFocus()
    te.setBackgroundMode(qt.Qt.PaletteBackground)
    setFont(te, 4) # medium
    te.resize(te.calcSize(80, 25))
    appli.setMainWidget(te)
    te.show()
    if len(argv) > 1:
        progname = findExecutablePath(argv[1])
        args = argv[2:]
    else:
        progname = pwd.getpwuid(os.getuid()).pw_shell
        print 'no shell specified. Using %s' % progname
        args = []
    session = Session(te, progname, args, "xterm");
    session.setConnect(True)
    session.setHistory(HistoryTypeBuffer(1000))
    session.run()
    def quit(*args, **kwargs):
        appli.quit()
    session.myconnect('done', quit)
    # XXX dunno why I've to do that to make Ctrl-C in the original term working 
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    appli.exec_loop()

def profile(argv):
    from hotshot import Profile
    prof = Profile('pyqonsole.prof')
    prof.runcall(main, argv)
    prof.close()
    import hotshot.stats
    stats = hotshot.stats.load('pyqonsole.prof')
    stats.strip_dirs()
    stats.sort_stats('time', 'calls')
    stats.print_stats(30)

def showHelp():
    print "pyqonsole --help: displays this message"
    print "pyqonsole [options] [command]: runs command in the console"
    print "options:"
    print " --profile : displays profiling statistics when console exits"
    print "             (internal development use. You don't need this)"
    
def run(args=None):
    args = args or sys.argv
    if "--profile" in sys.argv:
        sys.argv.remove("--profile")
        profile(sys.argv)
    elif '--help' in sys.argv or '-h' in sys.argv:
        showHelp()
    else:
        main(sys.argv)
    

if __name__ == '__main__':
    run()
