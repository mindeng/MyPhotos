from pyexiv2 import linkso
linkso.link_so()

from exif import ExifInfo, PropertyDict
from exif import get_file_time
from myexif import calc_middle_md5
from myexif import cp_file, compare_file

import sys
import os
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(
            os.path.realpath(__file__) ), '..') ))
import utils

def equal_file(path1, path2):
    # c extension module can only handle encoded path
    path1 = utils.encode_text(path1)
    path2 = utils.encode_text(path2)
    ret = compare_file(path1, path2)
    return ret == 0

def copy_file(src, dst):
    # c extension module can only handle encoded path
    src = utils.encode_text(src)
    dst = utils.encode_text(dst)
    ret, errmsg = cp_file(src, dst)
    return ret == 0, errmsg

def hex_middle_md5(path, full=False):
    # c extension module can only handle encoded path
    path = utils.encode_text(path)
    digest = calc_middle_md5(path, 1 if full else 0)
    return ''.join('{:02x}'.format(ord(x)) for x in digest)
