#define TY_CONSTR(T,A,N) ((int(N) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(T) & 0xff))

def TY_CHR___(   ): return TY_CONSTR(0,0,0)
def TY_CTL___(A  ): return TY_CONSTR(1,A,0)
def TY_ESC___(A  ): return TY_CONSTR(2,A,0)
def TY_ESC_CS(A,B): return TY_CONSTR(3,A,B)
def TY_ESC_DE(A  ): return TY_CONSTR(4,A,0)
def TY_CSI_PS(A,N): return TY_CONSTR(5,A,N)
def TY_CSI_PN(A  ): return TY_CONSTR(6,A,0)
def TY_CSI_PR(A,N): return TY_CONSTR(7,A,N)
def TY_VT52__(A  ): return TY_CONSTR(8,A,0)
def TY_CSI_PG(A  ): return TY_CONSTR(9,A,0)

#define lec(P,L,C) p == P and s[L] == C
#define lun(     ) p == 1 and cc >= 32 )
#define les(P,L,C) p == P and s[L] < 256  and (self.__tbl[s[L]] & C) == C
#define eec(C)     p >= 3 and cc == C
#define ees(C)     p >= 3 and cc < 256 and (self.__tbl[cc] & C) == C
#define eps(C)     p >= 3 and s[2] != '?' and s[2] != '>' and cc < 256 and (self.__tbl[cc] & C) == C
#define epp( )     p >= 3 and s[2] == '?'
#define egt(     ) p >= 3 and s[2] == '>'
#define Xpe        (len(self.__pbuf)-1) >= 2 and self.__pbuf[1] == ']'
#define Xte        Xpe and cc == 7
#define ces(C)     cc < 256 and (self.__tbl[cc] & C) == C and not Xte

#define CNTL(c) (ord(c)-ord('@'))

## Test

void TEmuVt102::printScan(int cc)
{
  if (cc == CNTL('Q') || cc == CNTL('S') || cc == 0) return;

  pushToToken(cc); // advance the state

  s = pbuf;
  p = ppos;

  if lec(1,0,ESC): // lec(1,0,ESC)
      return;
  if lec(2,1,'['): // lec(2,1,'[')
      return;
  if lec(3,2,'4'): // lec(3,2,'4')
      return;
  if lec(3,2,'5'): //lec(3,2,'5')
      return;
  if lec(4,3,'i'): // lec(4,3,'i')
      if s[2] == '4':
          setPrinterMode(false)
          resetToken()
          return

  for (int i = 0; i < p; i++) fwrite(s+i,1,1,print_fd);
  resetToken();
}


// process an incoming unicode character

void TEmuVt102::onRcvChar(int cc)
{ int i;

  if (print_fd) { printScan(cc); return; }

  if (cc == 127) return; //VT100: ignore.

  if ces(CTL): // ces(CTL)

    // DEC HACK ALERT! Control Characters are allowed *within* esc sequences in VT100
    // This means, they do neither a resetToken nor a pushToToken. Some of them, do
    // of course. Guess this originates from a weakly layered handling of the X-on
    // X-off protocol, which comes really below this level.
    if (cc == CNTL('X') || cc == CNTL('Z') || cc == ESC) resetToken(); //VT100: CAN or SUB
    if (cc != ESC)    { tau( TY_CTL___(cc+'@' ),    0,   0); return; }
  }

  pushToToken(cc) # Advance the state

  int* s = pbuf;
  int  p = ppos;

  if (getMode(MODE_Ansi): # Decide on proper action
    if lec(1,0,ESC): // lec(1,0,ESC)
        return
    if les(2,1,GRP): // les(2,1,GRP)
        return; }
    if Xte: // Xte
        XtermHack()
        resetToken()
        return
    if Xpe: // Xpe
        return
    if lec(3,2,'?'): //lec(3,2,'?')
        return
    if lec(3,2,'>'): // lec(3,2,'>')
        return
    if lun(       ): // lun()
        tau( TY_CHR___(), applyCharset(cc), 0)
        resetToken()
        return
    if lec(2,0,ESC): // lec(2,0,ESC)
        tau( TY_ESC___(s[1]), 0, 0)
        resetToken()
        return
    if les(3,1,SCS): // les(3,1,SCS)
        tau( TY_ESC_CS(s[1],s[2]), 0, 0)
        resetToken()
        return
    if lec(3,1,'#'): // lec(3,1,'#')
        tau( TY_ESC_DE(s[2]), 0, 0)
        resetToken()
        return
    if eps(CPN): // eps(CPN)
        tau( TY_CSI_PN(cc), argv[0],argv[1])
        resetToken()
        return
    if ees(    DIG): // ees(DIG)
        addDigit(cc-'0')
        return
    if eec(    ';'): // eec(';')
        addArgument()
        return
    for (i=0;i<=argc;i++)
    if epp(     ): //
          tau( TY_CSI_PR(cc,argv[i]), 0, 0)
    elif egt(): //
        tau( TY_CSI_PG(cc), 0, 0) # spec. case for ESC]>0c or ESC]>c
    else:
        tau( TY_CSI_PS(cc,argv[i]), 0, 0)
    resetToken();
  else: // mode VT52
    if lec(1,0,ESC): // lec(1,0,ESC)
        return;
    if les(1,0,CHR): // les(1,0,CHR)
        tau( TY_CHR___(), s[0], 0)
        resetToken()
        return
    if lec(2,1,'Y'): // lec(2,1,'Y')
        return
    if lec(3,1,'Y'): // lec(3,1,'Y')
        return
    if p < 4:
        tau( TY_VT52__(s[1]), 0, 0)
        resetToken()
        return
    tau( TY_VT52__(s[1]), s[2],s[3])
    resetToken()
    return
