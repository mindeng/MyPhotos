#! /usr/bin/env python

import os
from exif import ExifInfo, quick_read
from hashlib import md5
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

class MediaFile(object):
    MEDIA_UNKNOWN = 0
    MEDIA_IMAGE = 'image'
    MEDIA_VIDEO = 'video'

    MIN_FILE_SIZE = 10 * 1024
    MD5_CONTENT_LEN = 10 * 1024

    @property
    def create_time(self):
        return self.exif_info.create_time

    @property
    def exif_make(self):
        return self.exif_info.make

    @property
    def exif_model(self):
        return self.exif_info.model

    @property
    def gps_latitude(self):
        return self.exif_info.gps_latitude

    @property
    def gps_longitude(self):
        return self.exif_info.gps_longitude

    @property
    def gps_altitude(self):
        return self.exif_info.gps_altitude

    @property
    def image_width(self):
        return self.exif_info.image_width

    @property
    def image_height(self):
        return self.exif_info.image_height

    @property
    def f_number(self):
        return self.exif_info.f_number

    @property
    def exposure_time(self):
        return self.exif_info.exposure_time

    @property
    def iso(self):
        return self.exif_info.iso

    @property
    def focal_length_in_35mm(self):
        return self.exif_info.focal_length_in_35mm

    def __init__(self, path=None, relative_path=None, row=None):
        if path:
            self._init_with_path(path, relative_path)
        elif row:
            self._init_with_row(row)

    def _init_with_row(self, row):
        self._row = row

    def _init_with_path(self, path, relative_path):
        path = decode_text(path)
        relative_path = decode_text(relative_path)
        
        if not os.path.isfile(path):
            raise IllegalMediaFile("File not found: %s" % path)

        self.path = path
        self.filename = os.path.basename(path)
        self.relative_path = relative_path
        self.file_size = os.path.getsize(path)

        if self.file_size < MediaFile.MIN_FILE_SIZE:
            raise IllegalMediaFile(
                "File size is too small: " + self.file_size)
        
        self.file_extension = os.path.splitext(self.filename)[1].lower()

        self.load_media_type()
        self.load_exif_info()
        self.load_md5()

        self.tags = ''
        self.description = ''

    @classmethod
    def is_media_file(cls, path):
        extension = os.path.splitext(path)[1].lower()
        return extension in _IMAGE_EXTS or \
            extension in _VIDEO_EXTS

    def load_media_type(self):
        if self.file_extension in _IMAGE_EXTS:
            self.media_type = MediaFile.MEDIA_IMAGE
        elif self.file_extension in _VIDEO_EXTS:
            self.media_type = MediaFile.MEDIA_VIDEO
        else:
            self.media_type = MediaFile.MEDIA_UNKNOWN

    def load_exif_info(self):
        self.exif_info = ExifInfo(self.path)

    def load_md5(self):
        offset = (self.file_size - MediaFile.MD5_CONTENT_LEN) / 2
        length = MediaFile.MD5_CONTENT_LEN

        content = quick_read(self.path.encode('utf-8'), offset, length)
        self.middle_md5 = md5(content).hexdigest()
        
        # with open(self.path, "r+b") as f:
        #     # memory-map the file, size 0 means whole file
        #     mm = mmap.mmap(f.fileno(), 0)
        #     mm.seek(offset)
        #     content = mm.read(length)
        #     self.middle_md5 = md5(content).hexdigest()
        #     mm.close()

    def __str__(self):
        return 'MediaFile[%s, %s, %s]' % (
            self.relative_path, self.middle_md5, self.exif_info)



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