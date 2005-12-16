
import sys

import qt

from pyqonsole import keytrans
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
        if not f.exactMatch() and fontno != DEFAULTFONT:
            return
    else:
        f.setFamily("fixed")
        f.setFixedPitch(True)
        f.setPixelSize(int(FONTS[fontno]))
    te.setVTFont(f)


def main(argv):
    appli = qt.QApplication(argv)
    te = Widget(appli)
    te.setMinimumSize(150, 70)
    te.setFocus()
    te.resize(te.calcSize(80, 25))
    te.setBackgroundMode(qt.Qt.PaletteBackground)
    # w.setSize(80,25);
    setFont(te, 4) # 15
    appli.setMainWidget(te)
    te.show()
    args = []
    #args.append("/usr/bin/ipython");
    session = Session(te, "/usr/bin/python", args, "xterm");
    session.setConnect(True)
    session.setHistory(HistoryTypeBuffer(1000))
    session.run()
    appli.exec_loop()

if __name__ == '__main__':
##     import time
##     print "*" * 80
##     print "Move the mouse cursor to another ION panel to see stdout and pyqonsole"
##     print "*" * 80
##     print "3 seconds before launch..."
##     time.sleep(1)
##     print "2 seconds before launch..."
##     time.sleep(1)
##     print "1 second before launch..."
##     time.sleep(1)
##     print "let's rock!"
    main(sys.argv)
