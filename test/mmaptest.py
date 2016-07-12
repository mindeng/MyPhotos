#! /usr/bin/env python

import mmap
import struct
import os

def print_hex(data):
    print ' '.join('{0:02x}'.format(ord(c)) for c in data)

with open("/Users/min/Pictures/DSC_0001.JPG", "rb") as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

    print_hex(mm.read(16))
    
    mm.seek(-2, os.SEEK_END)
    print_hex(mm.read(2))

    mm.seek(0)

    tag = struct.pack('!BB', 0xFF, 0xDB)
    while True:
        head = mm.read(16)
        
        if len(head) == 0:
            break
            
        if tag in head:
            print_hex(head[head.index(tag):])
