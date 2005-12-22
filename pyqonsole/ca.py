# Copyright (c) 2005 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V1.pdf
#
""" Provide the Ca class.

This class implements a character with rendition atributes.

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003, 2005
@organization: CEA-Grenoble
@organization: Logilab
@license: CECILL
"""

__revision__ = "$Id: ca.py,v 1.12 2005-12-22 17:39:44 syt Exp $"

BASE_COLORS = 2+8
INTENSITIES = 2
TABLE_COLORS = INTENSITIES*BASE_COLORS

DEFAULT_FORE_COLOR = 0
DEFAULT_BACK_COLOR = 1

DEFAULT_RENDITION = 0
RE_BOLD = 2**0
RE_BLINK = 2**1
RE_UNDERLINE = 2**2
RE_REVERSE = 2**3
RE_CURSOR = 2**4


## _CACHE = {}

## def Ca(c=ord(' '), f=DEFAULT_FORE_COLOR,
##        b=DEFAULT_BACK_COLOR, r=DEFAULT_RENDITION, _c=_CACHE):
##     assert f < TABLE_COLORS
##     assert b < TABLE_COLORS
##     try:
##         return _c[(c, f, b, r)]
##     except:
##         ca = _Ca(c, f, b, r)
##         _c[(c, f, b, r)] = ca
##         return ca
    
class Ca(object):
    """a character with background / foreground colors and rendition attributes
    """
    __slots__ = ('c', 'f', 'b', 'r')
    
    def __init__(self, c=ord(' '), f=DEFAULT_FORE_COLOR,
                 b=DEFAULT_BACK_COLOR, r=DEFAULT_RENDITION):
        self.c = c # character
        self.f = f # foreground color
        self.b = b # background color
        self.r = r # rendition
        
    def __eq__(self, other):
        """implements the '==' operator"""
        return (self.c == other.c and self.f == other.f and 
                self.b == other.b and self.r == other.r)
    
    def __ne__(self, other):
        """implements the '!=' operator"""
        return (self.c != other.c or self.f != other.f or 
                self.b != other.b or self.r != other.r)

    def __repr__(self):
        return '%r %s %s %r' % (chr(self.c), self.f, self.b, self.r)

    def isSpace(self):
        return unichr(self.c).isspace()

    def charClass(self, word_characters=u":@-./_~"):
        """return a kind of category for this char
        * space
        * alpha numeric
        * other
        """
        ch = unichr(self.c)
        if ch.isspace():
            return ' '
        if ch.isalnum() or ch in word_characters:
            return 'a'
        # Everything else is weird
        return 1

##     # XXX for debugging
##     def setC(self, c):
##         assert isinstance(c, int)
##         self._c = c
##     def getC(self):
##         return self._c
##     c = property(getC, setC)

DCA = Ca() # default character

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
