CXX=g++
CXXFLAGS=-O2 -pedantic -Wall -Wextra -ansi -std=c++11

all: myexif

exif.o: exif.cpp
	$(CXX) $(CXXFLAGS) -c exif.cpp

myexif: exif.o myexif.cpp
	$(CXX) $(CXXFLAGS) -o myexif exif.o myexif.cpp

clean:
	rm -f *.o myexif myexif.exe
