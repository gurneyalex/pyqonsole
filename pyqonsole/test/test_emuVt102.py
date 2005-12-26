"""Test pyqonsole's VT102 emulation layer.

http://www.xfree86.org/current/ctlseqs.html#C1%20(8-Bit)%20Control%20Characters
http://www.xfree86.org/current/ctlseqs.html#VT100
http://www.xfree86.org/current/ctlseqs.html#VT52

Definitions
-----------
c: The literal character c.
C: A single (required) character.
Ps: A single (usually optional) numeric parameter, composed of one of
    more digits.
Pm: A multiple numeric parameter composed of any number of single
    numeric parameters, separated by ; character(s). Individual values
    for the parameters are listed with P s .
Pt: A text parameter composed of printable characters.

"""

import unittest
from utils import NoScreenTC, NullGui, MyEmuVt102, register_logger, reset_logs

from pyqonsole import emuVt102, emulation, ca, screen


class EmuVtTC(NoScreenTC):
    
    def setUp(self):
        NoScreenTC.setUp(self)
        self.emu = MyEmuVt102(NullGui())
        self.emu._connected = True
        register_logger(self.emu)
        reset_logs()
        
    def _test_sequence(self, seq, **kwargs):
        for c in seq:
            self.emu.onRcvChar(ord(c))
        self.assertEquals(kwargs.get('emu', []), self.emu._logs)
        self.assertEquals(kwargs.get('scr0', []), self.emu._screen[0]._logs)
        self.assertEquals(kwargs.get('scr1', []), self.emu._screen[1]._logs)
        self.assertEquals(kwargs.get('gui', []), self.emu._gui._logs)
        reset_logs()

        
class EmuVt102TC(EmuVtTC):

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
                            emu=[('9sndBlock', ('\x1b[?1;2c',))])
        
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
                            emu=[('9sndBlock', ('',))])
        self._test_sequence('\07', # BELL
                            emu=[('9notifySessionState', (1,))],      
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
                            scr0=[('getattr', 'resetMode'), ('call', (5,)),
                                  ('getattr', 'resetMode'), ('call', (4,)),
                                  ('getattr', 'reset'), ('call',)],
                            scr1=[('getattr', 'resetMode'), ('call', (5,)),
                                  ('getattr', 'resetMode'), ('call', (4,)),
                                  ('getattr', 'reset'), ('call',)],
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))],
                            emu=[('resetMode', (9,)), ('saveMode', (9,)),
                                 ('resetMode', (6,)), ('saveMode', (6,)),
                                 ('setMode', (10,)),
                                 ('resetMode', (7,)), ('saveMode', (7,)),
                                 ('resetMode', (5,)), ('resetMode', (8,)),
                                 ('resetMode', (4,))]
                            )
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
C=0 -> DEC Special Character and Line Drawing Set
C=A -> United Kingdom (UK)
C=B -> United States (USASCII)
C=4 -> Dutch
C=C or 5 -> Finnish
C=R -> French
C=Q -> French Canadian
C=K -> German
C=Y -> Italian
C=E or 6 -> Norwegian/Danish
C=Z -> Spanish
C=H or 7 -> Swedish
C== -> Swiss
        """
        self._test_sequence('\033(0',
                            emu=[('_setCharset', (0,'0'))])
        self._test_sequence('\033(A',
                            emu=[('_setCharset', (0, 'A'))])
        self._test_sequence('\033(B',
                            emu=[('_setCharset', (0, 'B'))])
        #self._test_sequence('\033(C')
        #self._test_sequence('\033(E')
        #self._test_sequence('\033(H')
        self._test_sequence('\033(K',
                            emu=[('_setCharset', (0, 'K',))])
        #self._test_sequence('\033(Q')
        self._test_sequence('\033(R',
                            emu=[('_setCharset', (0, 'R'))])
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
                                    emu=[('_setCharset', (i, c))])

    def test_receive_csi_cursor_manipulation(self):
        """Functions using CSI - cursor manipulation
        
CSI <Ps> @ 	Insert <Ps> (Blank) Character(s) (default = 1) (ICH)
CSI <Ps> A 	Cursor Up <Ps> Times (default = 1) (CUU)
CSI <Ps> B 	Cursor Down <Ps> Times (default = 1) (CUD)
CSI <Ps> C 	Cursor Forward <Ps> Times (default = 1) (CUF)
CSI <Ps> D 	Cursor Backward <Ps> Times (default = 1) (CUB)
CSI <Ps> E 	Cursor Next Line <Ps> Times (default = 1) (CNL) XXX
CSI <Ps> F 	Cursor Preceding Line <Ps> Times (default = 1) (CPL) XXX
CSI <Ps> G 	Cursor Character Absolute [column] (default = [row,1]) (CHA)
CSI <Ps> ; <Ps> H Cursor Position [row;column] (default = [1,1]) (CUP)
CSI <Ps> I 	Cursor Forward Tabulation <Ps> tab stops (default = 1) (CHT) XXX
CSI s		Save cursor (ANSI.SYS)
CSI u		Save cursor (ANSI.SYS) 	
        """
        self._test_sequence('\033[3@',
                            scr0=[('getattr', 'insertChars'), ('call', (3,))])
        self._test_sequence('\033[4A',
                            scr0=[('getattr', 'cursorUp'), ('call', (4,))])
        self._test_sequence('\033[1B',
                            scr0=[('getattr', 'cursorDown'), ('call', (1,))])
        self._test_sequence('\033[2C',
                            scr0=[('getattr', 'cursorRight'), ('call', (2,))])
        self._test_sequence('\033[3D',
                            scr0=[('getattr', 'cursorLeft'), ('call', (3,))])
        #self._test_sequence('\033[3F')
        self._test_sequence('\033[3G',
                            scr0=[('getattr', 'setCursorX'), ('call', (3,))])
        self._test_sequence('\033[3;5H',
                            scr0=[('getattr', 'setCursorYX'), ('call', (3, 5))])
        #self._test_sequence('\033[3I')
        #self._test_sequence('\033s')
        #self._test_sequence('\033u')
        
    def test_receive_csi_erase(self):
        """Functions using CSI - erase related
        
CSI <Ps> J 	Erase in Display (ED)
		    <Ps>=0 -> Erase Below (default)
		    <Ps>=1 -> Erase Above
		    <Ps>=2 -> Erase All
		    <Ps>=3 -> Erase Saved Lines (xterm)
CSI ? <Ps> J 	Erase in Display (DECSED) 	
	            <Ps>=0 -> Selective Erase Below (default)
		    <Ps>=1 -> Selective Erase Above
		    <Ps>=2 -> Selective Erase All
CSI <Ps> K 	Erase in Line (EL) 	
		    <Ps>=0 -> Erase to Right (default)
		    <Ps>=1 -> Erase to Left
		    <Ps>=2 -> Erase All
CSI ? <Ps> K 	Erase in Line (DECSEL) 	
		    <Ps>=0 -> Selective Erase to Right (default)
		    <Ps>=1 -> Selective Erase to Left
		    <Ps>=2 -> Selective Erase All
        """
        self._test_sequence('\033[0J',
                            scr0=[('getattr', 'clearToEndOfScreen'), ('call',)])
        self._test_sequence('\033[1J',
                            scr0=[('getattr', 'clearToBeginOfScreen'), ('call',)])
        self._test_sequence('\033[2J',
                            scr0=[('getattr', 'clearEntireScreen'), ('call',)])
        #self._test_sequence('\033[3J')
        #self._test_sequence('\033[?0J')
        #self._test_sequence('\033[?1J')
        #self._test_sequence('\033[?2J')
        self._test_sequence('\033[0K',
                            scr0=[('getattr', 'clearToEndOfLine'), ('call',)])
        self._test_sequence('\033[1K',
                            scr0=[('getattr', 'clearToBeginOfLine'), ('call',)])
        self._test_sequence('\033[2K',
                            scr0=[('getattr', 'clearEntireLine'), ('call',)])
        #self._test_sequence('\033[?0K')
        #self._test_sequence('\033[?1K')
        #self._test_sequence('\033[?2K')
        
    def test_receive_csi_lines_manipulation(self):
        """Functions using CSI - lines manipulation related

CSI <Ps> L 	Insert <Ps> Line(s) (default = 1) (IL) 	
CSI <Ps> M 	Delete <Ps> Line(s) (default = 1) (DL) 	
CSI <Ps> P 	Delete <Ps> Character(s) (default = 1) (DCH) 	
CSI <Ps> S 	Scroll up <Ps> lines (default = 1) (SU) 	
CSI <Ps> T 	Scroll down <Ps> lines (default = 1) (SD)

CSI <Ps> X 	Erase <Ps> Character(s) (default = 1) (ECH)
CSI <Ps> Z 	Cursor Backward Tabulation <Ps> tab stops (default = 1) (CBT)
CSI <Pm> ` 	Character Position Absolute [column] (default = [row,1]) (HPA)
CSI <Pm> d 	Line Position Absolute [row] (default = [1,column]) (VPA)
CSI <Ps> b 	Repeat the preceding graphic character <Ps> times (REP)
CSI <Ps> ; <Ps> f   Horizontal and Vertical Position [row;column] (default = [1,1]) (HVP)
CSI <Ps> g 	Tab Clear (TBC)
		<Ps>=0 -> Clear Current Column (default)
		<Ps>=3 -> Clear All
        """
        self._test_sequence('\033[3L',
                            scr0=[('getattr', 'insertLines'), ('call', (3,))])
        self._test_sequence('\033[3M',
                            scr0=[('getattr', 'deleteLines'), ('call', (3,))])
        self._test_sequence('\033[3P',
                            scr0=[('getattr', 'deleteChars'), ('call', (3,))])
        #self._test_sequence('\033[3S')
        #self._test_sequence('\033[3T')
        self._test_sequence('\033[3X',
                            scr0=[('getattr', 'eraseChars'), ('call', (3,))])
        #self._test_sequence('\033[3Z') 
        #self._test_sequence('\033[3;5`') 
        self._test_sequence('\033[3d',
                            scr0=[('getattr', 'setCursorY'), ('call', (3,))])
        #self._test_sequence('\033[3b') 
        self._test_sequence('\033[2;3f',
                            scr0=[('getattr', 'setCursorYX'), ('call', (2, 3))])
        self._test_sequence('\033[0g',
                            scr0=[('getattr', 'changeTabStop'), ('call', (False,))]) 
        self._test_sequence('\033[3g',
                            scr0=[('getattr', 'clearTabStops'), ('call',)]) 
       
    def test_receive_csi_modes_manipulation(self):
        """Functions using CSI - modes manipulation related

CSI <Ps> h 	Set Mode (SM) 	
	        <Ps>=2 -> Keyboard Action Mode (AM)
		<Ps>=4 -> Insert Mode (IRM)
		<Ps>=12 -> Send/receive (SRM)
		<Ps>=20 -> Automatic Newline (LNM)
CSI <Pm> l 	Reset Mode (RM) 	
		<Ps>=2 -> Keyboard Action Mode (AM)
		<Ps>=4 -> Replace Mode (IRM)
		<Ps>=12 -> Send/receive (SRM)
		<Ps>=20 -> Normal Linefeed (LNM)
        """
        #self._test_sequence('\033[2h') 
        self._test_sequence('\033[4h',
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_Insert,))]) 
        #self._test_sequence('\033[12h') 
        self._test_sequence('\033[20h',
                            emu=[('setMode', (screen.MODE_NewLine,))],
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_NewLine,))],
                            scr1=[('getattr', 'setMode'), ('call', (screen.MODE_NewLine,))]) 
        #self._test_sequence('\033[2l') 
        self._test_sequence('\033[4l',
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_Insert,))])
        
        #self._test_sequence('\033[12l') 
        self._test_sequence('\033[20l',
                            emu=[('resetMode', (screen.MODE_NewLine,))],
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_NewLine,))],
                            scr1=[('getattr', 'resetMode'), ('call', (screen.MODE_NewLine,))]) 


    def test_receive_csi_send_device_attributes(self):
        """Functions using CSI - send device attributes

CSI <Ps> c 	Send Device Attributes (Primary DA)
	        <Ps>=0 , 1 or omitted -> request attributes from terminal.
                The response depends on the decTerminalID resource setting.  
		-> CSI ? 1 ; 2 c ("VT100 with Advanced Video Option")
		-> CSI ? 1 ; 0 c ("VT101 with No Options")
		-> CSI ? 6 c ("VT102")
		-> CSI ? 6 0 ; 1 ; 2 ; 6 ; 8 ; 9 ; 1 5 ; c ("VT220")
		The VT100-style response parameters do not mean anything
	        by themselves. VT220 parameters do, telling the host
	        what features the terminal supports: 
		-> 1 132-columns
		-> 2 Printer
		-> 6 Selective erase
		-> 8 User-defined keys
		-> 9 National replacement character sets
		-> 1 5 Technical characters
		-> 2 2 ANSI color, e.g., VT525
		-> 2 9 ANSI text locator (i.e., DEC Locator mode)

CSI > <Ps> c 	Send Device Attributes (Secondary DA) 	
		<Ps>=0 , 1 or omitted -> request the terminal's identification
                code. The response depends on the decTerminalID resource setting.
                It should apply only to VT220 and up, but xterm extends this to
                VT100.
		-> CSI > <Pp> ; <Pv> ; <Pc> c
		where
                <Pp> denotes the terminal type
                * 0 ("VT100")
		* 1 ("VT220")
		<Pv> is the firmware version
                <Pc> indicates the ROM cartridge registration number (always zero) 
        """
        self._test_sequence('\033[c',
                            emu=[('9sndBlock', ('\x1b[?1;2c',))])
        self._test_sequence('\033[0c',
                            emu=[('9sndBlock', ('\x1b[?1;2c',))])
        self._test_sequence('\033[1c',
                            emu=[('9sndBlock', ('\x1b[?1;2c',))])
        self._test_sequence('\033[>c',
                            emu=[('9sndBlock', ('\x1b[>0;115;0c',))])
        self._test_sequence('\033[>0c',
                            emu=[('9sndBlock', ('\x1b[>0;115;0c',))])
        self._test_sequence('\033[>1c',
                            emu=[('9sndBlock', ('\x1b[>0;115;0c',))])
        
    def test_receive_csi_charater_attributes(self):
        """Functions using CSI - CSI <Pm> m 	Character Attributes (SGR)

<Ps>=0 -> Normal (default)
<Ps>=1 -> Bold
<Ps>=4 -> Underlined
<Ps>=5 -> Blink (appears as Bold)
<Ps>=7 -> Inverse
<Ps>=8 -> Invisible, i.e., hidden (VT300)
<Ps>=22 -> Normal (neither bold nor faint)
<Ps>=24 -> Not underlined
<Ps>=25 -> Steady (not blinking)
<Ps>=27 -> Positive (not inverse)
<Ps>=28 -> Visible, i.e., not hidden (VT300)
<Ps>=30 -> Set foreground color to Black
<Ps>=31 -> Set foreground color to Red
<Ps>=32 -> Set foreground color to Green
<Ps>=33 -> Set foreground color to Yellow
<Ps>=34 -> Set foreground color to Blue
<Ps>=35 -> Set foreground color to Magenta
<Ps>=36 -> Set foreground color to Cyan
<Ps>=37 -> Set foreground color to White
<Ps>=39 -> Set foreground color to default (original)
<Ps>=40 -> Set background color to Black
<Ps>=41 -> Set background color to Red
<Ps>=42 -> Set background color to Green
<Ps>=43 -> Set background color to Yellow
<Ps>=44 -> Set background color to Blue
<Ps>=45 -> Set background color to Magenta
<Ps>=46 -> Set background color to Cyan
<Ps>=47 -> Set background color to White
<Ps>=49 -> Set background color to default (original). If 16-color support is compiled, the following apply. Assume that xterm\u2019s resources are set so that the ISO color codes are the first 8 of a set of 16. Then the aixterm colors are the bright versions of the ISO colors:
<Ps>=90 -> Set foreground color to Black
<Ps>=91 -> Set foreground color to Red
<Ps>=92 -> Set foreground color to Green
<Ps>=93 -> Set foreground color to Yellow
<Ps>=94 -> Set foreground color to Blue
<Ps>=95 -> Set foreground color to Magenta
<Ps>=96 -> Set foreground color to Cyan
<Ps>=97 -> Set foreground color to White
<Ps>=100 -> Set background color to Black
<Ps>=101 -> Set background color to Red
<Ps>=102 -> Set background color to Green
<Ps>=103 -> Set background color to Yellow
<Ps>=104 -> Set background color to Blue
<Ps>=105 -> Set background color to Magenta
<Ps>=106 -> Set background color to Cyan
<Ps>=107 -> Set background color to White If xterm is compiled with the 16-color support disabled, it supports the following, from rxvt:
<Ps>=100 -> Set foreground and background color to default If 88- or 256-color support is compiled, the following apply.
<Ps>=38 ; 5 ; <Ps> -> Set foreground color to the second <Ps>
<Ps>=48 ; 5 ; <Ps> -> Set background color to the second <Ps>
        """
        self._test_sequence('\033[m',
                            scr0=[('getattr', 'setDefaultRendition'), ('call',)])
        self._test_sequence('\033[0m',
                            scr0=[('getattr', 'setDefaultRendition'), ('call',)])
        self._test_sequence('\033[1m',
                            scr0=[('getattr', 'setRendition'), ('call', (ca.RE_BOLD,))])
        self._test_sequence('\033[4m',
                            scr0=[('getattr', 'setRendition'), ('call', (ca.RE_UNDERLINE,))])
        self._test_sequence('\033[5m',
                            scr0=[('getattr', 'setRendition'), ('call', (ca.RE_BLINK,))])
        self._test_sequence('\033[7m',
                            scr0=[('getattr', 'setRendition'), ('call', (ca.RE_REVERSE,))])
        #self._test_sequence('\033[8m') # VT300
        self._test_sequence('\033[22m',
                            scr0=[('getattr', 'resetRendition'), ('call', (ca.RE_BOLD,))])
        self._test_sequence('\033[24m',
                            scr0=[('getattr', 'resetRendition'), ('call', (ca.RE_UNDERLINE,))])
        self._test_sequence('\033[25m',
                            scr0=[('getattr', 'resetRendition'), ('call', (ca.RE_BLINK,))])
        self._test_sequence('\033[27m',
                            scr0=[('getattr', 'resetRendition'), ('call', (ca.RE_REVERSE,))])
        #self._test_sequence('\033[28m') # VT300
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
        for i in range(8):
            self._test_sequence('\033[9%sm' % i,
                                scr0=[('getattr', 'setForeColor'), ('call', (i+8,))])
        for i in range(8):
            self._test_sequence('\033[10%sm' % i,
                                scr0=[('getattr', 'setBackColor'), ('call', (i+8,))])
        #self._test_sequence('\033[109m')
        #self._test_sequence('\033[38;5m', scr0=[('getattr', 'setRendition'), ('call', (2,))])
        #self._test_sequence('\033[48;5m', scr0=[('getattr', 'setRendition'), ('call', (2,))])

    def test_receive_csi_dec_private_mode_set(self):
        """Functions using CSI - CSI ? <Pm> h 	DEC Private Mode Set (DECSET)

<Ps>=1 -> Application Cursor Keys (DECCKM)
<Ps>=2 -> Designate USASCII for character sets G0-G3 (DECANM), and set VT100 mode.
<Ps>=3 -> 132 Column Mode (DECCOLM)
<Ps>=4 -> Smooth (Slow) Scroll (DECSCLM)
<Ps>=5 -> Reverse Video (DECSCNM)
<Ps>=6 -> Origin Mode (DECOM)
<Ps>=7 -> Wraparound Mode (DECAWM)
<Ps>=8 -> Auto-repeat Keys (DECARM)
<Ps>=9 -> Send Mouse X & Y on button press. See the section Mouse Tracking.
<Ps>=10 -> Show toolbar (rxvt)
<Ps>=12 -> Start Blinking Cursor (att610)
<Ps>=18 -> Print form feed (DECPFF)
<Ps>=19 -> Set print extent to full screen (DECPEX)
<Ps>=25 -> Show Cursor (DECTCEM)
<Ps>=30 -> Show scrollbar (rxvt).
<Ps>=35 -> Enable font-shifting functions (rxvt).
<Ps>=38 -> Enter Tektronix Mode (DECTEK)
<Ps>=40 -> Allow 80 -> 132 Mode
<Ps>=41 -> more(1) fix (see curses resource)
<Ps>=42 -> Enable Nation Replacement Character sets (DECNRCM)
<Ps>=44 -> Turn On Margin Bell
<Ps>=45 -> Reverse-wraparound Mode
<Ps>=46 -> Start Logging (normally disabled by a compile-time option)
<Ps>=47 -> Use Alternate Screen Buffer (unless disabled by the titeInhibit resource)
<Ps>=66 -> Application keypad (DECNKM)
<Ps>=67 -> Backarrow key sends delete (DECBKM)
<Ps>=1000 -> Send Mouse X & Y on button press and release. See the section Mouse Tracking.
<Ps>=1001 -> Use Hilite Mouse Tracking.
<Ps>=1002 -> Use Cell Motion Mouse Tracking.
<Ps>=1003 -> Use All Motion Mouse Tracking.
<Ps>=1010 -> Scroll to bottom on tty output (rxvt).
<Ps>=1011 -> Scroll to bottom on key press (rxvt).
<Ps>=1035 -> Enable special modifiers for Alt and NumLock keys.
<Ps>=1036 -> Send ESC when Meta modifies a key (enables the metaSendsEscape resource).
<Ps>=1037 -> Send DEL from the editing-keypad Delete key
<Ps>=1047 -> Use Alternate Screen Buffer (unless disabled by the titeInhibit resource)
<Ps>=1048 -> Save cursor as in DECSC (unless disabled by the titeInhibit resource)
<Ps>=1049 -> Save cursor as in DECSC and use Alternate Screen Buffer, clearing it first (unless disabled by the titeInhibit resource). This combines the effects of the 1 0 4 7 and 1 0 4 8 modes. Use this with terminfo-based applications rather than the 4 7 mode.
<Ps>=1051 -> Set Sun function-key mode.
<Ps>=1052 -> Set HP function-key mode.
<Ps>=1053 -> Set SCO function-key mode.
<Ps>=1060 -> Set legacy keyboard emulation (X11R6).
<Ps>=1061 -> Set Sun/PC keyboard emulation of VT220 keyboard.        
        """
        self._test_sequence('\033[?1h',
                            emu=[('setMode', (emuVt102.MODE_AppCuKeys,))])
        #self._test_sequence('\033[?2h')
        self._test_sequence('\033[?3h',
                            emu=[('9changeColumns', (132,))])
        self._test_sequence('\033[?4h')
        self._test_sequence('\033[?5h',
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_Screen,))])
        self._test_sequence('\033[?6h',
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_Origin,))])
        self._test_sequence('\033[?7h',
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_Wrap,))])
        self._test_sequence('\033[?8h')
        self._test_sequence('\033[?9h')
        self._test_sequence('\033[?25h',
                            emu=[('setMode', (screen.MODE_Cursor,))],
                            scr0=[('getattr', 'setMode'), ('call', (screen.MODE_Cursor,))],
                            scr1=[('getattr', 'setMode'), ('call', (screen.MODE_Cursor,))])
        self._test_sequence('\033[?41h')
        self._test_sequence('\033[?47h',
                            scr1=[('getattr', 'clearSelection'), ('call',)],
                            emu=[('setMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1000h',
                            gui=[('getattr', 'setMouseMarks'), ('call', (False,))],
                            emu=[('setMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1001h')
        self._test_sequence('\033[?1002h',
                            gui=[('getattr', 'setMouseMarks'), ('call', (False,))],
                            emu=[('setMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1003h',
                            gui=[('getattr', 'setMouseMarks'), ('call', (False,))],
                            emu=[('setMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1047h',
                            emu=[('setMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1048h',
                            scr1=[('getattr', 'saveCursor'), ('call',)])
        self._test_sequence('\033[?1049h',
                            emu=[('setMode', (emuVt102.MODE_AppScreen,))],
                            scr1=[('getattr', 'saveCursor'), ('call',),
                                  ('getattr', 'clearEntireScreen'), ('call',)])

    def test_receive_csi_dec_private_mode_save(self):
        """Functions using CSI - CSI ? <Pm> s 	Save DEC Private Mode Values.

<Ps> values are the same as for DECSET.
        """
        self._test_sequence('\033[?1s',
                            emu=[('saveMode', (emuVt102.MODE_AppCuKeys,))])
        #self._test_sequence('\033[?2s')
        #self._test_sequence('\033[?3s')
        #self._test_sequence('\033[?4s')
        #self._test_sequence('\033[?5s')
        self._test_sequence('\033[?6s',
                            scr0=[('getattr', 'saveMode'), ('call', (screen.MODE_Origin,))])
        self._test_sequence('\033[?7s',
                            scr0=[('getattr', 'saveMode'), ('call', (screen.MODE_Wrap,))])
        #self._test_sequence('\033[?8s')
        #self._test_sequence('\033[?9s')
        #self._test_sequence('\033[?25s')
        self._test_sequence('\033[?41s')
        self._test_sequence('\033[?47s',
                            emu=[('saveMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1000s',
                            emu=[('saveMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1001s')
        self._test_sequence('\033[?1002s',
                            emu=[('saveMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1003s',
                            emu=[('saveMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1047s',
                            emu=[('saveMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1048s',
                            scr0=[('getattr', 'saveCursor'), ('call',)])
        #self._test_sequence('\033[?1049s')

    def test_receive_csi_dec_private_mode_restore(self):
        """Functions using CSI - CSI ? <Pm> r 	Restore DEC Private Mode Values.

<Ps> values are the same as for DECSET.
        """
        self._test_sequence('\033[?1r',
                            emu=[('resetMode', (emuVt102.MODE_AppCuKeys,))])
        #self._test_sequence('\033[?2r')
        #self._test_sequence('\033[?3r')
        #self._test_sequence('\033[?4r')
        #self._test_sequence('\033[?5r')
        self._test_sequence('\033[?6r',
                            scr0=[('getattr', 'restoreMode'), ('call', (screen.MODE_Origin,))])
        self._test_sequence('\033[?7r',
                            scr0=[('getattr', 'restoreMode'), ('call', (screen.MODE_Wrap,))])
        #self._test_sequence('\033[?8r')
        #self._test_sequence('\033[?9r')
        #self._test_sequence('\033[?25r')
        self._test_sequence('\033[?41r')
        self._test_sequence('\033[?47r',
                            emu=[('resetMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1000r',
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,))],
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))])
        self._test_sequence('\033[?1001r')
        self._test_sequence('\033[?1002r',
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,))],
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))])
        self._test_sequence('\033[?1003r',
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,))],
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))])
        self._test_sequence('\033[?1047r',
                            emu=[('resetMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1048r',
                            scr0=[('getattr', 'restoreCursor'), ('call',)])
        #self._test_sequence('\033[?1049r')

    def test_receive_csi_dec_private_mode_reset_isolated_1(self):
        """Functions using CSI - CSI ? <Pm> l 	DEC Private Mode Reset (DECRST) 	

<Ps>=1 -> Normal Cursor Keys (DECCKM)
<Ps>=2 -> Designate VT52 mode (DECANM).
"""
        self._test_sequence('\033[?1l',
                            emu=[('resetMode', (emuVt102.MODE_AppCuKeys,))])
        self._test_sequence('\033[?2l',
                            emu=[('resetMode', (emuVt102.MODE_Ansi,))])

    def test_receive_csi_dec_private_mode_reset_isolated_2(self):
        """Functions using CSI - CSI ? <Pm> l 	DEC Private Mode Reset (DECRST) 	

<Ps>=3 -> 80 Column Mode (DECCOLM)
<Ps>=4 -> Jump (Fast) Scroll (DECSCLM)
<Ps>=5 -> Normal Video (DECSCNM)
<Ps>=6 -> Normal Cursor Mode (DECOM)
<Ps>=7 -> No Wraparound Mode (DECAWM)
<Ps>=8 -> No Auto-repeat Keys (DECARM)
<Ps>=9 -> Don't Send Mouse X & Y on button press
<Ps>=10 -> Hide toolbar (rxvt)
<Ps>=12 -> Stop Blinking Cursor (att610)
<Ps>=18 -> Don't print form feed (DECPFF)
<Ps>=19 -> Limit print to scrolling region (DECPEX)
<Ps>=25 -> Hide Cursor (DECTCEM)
        """
        self._test_sequence('\033[?3l',
                            emu=[('9changeColumns', (80,))])
        self._test_sequence('\033[?4l')
        self._test_sequence('\033[?5l',
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_Screen,))])
        self._test_sequence('\033[?6l',
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_Origin,))])
        self._test_sequence('\033[?7l',
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_Wrap,))])
        self._test_sequence('\033[?8l')
        self._test_sequence('\033[?9l')
        self._test_sequence('\033[?25l',
                            emu=[('resetMode', (screen.MODE_Cursor,))],
                            scr0=[('getattr', 'resetMode'), ('call', (screen.MODE_Cursor,))],
                            scr1=[('getattr', 'resetMode'), ('call', (screen.MODE_Cursor,))])
        
    def test_receive_csi_dec_private_mode_reset(self):
        """Functions using CSI - CSI ? <Pm> l 	DEC Private Mode Reset (DECRST) 	

<Ps>=30 -> Don't show scrollbar (rxvt).
<Ps>=35 -> Disable font-shifting functions (rxvt).
<Ps>=40 -> Disallow 80 -> 132 Mode
<Ps>=41 -> No more(1) fix (see curses resource)
<Ps>=42 -> Disable Nation Replacement Character sets (DECNRCM)
<Ps>=44 -> Turn Off Margin Bell
<Ps>=45 -> No Reverse-wraparound Mode
<Ps>=46 -> Stop Logging (normally disabled by a compile-time option)
<Ps>=47 -> Use Normal Screen Buffer
<Ps>=66 -> Numeric keypad (DECNKM)
<Ps>=67 -> Backarrow key sends backspace (DECBKM)
<Ps>=1000 -> Don't Send Mouse X & Y on button press and release. See the section Mouse Tracking.
<Ps>=1001 -> Don't Use Hilite Mouse Tracking
<Ps>=1002 -> Don't Use Cell Motion Mouse Tracking
<Ps>=1003 -> Don't Use All Motion Mouse Tracking
<Ps>=1010 -> Don't scroll to bottom on tty output (rxvt).
<Ps>=1011 -> Don't scroll to bottom on key press (rxvt).
<Ps>=1035 -> Disable special modifiers for Alt and NumLock keys.
<Ps>=1036 -> Don't send ESC when Meta modifies a key (disables the metaSendsEscape resource).
<Ps>=1037 -> Send VT220 Remove from the editing-keypad Delete key
<Ps>=1047 -> Use Normal Screen Buffer, clearing screen first if in the Alternate Screen (unless disabled by the titeInhibit resource)
<Ps>=1048 -> Restore cursor as in DECRC (unless disabled by the titeInhibit resource)
<Ps>=1049 -> Use Normal Screen Buffer and restore cursor as in DECRC (unless disabled by the titeInhibit resource). This combines the effects of the 1 0 4 7 and 1 0 4 8 modes. Use this with terminfo-based applications rather than the 4 7 mode.
<Ps>=1051 -> Reset Sun function-key mode.
<Ps>=1052 -> Reset HP function-key mode.
<Ps>=1053 -> Reset SCO function-key mode.
<Ps>=1060 -> Reset legacy keyboard emulation (X11R6).
<Ps>=1061 -> Reset Sun/PC keyboard emulation of VT220 keyboard.
"""        
        self._test_sequence('\033[?41l')
        self._test_sequence('\033[?47l',
                            emu= [('resetMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1000l',
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))],
                            emu= [('resetMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1002l',
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))],
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1003l',
                            gui=[('getattr', 'setMouseMarks'), ('call', (True,))],
                            emu=[('resetMode', (emuVt102.MODE_Mouse1000,))])
        self._test_sequence('\033[?1047l',
                            scr1=[('getattr', 'clearEntireScreen'), ('call',)],
                            emu=[('resetMode', (emuVt102.MODE_AppScreen,))])
        self._test_sequence('\033[?1048l',
                            scr0=[('getattr', 'restoreCursor'), ('call',)])
        self._test_sequence('\033[?1049l',
                            emu=[('resetMode', (emuVt102.MODE_AppScreen,))],
                            scr0=[('getattr', 'restoreCursor'), ('call',)])

    def test_receive_csi_device_status_report(self):
        """Functions using CSI - Device status report
        
CSI <Ps> n 	Device Status Report (DSR) 	
		<Ps>=5 -> Status Report CSI 0 n ("OK")
		<Ps>=6 -> Report Cursor Position (CPR) [row;column] as CSI r ; c R
CSI ? <Ps> n 	Device Status Report (DSR, DEC-specific) 	
	        <Ps>=6 -> Report Cursor Position (CPR) [row;column] as CSI ? r ; c R (assumes page is zero).
                <Ps>=15 -> Report Printer status as CSI ? 1 0 n (ready) or CSI ? 1 1 n (not ready)
                <Ps>=25 -> Report UDK status as CSI ? 2 0 n (unlocked) or CSI ? 2 1 n (locked)
		<Ps>=26 -> Report Keyboard status as CSI ? 2 7 ; 1 ; 0 ; 0 n (North American)
		The last two parameters apply to VT400 & up, and denote keyboard ready and LK01 respectively.
		<Ps>=53 -> Report Locator status as
                  CSI ? 53 n Locator available, if compiled-in, or
		  CSI ? 50 n No Locator, if not.

CSI <Ps> x 	Request Terminal Parameters (DECREQTPARM) 	
		if <Ps> is a "0" (default) or "1", and xterm is
		emulating VT100, the control sequence elicits a response
		of the  same form whose parameters describe the terminal: 
		<Ps> -> the given <Ps> incremented by 2.
		1 -> no parity
		1 -> eight bits
		128 -> transmit 38.4k baud
		128 -> receive 38.4k baud
		1 -> clock multiplier
		0 -> STP flags
        """
        self._test_sequence('\033[5n',
                            emu=[('9sndBlock', ('\x1b[0n',))])
        self._test_sequence('\033[6n',
                            emu=[('9sndBlock', ('\x1b[2;2R',))],
                            scr0=[('getattr', 'getCursorX'), ('getattr', 'getCursorY')])
        #self._test_sequence('\033[?6n')
        #self._test_sequence('\033[?15n')
        #self._test_sequence('\033[?25n') 
        #self._test_sequence('\033[?26n')
        #self._test_sequence('\033[?53n')
        self._test_sequence('\033[x',                            # XXX \x1b[0 ?
                            emu=[('9sndBlock', ('\x1b[2;1;1;112;112;1;0x',))])
        self._test_sequence('\033[0x',                           # XXX \x1b[0 ?
                            emu=[('9sndBlock', ('\x1b[2;1;1;112;112;1;0x',))])
        self._test_sequence('\033[1x',                           # XXX \x1b[2 ?
                            emu=[('9sndBlock', ('\x1b[3;1;1;112;112;1;0x',))])

    def test_receive_csi_media_copy(self):
        """Functions using CSI - Media Copy
        
CSI <Pm> i 	Media Copy (MC) 	
		<Ps>=0 -> Print screen (default)
		<Ps>=4 -> Turn off printer controller mode
		<Ps>=5 -> Turn on printer controller mode
CSI ? <Pm> i 	Media Copy (MC, DEC-specific) 	
		<Ps>=1 -> Print line containing cursor
		<Ps>=4 -> Turn off autoprint mode
		<Ps>=5 -> Turn on autoprint mode
		<Ps>=10 -> Print composed display, ignores DECPEX
		<Ps>=11 -> Print all pages
        """
        self._test_sequence('\033[0i')
        self._test_sequence('\033[5i', emu=[('setPrinterMode', (True,))])
        self._test_sequence('\033[4i', emu=[('setPrinterMode', (False,))])
        #self._test_sequence('\033[?1i')
        #self._test_sequence('\033[?4i')
        #self._test_sequence('\033[?5i')
        #self._test_sequence('\033[?10i')
        #self._test_sequence('\033[?11i')

    def test_receive_osc(self):
        """Operating System Controls
        
OSC <Ps> ; <Pt> ST 	
OSC <Ps> ; <Pt> BEL 	
		Set Text Parameters. For colors and font, if <Pt> is a "?", the
		control sequence elicits a response which consists of the
		control sequence which would set the corresponding value. The
		dtterm control sequences allow you to determine the icon name
		and window title.
                
<Ps>=0 -> Change Icon Name and Window Title to <Pt>
<Ps>=1 -> Change Icon Name to <Pt>
<Ps>=2 -> Change Window Title to <Pt>
<Ps>=3 -> Set X property on top-level window. <Pt> should be in
          the form "prop=value", or just "prop" to delete the property 
<Ps>=4 ; c ; spec
       -> Change Color Number c to the color
          specified by spec, i.e., a name or RGB specification as per
          XParseColor. Any number of c name pairs may be given. The color
          numbers correspond to the ANSI colors 0-7, their bright versions 8-15,
          and if supported, the remainder of the 88-color or 256-color table. If
          a "?" is given rather than a name or RGB specification, xterm replies
          with a control sequence of the same form which can be used to set the
          corresponding color. Because more than one pair of color number and
          specification can be given in one control sequence, xterm can make
          more than one reply. The 8 colors which may be set using 1 0 through 1
          7 are denoted dynamic colors, since the corresponding control
          sequences were the first means for setting xterm's colors dynamically,
          i.e., after it was started. They are not the same as the ANSI
          colors. One or more parameters is expected for <Pt> . Each succesive
          parameter changes the next color in the list. The value of <Ps> tells
          the starting point in the list. The colors are specified by name or
          RGB specification as per XParseColor. If a "?" is given rather than a
          name or RGB specification, xterm replies with a control sequence of
          the same form which can be used to set the corresponding dynamic
          color. Because more than one pair of color number and specification
          can be given in one control sequence, xterm can make more than one
          reply. <Ps>=1 0 -> Change VT100 text foreground color to <Pt>
<Ps>=11 -> Change VT100 text background color to <Pt>
<Ps>=12 -> Change text cursor color to <Pt>
<Ps>=13 -> Change mouse foreground color to <Pt>
<Ps>=14 -> Change mouse background color to <Pt>
<Ps>=15 -> Change Tektronix foreground color to <Pt>
<Ps>=16 -> Change Tektronix background color to <Pt>
<Ps>=17 -> Change highlight color to <Pt>
<Ps>=18 -> Change Tektronix cursor color to <Pt>
<Ps>=46 -> Change Log File to <Pt> (normally disabled by a compile-time option) 
<Ps>=50 -> Set Font to <Pt> If <Pt> begins with a '#', index in
           the font menu, relative (if the next character is a plus or minus
           sign) or absolute. A number is expected but not required after the
           sign (the default is the current entry for relative, zero for
           absolute indexing).

This is implemented as a 'XTerm hack' in emuVt102
        """
        self._test_sequence('\033]0;blablabla\07', # BELL is \007
                            emu=[('9changeTitle', (0, 'blablabla'))])
        self._test_sequence('\033]1;blablabla\07',
                            emu=[('9changeTitle', (1, 'blablabla'))])
        self._test_sequence('\033]2;blablabla\07',
                            emu=[('9changeTitle', (2, 'blablabla'))])

    def test_missing_vi_code1(self):
        """CSI ? <Pm> l
        
	<Ps>=12 -> Stop Blinking Cursor (att610)
        """
        self._test_sequence('\033[?12l')
        
    def test_missing_vi_code3(self):
        """?"""
        self._test_sequence('\033[?12;25h')

        
        
class EmuVtNOT102TC(EmuVtTC):
    
    CSI_PS_EXPECTED_LOGS = {
        # XXX not implemented
        #3: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'setRendition'), ('call', (ca.RE_ITALIC,))]}        
        # XXX not implemented
        #9: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'setRendition'), ('call', (ca.RE_CROSSED_OUT,))]}
        # XXX: 10, 11 and 12 are explicitly passed with the following comment:
        # IGNORED: mapping related # LINUX
        # XXX 13 -> 18, 21 unimplemented
        # XXX not implemented
        #21: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_DOUBLE_UNDERLINE,))]}        
        #23: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_ITALIC,))]}        
        #29: {'scr0': [('getattr', 'setDefaultRendition'), ('call',), 
        #             ('getattr', 'resetRendition'), ('call', (ca.RE_CROSSED_OUT,))]}
        }
    def test_receive_graphic_sequences(self):
        """Select Graphic Rendition
        
	\033[3m	Italic
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
	\033[23m	Italic off
	\033[29m	Crossed out off
        """
        NOT_IMPLEMENTED = (3, 9, 13, 14, 15, 16, 17, 18, 19, 21, 23, 29)
        for i in (10, 11, 12):
            #print i
            self._test_sequence('\033[%sm' % i,
                                **self.CSI_PS_EXPECTED_LOGS.get(i, {}))
            
    def test_receive_out_spec(self):
        """
        XXX implemented but not in spec
        \030 show caracter
        \032 show caracter
        \033[<n1;n2>r  Set margin
        \033[<n1;n2>y  ignored
        """
        self._test_sequence('\033[3;5r',
                            scr0=[('getattr', 'setMargins'), ('call', (3, 5))],
                            scr1=[('getattr', 'setMargins'), ('call', (3, 5))])
        self._test_sequence('\033[y')
        self._test_sequence('\030',
                            scr0=[('getattr', 'showCharacter'), ('call', (9618,))])
        self._test_sequence('\032',
                            scr0=[('getattr', 'showCharacter'), ('call', (9618,))])
        self._test_sequence('\033[0s',
                            scr0=[('getattr', 'saveCursor'), ('call',)])
        self._test_sequence('\033[0u',
                            scr0=[('getattr', 'restoreCursor'), ('call',)])
        self._test_sequence('\033[0q')
        self._test_sequence('\033[1q')
        self._test_sequence('\033[2q')
        self._test_sequence('\033[3q')
        self._test_sequence('\033[4q')


class EmuVt102PrinterModeTC(EmuVtTC):
    
    def setUp(self):
        EmuVtTC.setUp(self)
        # set printer mode on
        self._test_sequence('\033[5i', emu=[('setPrinterMode', (True,))])
        self.failUnless(self.emu._print_fd)
        reset_logs()

    def test_set_printer_mode_off(self):
        self._test_sequence('\033[4i', emu=[('setPrinterMode', (False,))])
        self.failUnlessEqual(self.emu._print_fd, None)
       
    def test_hide_ctrl(self):
        self._test_sequence('\000\021\023') # 0, CNTL(Q), CNTL(S)
    
    def test_receive_printable_chars(self):
        """test onRcvChar(printable characters) in printer mode trigger nothing
        (chars are written to the print_fd
        """
        for ch in range(32, 256):
            if ch == 127:
                continue
            #print 'chr', ch, chr(ch)
            self._test_sequence(chr(ch))
            

class EmuVt52TC(EmuVtTC):
    
    def setUp(self):
        EmuVtTC.setUp(self)
        self.emu.resetMode(emuVt102.MODE_Ansi)
        reset_logs()

    def test(self):
        """VT52 Mode

Parameters for cursor movement are at the end of the ESC Y escape
sequence. Each ordinate is encoded in a single character as
value+32. For example, ! is 1. The screen coodinate system is 0-based. 

ESC A 		Cursor up.
ESC B 		Cursor down.
ESC C 		Cursor right.
ESC D 		Cursor left.
ESC F 		Enter graphics mode.
ESC G 		Exit graphics mode.
ESC H 		Move the cursor to the home position.
ESC I 		Reverse line feed.
ESC J 		Erase from the cursor to the end of the screen.
ESC K 		Erase from the cursor to the end of the line.
ESC Y <Ps> <Ps> Move the cursor to given row and column.
ESC Z 		Identify
	        -> ESC / Z ("I am a VT52.")
ESC =		Enter alternate keypad mode. 	
ESC > 		Exit alternate keypad mode. 	
ESC < 		Exit VT52 mode (Enter VT100 mode).
        """
        self._test_sequence('\033A',
                            scr0=[('getattr', 'cursorUp'), ('call', (1,))])
        self._test_sequence('\033B',
                            scr0=[('getattr', 'cursorDown'), ('call', (1,))])
        self._test_sequence('\033C',
                            scr0=[('getattr', 'cursorRight'), ('call', (1,))])
        self._test_sequence('\033D',
                            scr0=[('getattr', 'cursorLeft'), ('call', (1,))])
        self._test_sequence('\033F',
                            emu= [('_useCharset', (0,))])
        self._test_sequence('\033G',
                            emu= [('_useCharset', (0,))])
        self._test_sequence('\033H',
                            scr0=[('getattr', 'setCursorYX'), ('call', (1, 1))])
        self._test_sequence('\033I',
                            scr0=[('getattr', 'reverseIndex'), ('call',)])
        self._test_sequence('\033J',
                            scr0= [('getattr', 'clearToEndOfScreen'), ('call',)])
        self._test_sequence('\033K',
                            scr0= [('getattr', 'clearToEndOfLine'), ('call',)])
        self._test_sequence('\033Y12',
                            scr0=[('getattr', 'setCursorYX'), ('call', (18, 19))]) # XXX
        self._test_sequence('\033Z',
                            emu=[('9sndBlock', ('\x1b/Z',))])
        self._test_sequence('\033=',
                            emu=[('setMode', (emuVt102.MODE_AppKeyPad,))])
        self._test_sequence('\033>',
                            emu=[('resetMode', (emuVt102.MODE_AppKeyPad,))])
        self._test_sequence('\033<',
                            emu=[('setMode', (emuVt102.MODE_Ansi,))])


class EmuVt102ModesTC(EmuVtTC):

    def test(self):
        EMU_MODES = (emuVt102.MODE_AppScreen, emuVt102.MODE_AppCuKeys,
                     emuVt102.MODE_AppKeyPad, emuVt102.MODE_Mouse1000,
                     emuVt102.MODE_Ansi, screen.MODE_NewLine, screen.MODE_Cursor)
        self.emu.resetMode(emuVt102.MODE_Ansi) # reset ansi mode so all modes are unset
        for mode in EMU_MODES:
            self.emu.setMode(mode)
            self.failUnless(self.emu.getMode(mode))
            for omode in EMU_MODES:
                if omode == mode:
                    continue
                self.failUnless(not self.emu.getMode(omode))
            self.emu.resetMode(mode)
            for omode in EMU_MODES:
                self.failUnless(not self.emu.getMode(omode))
                
        
if __name__ == '__main__':
    unittest.main()
