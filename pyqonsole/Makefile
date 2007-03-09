PYTHON=python2.4
CFLAGS=-O2 -I/usr/include/$(PYTHON)

all: _helpers.so Makefile

helpers.o: helpers.c
	$(CC) $(CFLAGS) -fPIC -c -o $@ $<

_helpers.so: helpers.o
	$(CC) $(CFLAGS) --shared -o $@ $<

install: _helpers.so setup.py __pkginfo__.py
	$(PYTHON) setup.py install

clean:
	rm -f *.o *.so *~
