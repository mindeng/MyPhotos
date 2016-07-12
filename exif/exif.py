#! /usr/bin/env python

import subprocess
import json
import datetime
import os
from myexif import get_exif_info

Tag_DateTimeOriginal = 'DateTimeOriginal'
Tag_DateTimeDigitized = 'DateTimeDigitized'
Tag_DateTime = 'DateTime'
Tag_CreateDate = 'CreateDate'
Tag_ModifyDate = 'ModifyDate'
Tag_FileModifyDate = 'FileModifyDate'

Tag_Make = 'Make'
Tag_Model = 'Model'
Tag_ImageWidth = 'ImageWidth'
Tag_ImageHeight = 'ImageHeight'
Tag_ExposureTime = 'ExposureTime'
Tag_FNumber = 'FNumber'
Tag_ISO = 'ISO'
Tag_FocalLengthIn35mm = 'FocalLengthIn35mmFormat'
Tag_GPSLatitude = 'GPSLatitude'
Tag_GPSLongitude = 'GPSLongitude'
Tag_GPSAltitude = 'GPSAltitude'

def get_exif_time(exif_info):
    TIME_TAGS = [
        Tag_DateTimeOriginal,
        Tag_DateTimeDigitized,
        Tag_DateTime,
        Tag_CreateDate,
        Tag_ModifyDate,
        Tag_FileModifyDate,
    ]
    for tag in TIME_TAGS:
        v = exif_info.get(tag)
        if v:
            return v
    return None


def gps_decimal_degree(degrees, minutes, seconds):
    return degrees + minutes / 60.0 + seconds / 3600.0

import re
_GPS_PAT = re.compile(r'[^\d]*(\d+)[^\d]+(\d+)[^\d]+([\d.]+)[^\d]+')
def gps_text_to_degree(text):
    # 39 deg 59' 47.37" N
    # ->
    # 39.996492
    found = re.match(_GPS_PAT, text)
    if found:
        degree = int(found.group(1))
        minutes = int(found.group(2))
        seconds = float(found.group(3))
        return gps_decimal_degree(degree, minutes, seconds)
        
    return 0

def gps_text_to_metre(text):
    try:
        pos = text.index('m')
        s = text[:pos].strip()
        return float(s)
    except ValueError:
        return 0

    
class ExifInfo(object):
    EXIF_TIME_FORMAT = '%Y:%m:%d %H:%M:%S'

    def __init__(self, path):
        self.load(path)

    def load(self, path):
        exif_info = None
        exif = None
        
        if path.lower().endswith('.jpg'):
            exif_info = get_exif_info(path.encode('utf-8'))
            exif = exif_info and json.loads(exif_info)
            
        exif = exif or get_exif_by_exiftool(path)
        
        self.make = exif.get(Tag_Make)
        self.model = exif.get(Tag_Model)
        self.image_width = exif.get(Tag_ImageWidth)
        self.image_height = exif.get(Tag_ImageHeight)
        self.create_time = get_exif_time(exif)
        self.exposure_time = exif.get(Tag_ExposureTime)
        self.f_number = exif.get(Tag_FNumber)
        self.iso = exif.get(Tag_ISO)
        self.focal_length_in_35mm = exif.get(Tag_FocalLengthIn35mm)
        self.gps_latitude = exif.get(Tag_GPSAltitude)
        self.gps_longitude = exif.get(Tag_GPSLongitude)
        self.gps_altitude = exif.get(Tag_GPSAltitude)
        
        if self.gps_latitude and isinstance(self.gps_latitude, basestring):
            self.gps_latitude = gps_text_to_degree(self.gps_latitude)
            self.gps_longitude = gps_text_to_degree(self.gps_longitude)
            self.gps_altitude = gps_text_to_metre(self.gps_altitude)
        
        if self.create_time:
            self.create_time = datetime.datetime.strptime(
                self.create_time[:19], ExifInfo.EXIF_TIME_FORMAT)
        else:
            self.create_time = get_file_time(path)

    def __str__(self):
        return 'ExifInfo[%s, %s, %s, %s, %s, %s]' % \
            (self.make, self.model, self.create_time,
             self.gps_latitude, self.gps_longitude, self.gps_altitude)

class ExifException(Exception):

    def __init__(self, msg):
        super(ExifException, self).__init__(msg)
        
def command_line(cmd):
    try:
        s = subprocess.check_output(cmd)
        return s.strip()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            # handle file not found error.
            raise ExifException("Load exif info: exiftool not found!")
        else:
            pass
        return None
    except subprocess.CalledProcessError:
        return None
    return None

def get_exif_by_exiftool(filename):
    ret = None
    filename = os.path.abspath(filename)
    #s = command_line(['exiftool', '-G', '-j', '-sort', filename])
    s = command_line(['exiftool', '-j', filename])
    if s:
        #convert bytes to string
        s = s.decode('utf-8').strip()
        jsonobj = json.loads(s)
        if jsonobj and len(jsonobj) >= 1:
            ret = jsonobj[0]

    return ret
            
def get_file_time(path):
    return datetime.datetime.fromtimestamp(os.path.getctime(path))

if __name__ == '__main__':
    import sys

    path = sys.argv[1]
    print ExifInfo(path)

    import timeit
    def testit():
        ExifInfo(path)
    print timeit.timeit('testit()',
                  'from __main__ import testit',
                  number=10)

    # exiftool: 10 times 1.38 seconds
    # myexif: 10000 times 0.97 seconds
