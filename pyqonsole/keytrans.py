# Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
# Copyright (c) 2005-2006 CEA Grenoble 
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the CECILL license, available at
# http://www.inria.fr/valorisation/logiciels/Licence.CeCILL-V2.pdf
#
"""Provide the KeyTrans class.

The keyboard translation table allows to configure pyonsoles behavior
on key strokes.
FIXME: some bug crept in, disallowing '\0' to be emitted.

Based on the konsole code from Lars Doelle.

@author: Lars Doelle
@author: Sylvain Thenault
@copyright: 2003, 2005, 2006
@organization: Logilab
@license: CECILL
"""

__revision__ = '$Id: keytrans.py,v 1.15 2006-02-15 10:24:01 alf Exp $'


import re
import sys
from os.path import basename, dirname, splitext, join, isfile
import os

from pyqonsole.qtwrapper import Qt
from pyqonsole import qtconfig

for _path in [dirname(__file__),
              join(sys.exec_prefix, 'share/pyqonsole'),
              join(dirname(__file__), "../../../../share/pyqonsole"),
              join(dirname(__file__), "../../../share/pyqonsole/ "),
              os.environ.get('PYQONSOLE_KEYTAB_DIR', './'),
              ]:
    DEFAULT_KEYTAB_FILE = join(_path, 'default.keytab')
    if isfile(DEFAULT_KEYTAB_FILE):
        break
else:
    raise ValueError("Unable to find default.keytab."
                     "Set the PYQONSOLE_KEYTAB_DIR environment variable.")
del _path

BITS_NewLine   = 0
BITS_BsHack    = 1
BITS_Ansi      = 2
BITS_AppCuKeys = 3
BITS_Control   = 4
BITS_Shift     = 5
BITS_Alt       = 6
BITS_COUNT     = 7

def encodeModes(newline, ansi, appcukeys):    
    return newline + (ansi << BITS_Ansi) + (appcukeys << BITS_AppCuKeys)

def encodeButtons(control, shift, alt):    
    return (control << BITS_Control) + (shift << BITS_Shift) + (alt << BITS_Alt)

CMD_none             = -1
CMD_send             =  0
CMD_emitSelection    =  1
CMD_scrollPageUp     =  2
CMD_scrollPageDown   =  3
CMD_scrollLineUp     =  4
CMD_scrollLineDown   =  5
CMD_prevSession      =  6
CMD_nextSession      =  7
CMD_newSession       =  8
CMD_activateMenu     =  9
CMD_moveSessionLeft  = 10
CMD_moveSessionRight = 11
CMD_scrollLock       = 12
CMD_emitClipboard    = 13
CMD_renameSession    = 14

_KEYMAPS = {}

def loadAll():
    kt = KeyTrans()
    kt.addKeyTrans()
    # XXX load other keytab files ?
    
def find(ktid=0):
    if isinstance(ktid, int):
        try:
            return _KEYMAPS[ktid]
        except KeyError:
            pass
    for kt in _KEYMAPS.values():
        if kt.id == ktid:
            return kt
    return _KEYMAPS[0]

def count():
    return len(_KEYMAPS)

class EntryNotFound(Exception): pass

class KeyEntry:
    """instances represent the individual assignments"""
    def __init__(self, ref, key, bits, mask, cmd, txt):
        self.ref = ref
        self.key = key
        self.bits = bits
        self.mask = mask
        self.cmd = cmd
        self.txt = txt
        
    def matches(self, key, bits, mask):
        m = self.mask & mask
        return key == self.key and (self.bits & m) == (bits & m)
    
    def metaspecified(self):
        return (self.mask & (1 << BITS_Alt)) and (self.bits & (1 << BITS_Alt))


class KeyTrans:
    """combines the individual assignments to a proper map
    Takes part in a collection themself.
    """
    
    def __init__(self, path='[builtin]'):
        self._hdr = ''
        self.num = 0
        self.path = path
        if path == '[builtin]':
            self.id = 'default'
        else:
            self.id = splitext(basename(path))[0]
        self._file_read = False
        self._table = []
            
    def addKeyTrans(self):
        """XXX why is this here ??"""
        self.num = count()
        _KEYMAPS[self.num] = self
    
    def readConfig(self):
        if self._file_read:
            return
        self._file_read = True
        if self.path == '[builtin]':
            buf = open(DEFAULT_KEYTAB_FILE)
        else: 
            buf = open(self.path)
        ktr = KeytabReader(self.path, buf)
        ktr.parseTo(self)
        
    def addEntry(self, ref, key, bits, mask, cmd, txt):
        """returns conflicting entry if any, else create it, add it to the
        table, and return None
        """
        try:
            return self._findEntry(key, bits, mask)
        except EntryNotFound:
            entry = KeyEntry(ref, key, bits, mask, cmd, txt)
            self._table.append(entry)
    
    def findEntry(self, key, newline, ansi, appcukeys, control, shift, alt):
        if not self._file_read:
            self.readConfig()
        bits = encodeModes(newline, ansi, appcukeys) + encodeButtons(control, shift, alt)
        return self._findEntry(key, bits)
    
    def _findEntry(self, key, bits, mask=0xffff):
        for entry in self._table:
            if entry.matches(key, bits, 0xffff):
                return entry
        raise EntryNotFound('no entry matching %s %s %0x' % (key, bits, mask))
    
    def hdr(self):
        if not self._file_read:
            self.readConfig()
        return self._hdr



# Scanner for keyboard configuration ##########################################

OPR_SYMS = {
  "scrollLineUp":  CMD_scrollLineUp  ,
  "scrollLineDown":CMD_scrollLineDown,
  "scrollPageUp":  CMD_scrollPageUp  ,
  "scrollPageDown":CMD_scrollPageDown,
  "emitSelection": CMD_emitSelection ,
  "prevSession":   CMD_prevSession   ,
  "nextSession":   CMD_nextSession   ,
  "newSession":    CMD_newSession    ,
  "activateMenu":  CMD_activateMenu  ,
  "renameSession":  CMD_renameSession ,
  "moveSessionLeft":  CMD_moveSessionLeft   ,
  "moveSessionRight": CMD_moveSessionRight  ,
  "scrollLock":    CMD_scrollLock,
  "emitClipboard": CMD_emitClipboard,
    }

MOD_SYMS = {
  # Modifier
  "Shift":      BITS_Shift        ,
  "Control":    BITS_Control      ,
  "Alt":        BITS_Alt          ,
  # Modes
  "BsHack":     BITS_BsHack       , # deprecated
  "Ansi":       BITS_Ansi         ,
  "NewLine":    BITS_NewLine      ,
  "AppCuKeys":  BITS_AppCuKeys    ,
    }

KEY_SYMS = {
  # Grey keys
  "Escape":       Qt.Key_Escape      ,
  "Tab":          Qt.Key_Tab         ,
  "Backtab":      Qt.Key_Backtab     ,
  "Backspace":    Qt.Key_Backspace   ,
  "Return":       Qt.Key_Return      ,
  "Enter":        Qt.Key_Enter       ,
  "Insert":       Qt.Key_Insert      ,
  "Delete":       Qt.Key_Delete      ,
  "Pause":        Qt.Key_Pause       ,
  "Print":        Qt.Key_Print       ,
  "SysReq":       Qt.Key_SysReq      ,
  "Home":         Qt.Key_Home        ,
  "End":          Qt.Key_End         ,
  "Left":         Qt.Key_Left        ,
  "Up":           Qt.Key_Up          ,
  "Right":        Qt.Key_Right       ,
  "Down":         Qt.Key_Down        ,
  "Prior":         None      ,
  "Next":         None    ,
  "Shift":        Qt.Key_Shift       ,
  "Control":      Qt.Key_Control     ,
  "Meta":         Qt.Key_Meta        ,
  "Alt":          Qt.Key_Alt         ,
  "CapsLock":     Qt.Key_CapsLock    ,
  "NumLock":      Qt.Key_NumLock     ,
  "ScrollLock":   Qt.Key_ScrollLock  ,
  "F1":           Qt.Key_F1          ,
  "F2":           Qt.Key_F2          ,
  "F3":           Qt.Key_F3          ,
  "F4":           Qt.Key_F4          ,
  "F5":           Qt.Key_F5          ,
  "F6":           Qt.Key_F6          ,
  "F7":           Qt.Key_F7          ,
  "F8":           Qt.Key_F8          ,
  "F9":           Qt.Key_F9          ,
  "F10":          Qt.Key_F10         ,
  "F11":          Qt.Key_F11         ,
  "F12":          Qt.Key_F12         ,
  "F13":          Qt.Key_F13         ,
  "F14":          Qt.Key_F14         ,
  "F15":          Qt.Key_F15         ,
  "F16":          Qt.Key_F16         ,
  "F17":          Qt.Key_F17         ,
  "F18":          Qt.Key_F18         ,
  "F19":          Qt.Key_F19         ,
  "F20":          Qt.Key_F20         ,
  "F21":          Qt.Key_F21         ,
  "F22":          Qt.Key_F22         ,
  "F23":          Qt.Key_F23         ,
  "F24":          Qt.Key_F24         ,
  "F25":          Qt.Key_F25         ,
  "F26":          Qt.Key_F26         ,
  "F27":          Qt.Key_F27         ,
  "F28":          Qt.Key_F28         ,
  "F29":          Qt.Key_F29         ,
  "F30":          Qt.Key_F30         ,
  "F31":          Qt.Key_F31         ,
  "F32":          Qt.Key_F32         ,
  "F33":          Qt.Key_F33         ,
  "F34":          Qt.Key_F34         ,
  "F35":          Qt.Key_F35         ,
  "Super_L":      Qt.Key_Super_L     ,
  "Super_R":      Qt.Key_Super_R     ,
  "Menu":         Qt.Key_Menu        ,
  "Hyper_L":      Qt.Key_Hyper_L     ,
  "Hyper_R":      Qt.Key_Hyper_R     ,
  # Regular keys
  "Space":        Qt.Key_Space       ,
  "Exclam":       Qt.Key_Exclam      ,
  "QuoteDbl":     Qt.Key_QuoteDbl    ,
  "NumberSign":   Qt.Key_NumberSign  ,
  "Dollar":       Qt.Key_Dollar      ,
  "Percent":      Qt.Key_Percent     ,
  "Ampersand":    Qt.Key_Ampersand   ,
  "Apostrophe":   Qt.Key_Apostrophe  ,
  "ParenLeft":    Qt.Key_ParenLeft   ,
  "ParenRight":   Qt.Key_ParenRight  ,
  "Asterisk":     Qt.Key_Asterisk    ,
  "Plus":         Qt.Key_Plus        ,
  "Comma":        Qt.Key_Comma       ,
  "Minus":        Qt.Key_Minus       ,
  "Period":       Qt.Key_Period      ,
  "Slash":        Qt.Key_Slash       ,
  "0":            Qt.Key_0           ,
  "1":            Qt.Key_1           ,
  "2":            Qt.Key_2           ,
  "3":            Qt.Key_3           ,
  "4":            Qt.Key_4           ,
  "5":            Qt.Key_5           ,
  "6":            Qt.Key_6           ,
  "7":            Qt.Key_7           ,
  "8":            Qt.Key_8           ,
  "9":            Qt.Key_9           ,
  "Colon":        Qt.Key_Colon       ,
  "Semicolon":    Qt.Key_Semicolon   ,
  "Less":         Qt.Key_Less        ,
  "Equal":        Qt.Key_Equal       ,
  "Greater":      Qt.Key_Greater     ,
  "Question":     Qt.Key_Question    ,
  "At":           Qt.Key_At          ,
  "A":            Qt.Key_A           ,
  "B":            Qt.Key_B           ,
  "C":            Qt.Key_C           ,
  "D":            Qt.Key_D           ,
  "E":            Qt.Key_E           ,
  "F":            Qt.Key_F           ,
  "G":            Qt.Key_G           ,
  "H":            Qt.Key_H           ,
  "I":            Qt.Key_I           ,
  "J":            Qt.Key_J           ,
  "K":            Qt.Key_K           ,
  "L":            Qt.Key_L           ,
  "M":            Qt.Key_M           ,
  "N":            Qt.Key_N           ,
  "O":            Qt.Key_O           ,
  "P":            Qt.Key_P           ,
  "Q":            Qt.Key_Q           ,
  "R":            Qt.Key_R           ,
  "S":            Qt.Key_S           ,
  "T":            Qt.Key_T           ,
  "U":            Qt.Key_U           ,
  "V":            Qt.Key_V           ,
  "W":            Qt.Key_W           ,
  "X":            Qt.Key_X           ,
  "Y":            Qt.Key_Y           ,
  "Z":            Qt.Key_Z           ,
  "BracketLeft":  Qt.Key_BracketLeft ,
  "Backslash":    Qt.Key_Backslash   ,
  "BracketRight": Qt.Key_BracketRight,
  "AsciiCircum":  Qt.Key_AsciiCircum ,
  "Underscore":   Qt.Key_Underscore  ,
  "QuoteLeft":    Qt.Key_QuoteLeft   ,
  "BraceLeft":    Qt.Key_BraceLeft   ,
  "Bar":          Qt.Key_Bar         ,
  "BraceRight":   Qt.Key_BraceRight  ,
  "AsciiTilde":   Qt.Key_AsciiTilde  ,
    }

# Special handling for keys which have changed symbolic names
# in the Qt3/4 migration
if qtconfig() == 3:
    KEY_SYMS.update({"Prior": Qt.Key_Prior,
                     "Next": Qt.Key_Next,
                     })
else:
    KEY_SYMS.update({"Prior": Qt.Key_PageUp,
                     "Next": Qt.Key_PageDown,
                     })

KEY_DEF_SPLIT_RGX = re.compile('[+-]?\W*\w+')

class KeytabReader:
    """Scanner for keyboard configuration"""
    
    def __init__(self, path, stream):
        self.stream = stream
        self.path = path
        self.linno = None

    def parseTo(self, kt):
        """fill the given KeyTrans according to the parsed stream
        
        XXX: need to check that keyboard header is encountered first
        """
        self.linno = 1
        for line in self.stream:
            line = line.strip()
            self.linno += 1
            if not line or line.startswith('#'):
                continue
            # remove comments at the end of the line
            line = line.split('#', 1)[0]
            words = line.split()
            linetype = words.pop(0)
            # check the line begins with word "key"
            if linetype == 'keyboard':
                self._parseKeyboard(kt, ' '.join(words))
            elif linetype == 'key':
                self._parseKey(kt, ' '.join(words))
            else:
                self._reportError('malformed line')

    def _parseKeyboard(self, kt, string):
        '''example keyboard line:

        keyboard "XTerm (XFree 4.x.x)"

        here only the last part is received ("keyboard" has been removed)
        '''
        if not (string[0] == '"' and string[-1] == '"'):
            self._reportError('malformed string %s' % string)
        else:
            kt._hdr = string[1:-1] # unquote
        
    def _parseKey(self, kt, string):
        '''example key lines
        
        key Escape             : "\E"
        key Tab   -Shift       : "\t"
        key Tab   +Shift-Ansi  : "\t"
        key Return-Shift+NewLine : "\r\n"
        key Return+Shift         : "\EOM"

        here only the last part is received ("key" has been removed)
        '''
        symbols, keystr = [w.strip() for w in string.split(':', 1)]
        # symbols should be a list of names with +- to concatenate them
        key = None
        mode = 0
        mask = 0
        for op_sym in KEY_DEF_SPLIT_RGX.findall(symbols):
            op_sym = op_sym.strip()
            if key is None:
                try:
                    key = KEY_SYMS[op_sym]# - 1 # XXX why -1 ?
                except KeyError:
                    self._reportError('%s is not a valid key' % op_sym)
                    return
            else:
                # search +/-
                op, mod = op_sym[0], op_sym[1:].strip()
                if not op in '+-':
                    self._reportError('expect + or - before modifier %s' % mod)
                    return
                on = op == '+'
                try:
                    bits = MOD_SYMS[mod]# - 1 # XXX why -1
                except KeyError:
                    self._reportError('%s is not a valid mode or modifier' % mod)
                    return
                if mask & (1 << bits):
                    self._reportError('mode name %s used multible times' % mod)
                else:
                    mode |= (on << bits)
                    mask |= (1 << bits)
        # decode the key
        try:
            cmd = OPR_SYMS[keystr]# - 1 # XXX why -1
        except KeyError:
            if not (keystr[0] == '"' and keystr[-1] == '"'):
                self._reportError('malformed string or operation %s' % string)
                return
            else:
                cmd = CMD_send
                keystr = eval(keystr) # unquote + evaluation of special characters
                keystr = keystr.replace('\\E', '\033')
        entry = kt.addEntry(self.linno, key, mode, mask, cmd, keystr)
        if entry:
            self._reportError('keystroke already assigned in line %d' % entry.ref)
            
    def _reportError(self, msg):
        print >> sys.stderr, '%s line %s: %s' % (self.linno, self.path, msg)


loadAll()
