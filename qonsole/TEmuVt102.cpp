/* ------------------------------------------------------------------------- */
/*                                                                           */
/* [TEmuVt102.C]            VT102 Terminal Emulation                         */
/*                                                                           */
/* ------------------------------------------------------------------------- */
/*                                                                           */
/* Copyright (c) 1997,1998 by Lars Doelle <lars.doelle@on-line.de>           */
/*                                                                           */
/* This file is part of Konsole - an X terminal for KDE                      */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/*! \class TEmuVt102

   \brief Actual Emulation for Konsole

   \sa TEWidget \sa TEScreen
*/

#include "config.h"

// this allows konsole to be compiled without XKB and XTEST extensions
// even though it might be available on a particular system.
#if defined(AVOID_XKB)
#undef HAVE_XKB
#undef HAVE_XTEST
#endif

#include "TEmuVt102.h"

#include <stdio.h>
#include <unistd.h>
#include <assert.h>

#include "TEWidget.h"
#include "TEScreen.h"

#include "TEmuVt102.moc"

/* VT102 Terminal Emulation

   This class puts together the screens, the pty and the widget to a
   complete terminal emulation. Beside combining it's componentes, it
   handles the emulations's protocol.

   This module consists of the following sections:

   - Constructor/Destructor
   - Incoming Bytes Event pipeline
   - Outgoing Bytes
     - Mouse Events
     - Keyboard Events
   - Modes and Charset State
   - Diagnostics
*/

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                       Constructor / Destructor                            */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/*
   Nothing really intesting happens here.
*/

TEmuVt102::TEmuVt102(TEWidget* gui) : TEmulation(gui)
{
  QObject::connect(gui,SIGNAL(mouseSignal(int,int,int)), this, SLOT(onMouse(int,int,int)));
  initTokenizer();
  reset();
}

TEmuVt102::~TEmuVt102()
{
}

void TEmuVt102::reset()
{
  resetToken();
  resetModes();
  resetCharset(0);
  screen[0]->reset();
  resetCharset(1);
  screen[1]->reset();
  setCodec(0);
  print_fd = NULL;
}

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                     Processing the incoming byte stream                   */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/* Incoming Bytes Event pipeline

   This section deals with decoding the incoming character stream.
   Decoding means here, that the stream is first seperated into `tokens'
   which are then mapped to a `meaning' provided as operations by the
   `TEScreen' class or by the emulation class itself.

   The pipeline proceeds as follows:

   - Tokenizing the ESC codes (onRcvChar)
   - VT100 code page translation of plain characters (applyCharset)
   - Interpretation of ESC codes (tau)

   The escape codes and their meaning are described in the
   technical reference of this program.
*/

// Tokens ------------------------------------------------------------------ --

/*
   Since the tokens are the central notion if this section, we've put them
   in front. They provide the syntactical elements used to represent the
   terminals operations as byte sequences.

   They are encodes here into a single machine word, so that we can later
   switch over them easily. Depending on the token itself, additional
   argument variables are filled with parameter values.

   The tokens are defined below:

   - CHR        - Printable characters     (32..255 but DEL (=127))
   - CTL        - Control characters       (0..31 but ESC (= 27), DEL)
   - ESC        - Escape codes of the form <ESC><CHR but `[]()+*#'>
   - ESC_DE     - Escape codes of the form <ESC><any of `()+*#%'> C
   - CSI_PN     - Escape codes of the form <ESC>'['     {Pn} ';' {Pn} C
   - CSI_PS     - Escape codes of the form <ESC>'['     {Pn} ';' ...  C
   - CSI_PR     - Escape codes of the form <ESC>'[' '?' {Pn} ';' ...  C
   - VT52       - VT52 escape codes
                  - <ESC><Chr>
                  - <ESC>'Y'{Pc}{Pc}
   - XTE_HA     - Xterm hacks              <ESC>`]' {Pn} `;' {Text} <BEL>
                  note that this is handled differently

   The last two forms allow list of arguments. Since the elements of
   the lists are treated individually the same way, they are passed
   as individual tokens to the interpretation. Further, because the
   meaning of the parameters are names (althought represented as numbers),
   they are includes within the token ('N').

*/

#define TY_CONSTR(T,A,N) ( ((((int)N) & 0xffff) << 16) | ((((int)A) & 0xff) << 8) | (((int)T) & 0xff) )

#define TY_CHR___(   )  TY_CONSTR(0,0,0)
#define TY_CTL___(A  )  TY_CONSTR(1,A,0)
#define TY_ESC___(A  )  TY_CONSTR(2,A,0)
#define TY_ESC_CS(A,B)  TY_CONSTR(3,A,B)
#define TY_ESC_DE(A  )  TY_CONSTR(4,A,0)
#define TY_CSI_PS(A,N)  TY_CONSTR(5,A,N)
#define TY_CSI_PN(A  )  TY_CONSTR(6,A,0)
#define TY_CSI_PR(A,N)  TY_CONSTR(7,A,N)

#define TY_VT52__(A  )  TY_CONSTR(8,A,0)

#define TY_CSI_PG(A  )  TY_CONSTR(9,A,0)

// Tokenizer --------------------------------------------------------------- --

/* The tokenizers state

   The state is represented by the buffer (pbuf, ppos),
   and accompanied by decoded arguments kept in (argv,argc).
   Note that they are kept internal in the tokenizer.
*/

void TEmuVt102::resetToken()
{
  ppos = 0; argc = 0; argv[0] = 0; argv[1] = 0;
}

void TEmuVt102::addDigit(int dig)
{
  argv[argc] = 10*argv[argc] + dig;
}

void TEmuVt102::addArgument()
{
  argc = QMIN(argc+1,MAXARGS-1);
  argv[argc] = 0;
}

void TEmuVt102::pushToToken(int cc)
{
  pbuf[ppos] = cc;
  ppos = QMIN(ppos+1,MAXPBUF-1);
}

// Character Classes used while decoding

#define CTL  1
#define CHR  2
#define CPN  4
#define DIG  8
#define SCS 16
#define GRP 32

void TEmuVt102::initTokenizer()
{ int i; UINT8* s;
  for(i =  0;                    i < 256; i++) tbl[ i]  = 0;
  for(i =  0;                    i <  32; i++) tbl[ i] |= CTL;
  for(i = 32;                    i < 256; i++) tbl[ i] |= CHR;
  for(s = (UINT8*)"@ABCDGHLMPXcdfry"; *s; s++) tbl[*s] |= CPN;
  for(s = (UINT8*)"0123456789"      ; *s; s++) tbl[*s] |= DIG;
  for(s = (UINT8*)"()+*%"           ; *s; s++) tbl[*s] |= SCS;
  for(s = (UINT8*)"()+*#[]%"        ; *s; s++) tbl[*s] |= GRP;
  resetToken();
}

/* Ok, here comes the nasty part of the decoder.

   Instead of keeping an explicit state, we deduce it from the
   token scanned so far. It is then immediately combined with
   the current character to form a scanning decision.

   This is done by the following defines.

   - P is the length of the token scanned so far.
   - L (often P-1) is the position on which contents we base a decision.
   - C is a character or a group of characters (taken from 'tbl').

   Note that they need to applied in proper order.
*/

#define lec(P,L,C) (p == (P) &&                     s[(L)]         == (C))
#define lun(     ) (p ==  1  &&                       cc           >= 32 )
#define les(P,L,C) (p == (P) && s[L] < 256  && (tbl[s[(L)]] & (C)) == (C))
#define eec(C)     (p >=  3  &&        cc                          == (C))
#define ees(C)     (p >=  3  && cc < 256 &&    (tbl[  cc  ] & (C)) == (C))
#define eps(C)     (p >=  3  && s[2] != '?' && s[2] != '>' && cc < 256 && (tbl[  cc  ] & (C)) == (C))
#define epp( )     (p >=  3  && s[2] == '?'                              )
#define egt(     ) (p >=  3  && s[2] == '>'                              )
#define Xpe        (ppos>=2  && pbuf[1] == ']'                           )
#define Xte        (Xpe                        &&     cc           ==  7 )
#define ces(C)     (            cc < 256 &&    (tbl[  cc  ] & (C)) == (C) && !Xte)

#define ESC 27
#define CNTL(c) ((c)-'@')

void TEmuVt102::printScan(int cc)
{
  if (cc == CNTL('Q') || cc == CNTL('S') || cc == 0) return;

  pushToToken(cc); // advance the state

  int* s = pbuf;
  int  p = ppos;

  if (lec(1,0,ESC)) return;
  if (lec(2,1,'[')) return;
  if (lec(3,2,'4')) return;
  if (lec(3,2,'5')) return;
  if (lec(4,3,'i')) { if (s[2] == '4') setPrinterMode(false); resetToken(); return; }

  for (int i = 0; i < p; i++) fwrite(s+i,1,1,print_fd);
  resetToken();
}

// toggle printer mode

#define PRINT_COMMAND  "cat > /dev/null"

void TEmuVt102::setPrinterMode(bool on)
{
  if( on )
  { char* c = getenv("PRINT_COMMAND");
    print_fd = popen(c?c:PRINT_COMMAND,"w");
  }
  else
  {
    pclose(print_fd);
    print_fd = NULL;
  }
}

// process an incoming unicode character

void TEmuVt102::onRcvChar(int cc)
{ int i;

  if (print_fd) { printScan(cc); return; }

  if (cc == 127) return; //VT100: ignore.

  if (ces(    CTL))
  { // DEC HACK ALERT! Control Characters are allowed *within* esc sequences in VT100
    // This means, they do neither a resetToken nor a pushToToken. Some of them, do
    // of course. Guess this originates from a weakly layered handling of the X-on
    // X-off protocol, which comes really below this level.
    if (cc == CNTL('X') || cc == CNTL('Z') || cc == ESC) resetToken(); //VT100: CAN or SUB
    if (cc != ESC)    { tau( TY_CTL___(cc+'@' ),    0,   0); return; }
  }

  pushToToken(cc); // advance the state

  int* s = pbuf;
  int  p = ppos;

  if (getMode(MODE_Ansi)) // decide on proper action
  {
    if (lec(1,0,ESC)) {                                                       return; }
    if (les(2,1,GRP)) {                                                       return; }
    if (Xte         ) { XtermHack();                            resetToken(); return; }
    if (Xpe         ) {                                                       return; }
    if (lec(3,2,'?')) {                                                       return; }
    if (lec(3,2,'>')) {                                                       return; }
    if (lun(       )) { tau( TY_CHR___(), applyCharset(cc), 0); resetToken(); return; }
    if (lec(2,0,ESC)) { tau( TY_ESC___(s[1]),    0,   0);       resetToken(); return; }
    if (les(3,1,SCS)) { tau( TY_ESC_CS(s[1],s[2]),    0,   0);  resetToken(); return; }
    if (lec(3,1,'#')) { tau( TY_ESC_DE(s[2]),    0,   0);       resetToken(); return; }
    if (eps(    CPN)) { tau( TY_CSI_PN(cc), argv[0],argv[1]);   resetToken(); return; }
    if (ees(    DIG)) { addDigit(cc-'0');                                     return; }
    if (eec(    ';')) { addArgument();                                        return; }
    for (i=0;i<=argc;i++)
    if ( epp(     ))  { tau( TY_CSI_PR(cc,argv[i]),    0,   0); }
    else if(egt(    ))   { tau( TY_CSI_PG(cc     ),    0,   0); } // spec. case for ESC]>0c or ESC]>c
    else              { tau( TY_CSI_PS(cc,argv[i]),    0,   0); }
    resetToken();
  }
  else // mode VT52
  {
    if (lec(1,0,ESC))                                                      return;
    if (les(1,0,CHR)) { tau( TY_CHR___(       ), s[0],   0); resetToken(); return; }
    if (lec(2,1,'Y'))                                                      return;
    if (lec(3,1,'Y'))                                                      return;
    if (p < 4)        { tau( TY_VT52__(s[1]   ),    0,   0); resetToken(); return; }
                        tau( TY_VT52__(s[1]   ), s[2],s[3]); resetToken(); return;
  }
}

void TEmuVt102::XtermHack()
{ int i,arg = 0;
  for (i = 2; i < ppos && '0'<=pbuf[i] && pbuf[i]<'9' ; i++)
    arg = 10*arg + (pbuf[i]-'0');
  if (pbuf[i] != ';') { ReportErrorToken(); return; }
  QChar *str = new QChar[ppos-i-2];
  for (int j = 0; j < ppos-i-2; j++) str[j] = pbuf[i+1+j];
  QString unistr(str,ppos-i-2);
  // arg == 1 doesn't change the title. In XTerm it only changes the icon name
  // (btw: arg=0 changes title and icon, arg=1 only icon, arg=2 only title
  emit changeTitle(arg,unistr);
  delete [] str;
}

// Interpreting Codes ---------------------------------------------------------

/*
   Now that the incoming character stream is properly tokenized,
   meaning is assigned to them. These are either operations of
   the current screen, or of the emulation class itself.

   The token to be interpreteted comes in as a machine word
   possibly accompanied by two parameters.

   Likewise, the operations assigned to, come with up to two
   arguments. One could consider to make up a proper table
   from the function below.

   The technical reference manual provides more informations
   about this mapping.
*/

void TEmuVt102::tau( int token, int p, int q )
{
  switch (token)
  {

    case TY_CHR___(         ) : scr->ShowCharacter        (p         ); break; //UTF16

    //             127 DEL    : ignored on input

    case TY_CTL___('@'      ) : /* NUL: ignored                      */ break;
    case TY_CTL___('A'      ) : /* SOH: ignored                      */ break;
    case TY_CTL___('B'      ) : /* STX: ignored                      */ break;
    case TY_CTL___('C'      ) : /* ETX: ignored                      */ break;
    case TY_CTL___('D'      ) : /* EOT: ignored                      */ break;
    case TY_CTL___('E'      ) :      reportAnswerBack     (          ); break; //VT100
    case TY_CTL___('F'      ) : /* ACK: ignored                      */ break;
    case TY_CTL___('G'      ) : if (connected)
                                  gui->Bell  (          );
                                emit notifySessionState(NOTIFYBELL);
                                break; //VT100
    case TY_CTL___('H'      ) : scr->BackSpace            (          ); break; //VT100
    case TY_CTL___('I'      ) : scr->Tabulate             (          ); break; //VT100
    case TY_CTL___('J'      ) : scr->NewLine              (          ); break; //VT100
    case TY_CTL___('K'      ) : scr->NewLine              (          ); break; //VT100
    case TY_CTL___('L'      ) : scr->NewLine              (          ); break; //VT100
    case TY_CTL___('M'      ) : scr->Return               (          ); break; //VT100

    case TY_CTL___('N'      ) :      useCharset           (         1); break; //VT100
    case TY_CTL___('O'      ) :      useCharset           (         0); break; //VT100

    case TY_CTL___('P'      ) : /* DLE: ignored                      */ break;
    case TY_CTL___('Q'      ) : /* DC1: XON continue                 */ break; //VT100
    case TY_CTL___('R'      ) : /* DC2: ignored                      */ break;
    case TY_CTL___('S'      ) : /* DC3: XOFF halt                    */ break; //VT100
    case TY_CTL___('T'      ) : /* DC4: ignored                      */ break;
    case TY_CTL___('U'      ) : /* NAK: ignored                      */ break;
    case TY_CTL___('V'      ) : /* SYN: ignored                      */ break;
    case TY_CTL___('W'      ) : /* ETB: ignored                      */ break;
    case TY_CTL___('X'      ) : scr->ShowCharacter        (    0x2592); break; //VT100
    case TY_CTL___('Y'      ) : /* EM : ignored                      */ break;
    case TY_CTL___('Z'      ) : scr->ShowCharacter        (    0x2592); break; //VT100
    case TY_CTL___('['      ) : /* ESC: cannot be seen here.         */ break;
    case TY_CTL___('\\'     ) : /* FS : ignored                      */ break;
    case TY_CTL___(']'      ) : /* GS : ignored                      */ break;
    case TY_CTL___('^'      ) : /* RS : ignored                      */ break;
    case TY_CTL___('_'      ) : /* US : ignored                      */ break;

    case TY_ESC___('D'      ) : scr->index                (          ); break; //VT100
    case TY_ESC___('E'      ) : scr->NextLine             (          ); break; //VT100
    case TY_ESC___('H'      ) : scr->changeTabStop        (TRUE      ); break; //VT100
    case TY_ESC___('M'      ) : scr->reverseIndex         (          ); break; //VT100
    case TY_ESC___('Z'      ) :      reportTerminalType   (          ); break;
    case TY_ESC___('c'      ) :      reset                (          ); break;

    case TY_ESC___('n'      ) :      useCharset           (         2); break;
    case TY_ESC___('o'      ) :      useCharset           (         3); break;
    case TY_ESC___('7'      ) :      saveCursor           (          ); break;
    case TY_ESC___('8'      ) :      restoreCursor        (          ); break;

    case TY_ESC___('='      ) :          setMode      (MODE_AppKeyPad); break;
    case TY_ESC___('>'      ) :        resetMode      (MODE_AppKeyPad); break;
    case TY_ESC___('<'      ) :          setMode      (MODE_Ansi     ); break; //VT100

    case TY_ESC_CS('(',  '0') :      setCharset           (0,     '0'); break; //VT100
    case TY_ESC_CS('(',  'A') :      setCharset           (0,     'A'); break; //VT100
    case TY_ESC_CS('(',  'B') :      setCharset           (0,     'B'); break; //VT100
    case TY_ESC_CS('(',  'K') :      setCharset           (0,     'K'); break; //VT220
    case TY_ESC_CS('(',  'R') :      setCharset           (0,     'R'); break; //VT220

    case TY_ESC_CS(')',  '0') :      setCharset           (1,     '0'); break; //VT100
    case TY_ESC_CS(')',  'A') :      setCharset           (1,     'A'); break; //VT100
    case TY_ESC_CS(')',  'B') :      setCharset           (1,     'B'); break; //VT100
    case TY_ESC_CS(')',  'K') :      setCharset           (1,     'K'); break; //VT220
    case TY_ESC_CS(')',  'R') :      setCharset           (1,     'R'); break; //VT220

    case TY_ESC_CS('*',  '0') :      setCharset           (2,     '0'); break; //VT100
    case TY_ESC_CS('*',  'A') :      setCharset           (2,     'A'); break; //VT100
    case TY_ESC_CS('*',  'B') :      setCharset           (2,     'B'); break; //VT100
    case TY_ESC_CS('*',  'K') :      setCharset           (2,     'K'); break; //VT220
    case TY_ESC_CS('*',  'R') :      setCharset           (2,     'R'); break; //VT220

    case TY_ESC_CS('+',  '0') :      setCharset           (3,     '0'); break; //VT100
    case TY_ESC_CS('+',  'A') :      setCharset           (3,     'A'); break; //VT100
    case TY_ESC_CS('+',  'B') :      setCharset           (3,     'B'); break; //VT100
    case TY_ESC_CS('+',  'K') :      setCharset           (3,     'K'); break; //VT220
    case TY_ESC_CS('+',  'R') :      setCharset           (3,     'R'); break; //VT220

    case TY_ESC_CS('%',  'G') :      setCodec             (1         ); break; //LINUX
    case TY_ESC_CS('%',  '@') :      setCodec             (0         ); break; //LINUX

    case TY_ESC_DE('3'      ) : /* IGNORED: double high, top half    */ break;
    case TY_ESC_DE('4'      ) : /* IGNORED: double high, bottom half */ break;
    case TY_ESC_DE('5'      ) : /* IGNORED: single width, single high*/ break;
    case TY_ESC_DE('6'      ) : /* IGNORED: double width, single high*/ break;
    case TY_ESC_DE('8'      ) : scr->helpAlign            (          ); break;

    case TY_CSI_PS('K',    0) : scr->clearToEndOfLine     (          ); break;
    case TY_CSI_PS('K',    1) : scr->clearToBeginOfLine   (          ); break;
    case TY_CSI_PS('K',    2) : scr->clearEntireLine      (          ); break;
    case TY_CSI_PS('J',    0) : scr->clearToEndOfScreen   (          ); break;
    case TY_CSI_PS('J',    1) : scr->clearToBeginOfScreen (          ); break;
    case TY_CSI_PS('J',    2) : scr->clearEntireScreen    (          ); break;
    case TY_CSI_PS('g',    0) : scr->changeTabStop        (FALSE     ); break; //VT100
    case TY_CSI_PS('g',    3) : scr->clearTabStops        (          ); break; //VT100
    case TY_CSI_PS('h',    4) : scr->    setMode      (MODE_Insert   ); break;
    case TY_CSI_PS('h',   20) :          setMode      (MODE_NewLine  ); break;
    case TY_CSI_PS('i',    0) : /* IGNORE: attached printer          */ break; //VT100
    case TY_CSI_PS('i',    4) : /* IGNORE: attached printer          */ break; //VT100
    case TY_CSI_PS('i',    5) : setPrinterMode            (true      ); break; //VT100
    case TY_CSI_PS('l',    4) : scr->  resetMode      (MODE_Insert   ); break;
    case TY_CSI_PS('l',   20) :        resetMode      (MODE_NewLine  ); break;
    case TY_CSI_PS('s',    0) :      saveCursor           (          ); break;
    case TY_CSI_PS('u',    0) :      restoreCursor        (          ); break;

    case TY_CSI_PS('m',    0) : scr->setDefaultRendition  (          ); break;
    case TY_CSI_PS('m',    1) : scr->  setRendition     (RE_BOLD     ); break; //VT100
    case TY_CSI_PS('m',    4) : scr->  setRendition     (RE_UNDERLINE); break; //VT100
    case TY_CSI_PS('m',    5) : scr->  setRendition     (RE_BLINK    ); break; //VT100
    case TY_CSI_PS('m',    7) : scr->  setRendition     (RE_REVERSE  ); break;
    case TY_CSI_PS('m',   10) : /* IGNORED: mapping related          */ break; //LINUX
    case TY_CSI_PS('m',   11) : /* IGNORED: mapping related          */ break; //LINUX
    case TY_CSI_PS('m',   12) : /* IGNORED: mapping related          */ break; //LINUX
    case TY_CSI_PS('m',   22) : scr->resetRendition     (RE_BOLD     ); break;
    case TY_CSI_PS('m',   24) : scr->resetRendition     (RE_UNDERLINE); break;
    case TY_CSI_PS('m',   25) : scr->resetRendition     (RE_BLINK    ); break;
    case TY_CSI_PS('m',   27) : scr->resetRendition     (RE_REVERSE  ); break;

    case TY_CSI_PS('m',   30) : scr->setForeColor         (         0); break;
    case TY_CSI_PS('m',   31) : scr->setForeColor         (         1); break;
    case TY_CSI_PS('m',   32) : scr->setForeColor         (         2); break;
    case TY_CSI_PS('m',   33) : scr->setForeColor         (         3); break;
    case TY_CSI_PS('m',   34) : scr->setForeColor         (         4); break;
    case TY_CSI_PS('m',   35) : scr->setForeColor         (         5); break;
    case TY_CSI_PS('m',   36) : scr->setForeColor         (         6); break;
    case TY_CSI_PS('m',   37) : scr->setForeColor         (         7); break;
    case TY_CSI_PS('m',   39) : scr->setForeColorToDefault(          ); break;

    case TY_CSI_PS('m',   40) : scr->setBackColor         (         0); break;
    case TY_CSI_PS('m',   41) : scr->setBackColor         (         1); break;
    case TY_CSI_PS('m',   42) : scr->setBackColor         (         2); break;
    case TY_CSI_PS('m',   43) : scr->setBackColor         (         3); break;
    case TY_CSI_PS('m',   44) : scr->setBackColor         (         4); break;
    case TY_CSI_PS('m',   45) : scr->setBackColor         (         5); break;
    case TY_CSI_PS('m',   46) : scr->setBackColor         (         6); break;
    case TY_CSI_PS('m',   47) : scr->setBackColor         (         7); break;
    case TY_CSI_PS('m',   49) : scr->setBackColorToDefault(          ); break;

    case TY_CSI_PS('m',   90) : scr->setForeColor         (         8); break;
    case TY_CSI_PS('m',   91) : scr->setForeColor         (         9); break;
    case TY_CSI_PS('m',   92) : scr->setForeColor         (        10); break;
    case TY_CSI_PS('m',   93) : scr->setForeColor         (        11); break;
    case TY_CSI_PS('m',   94) : scr->setForeColor         (        12); break;
    case TY_CSI_PS('m',   95) : scr->setForeColor         (        13); break;
    case TY_CSI_PS('m',   96) : scr->setForeColor         (        14); break;
    case TY_CSI_PS('m',   97) : scr->setForeColor         (        15); break;

    case TY_CSI_PS('m',  100) : scr->setBackColor         (         8); break;
    case TY_CSI_PS('m',  101) : scr->setBackColor         (         9); break;
    case TY_CSI_PS('m',  102) : scr->setBackColor         (        10); break;
    case TY_CSI_PS('m',  103) : scr->setBackColor         (        11); break;
    case TY_CSI_PS('m',  104) : scr->setBackColor         (        12); break;
    case TY_CSI_PS('m',  105) : scr->setBackColor         (        13); break;
    case TY_CSI_PS('m',  106) : scr->setBackColor         (        14); break;
    case TY_CSI_PS('m',  107) : scr->setBackColor         (        15); break;

    case TY_CSI_PS('n',    5) :      reportStatus         (          ); break;
    case TY_CSI_PS('n',    6) :      reportCursorPosition (          ); break;
    case TY_CSI_PS('q',    0) : /* IGNORED: LEDs off                 */ break; //VT100
    case TY_CSI_PS('q',    1) : /* IGNORED: LED1 on                  */ break; //VT100
    case TY_CSI_PS('q',    2) : /* IGNORED: LED2 on                  */ break; //VT100
    case TY_CSI_PS('q',    3) : /* IGNORED: LED3 on                  */ break; //VT100
    case TY_CSI_PS('q',    4) : /* IGNORED: LED4 on                  */ break; //VT100
    case TY_CSI_PS('x',    0) :      reportTerminalParms  (         2); break; //VT100
    case TY_CSI_PS('x',    1) :      reportTerminalParms  (         3); break; //VT100

    case TY_CSI_PN('@'      ) : scr->insertChars          (p         ); break;
    case TY_CSI_PN('A'      ) : scr->cursorUp             (p         ); break; //VT100
    case TY_CSI_PN('B'      ) : scr->cursorDown           (p         ); break; //VT100
    case TY_CSI_PN('C'      ) : scr->cursorRight          (p         ); break; //VT100
    case TY_CSI_PN('D'      ) : scr->cursorLeft           (p         ); break; //VT100
    case TY_CSI_PN('G'      ) : scr->setCursorX           (p         ); break; //LINUX
    case TY_CSI_PN('H'      ) : scr->setCursorYX          (p,       q); break; //VT100
    case TY_CSI_PN('L'      ) : scr->insertLines          (p         ); break;
    case TY_CSI_PN('M'      ) : scr->deleteLines          (p         ); break;
    case TY_CSI_PN('P'      ) : scr->deleteChars          (p         ); break;
    case TY_CSI_PN('X'      ) : scr->eraseChars           (p         ); break;
    case TY_CSI_PN('c'      ) :      reportTerminalType   (          ); break; //VT100
    case TY_CSI_PN('d'      ) : scr->setCursorY           (p         ); break; //LINUX
    case TY_CSI_PN('f'      ) : scr->setCursorYX          (p,       q); break; //VT100
    case TY_CSI_PN('r'      ) :      setMargins           (p,       q); break; //VT100
    case TY_CSI_PN('y'      ) : /* IGNORED: Confidence test          */ break; //VT100

    case TY_CSI_PR('h',    1) :          setMode      (MODE_AppCuKeys); break; //VT100
    case TY_CSI_PR('l',    1) :        resetMode      (MODE_AppCuKeys); break; //VT100
    case TY_CSI_PR('s',    1) :         saveMode      (MODE_AppCuKeys); break; //FIXME
    case TY_CSI_PR('r',    1) :      restoreMode      (MODE_AppCuKeys); break; //FIXME

    case TY_CSI_PR('l',    2) :        resetMode      (MODE_Ansi     ); break; //VT100

    case TY_CSI_PR('h',    3) :      setColumns           (       132); break; //VT100
    case TY_CSI_PR('l',    3) :      setColumns           (        80); break; //VT100

    case TY_CSI_PR('h',    4) : /* IGNORED: soft scrolling           */ break; //VT100
    case TY_CSI_PR('l',    4) : /* IGNORED: soft scrolling           */ break; //VT100

    case TY_CSI_PR('h',    5) : scr->    setMode      (MODE_Screen   ); break; //VT100
    case TY_CSI_PR('l',    5) : scr->  resetMode      (MODE_Screen   ); break; //VT100

    case TY_CSI_PR('h',    6) : scr->    setMode      (MODE_Origin   ); break; //VT100
    case TY_CSI_PR('l',    6) : scr->  resetMode      (MODE_Origin   ); break; //VT100
    case TY_CSI_PR('s',    6) : scr->   saveMode      (MODE_Origin   ); break; //FIXME
    case TY_CSI_PR('r',    6) : scr->restoreMode      (MODE_Origin   ); break; //FIXME

    case TY_CSI_PR('h',    7) : scr->    setMode      (MODE_Wrap     ); break; //VT100
    case TY_CSI_PR('l',    7) : scr->  resetMode      (MODE_Wrap     ); break; //VT100
    case TY_CSI_PR('s',    7) : scr->   saveMode      (MODE_Wrap     ); break; //FIXME
    case TY_CSI_PR('r',    7) : scr->restoreMode      (MODE_Wrap     ); break; //FIXME

    case TY_CSI_PR('h',    8) : /* IGNORED: autorepeat on            */ break; //VT100
    case TY_CSI_PR('l',    8) : /* IGNORED: autorepeat off           */ break; //VT100

    case TY_CSI_PR('h',    9) : /* IGNORED: interlace                */ break; //VT100
    case TY_CSI_PR('l',    9) : /* IGNORED: interlace                */ break; //VT100

    case TY_CSI_PR('h',   25) :          setMode      (MODE_Cursor   ); break; //VT100
    case TY_CSI_PR('l',   25) :        resetMode      (MODE_Cursor   ); break; //VT100

    case TY_CSI_PR('h',   41) : /* IGNORED: obsolete more(1) fix     */ break; //XTERM
    case TY_CSI_PR('l',   41) : /* IGNORED: obsolete more(1) fix     */ break; //XTERM
    case TY_CSI_PR('s',   41) : /* IGNORED: obsolete more(1) fix     */ break; //XTERM
    case TY_CSI_PR('r',   41) : /* IGNORED: obsolete more(1) fix     */ break; //XTERM

    case TY_CSI_PR('h',   47) :          setMode      (MODE_AppScreen); break; //VT100
    case TY_CSI_PR('l',   47) :        resetMode      (MODE_AppScreen); break; //VT100
    case TY_CSI_PR('s',   47) :         saveMode      (MODE_AppScreen); break; //XTERM
    case TY_CSI_PR('r',   47) :      restoreMode      (MODE_AppScreen); break; //XTERM

    // XTerm defines the following modes:
    // SET_VT200_MOUSE             1000
    // SET_VT200_HIGHLIGHT_MOUSE   1001
    // SET_BTN_EVENT_MOUSE         1002
    // SET_ANY_EVENT_MOUSE         1003
    //
    // FIXME: Modes 1000,1002 and 1003 have subtle differences which we don't
    // support yet, we treat them all the same.

    case TY_CSI_PR('h', 1000) :          setMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('l', 1000) :        resetMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('s', 1000) :         saveMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('r', 1000) :      restoreMode      (MODE_Mouse1000); break; //XTERM

    case TY_CSI_PR('h', 1001) : /* IGNORED: hilite mouse tracking    */ break; //XTERM
    case TY_CSI_PR('l', 1001) :        resetMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('s', 1001) : /* IGNORED: hilite mouse tracking    */ break; //XTERM
    case TY_CSI_PR('r', 1001) : /* IGNORED: hilite mouse tracking    */ break; //XTERM

    case TY_CSI_PR('h', 1002) :          setMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('l', 1002) :        resetMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('s', 1002) :         saveMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('r', 1002) :      restoreMode      (MODE_Mouse1000); break; //XTERM

    case TY_CSI_PR('h', 1003) :          setMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('l', 1003) :        resetMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('s', 1003) :         saveMode      (MODE_Mouse1000); break; //XTERM
    case TY_CSI_PR('r', 1003) :      restoreMode      (MODE_Mouse1000); break; //XTERM

    case TY_CSI_PR('h', 1047) :          setMode      (MODE_AppScreen); break; //XTERM
    case TY_CSI_PR('l', 1047) : screen[1]->clearEntireScreen(); resetMode(MODE_AppScreen); break; //XTERM
    case TY_CSI_PR('s', 1047) :         saveMode      (MODE_AppScreen); break; //XTERM
    case TY_CSI_PR('r', 1047) :      restoreMode      (MODE_AppScreen); break; //XTERM

    //FIXME: Unitoken: save translations
    case TY_CSI_PR('h', 1048) :      saveCursor           (          ); break; //XTERM
    case TY_CSI_PR('l', 1048) :      restoreCursor        (          ); break; //XTERM
    case TY_CSI_PR('s', 1048) :      saveCursor           (          ); break; //XTERM
    case TY_CSI_PR('r', 1048) :      restoreCursor        (          ); break; //XTERM

    //FIXME: every once new sequences like this pop up in xterm.
    //       Here's a guess of what they could mean.
    case TY_CSI_PR('h', 1049) : saveCursor(); screen[1]->clearEntireScreen(); setMode(MODE_AppScreen); break; //XTERM
    case TY_CSI_PR('l', 1049) : resetMode(MODE_AppScreen); restoreCursor(); break; //XTERM

    //FIXME: when changing between vt52 and ansi mode evtl do some resetting.
    case TY_VT52__('A'      ) : scr->cursorUp             (         1); break; //VT52
    case TY_VT52__('B'      ) : scr->cursorDown           (         1); break; //VT52
    case TY_VT52__('C'      ) : scr->cursorRight          (         1); break; //VT52
    case TY_VT52__('D'      ) : scr->cursorLeft           (         1); break; //VT52

    case TY_VT52__('F'      ) :      setAndUseCharset     (0,     '0'); break; //VT52
    case TY_VT52__('G'      ) :      setAndUseCharset     (0,     'B'); break; //VT52

    case TY_VT52__('H'      ) : scr->setCursorYX          (1,1       ); break; //VT52
    case TY_VT52__('I'      ) : scr->reverseIndex         (          ); break; //VT52
    case TY_VT52__('J'      ) : scr->clearToEndOfScreen   (          ); break; //VT52
    case TY_VT52__('K'      ) : scr->clearToEndOfLine     (          ); break; //VT52
    case TY_VT52__('Y'      ) : scr->setCursorYX          (p-31,q-31 ); break; //VT52
    case TY_VT52__('Z'      ) :      reportTerminalType   (           ); break; //VT52
    case TY_VT52__('<'      ) :          setMode      (MODE_Ansi     ); break; //VT52
    case TY_VT52__('='      ) :          setMode      (MODE_AppKeyPad); break; //VT52
    case TY_VT52__('>'      ) :        resetMode      (MODE_AppKeyPad); break; //VT52

    case TY_CSI_PG('c'      ) :  reportSecondaryAttributes(          ); break; //VT100

    default : ReportErrorToken();    break;
  };
}

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                          Terminal to Host protocol                        */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/* 
   Outgoing bytes originate from several sources:

   - Replies to Enquieries.
   - Mouse Events
   - Keyboard Events
*/

/*!
*/

void TEmuVt102::sendString(const char* s)
{
  emit sndBlock(s,strlen(s));
}

// Replies ----------------------------------------------------------------- --

// This section copes with replies send as response to an enquiery control code.

/*!
*/

void TEmuVt102::reportCursorPosition()
{ char tmp[20];
  sprintf(tmp,"\033[%d;%dR",scr->getCursorY()+1,scr->getCursorX()+1);
  sendString(tmp);
}

/*
   What follows here is rather obsolete and faked stuff.
   The correspondent enquieries are neverthenless issued.
*/

/*!
*/

void TEmuVt102::reportTerminalType()
{
  // Primary device attribute response (Request was: ^[[0c or ^[[c (from TT321 Users Guide))
  //   VT220:  ^[[?63;1;2;3;6;7;8c   (list deps on emul. capabilities)
  //   VT100:  ^[[?1;2c
  //   VT101:  ^[[?1;0c
  //   VT102:  ^[[?6v
  if (getMode(MODE_Ansi))
    sendString("\033[?1;2c");     // I'm a VT100
  else
    sendString("\033/Z");         // I'm a VT52
}

void TEmuVt102::reportSecondaryAttributes()
{
  // Seconday device attribute response (Request was: ^[[>0c or ^[[>c)
  if (getMode(MODE_Ansi))
    sendString("\033[>0;115;0c"); // Why 115?  ;)
  else
    sendString("\033/Z");         // FIXME I don't think VT52 knows about it but kept for
                                  // konsoles backward compatibility.
}

void TEmuVt102::reportTerminalParms(int p)
// DECREPTPARM
{ char tmp[100];
  sprintf(tmp,"\033[%d;1;1;112;112;1;0x",p); // not really true.
  sendString(tmp);
}

void TEmuVt102::reportStatus()
{
  sendString("\033[0n"); //VT100. Device status report. 0 = Ready.
}

#define ANSWER_BACK "" // This is really obsolete VT100 stuff.

void TEmuVt102::reportAnswerBack()
{
  char* a = getenv("ANSWER_BACK");
  
  sendString(a?a:ANSWER_BACK);
}

// Mouse Handling ---------------------------------------------------------- --

/*!
    Mouse clicks are possibly reported to the client
    application if it has issued interest in them.
    They are normally consumed by the widget for copy
    and paste, but may be propagated from the widget
    when gui->setMouseMarks is set via setMode(MODE_Mouse1000).

    `x',`y' are 1-based.
    `ev' (event) indicates the button pressed (0-2)
                 or a general mouse release (3).
*/

void TEmuVt102::onMouse( int cb, int cx, int cy )
{ char tmp[20];
  if (!connected) return;
  sprintf(tmp,"\033[M%c%c%c",cb+040,cx+040,cy+040);
  sendString(tmp);
}

// Keyboard Handling ------------------------------------------------------- --

#if defined(HAVE_XTEST) || defined(HAVE_XKB)
static void scrolllock_set_off();
static void scrolllock_set_on();
#endif

void TEmuVt102::scrollLock(const bool lock)
{
  if (lock)
  {
    holdScreen = true;
    emit sndBlock("\023", 1); // XOFF -> ^S
  }
  else
  {
    holdScreen = false;
    emit sndBlock("\021", 1); // XON -> ^Q
  }
#if defined(HAVE_XTEST) || defined(HAVE_XKB)
  if (holdScreen)
    scrolllock_set_on();
  else
    scrolllock_set_off();
#endif
}

void TEmuVt102::onScrollLock()
{
  bool switchlock = !holdScreen;
  scrollLock(switchlock);
}

#define encodeMode(M,B) BITS(B,getMode(M))
#define encodeStat(M,B) BITS(B,((ev->state() & (M)) == (M)))

/*
   Keyboard event handling has been simplified somewhat by pushing
   the complications towards a configuration file [see KeyTrans class].
*/

void TEmuVt102::onKeyPress( QKeyEvent* ev )
{
  if (!listenToKeyPress) return; // someone else gets the keys
  emit notifySessionState(NOTIFYNORMAL);

//printf("State/Key: 0x%04x 0x%04x (%d,%d)\n",ev->state(),ev->key(),ev->text().length(),ev->text().length()?ev->text().ascii()[0]:0);

  // lookup in keyboard translation table ...
  int cmd = CMD_none; 
  const char* txt; 
  int len;
  bool metaspecified;
  if (keytrans->findEntry(ev->key(), encodeMode(MODE_NewLine  , BITS_NewLine   ) + // OLD,
                                     encodeMode(MODE_Ansi     , BITS_Ansi      ) + // OBSOLETE,
                                     encodeMode(MODE_AppCuKeys, BITS_AppCuKeys ) + // VT100 stuff
                                     encodeStat(ControlButton , BITS_Control   ) +
                                     encodeStat(ShiftButton   , BITS_Shift     ) +
                                     encodeStat(AltButton     , BITS_Alt       ),
                          &cmd, &txt, &len, &metaspecified ))
//printf("cmd: %d, %s, %d\n",cmd,txt,len);
  switch(cmd) // ... and execute if found.
  {
    case CMD_emitClipboard  : gui->emitSelection(false,false); return;
    case CMD_emitSelection  : gui->emitSelection(true,false); return;
    case CMD_scrollPageUp   : gui->doScroll(-gui->Lines()/2); return;
    case CMD_scrollPageDown : gui->doScroll(+gui->Lines()/2); return;
    case CMD_scrollLineUp   : gui->doScroll(-1             ); return;
    case CMD_scrollLineDown : gui->doScroll(+1             ); return;
    case CMD_prevSession    : 
	if ( QApplication::reverseLayout() )
	    emit nextSession();
	else
	    emit prevSession();             
	return;
    case CMD_nextSession    : 
	if ( QApplication::reverseLayout() )
	    emit prevSession();
	else
	    emit nextSession();             
	return;
    case CMD_newSession     : emit newSession();              return;
    case CMD_renameSession  : emit renameSession();           return;
    case CMD_activateMenu   : emit activateMenu();            return;
    case CMD_moveSessionLeft : 
	if ( QApplication::reverseLayout() )
	    emit moveSessionRight();
	else
	    emit moveSessionLeft();        
	return;
    case CMD_moveSessionRight: 
	if ( QApplication::reverseLayout() )
	    emit moveSessionLeft();
	else
	    emit moveSessionRight();       
	return;
    case CMD_scrollLock     : onScrollLock(                ); return;
  }

  // revert to non-history when typing
  if (scr->getHistCursor() != scr->getHistLines() && (!ev->text().isEmpty()
    || ev->key()==Key_Down || ev->key()==Key_Up || ev->key()==Key_Left || ev->key()==Key_Right
    || ev->key()==Key_PageUp || ev->key()==Key_PageDown))
    scr->setHistCursor(scr->getHistLines());

  if (cmd==CMD_send) {
//printf("%s %s '%s'\n",(ev->state()&AltButton)?"alt":"",metaspecified?"meta":"",txt);
    if ((ev->state() & AltButton) && !metaspecified ) sendString("\033");
    emit sndBlock(txt,len);
    return;
  }

  // fall back handling
  if (!ev->text().isEmpty())
  {
//printf("%s %s '%s'\n",(ev->state()&AltButton)?"alt":"",metaspecified?"meta":"",ev->text().data());
    if (ev->state() & AltButton) sendString("\033"); // ESC, this is the ALT prefix
    QCString s = codec->fromUnicode(ev->text());     // encode for application
    // FIXME: In Qt 2, QKeyEvent::text() would return "\003" for Ctrl-C etc.
    //        while in Qt 3 it returns the actual key ("c" or "C") which caused
    //        the ControlButton to be ignored. This hack seems to work for
    //        latin1 locales at least. Please anyone find a clean solution (malte)
    if (ev->state() & ControlButton)
      s.fill(ev->ascii(), 1);
    emit sndBlock(s.data(),s.length());              // we may well have s.length() > 1 
    return;
  }
}

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                                VT100 Charsets                             */
/*                                                                           */
/* ------------------------------------------------------------------------- */

// Character Set Conversion ------------------------------------------------ --

/* 
   The processing contains a VT100 specific code translation layer.
   It's still in use and mainly responsible for the line drawing graphics.

   These and some other glyphs are assigned to codes (0x5f-0xfe)
   normally occupied by the latin letters. Since this codes also
   appear within control sequences, the extra code conversion
   does not permute with the tokenizer and is placed behind it
   in the pipeline. It only applies to tokens, which represent
   plain characters.

   This conversion it eventually continued in TEWidget.C, since 
   it might involve VT100 enhanced fonts, which have these
   particular glyphs allocated in (0x00-0x1f) in their code page.
*/

#define CHARSET charset[scr==screen[1]]

// Apply current character map.

unsigned short TEmuVt102::applyCharset(unsigned short c)
{
  if (CHARSET.graphic && 0x5f <= c && c <= 0x7e) return vt100_graphics[c-0x5f];
  if (CHARSET.pound                && c == '#' ) return 0xa3;   // This mode is obsolete
  if ('[' <= c && c <= ']') return CHARSET.trans[c-'['+0]&0xff; // This mode is ancient
  if ('{' <= c && c <= '~') return CHARSET.trans[c-'{'+3]&0xff; // This mode is ancient
  return c;
}

/*
   "Charset" related part of the emulation state.
   This configures the VT100 charset filter.

   While most operation work on the current screen,
   the following two are different.
*/

void TEmuVt102::resetCharset(int scrno)
{
  charset[scrno].cu_cs   = 0;
  strncpy(charset[scrno].charset,"BBBB",4);
  charset[scrno].sa_graphic = FALSE;
  charset[scrno].sa_pound   = FALSE;
  charset[scrno].graphic = FALSE;
  charset[scrno].pound   = FALSE;
  strncpy(charset[scrno].trans,"[\\]{|}~",7);
}

/*!
*/

void TEmuVt102::setCharset(int n, int cs) // on both screens.
{
  charset[0].charset[n&3] = cs; useCharset(charset[0].cu_cs);
  charset[1].charset[n&3] = cs; useCharset(charset[1].cu_cs);
}

/*!
*/

void TEmuVt102::setAndUseCharset(int n, int cs)
{
  CHARSET.charset[n&3] = cs;
  useCharset(n&3);
}

/*!
*/

void TEmuVt102::useCharset(int n)
{
  CHARSET.cu_cs   = n&3;
  CHARSET.graphic = (CHARSET.charset[n&3] == '0');
  CHARSET.pound   = (CHARSET.charset[n&3] == 'A'); //This mode is obsolete
  strncpy(CHARSET.trans,"[\\]{|}~",7); // ancient mode, identical
  //FIXME: we might better use octal strings below to prevent filter problems
  if (CHARSET.charset[n&3] == 'K') strncpy(CHARSET.trans,"�������",7); // ancient mode, german
  if (CHARSET.charset[n&3] == 'R') strncpy(CHARSET.trans,"�����",7); // ancient mode, french
}

void TEmuVt102::setMargins(int t, int b)
{
  screen[0]->setMargins(t, b);
  screen[1]->setMargins(t, b);
}

/*! Save the cursor position and the rendition attribute settings. */

void TEmuVt102::saveCursor()
{
  CHARSET.sa_graphic = CHARSET.graphic;
  CHARSET.sa_pound   = CHARSET.pound; //This mode is obsolete
  strncpy(CHARSET.sa_trans,CHARSET.trans,7); //This mode is ancient
  // we are not clear about these
  //sa_charset = charsets[cScreen->charset];
  //sa_charset_num = cScreen->charset;
  scr->saveCursor();
}

/*! Restore the cursor position and the rendition attribute settings. */

void TEmuVt102::restoreCursor()
{
  CHARSET.graphic = CHARSET.sa_graphic;
  CHARSET.pound   = CHARSET.sa_pound; //This mode is obsolete
  strncpy(CHARSET.trans,CHARSET.sa_trans,7); //This mode is ancient
  scr->restoreCursor();
}

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                                Mode Operations                            */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/*
   Some of the emulations state is either added to the state of the screens.

   This causes some scoping problems, since different emulations choose to
   located the mode either to the current screen or to both.

   For strange reasons, the extend of the rendition attributes ranges over
   all screens and not over the actual screen.

   We decided on the precise precise extend, somehow.
*/

// "Mode" related part of the state. These are all booleans.

void TEmuVt102::resetModes()
{
  resetMode(MODE_Mouse1000); saveMode(MODE_Mouse1000);
  resetMode(MODE_AppScreen); saveMode(MODE_AppScreen);
  // here come obsolete modes
  resetMode(MODE_AppCuKeys); saveMode(MODE_AppCuKeys);
  resetMode(MODE_NewLine  );
    setMode(MODE_Ansi     );
  holdScreen = false;
}

void TEmuVt102::setMode(int m)
{
  currParm.mode[m] = TRUE;
  switch (m)
  {
    case MODE_Mouse1000 : gui->setMouseMarks(FALSE);
    break;

    case MODE_AppScreen : screen[1]->clearSelection();
                          setScreen(1);
    break;
  }
  if (m < MODES_SCREEN || m == MODE_NewLine)
  {
    screen[0]->setMode(m);
    screen[1]->setMode(m);
  }
}

void TEmuVt102::resetMode(int m)
{
  currParm.mode[m] = FALSE;
  switch (m)
  {
    case MODE_Mouse1000 : gui->setMouseMarks(TRUE);
    break;

    case MODE_AppScreen : screen[0]->clearSelection();
                          setScreen(0);
    break;
  }
  if (m < MODES_SCREEN || m == MODE_NewLine)
  {
    screen[0]->resetMode(m);
    screen[1]->resetMode(m);
  }
}

void TEmuVt102::saveMode(int m)
{
  saveParm.mode[m] = currParm.mode[m];
}

void TEmuVt102::restoreMode(int m)
{
  if(saveParm.mode[m]) setMode(m); else resetMode(m);
}

BOOL TEmuVt102::getMode(int m)
{
  return currParm.mode[m];
}

void TEmuVt102::setConnect(bool c)
{
  TEmulation::setConnect(c);
  if (c)
  { // refresh mouse mode
    if (getMode(MODE_Mouse1000))
      setMode(MODE_Mouse1000);
    else
      resetMode(MODE_Mouse1000);
#if defined(HAVE_XTEST) || defined(HAVE_XKB)
    if (holdScreen)
      scrolllock_set_on();
    else
      scrolllock_set_off();
#endif
  }
}

/* ------------------------------------------------------------------------- */
/*                                                                           */
/*                               Diagnostic                                  */
/*                                                                           */
/* ------------------------------------------------------------------------- */

/*! shows the contents of the scan buffer.

    This functions is used for diagnostics. It is called by \e ReportErrorToken
    to inform about strings that cannot be decoded or handled by the emulation.

    \sa ReportErrorToken
*/

static void hexdump(int* s, int len)
{ int i;
  for (i = 0; i < len; i++)
  {
    if (s[i] == '\\')
      printf("\\\\");
    else
    if ((s[i]) > 32 && s[i] < 127)
      printf("%c",s[i]);
    else
      printf("\\%04x(hex)", s[i]);
  }
}

void TEmuVt102::scan_buffer_report()
{
  if (ppos == 0 || ppos == 1 && (pbuf[0] & 0xff) >= 32) return;
  printf("token: "); hexdump(pbuf, ppos); printf("\n");
}

void TEmuVt102::ReportErrorToken()
{
  printf("undecodable "); scan_buffer_report();
}

/*
 Originally comes from NumLockX http://dforce.sh.cvut.cz/~seli/en/numlockx

 NumLockX
 
 Copyright (C) 2000-2001 Lubos Lunak        <l.lunak@kde.org>
 Copyright (C) 2001      Oswald Buddenhagen <ossi@kde.org>

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

****************************************************************************/

#include <X11/Xlib.h>

#ifdef HAVE_XTEST
#include <X11/extensions/XTest.h>
#endif

#ifdef HAVE_XKB
#define explicit myexplicit
#include <X11/XKBlib.h>
#undef explicit
#endif

#include <X11/keysym.h>

#if defined(HAVE_XTEST) || defined(HAVE_XKB)

/* the XKB stuff is based on code created by Oswald Buddenhagen <ossi@kde.org> */
#ifdef HAVE_XKB
static int xkb_init()
{
    int xkb_opcode, xkb_event, xkb_error;
    int xkb_lmaj = XkbMajorVersion;
    int xkb_lmin = XkbMinorVersion;
    return XkbLibraryVersion( &xkb_lmaj, &xkb_lmin )
        && XkbQueryExtension( qt_xdisplay(), &xkb_opcode, &xkb_event, &xkb_error,
			       &xkb_lmaj, &xkb_lmin );
}
    
static unsigned int xkb_mask_modifier( XkbDescPtr xkb, const char *name )
{
    int i;
    if( !xkb || !xkb->names )
	return 0;
    for( i = 0;
         i < XkbNumVirtualMods;
	 i++ )
	{
	char* modStr = XGetAtomName( xkb->dpy, xkb->names->vmods[i] );
	if( modStr != NULL && strcmp(name, modStr) == 0 )
	    {
	    unsigned int mask;
	    XkbVirtualModsToReal( xkb, 1 << i, &mask );
	    return mask;
	    }
	}
    return 0;
}

static unsigned int xkb_scrolllock_mask()
{
    XkbDescPtr xkb;
    if(( xkb = XkbGetKeyboard( qt_xdisplay(), XkbAllComponentsMask, XkbUseCoreKbd )) != NULL )
	{
        unsigned int mask = xkb_mask_modifier( xkb, "ScrollLock" );
        XkbFreeKeyboard( xkb, 0, True );
        return mask;
        }
    return 0;
}

static unsigned int scrolllock_mask = 0;
        
static int xkb_set_on()
{
    if (!scrolllock_mask)
    {
       if( !xkb_init())
          return 0;
       scrolllock_mask = xkb_scrolllock_mask();
       if( scrolllock_mask == 0 )
          return 0;
    }
    XkbLockModifiers ( qt_xdisplay(), XkbUseCoreKbd, scrolllock_mask, scrolllock_mask);
    return 1;
}
    
static int xkb_set_off()
{
    if (!scrolllock_mask)
    {
       if( !xkb_init())
          return 0;
       scrolllock_mask = xkb_scrolllock_mask();
       if( scrolllock_mask == 0 )
          return 0;
    }
    XkbLockModifiers ( qt_xdisplay(), XkbUseCoreKbd, scrolllock_mask, 0);
    return 1;
}
#endif

#ifdef HAVE_XTEST
static int xtest_get_scrolllock_state()
{
    int i;
    int scrolllock_mask = 0;
    Window dummy1, dummy2;
    int dummy3, dummy4, dummy5, dummy6;
    unsigned int mask;
    XModifierKeymap* map = XGetModifierMapping( qt_xdisplay() );
    KeyCode scrolllock_keycode = XKeysymToKeycode( qt_xdisplay(), XK_Scroll_Lock );
    if( scrolllock_keycode == NoSymbol )
        return 0;
    for( i = 0;
         i < 8;
         ++i )
        {
	if( map->modifiermap[ map->max_keypermod * i ] == scrolllock_keycode )
		scrolllock_mask = 1 << i;
	}
    XQueryPointer( qt_xdisplay(), DefaultRootWindow( qt_xdisplay() ), &dummy1, &dummy2,
        &dummy3, &dummy4, &dummy5, &dummy6, &mask );
    XFreeModifiermap( map );
    return mask & scrolllock_mask;
}

static void xtest_change_scrolllock()
{
    XTestFakeKeyEvent( qt_xdisplay(), XKeysymToKeycode( qt_xdisplay(), XK_Scroll_Lock ), True, CurrentTime );
    XTestFakeKeyEvent( qt_xdisplay(), XKeysymToKeycode( qt_xdisplay(), XK_Scroll_Lock ), False, CurrentTime );
}

static void xtest_set_on()
{
    if( !xtest_get_scrolllock_state())
        xtest_change_scrolllock();
}

static void xtest_set_off()
{
    if( xtest_get_scrolllock_state())
        xtest_change_scrolllock();
}
#endif

static void scrolllock_set_on()
{
#ifdef HAVE_XKB
    if( xkb_set_on())
        return;
#endif
#ifdef HAVE_XTEST
    xtest_set_on();
#endif
}

static void scrolllock_set_off()
{
#ifdef HAVE_XKB
    if( xkb_set_off())
        return;
#endif
#ifdef HAVE_XTEST
    xtest_set_off();
#endif
}
#endif // defined(HAVE_XTEST) || defined(HAVE_XKB)
