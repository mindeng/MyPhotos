
#! /usr/bin/env python

import sys
import os
sys.path.append(
        os.path.abspath(
            os.path.join(os.path.dirname(
                os.path.realpath(__file__) ), '..') ))
import myexif
import timeit

src = "/Users/min/Pictures/DSC_0001.JPG"
dst = "/tmp/t/1.jpg"
def testit():
    try:
        os.unlink(dst)
    except OSError:
        pass
    return myexif.cp_file(src, dst)

print testit()

#print timeit.timeit('testit()', 'from __main__ import testit', number=1000)
