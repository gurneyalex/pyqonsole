# 1 "cpp2py.cpp"
# 1 "<built-in>"
# 1 "<command line>"
# 1 "cpp2py.cpp"


def TY_CHR___( ): return ((int(0) & 0xffff) << 16) | ((int(0) & 0xff) << 8) | ((int(0) & 0xff))
def TY_CTL___(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(1) & 0xff))
def TY_ESC___(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(2) & 0xff))
def TY_ESC_CS(A,B): return ((int(B) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(3) & 0xff))
def TY_ESC_DE(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(4) & 0xff))
def TY_CSI_PS(A,N): return ((int(N) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(5) & 0xff))
def TY_CSI_PN(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(6) & 0xff))
def TY_CSI_PR(A,N): return ((int(N) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(7) & 0xff))
def TY_VT52__(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(8) & 0xff))
def TY_CSI_PG(A ): return ((int(0) & 0xffff) << 16) | ((int(A) & 0xff) << 8) | ((int(9) & 0xff))
# 28 "cpp2py.cpp"
## Test

void TEmuVt102::printScan(int cc)
{
  if (cc == (ord('Q')-ord('@')) || cc == (ord('S')-ord('@')) || cc == 0) return;

  pushToToken(cc);

  s = pbuf;
  p = ppos;

  if p == 1 and s[0] == ESC:
      return;
  if p == 2 and s[1] == '[':
      return;
  if p == 3 and s[2] == '4':
      return;
  if p == 3 and s[2] == '5':
      return;
  if p == 4 and s[3] == 'i':
      if s[2] == '4':
          setPrinterMode(false)
          resetToken()
          return

  for (int i = 0; i < p; i++) fwrite(s+i,1,1,print_fd);
  resetToken();
}




void TEmuVt102::onRcvChar(int cc)
{ int i;

  if (print_fd) { printScan(cc); return; }

  if (cc == 127) return;

  if cc < 256 and (self.__tbl[cc] & CTL) == CTL and not (len(self.__pbuf)-1) >= 2 and self.__pbuf[1] == ']' and cc == 7:





    if (cc == (ord('X')-ord('@')) || cc == (ord('Z')-ord('@')) || cc == ESC) resetToken();
    if (cc != ESC) { tau( TY_CTL___(cc+'@' ), 0, 0); return; }
  }

  pushToToken(cc) # Advance the state

  int* s = pbuf;
  int p = ppos;

  if (getMode(MODE_Ansi): # Decide on proper action
    if p == 1 and s[0] == ESC:
        return
    if p == 2 and s[1] < 256 and (self.__tbl[s[1]] & GRP) == GRP:
        return; }
    if (len(self.__pbuf)-1) >= 2 and self.__pbuf[1] == ']' and cc == 7:
        XtermHack()
        resetToken()
        return
    if (len(self.__pbuf)-1) >= 2 and self.__pbuf[1] == ']':
        return
    if p == 3 and s[2] == '?':
        return
    if p == 3 and s[2] == '>':
        return
    if p == 1 and cc >= 32 ):
        tau( TY_CHR___(), applyCharset(cc), 0)
        resetToken()
        return
    if p == 2 and s[0] == ESC:
        tau( TY_ESC___(s[1]), 0, 0)
        resetToken()
        return
    if p == 3 and s[1] < 256 and (self.__tbl[s[1]] & SCS) == SCS:
        tau( TY_ESC_CS(s[1],s[2]), 0, 0)
        resetToken()
        return
    if p == 3 and s[1] == '#':
        tau( TY_ESC_DE(s[2]), 0, 0)
        resetToken()
        return
    if p >= 3 and s[2] != '?' and s[2] != '>' and cc < 256 and (self.__tbl[cc] & CPN) == CPN:
        tau( TY_CSI_PN(cc), argv[0],argv[1])
        resetToken()
        return
    if p >= 3 and cc < 256 and (self.__tbl[cc] & DIG) == DIG:
        addDigit(cc-'0')
        return
    if p >= 3 and cc == ';':
        addArgument()
        return
    for (i=0;i<=argc;i++)
    if p >= 3 and s[2] == '?':
          tau( TY_CSI_PR(cc,argv[i]), 0, 0)
    elif p >= 3 and s[2] == '>':
        tau( TY_CSI_PG(cc), 0, 0) # spec. case for ESC]>0c or ESC]>c
    else:
        tau( TY_CSI_PS(cc,argv[i]), 0, 0)
    resetToken();
  else:
    if p == 1 and s[0] == ESC:
        return;
    if p == 1 and s[0] < 256 and (self.__tbl[s[0]] & CHR) == CHR:
        tau( TY_CHR___(), s[0], 0)
        resetToken()
        return
    if p == 2 and s[1] == 'Y':
        return
    if p == 3 and s[1] == 'Y':
        return
    if p < 4:
        tau( TY_VT52__(s[1]), 0, 0)
        resetToken()
        return
    tau( TY_VT52__(s[1]), s[2],s[3])
    resetToken()
    return
