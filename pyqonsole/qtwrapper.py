
from pyqonsole import qtconfig

if qtconfig() == 3:
    import qt
    from qt import QObject, SIGNAL, QSocketNotifier, QTimer, QTextCodec, QEvent, Qt, QRegExp, QString, QRect, QSize, QPoint
elif qtconfig() == 4:
    print "using Qt4"
    from PyQt4 import QtGui as qt
    from PyQt4.QtCore import QObject, SIGNAL, QSocketNotifier, QTimer, QTextCodec, QEvent, Qt, QRegExp, QString, QRect, QSize, QPoint
