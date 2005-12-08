_helpers.so: helpers.o
	gcc --shared -o_helpers.so helpers.o

helpers.o: helpers.c
	gcc -O2 -c -o helpers.o -I. -I/usr/include/python2.4 -I/usr/include/qt3 helpers.c

clean:
	rm -f *.o *.so *~
