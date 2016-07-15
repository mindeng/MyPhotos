#! /usr/bin/env python

import os
from exif import ExifInfo, PropertyDict
from exif import calc_file_md5
from hashlib import md5
import json
#import mmap
from utils import *

_IMAGE_EXTS = set([
    # Image files
    '.jpg',
    '.png',
    '.tif',
    '.tiff',

    # sony raw file
    '.arw',
    # nikon raw file
    '.nef',
    ])  

_VIDEO_EXTS = set([
    # Video files
    '.avi',
    '.mp4',
    '.mov',
    '.m4v'
    ])  

class MediaFile(PropertyDict):
    MEDIA_UNKNOWN = 0
    MEDIA_IMAGE = 'image'
    MEDIA_VIDEO = 'video'

    MIN_FILE_SIZE = 10 * 1024
    MD5_CONTENT_LEN = 10 * 1024

    def _stringtify(self, copy):
        if getattr(self, 'create_time', None):
            copy['create_time'] = str(self.create_time)

    def __init__(self, *parameters, **kwparameters):
        path = kwparameters.get("path")
        relative_path = kwparameters.get("relative_path")
        if path:
            # init from path
            super(MediaFile, self).__init__()
            self.relative_path = relative_path
            self.load_from_path(path)
        else:
            # init from db row or empty dict
            super(MediaFile, self).__init__(*parameters, **kwparameters)
            self._exif_info = ExifInfo.from_dict(self)

    # Load exif info, base file info & md5
    def load_from_path(self, path):
        self.load_exif_info(path)
        self.load_file_info(path)

        # init user info
        self.tags = ''
        self.description = ''

    # Load base file info & md5
    def load_file_info(self, path):
        self.load_base_file_info(path)
        self.load_md5(path)

    # Only load base file info
    def load_base_file_info(self, path):
        if not os.path.isfile(path):
            raise IllegalMediaFile("File not found: %s" % path)

        self.path = path
        self.filename = os.path.basename(path)
        self.file_size = os.path.getsize(path)
        self.file_extension = os.path.splitext(self.filename)[1].lower()

        #if self.file_size < MediaFile.MIN_FILE_SIZE:
        #    raise IllegalMediaFile(
        #        "File size is too small: " + self.file_size)

        if self.file_extension in _IMAGE_EXTS:
            self.media_type = MediaFile.MEDIA_IMAGE
        elif self.file_extension in _VIDEO_EXTS:
            self.media_type = MediaFile.MEDIA_VIDEO
        else:
            self.media_type = MediaFile.MEDIA_UNKNOWN

    # Only load exif info
    def load_exif_info(self, path):
        self._exif_info = ExifInfo(path)

    # Only load md5
    def load_md5(self, path):
        # NOTE: c extension module can only handle encoded path
        path = encode_text(path)

        offset = (self.file_size - MediaFile.MD5_CONTENT_LEN) / 2
        length = MediaFile.MD5_CONTENT_LEN
        digest = calc_file_md5(path, offset, length)
        self.middle_md5 = ''.join('{:02x}'.format(ord(x)) for x in digest)

        #content = quick_read(self.path.encode('utf-8'), offset, length)
        #self.middle_md5 = md5(content).hexdigest()
        
        # with open(self.path, "r+b") as f:
        #     # memory-map the file, size 0 means whole file
        #     mm = mmap.mmap(f.fileno(), 0)
        #     mm.seek(offset)
        #     content = mm.read(length)
        #     self.middle_md5 = md5(content).hexdigest()
        #     mm.close()


class IllegalMediaFile(Exception):

    def __init__(self, s=None):
        super(IllegalMediaFile, self).__init__(s)

if __name__ == '__main__':
    path = '/Users/min/Pictures/DSC_0001.JPG'
    print MediaFile(path, None)

    import timeit
    def testit():
        MediaFile(path, None)
    print timeit.timeit('testit()',
                  'from __main__ import testit',
                  number=100)

    # 100 times: 1 second
    # quick_read: 10000 times: 1.6 seconds
