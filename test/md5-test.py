#! /usr/bin/env python

import timeit
from hashlib import md5

import sys
import os
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(
            os.path.realpath(__file__) ), '..') ))
import exif
from exif.myexif import calc_middle_md5


def test_calc_middle_md5():
    #calc_middle_md5('/Volumes/sg2/01Photos/2016/201604/Raw/DSC_0161.NEF')
    calc_middle_md5(sys.argv[1])
print 'test_calc_middle_md5', timeit.timeit('test_calc_middle_md5()', 'from __main__ import test_calc_middle_md5', number=1000)

default_recursion_limit = sys.getrecursionlimit()
sys.setrecursionlimit(10001)

def recursive_md5(s, count, n):
    ret = md5(s).digest()
    
    count += 1
    if count >= n:
        return ret
    else:
        return recursive_md5(ret, count, n)

exit(0)

import binascii
import uuid
#s = ''.join((uuid.uuid4().bytes*2 for i in xrange(1024)))
s = ''.join((uuid.uuid4().bytes for i in xrange(640)))
print len(s)

def testit():
    md5(s).hexdigest()

print timeit.timeit('testit()', 'from __main__ import testit', number=10000)

# 10240 & 10000: 0.2 seconds

# ret = recursive_md5(s, 0, 10000)
# print binascii.hexlify(ret)

# sys.setrecursionlimit(default_recursion_limit)
