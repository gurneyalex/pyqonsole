""" Provide the Widget class.

Visible screen contents

   This class is responsible to map the `image' of a terminal emulation to the
   display. All the dependency of the emulation to a specific GUI or toolkit is
   localized here. Further, this widget has no knowledge about being part of an
   emulation, it simply work within the terminal emulation framework by exposing
   size and key events and by being ordered to show a new image.

   - The internal image has the size of the widget (evtl. rounded up)
   - The external image used in setImage can have any size.
   - (internally) the external image is simply copied to the internal
     when a setImage happens. During a resizeEvent no painting is done
     a paintEvent is expected to follow anyway.

FIXME:
   - 'image' may also be used uninitialized (it isn't in fact) in resizeEvent
   - 'font_a' not used in mouse events
   - add destructor

TODO
   - evtl. be sensitive to `paletteChange' while using default colors.
   - set different 'rounding' styles? I.e. have a mode to show clipped chars?

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Benjamin Longuet
@author: Frederic Mantegazza
@author: Cyrille Boullier
@copyright: 2003
@organization: CEA-Grenoble
@license: ??
"""


import qt

from screen import Screen


def loc(x, y):
    return y*self.__columns+x
    

class Widget(qt.QFrame):
    pass