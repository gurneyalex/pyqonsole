QTINC=/usr/include/qt3
QTLIB=/usr/lib
MOC=/usr/bin/moc

CXXFLAGS=-Wall -O2 -I$(QTINC) -I.

all: kdelibs.a

kdelibs.a: $(LINKS) kprocess.o kprocctrl.o # kurl.o kurldrag.o ktempfile.o
	ar r kdelibs.a $^

%.moc: %.h
	$(MOC) $^ > $@

clean:
	rm -f *.o *.moc *.a

kprocess.o: kprocess.moc
kprocctrl.o: kprocctrl.moc
