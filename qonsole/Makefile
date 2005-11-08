QTINC=/usr/include/qt3
QTLIB=/usr/lib
MOC=/usr/bin/moc

CXXFLAGS=-Wall -O2 -I$(QTINC) -g -I. -DHAVE_CONFIG_H

all: kdelibs.a qonsole.a qonsole

qonsole: main.o qonsole.a kdelibs.a
	gcc -o qonsole $^ -lqt-mt

qonsole.a: $(LINKS) BlockArray.o TEScreen.o TEHistory.o TEmuVt102.o TEmulation.o keytrans.o TEPty.o TEWidget.o TESession.o qonsole_wcwidth.o
	ar r qonsole.a *.o

kdelibs.a: $(LINKS) kprocess.o kprocctrl.o
	ar r kdelibs.a $^

%.moc: %.h
	$(MOC) $^ > $@

clean:
	rm -f *.o *.moc *.a qonsole

TEPty.o: TEPty.moc
TEmuVt102.o: TEmuVt102.moc
TEWidget.o: TEWidget.moc
TEmulation.o: TEmulation.moc
TESession.o: TESession.moc

kprocess.o: kprocess.moc
kprocctrl.o: kprocctrl.moc
