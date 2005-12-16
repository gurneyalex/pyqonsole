/* main.cpp */

#include "TEWidget.h"
#include "TESession.h"
#include "keytrans.h"

#include <qapplication.h>
#include <qfont.h>

const char *fonts[] = {
               "13",
               "7",   // tiny font, never used
               "10",  // small font
               "13",  // medium
               "15",  // large
               "20",  // huge
               "-misc-console-medium-r-normal--16-160-72-72-c-160-iso10646-1", // "Linux"
               "-misc-fixed-medium-r-normal--15-140-75-75-c-90-iso10646-1",    // "Unicode"
           };

#define TOPFONT (sizeof(fonts)/sizeof(char*))
#define DEFAULTFONT TOPFONT

void setFont(TEWidget* te, int fontno)
{
  QFont f;
  if (fonts[fontno][0] == '-') {
    f.setRawName( fonts[fontno] );
    if ( !f.exactMatch() && fontno != DEFAULTFONT) {
      return;
    }
  }
  else
  {
    f.setFamily("fixed");
    f.setFixedPitch(true);
    f.setPixelSize(QString(fonts[fontno]).toInt());
  }
  te->setVTFont(f);
}

int main(int argc, char* argv[])
{
  QApplication app(argc,argv);

  KeyTrans::loadAll();
  TEWidget* te = new TEWidget;
  te->setMinimumSize(150, 70);
  te->setFocus();
  te->resize(te->calcSize(80,25));
  te->setBackgroundMode(Qt::PaletteBackground);
//w->setSize(80,25);
  setFont(te, 4); // 15
  app.setMainWidget(te);
  te->show();

  QStrList args;
  args.append("/bin/bash");
  TESession session(te, "/bin/bash", args, "xterm");
  session.setConnect(true);
  session.setHistory(HistoryTypeBuffer(1000));
  session.run();

  return app.exec();
}
