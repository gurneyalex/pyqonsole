""" Provide the Ca class.

This class implements a character with rendition atributes.

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003
@organization: CEA-Grenoble
@license: ??
"""

__revision__ = "$Id: ca.py,v 1.3 2005-12-11 20:04:26 syt Exp $"

BASE_COLORS = 2+8
INTENSITIES = 2
TABLE_COLORS = INTENSITIES*BASE_COLORS

DEFAULT_FORE_COLOR = 0
DEFAULT_BACK_COLOR = 1

DEFAULT_RENDITION = 0
RE_BOLD = 2**0
RE_BLINK = 2**1
RE_UNDERLINE = 2**2
RE_REVERSE = 2**3   # Screen only
RE_INTENSIVE = 2**3 # Widget only
RE_CURSOR = 2**4


class Ca:
    """ Ca class.
    """
    def __init__(self, c=' ', f=DEFAULT_FORE_COLOR,
                 b=DEFAULT_BACK_COLOR, r=DEFAULT_RENDITION):
        """ Init a Ca instance.
        """
        self.c = c # character
        self.f = f # foreground color
        self.b = b # background color
        self.r = r # rendition
        
    def __eq__(self, other):
        """ Implements the '==' operator
        """
        return (self.c == other.c) and (self.f == other.f) and \
               (self.b == other.b) and (self.r == other.r)
    
    def __ne__(self, other):
        """ Implements the '!=' operator
        """
        return (self.c != other.c) or (self.f != other.f) or \
               (self.b != other.b) or (self.r != other.r)

class ColorEntry:

    def __init__(self, c=None, tr=False, b=False):
        self.color = c
        self.transparent = tr # if used on bg
        self.bold = b # if used on fg
        
    # XXX
    #void operator=(const ColorEntry& rhs) 
    #     color = rhs.color; 
    #     transparent = rhs.transparent; 
    #     bold = rhs.bold; 
