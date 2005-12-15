#include "TESession.h"

#include <stdlib.h>
#include <qfile.h>
#include <qdir.h>

#define SILENCE_TIMEOUT 10000 // milliseconds

/*! \class TESession

    Sessions are combinations of TEPTy and Emulations.

    The stuff in here does not belong to the terminal emulation framework,
    but to main.cpp. It serves it's duty by providing a single reference
    to TEPTy/Emulation pairs. In fact, it is only there to demonstrate one
    of the abilities of the framework - multible sessions.
*/

TESession::TESession(TEWidget* _te, const QString &_pgm, QStrList & _args, const QString &_term,const QString &_sessionId, const QString &_cwd) : //DCOPObject( _sessionId.latin1() )
    monitorActivity(false)
   , monitorSilence(false)
   , masterMode(false)
   , schema_no(0)
   , font_no(3)
   , pgm(_pgm)
   , args(_args)
   , sessionId(_sessionId)
   , cwd(_cwd)
{
  sh = new TEPty();
  te = _te;
  em = new TEmuVt102(te);

  term = _term;
  iconName = "openterm";
  iconText = "qonsole";

  sh->setSize(te->Lines(),te->Columns()); // not absolutely nessesary
  connect( sh,SIGNAL(block_in(const char*,int)),em,SLOT(onRcvBlock(const char*,int)) );
  connect( em,SIGNAL(ImageSizeChanged(int,int)),sh,SLOT(setSize(int,int)));
  connect( em,SIGNAL(sndBlock(const char*,int)),sh,SLOT(send_bytes(const char*,int)) );

  connect( em, SIGNAL( changeTitle( int, const QString & ) ),
           this, SLOT( setUserTitle( int, const QString & ) ) );

  connect( em, SIGNAL( notifySessionState(int) ),
           this, SLOT( notifySessionState(int) ) );
  monitorTimer = new QTimer(this);
  connect(monitorTimer, SIGNAL(timeout()), this, SLOT(monitorTimerDone()));

  connect( sh,SIGNAL(done(int)), this,SLOT(done(int)) );
}



void TESession::run()
{
  QString appId = "qonsole";

  QString cwd_save = QDir::currentDirPath();
  if (!cwd.isEmpty())
    QDir::setCurrent(cwd);
  sh->run(QFile::encodeName(pgm),args,term.latin1(),true);
  if (!cwd.isEmpty())
    QDir::setCurrent(cwd_save);

  sh->setWriteable(false);  // We are reachable via kwrited.
}

void TESession::setUserTitle( int what, const QString &caption )
{
    // (btw: what=0 changes title and icon, what=1 only icon, what=2 only title
    if ((what == 0) || (what == 2))
      userTitle = caption;
    if ((what == 0) || (what == 1))
      iconText = caption;
    emit updateTitle();
}

QString TESession::fullTitle() const
{
    QString res = title;
    if ( !userTitle.isEmpty() )
        res = userTitle + " - " + res;
    return res;
}

void TESession::monitorTimerDone()
{
  emit notifySessionState(this,NOTIFYSILENCE);
  monitorTimer->start(SILENCE_TIMEOUT,true);
}

void TESession::notifySessionState(int state)
{
  if (state==NOTIFYACTIVITY) {
    if (monitorSilence) {
      monitorTimer->stop();
      monitorTimer->start(SILENCE_TIMEOUT,true);
    }
    if (!monitorActivity)
      return;
  }

  emit notifySessionState(this, state);
}

bool TESession::sendSignal(int signal)
{
  return sh->kill(signal);
}

TESession::~TESession()
{
 QObject::disconnect( sh, SIGNAL( done( int ) ),
		      this, SLOT( done( int ) ) );
  delete em;
  delete sh;
}

void TESession::setConnect(bool c)
{
  em->setConnect(c);
  setListenToKeyPress(c);
}

void TESession::setListenToKeyPress(bool l)
{
  em->setListenToKeyPress(l);
}

void TESession::done(int status)
{
  emit done(this,status);
}

void TESession::terminate()
{
  delete this;
}

TEmulation* TESession::getEmulation()
{
  return em;
}

// following interfaces might be misplaced ///
int TESession::schemaNo()
{
  return schema_no;
}

int TESession::keymapNo()
{
  return em->keymapNo();
}

QString TESession::keymap()
{
  return em->keymap();
}

int TESession::fontNo()
{
  return font_no;
}

const QString & TESession::Term()
{
  return term;
}

const QString & TESession::SessionId()
{
  return sessionId;
}

void TESession::setSchemaNo(int sn)
{
  schema_no = sn;
}

void TESession::setKeymapNo(int kn)
{
  em->setKeymap(kn);
}

void TESession::setKeymap(const QString &id)
{
  em->setKeymap(id);
}

void TESession::setFontNo(int fn)
{
  font_no = fn;
}

void TESession::setTitle(const QString& _title)
{
  title = _title;
}

const QString& TESession::Title()
{
  return title;
}

void TESession::setIconName(const QString& _iconName)
{
  iconName = _iconName;
}

void TESession::setIconText(const QString& _iconText)
{
  iconText = _iconText;
}

const QString& TESession::IconName()
{
  return iconName;
}

const QString& TESession::IconText()
{
  return iconText;
}

bool TESession::testAndSetStateIconName (const QString& newname)
{
  if (newname != stateIconName)
    {
      stateIconName = newname;
      return true;
    }
  return false;
}

void TESession::setHistory(const HistoryType &hType)
{
  em->setHistory(hType);
}

const HistoryType& TESession::history()
{
  return em->history();
}

QStrList TESession::getArgs()
{
  return args;
}

QString TESession::getPgm()
{
  return pgm;
}

bool TESession::isMonitorActivity() { return monitorActivity; }
bool TESession::isMonitorSilence() { return monitorSilence; }
bool TESession::isMasterMode() { return masterMode; }

void TESession::setMonitorActivity(bool _monitor) { monitorActivity=_monitor; }
void TESession::setMonitorSilence(bool _monitor)
{
  if (monitorSilence==_monitor)
    return;

  monitorSilence=_monitor;
  if (monitorSilence)
    monitorTimer->start(SILENCE_TIMEOUT,true);
  else
    monitorTimer->stop();
}

void TESession::setMasterMode(bool _master)
{
  masterMode=_master;
}

#include "TESession.moc"
