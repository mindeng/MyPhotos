
# dynamic link with libexiv2
#myexiv2: myexiv2.cpp Jzon.cpp
#	g++ -o myexiv2 myexiv2.cpp Jzon.cpp -I../include ../src/.libs/libexiv2.dylib -liconv -lz -lexpat #-g
#	install_name_tool -change /usr/local/lib/libexiv2.14.dylib @executable_path/libexiv2.14.dylib myexiv2

# static link with libexiv2
myexiv2: myexiv2.cpp Jzon.cpp
	g++ -o myexiv2 myexiv2.cpp Jzon.cpp -I${EXIV2_PATH}/include libexiv2.a -liconv -lz -lexpat #-g

clean:
	rm -f myexiv2 myexiv2.exe
