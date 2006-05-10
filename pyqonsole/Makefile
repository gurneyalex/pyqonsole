PYTHON=python2.3
CFLAGS=-O2 -I/usr/include/$(PYTHON)

all: _helpers.so Makefile

_helpers.so: helpers.o
	$(CC) $(CFLAGS) --shared -o $@ $<

install: _helpers.so setup.py __pkginfo__.py
	$(PYTHON) setup.py install

clean:
	rm -f *.o *.so *~
