#! /usr/bin/env python

import sys
import os
sys.path.append(
        os.path.abspath(
            os.path.join(os.path.dirname(
                os.path.realpath(__file__) ), '..') ))

import myexif
import timeit
import mmap

path = "/Users/min/Pictures/DSC_0001.JPG"
#path = "/Users/min/Downloads/203518Spc.jpg"
def testit():
    return myexif.get_exif_info(path)

print testit()

#print timeit.timeit('testit()', 'from __main__ import testit', number=10000)
# 100 0.96 seconds
# 100 0.46 seconds
# 10000 0.36 seconds

def read_file(path, offset, length):
    with open(path, "r+b") as f:
        # memory-map the file, size 0 means whole file
        mm = mmap.mmap(f.fileno(), 0)
        mm.seek(offset)
        content = mm.read(length)
        return content

path = "test-myexif.py"
print myexif.quick_read(path, 20, 100) == read_file(path, 20, 100)
