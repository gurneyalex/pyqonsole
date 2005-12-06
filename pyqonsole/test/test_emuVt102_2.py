# -*- coding: latin1 -*-
"""Test pyqonsole's VT102 emulation layer.

Definitions
-----------
c: The literal character c.
C: A single (required) character.
P s: A single (usually optional) numeric parameter, composed of one of
     more digits.
P m: A multiple numeric parameter composed of any number of single
     numeric parameters, separated by ; character(s). Individual values
     for the parameters are listed with P s .
P t: A text parameter composed of printable characters.

cf http://www.xfree86.org/current/ctlseqs.html#VT100
"""

import unittest
from utils import NullScreen, NullGui, MyEmuVt102, register_logger, reset_logs

from pyqonsole import emuVt102, emulation, ca

class EmuVt102TC(unittest.TestCase):
    
    def setUp(self):
        emulation.Screen = NullScreen        
        self.emu = MyEmuVt102(NullGui())
        self.emu._connected = True
        register_logger(self.emu)
        reset_logs()
        
    def _test_sequence(self, seq, **kwargs):
        for c in seq:
            self.emu.onRcvChar(ord(c))
        self.assertEquals(kwargs.get('scr0', []), self.emu._screen[0]._logs)
        self.assertEquals(kwargs.get('scr1', []), self.emu._screen[1]._logs)
        self.assertEquals(kwargs.get('gui', []), self.emu._gui._logs)
        self.assertEquals(kwargs.get('emu', []), self.emu._logs)
        reset_logs()

    def test_receive_printable_chars(self):
        """test onRcvChar(printable characters) trigger "showCharacter"
        method call on the working screen
        
        Printable characters:     32..255 but DEL (=127)
        """
        for ch in range(32, 256):
            if ch == 127:
                continue
            #print 'chr', ch, chr(ch)
            self._test_sequence(chr(ch),
                                scr0=[('getattr', 'showCharacter'), ('call', (ch,))])
            
    def test_receive_c1_control_chars(self):
        """C1 (8-Bit) Control Characters

ESC D 	Index (IND is 0x84) (cursor down with scroll up when at margin)
ESC E 	Next Line (NEL is 0x85) (CR+Index)
ESC H 	Tab Set (HTS is 0x88) (change tab stop(True))
ESC M 	Reverse Index (RI is 0x8d) (cursor up with scroll down when at margin)
XXX Unimplemented:
ESC N 	Single Shift Select of G2 Character Set (SS2 is 0x8e): affects next character only
ESC O 	Single Shift Select of G3 Character Set (SS3 is 0x8f): affects next character only
ESC P 	Device Control String (DCS is 0x90)
ESC V 	Start of Guarded Area (SPA is 0x96)
ESC W 	End of Guarded Area (EPA is 0x97)
ESC X 	Start of String (SOS is 0x98)
ESC Z 	Return Terminal ID (DECID is 0x9a). Obsolete form of CSI c (DA).
XXX Untested here:
ESC [ 	Control Sequence Introducer (CSI is 0x9b)
ESC \ 	String Terminator (ST is 0x9c)
ESC ] 	Operating System Command (OSC is 0x9d)
ESC ^ 	Privacy Message (PM is 0x9e)
ESC _ 	Application Program Command (APC is 0x9f)
        """
        self._test_sequence('\033D',
                            scr0=[('getattr', 'index'), ('call',)])
        self._test_sequence('\033E',
                            scr0=[('getattr', 'NextLine'), ('call',)])
        self._test_sequence('\033H',
                            scr0=[('getattr', 'changeTabStop'), ('call', (True,))])
        self._test_sequence('\033M',
                            scr0=[('getattr', 'reverseIndex'), ('call',)])        
        #self._test_sequence('\033N')
        #self._test_sequence('\033O')
        #self._test_sequence('\033P')
        #self._test_sequence('\033V')
        #self._test_sequence('\033W')
        #self._test_sequence('\033X')
        self._test_sequence('\033Z',
                            emu=[('9sndBlock(const char*,int)', ('\x1b[?1;2c', 7))])
        
    def test_receive_single_char_functions(self):
        """Single-character functions

BEL 	Bell
BS 	Backspace
CR 	Carriage Return
ENQ 	Return Terminal Status. Default response is an empty string, but may be overridden by a resource answerbackString.
FF 	Form Feed or New Page same as LF
LF 	Line Feed or New Line
SO 	Shift Out -> Switch to Alternate Character Set: invokes the G1 character set.
SI 	Shift In  -> Switch to Standard Character Set: invokes the G0 character set (the default).
SP 	Space
HT 	Horizontal Tab
VT 	Vertical Tab same as LF
        """
        self._test_sequence('\05', # ENQ
                            emu=[('9sndBlock(const char*,int)', ('', 0))])
        self._test_sequence('\07', # BELL
                            emu=[('9notifySessionState(int)', (1,))],
                            gui=[('getattr', 'bell'), ('call',)])
        self._test_sequence('\010', # BS
                            scr0=[('getattr', 'backSpace'), ('call',)])
        self._test_sequence('\011', # HT
                            scr0=[('getattr', 'tabulate'), ('call',)])
        self._test_sequence('\012', # LF
                            scr0=[('getattr', 'newLine'), ('call',)])
        self._test_sequence('\013', # VT
                            scr0=[('getattr', 'newLine'), ('call',)])
        self._test_sequence('\014', # FF
                            scr0=[('getattr', 'newLine'), ('call',)])
        self._test_sequence('\015', # CR
                            scr0=[('getattr', 'return_'), ('call',)])
        self._test_sequence('\016', # SO
                            emu=[('_useCharset', (1,))])
        self._test_sequence('\017', # SI
                            emu=[('_useCharset', (0,))])
        self._test_sequence('\040', # SP
                            scr0=[('getattr', 'showCharacter'), ('call', (32,))])

    def test_receive_esc_controls(self):
        """Controls beginning with ESC and not related to charset selection

ESC # 3 	DEC double-height line, top half (DECDHL)
ESC # 4 	DEC double-height line, bottom half (DECDHL)
ESC # 5 	DEC single-width line (DECSWL)
ESC # 6 	DEC double-width line (DECDWL)
ESC # 8 	DEC Screen Alignment Test (DECALN)
ESC % @ 	Select default character set, ISO 8859-1 (ISO 2022)
ESC % G 	Select UTF-8 character set (ISO 2022)
ESC 7 		Save Cursor (DECSC)
ESC 8 		Restore Cursor (DECRC)
ESC = 		Application Keypad (DECPAM)
ESC > 		Normal Keypad (DECPNM)
ESC c 		Full Reset (RIS)
ESC n 		Invoke the G2 Character Set as GL (LS2).
ESC o 		Invoke the G3 Character Set as GL (LS3).

XXX Unimplemented:
ESC SP F 	7-bit controls (S7C1T).
ESC SP G 	8-bit controls (S8C1T).
ESC SP L 	Set ANSI conformance level 1 (dpANS X3.134.1).
ESC SP M 	Set ANSI conformance level 2 (dpANS X3.134.1).
ESC SP N 	Set ANSI conformance level 3 (dpANS X3.134.1).
ESC F 		Cursor to lower left corner of screen (if enabled by the hpLowerleftBugCompat resource).
ESC l 		Memory Lock (per HP terminals). Locks memory above the cursor.
ESC m 		Memory Unlock (per HP terminals)
ESC | 		Invoke the G3 Character Set as GR (LS3R).
ESC } 		Invoke the G2 Character Set as GR (LS2R).
ESC ~ 		Invoke the G1 Character Set as GR (LS1R).
        """
        #self._test_sequence('\033 F')
        #self._test_sequence('\033 G')
        #self._test_sequence('\033 L')
        #self._test_sequence('\033 M')
        #self._test_sequence('\033 N')
        self._test_sequence('\033#3')
        self._test_sequence('\033#4')
        self._test_sequence('\033#5')
        self._test_sequence('\033#6')
        self._test_sequence('\033#8',
                            scr0=[('getattr', 'helpAlign'), ('call',)])
        self._test_sequence('\033%@')
        self._test_sequence('\033%G')
        self._test_sequence('\0337',
                            scr0=[('getattr', 'saveCursor'), ('call',)])
        self._test_sequence('\0338',
                            scr0=[('getattr', 'restoreCursor'), ('call',)])
        self._test_sequence('\033=',
                            emu=[('setMode', (emuVt102.MODE_AppKeyPad,))])
        self._test_sequence('\033>',
                            emu=[('resetMode', (emuVt102.MODE_AppKeyPad,))])
        #self._test_sequence('\033F')
        self._test_sequence('\033c',
                            scr0=[('getattr', 'clearSelection'), ('call',),
                                  ('getattr', 'resetMode'), ('call', (5,)),
                                  ('getattr', 'reset'), ('call',)],
                            scr1=[('getattr', 'resetMode'), ('call', (5,)),
                                  ('getattr', 'reset'), ('call',)],
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))],
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,)),
                                 ('resetMode', (emuVt102.MODE_AppScreen,)),
                                 ('resetMode', (emuVt102.MODE_AppCuKeys,)),
                                 ('resetMode', (5,)),
                                 ('setMode', (emuVt102.MODE_Ansi,))])
        #self._test_sequence('\033l')
        #self._test_sequence('\033m')
        self._test_sequence('\033n', emu=[('_useCharset', (2,))])
        self._test_sequence('\033o', emu=[('_useCharset', (3,))])
        #self._test_sequence('\033|')
        #self._test_sequence('\033}')
        #self._test_sequence('\033~')

    def test_receive_esc_charset_controls(self):
        """Controls beginning with ESC and related to charset selection

ESC (C		Designate G0 Character Set (ISO 2022)
ESC ) C 	Designate G1 Character Set (ISO 2022)
ESC * C 	Designate G2 Character Set (ISO 2022)
ESC + C 	Designate G3 Character Set (ISO 2022)

Final character C for designating character sets (0 , A and B apply to
VT100 and up, the remainder to VT220 and up): 
C = 0 -> DEC Special Character and Line Drawing Set
C = A -> United Kingdom (UK)
C = B -> United States (USASCII)
C = 4 -> Dutch
C = C or 5 -> Finnish
C = R -> French
C = Q -> French Canadian
C = K -> German
C = Y -> Italian
C = E or 6 -> Norwegian/Danish
C = Z -> Spanish
C = H or 7 -> Swedish
C = = -> Swiss
        """
        self._test_sequence('\033(0',
                            emu=[('_setCharset', (0,'0')), ('_useCharset', (0,)), ('_useCharset', (0,))])
        self._test_sequence('\033(A',
                            emu=[('_setCharset', (0, 'A')), ('_useCharset', (0,)), ('_useCharset', (0,))])
        self._test_sequence('\033(B',
                            emu=[('_setCharset', (0, 'B')), ('_useCharset', (0,)), ('_useCharset', (0,))])
        #self._test_sequence('\033(C')
        #self._test_sequence('\033(E')
        #self._test_sequence('\033(H')
        self._test_sequence('\033(K',
                            emu=[('_setCharset', (0, 'K',)), ('_useCharset', (0,)), ('_useCharset', (0,))])
        #self._test_sequence('\033(Q')
        self._test_sequence('\033(R',
                            emu=[('_setCharset', (0, 'R')), ('_useCharset', (0,)), ('_useCharset', (0,))])
        #self._test_sequence('\033(Y')
        #self._test_sequence('\033(Z')
        #self._test_sequence('\033(4')
        #self._test_sequence('\033(5')
        #self._test_sequence('\033(6')
        #self._test_sequence('\033(7')
        #self._test_sequence('\033(=')
        for i, s in enumerate( ('(', ')', '*', '+') ):
            for c in '0ABKR':
                #print repr('\033%s%s' % (s, c))
                self._test_sequence('\033%s%s' % (s, c),
                                    emu=[('_setCharset', (i, c)), ('_useCharset', (0,)), ('_useCharset', (0,))])

    def test_receive_del(self):
        """test onRcvChar(DEL = 127) is ignored (VT100)
        """
        self._test_sequence(chr(127))

    CTL_EXPECTED_LOGS = {
        24: {'scr0': [('getattr', 'showCharacter'), ('call', (9618,))]}, # VT100
        26: {'scr0': [('getattr', 'showCharacter'), ('call', (9618,))]}, # VT100
        # all others are ignored:
        # * 0 (NULL), 1 (SOH), 2 (STX), 3 (ETX), 4 (EOT)
        # * 6 (ACK)
        # * 16 (DLE), 17 (DC1 XON continue), 18 (DC2), 19 (DC3 XOFF halt),
        #   20 (DC4), 21 (NAK), , 22 (SYN), , 23 (ETB)
        # * 25 (EM)
        # * 27 (ESC)
        # * 28 (FS), 29 (GS), 30 (RS), 31 (US)
        }
    
    def test_receive_ctl_chars(self):
        """test onRcvChar(control characters) trigger 
        
        Control characters       0..31 but ESC (= 27), DEL
        """
        for ch in range(0, 32):
            if ch in (5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 27):
                continue
            print 'chr', ch
            self._test_sequence(chr(ch), **self.CTL_EXPECTED_LOGS.get(ch, {}))
        
    def test_receive_color_sequences(self):
        """Select Graphic Rendition
        
	\033[30m	Black foreground
	\033[31m	Red foreground
	\033[32m	Green foreground
	\033[33m	Yellow foreground
	\033[34m	Blue foreground
	\033[35m	Magenta foreground
	\033[36m	Cyan foreground
	\033[37m	White foreground
	\033[39m	Default foreground

	\033[40m	Black background
	\033[41m	Red background
	\033[42m	Green background
	\033[43m	Yellow background
	\033[44m	Blue background
	\033[45m	Magenta background
	\033[46m	Cyan background
	\033[47m	White background
	\033[49m	Default background
        """
        for i in range(8):
            self._test_sequence('\033[3%sm' % i,
                                scr0=[('getattr', 'setForeColor'), ('call', (i,))])
        self._test_sequence('\033[39m',
                            scr0=[('getattr', 'setForeColorToDefault'), ('call',)])
        for i in range(8):
            self._test_sequence('\033[4%sm' % i,
                                scr0=[('getattr', 'setBackColor'), ('call', (i,))])
        self._test_sequence('\033[49m',
                            scr0=[('getattr', 'setBackColorToDefault'), ('call',)])
        # XXX not in spec ?
        for i in range(8):
            self._test_sequence('\033[9%sm' % i,
                                scr0=[('getattr', 'setForeColor'), ('call', (i+8,))])
        for i in range(8):
            self._test_sequence('\033[10%sm' % i,
                                scr0=[('getattr', 'setBackColor'), ('call', (i+8,))])

    NOTHING_SCR_LOG = []
    CSI_PS_EXPECTED_LOGS = {
        0: {'scr0' : [('getattr', 'setDefaultRendition'), ('call',)]},
        1: {'scr0': [('getattr', 'setRendition'), ('call', (ca.RE_BOLD,))]},
        # XXX not implemented
        #3: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'setRendition'), ('call', (ca.RE_ITALIC,))]}        
        4: {'scr0': [('getattr', 'setRendition'), ('call', (ca.RE_UNDERLINE,))]},
        # XXX not in ISO 6429
        5: {'scr0': [('getattr', 'setRendition'), ('call', (ca.RE_BLINK,))]},
        7: {'scr0': [('getattr', 'setRendition'), ('call', (ca.RE_REVERSE,))]},
        # XXX not implemented
        #9: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'setRendition'), ('call', (ca.RE_CROSSED_OUT,))]}
        # XXX: 10, 11 and 12 are explicitly passed with the following comment:
        # IGNORED: mapping related # LINUX
        10: {'scr0': NOTHING_SCR_LOG},
        11: {'scr0': NOTHING_SCR_LOG},
        12: {'scr0': NOTHING_SCR_LOG},
        # XXX 13 -> 18, 21 unimplemented
        # XXX not implemented
        #21: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_DOUBLE_UNDERLINE,))]}        
        22: {'scr0': [('getattr', 'resetRendition'), ('call', (ca.RE_BOLD,))]},
        # XXX not implemented
        #23: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_ITALIC,))]}        
        24: {'scr0': [('getattr', 'resetRendition'), ('call', (ca.RE_UNDERLINE,))]},
        # XXX not in ISO 6429
        25: {'scr0': [('getattr', 'resetRendition'), ('call', (ca.RE_BLINK,))]},
        27: {'scr0': [('getattr', 'resetRendition'), ('call', (ca.RE_REVERSE,))]},
        # XXX not implemented
        #29: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_CROSSED_OUT,))]}
        }
    def test_receive_graphic_sequences(self):
        """Select Graphic Rendition
        
	\033[m	Reset
	\033[0m	Reset
	\033[1m	Bold
	\033[3m	Italic
	\033[4m	Underline
	\033[7m	Inverse
	\033[9m	Crossed out
	\033[10m	primary font
	\033[11m	1st alternate font
	\033[12m	2nd alternate font
	\033[13m	3rd alternate font
	\033[14m	4th alternate font
	\033[15m	5th alternate font
	\033[16m	6th alternate font
	\033[17m	7th alternate font
	\033[18m	8th alternate font
	\033[19m	9th alternate font
	\033[21m	Double underline
	\033[22m	Bold off
	\033[23m	Italic off
	\033[24m	Underline off (double or single)
	\033[27m	Inverse off
	\033[29m	Crossed out off
        """
        NOT_IMPLEMENTED = (3, 9, 13, 14, 15, 16, 17, 18, 19, 21, 23, 29)
        self._test_sequence('\033[m', **self.CSI_PS_EXPECTED_LOGS[0])
        for i in (0, 1, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21,
                  22, 23, 24, 25, 27, 29):
            if i in NOT_IMPLEMENTED:
                continue
            self._test_sequence('\033[%sm' % i,
                                **self.CSI_PS_EXPECTED_LOGS.get(i))
            
    def test_receive_cursor_manipulation_sequences_1(self):
        """
CSI <n> @ 	Insert <n> (Blank) Character(s) (default = 1) (ICH)
CSI <n> A 	Cursor Up <n> Times (default = 1) (CUU)
CSI <n> B 	Cursor Down <n> Times (default = 1) (CUD)
CSI <n> C 	Cursor Forward <n> Times (default = 1) (CUF)
CSI <n> D 	Cursor Backward <n> Times (default = 1) (CUB)
CSI <n> E 	Cursor Next Line <n> Times (default = 1) (CNL) XXX
CSI <n> F 	Cursor Preceding Line <n> Times (default = 1) (CPL) XXX
CSI <n> G 	Cursor Character Absolute [column] (default = [row,1]) (CHA)
CSI <n> ; <n> H Cursor Position [row;column] (default = [1,1]) (CUP)
CSI <n> I 	Cursor Forward Tabulation <n> tab stops (default = 1) (CHT) XXX
CSI <n> J 	Erase in Display (ED) XXX
                  <n> = 0 -> Erase Below (default)
                  <n> = 1 -> Erase Above
                  <n> = 2 -> Erase All
                  <n> = 3 -> Erase Saved Lines (xterm)
CSI <n> L 	Insert <n> Line(s) (default = 1) (IL) 	
CSI <n> M 	Delete <n> Line(s) (default = 1) (DL) 	
CSI <n> P 	Delete <n> Character(s) (default = 1) (DCH) 	

        XXX not in spec ?
        \033[<n>X Erase chars
        \033[c    Report terminal type
        \033[<n>d Set cursor y position
        \033[<n1;n2>r Set margin
        \033[<n1;n2>y ignored
        """
        self._test_sequence('\033[4A',
                            scr0=[('getattr', 'cursorUp'), ('call', (4,))])
        self._test_sequence('\033[1B',
                            scr0=[('getattr', 'cursorDown'), ('call', (1,))])
        self._test_sequence('\033[2C',
                            scr0=[('getattr', 'cursorRight'), ('call', (2,))])
        self._test_sequence('\033[3D',
                            scr0=[('getattr', 'cursorLeft'), ('call', (3,))])
        self._test_sequence('\033[3;5H',
                            scr0=[('getattr', 'setCursorYX'), ('call', (3, 5))])
        self._test_sequence('\033[2;3f',
                            scr0=[('getattr', 'setCursorYX'), ('call', (2, 3))])
        self._test_sequence('\033[3G',
                            scr0=[('getattr', 'setCursorX'), ('call', (3,))])

        self._test_sequence('\033[OJ',
                            scr0=[('getattr', 'showCharacter'), ('call', (74,))])
        self._test_sequence('\033[1J',
                            scr0=[('getattr', 'cursorLeft'), ('call', (3,))])
        self._test_sequence('\033[2J',
                            scr0=[('getattr', 'cursorLeft'), ('call', (3,))])
        self._test_sequence('\033[3J',
                            scr0=[('getattr', 'cursorLeft'), ('call', (3,))])
        
        self._test_sequence('\033[3L',
                            scr0=[('getattr', 'insertLines'), ('call', (3,))])
        self._test_sequence('\033[3M',
                            scr0=[('getattr', 'deleteLines'), ('call', (3,))])
        self._test_sequence('\033[3P',
                            scr0=[('getattr', 'deleteChars'), ('call', (3,))])
        
        self._test_sequence('\033[3X',
                            scr0=[('getattr', 'eraseChars'), ('call', (3,))])
        self._test_sequence('\033[c',
                            emu=[('9sndBlock(const char*,int)', ('\x1b[?1;2c', 7))])
        self._test_sequence('\033[3d',
                            scr0=[('getattr', 'setCursorY'), ('call', (3,))])
        self._test_sequence('\033[3;5r',
                            scr0=[('getattr', 'setMargins'), ('call', (3, 5))],
                            scr1=[('getattr', 'setMargins'), ('call', (3, 5))])
        self._test_sequence('\033[y')



class EmuVt52TC(EmuVt102TC):
    
    def setUp(self):
        EmuVt102TC.setUp(self)
        self.emu.resetMode(emuVt102.MODE_Ansi)
        reset_logs()

if __name__ == '__main__':
    unittest.main()
