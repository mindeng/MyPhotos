#! /usr/bin/env python

import os
from exif import ExifInfo, PropertyDict
from exif import hex_middle_md5
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

_RAW_EXTS = set([
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

    def __getattr__(self, name):
        # check if the name is in the exif info first
        try:
            _exif_info = super(MediaFile, self).__getattribute__('_exif_info')
            return _exif_info[name]
        except KeyError:
            return super(MediaFile, self).__getattr__(name)

    def __setattr__(self, name, value):
        # check if the name is in the exif info first
        if not name.startswith("_") and name in self._exif_info:
            self._exif_info[name] = value
        else:
            super(MediaFile, self).__setattr__(name, value)

    def _stringtify(self, copy):
        copy['exif'] = self._exif_info
        copy['exif'].create_time = str(copy['exif'].create_time) if copy['exif'].create_time else None

    def __init__(self, *parameters, **kwparameters):
        path = kwparameters.get("path")
        relative_path = kwparameters.get("relative_path")
        if path:
            # init from path
            super(MediaFile, self).__init__()
            self._exif_info = ExifInfo()
            self.relative_path = relative_path
            self.id = None
            self.load_from_path(path)
        else:
            # init from db row or empty dict
            super(MediaFile, self).__init__(*parameters, **kwparameters)

            # Copy all exif info to self._exif_info, and delete all exif info
            # fields from self, so we can make sure all exif info is
            # getted/setted from self._exif_info
            if len(parameters) > 0 and getattr(parameters[0], '_exif_info', None) != None:
                self._exif_info = ExifInfo.from_dict(parameters[0]._exif_info)
            else:
                self._exif_info = ExifInfo.from_dict(self)
                [self.pop(k) for k in self.keys() if k in self._exif_info]

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

        self.path           = path
        self.filename       = os.path.basename(path)
        self.file_size      = os.path.getsize(path)
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

    @staticmethod
    def is_video(filename):
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        return ext in _VIDEO_EXTS
    @staticmethod
    def is_image(filename):
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        return ext in _IMAGE_EXTS
    @staticmethod
    def is_raw(filename):
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        return ext in _RAW_EXTS

    # Only load exif info
    def load_exif_info(self, path):
        self._exif_info = ExifInfo(path)

    # Only load md5
    def load_md5(self, path):
        #offset = (self.file_size - MediaFile.MD5_CONTENT_LEN) / 2
        #length = MediaFile.MD5_CONTENT_LEN

        self.middle_md5 = hex_middle_md5(path)

        #content = quick_read(self.path.encode('utf-8'), offset, length)
        #self.middle_md5 = md5(content).hexdigest()
        
        # with open(self.path, "r+b") as f:
        #     # memory-map the file, size 0 means whole file
        #     mm = mmap.mmap(f.fileno(), 0)
        #     mm.seek(offset)
        #     content = mm.read(length)
        #     self.middle_md5 = md5(content).hexdigest()
        #     mm.close()

    def __eq__(self, o):
        return o and \
                self.path           == o.path           and \
                self.filename       == o.filename       and \
                self.file_size      == o.file_size      and \
                self.file_extension == o.file_extension and \
                self.middle_md5     == o.middle_md5     and \
                self._exif_info     == o._exif_info

    def __ne__(self, o):
        return not self.__eq__(o)

class IllegalMediaFile(Exception):

    def __init__(self, s=None):
        super(IllegalMediaFile, self).__init__(s)

if __name__ == '__main__':
    path = '/Users/min/Pictures/DSC_0001.JPG'
    print MediaFile(path=path, relative_path=None)

    import timeit
    def testit():
        MediaFile(path=path, relative_path=None)
    print timeit.timeit('testit()',
                  'from __main__ import testit',
                  number=100)

    # 100 times: 1 second
    # quick_read: 10000 times: 1.6 seconds
