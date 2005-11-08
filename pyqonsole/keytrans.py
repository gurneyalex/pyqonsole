"""  Provide KeyTrans class.
"""

BITS_NewLine   = 0
BITS_BsHack    = 1
BITS_Ansi      = 2
BITS_AppCuKeys = 3
BITS_Control   = 4
BITS_Shift     = 5
BITS_Alt       = 6
BITS_COUNT     = 7

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


class KeyTrans:
    pass