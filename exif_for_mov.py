#!/usr/bin/python

import datetime
import struct
import sys

ATOM_HEADER_SIZE = 8
# difference between Unix epoch and QuickTime epoch, in seconds
EPOCH_ADJUSTER = 2082844800

if len(sys.argv) < 2:
    print "USAGE: mov-length.py <file.mov>"
    sys.exit(1)

# open file and search for moov item
f = open(sys.argv[1], "rb")
while 1:
    atom_header = f.read(ATOM_HEADER_SIZE)
    if atom_header[4:8] == 'moov':
        break
    else:
        atom_size = struct.unpack(">I", atom_header[0:4])[0]
        f.seek(atom_size - 8, 1)

# found 'moov', look for 'mvhd' and timestamps
atom_header = f.read(ATOM_HEADER_SIZE)
if atom_header[4:8] == 'cmov':
    print "moov atom is compressed"
elif atom_header[4:8] != 'mvhd':
    print "expected to find 'mvhd' header"
else:
    f.seek(4, 1)
    creation_date = struct.unpack(">I", f.read(4))[0]
    modification_date = struct.unpack(">I", f.read(4))[0]
    print "creation date:",
    print datetime.datetime.utcfromtimestamp(creation_date - EPOCH_ADJUSTER)
    print "modification date:",
    print datetime.datetime.utcfromtimestamp(modification_date - EPOCH_ADJUSTER)
