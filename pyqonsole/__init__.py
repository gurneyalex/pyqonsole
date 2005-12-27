"""pyqonsole is a python xterm, which may be used independantly or as a qt
widget
"""
__revision__ = "$Id: __init__.py,v 1.4 2005-12-27 13:21:45 syt Exp $"

def CTRL(c):
    """return the code of the given character when typed with the control
    button enabled
    """
    return ord(c) - ord("@")

