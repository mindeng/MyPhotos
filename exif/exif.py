#! /usr/bin/env python

import subprocess
import json
import datetime
import os
from myexif import get_exif_info
import logging
import re

from utils import *

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
Tag_ISO = 'ISOSpeedRatings'
Tag_FocalLengthIn35mm = 'FocalLengthIn35mmFilm'
Tag_GPSLatitude = 'GPSLatitude'
Tag_GPSLongitude = 'GPSLongitude'
Tag_GPSAltitude = 'GPSAltitude'
Tag_MediaDuration = 'MediaDuration'

def get_exif_time(exif_info):
    TIME_TAGS = [
        Tag_DateTimeOriginal,
        Tag_DateTimeDigitized,
        Tag_DateTime,
        Tag_CreateDate,
        Tag_ModifyDate,
        #Tag_FileModifyDate,
    ]

    for tag in TIME_TAGS:
        try:
            v = exif_info.get(tag)[:19]
            v = re.sub(r'[-T:]', ' ', v)
            return datetime.datetime.strptime(
                v, ExifInfo.TIME_FORMAT)
        except (ValueError, TypeError) as e:
            pass
            
    return None


def gps_decimal_degree(degrees, minutes, seconds):
    return degrees + minutes / 60.0 + seconds / 3600.0

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

class PropertyDict(dict):

    def __init__(self, *parameters, **kwparameters):
        super(PropertyDict, self).__init__(*parameters, **kwparameters)

    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        if name.startswith('_'):
            return super(PropertyDict, self).__getattribute__(name)

        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(PropertyDict, self).__setattr__(name, value)
        else:
            self[name] = value

    def _stringtified_copy(self):
        copy = dict(self)
        self._stringtify(copy)
        return copy

    def _stringtify(self, copy):
        """Subclass should overwrite this method to stringtify fields if there are some
        fields can't be dumped by json.
        """
        pass

    def __str__(self):
        return json.dumps(
                self._stringtified_copy(),
                sort_keys=True,
                indent=4, separators=(',', ': '),
                ensure_ascii=False).encode('utf-8')
    
class ExifInfo(PropertyDict):
    TIME_FORMAT = '%Y %m %d %H %M %S'

    def _stringtify(self, copy):
        copy['create_time'] = str(self.create_time)

    @staticmethod
    def from_path(path):
        return ExifInfo(path)

    @staticmethod
    def from_dict(d):
        ret = ExifInfo()
        for k, v in ret.iteritems():
            ret[k] = d.get(k)
        return ret

    def __init__(self, path=None):
        super(ExifInfo, self).__init__()
        self.load(path)

    def load(self, path):
        exif_info = None
        exif = {}
        
        #lower_path = path.lower()
        # if lower_path.endswith('.jpg'):
        #     exif_info = get_exif_info(encode_text(path))
        #     exif = exif_info and json.loads(exif_info)
        # elif lower_path.endswith('.png'):
        #     # Ignore png files
        #     pass
        # else:
        #     exif = exif or get_exif_by_exiftool(path)

        if path:
            exif_info = get_exif_info(encode_text(path))
            exif = exif_info and json.loads(exif_info)

        self.exif_make              = exif.get(Tag_Make)
        self.exif_model             = exif.get(Tag_Model)
        self.image_width            = exif.get(Tag_ImageWidth)
        self.image_height           = exif.get(Tag_ImageHeight)
        self.create_time            = get_exif_time(exif)
        self.exposure_time          = exif.get(Tag_ExposureTime)
        self.f_number               = exif.get(Tag_FNumber)
        self.iso                    = exif.get(Tag_ISO)
        self.focal_length_in_35mm   = exif.get(Tag_FocalLengthIn35mm)
        self.gps_latitude           = exif.get(Tag_GPSLatitude)
        self.gps_longitude          = exif.get(Tag_GPSLongitude)
        self.gps_altitude           = exif.get(Tag_GPSAltitude)
        self.duration               = exif.get(Tag_MediaDuration)
        
        if self.gps_latitude and isinstance(self.gps_latitude, basestring):
            self.gps_latitude = gps_text_to_degree(self.gps_latitude)
            self.gps_longitude = gps_text_to_degree(self.gps_longitude)
            self.gps_altitude = gps_text_to_metre(self.gps_altitude)

        if not self.create_time:
            self.create_time = parse_time_by_filename(path)
            # logging.error("Load create_time error: %s" % path)
            # # file time has no meaning
            # self.create_time = get_file_time(path)

    #def __str__(self):
    #    return 'ExifInfo[%s, %s, %s, GPS:[%s %s %s], FNumber:%s, ExposureTime:%s, ISO:%s, Focal:%s, duration:%s]' % \
    #        (self.exif_make, self.exif_model, self.create_time,
    #         self.gps_latitude, self.gps_longitude, self.gps_altitude,
    #         self.f_number, self.exposure_time, self.iso, self.focal_length_in_35mm,
    #         self.duration)

    def _p(self, v):
        log('exif_info.%s is not equal' % v)
        return False

    def __eq__(self, o):
        return o and \
                ( self.exif_make             == o.exif_make            or self._p("exif_make           ") ) and \
                ( self.exif_model            == o.exif_model           or self._p("exif_model          ") ) and \
                ( self.image_width           == o.image_width          or self._p("image_width         ") ) and \
                ( self.image_height          == o.image_height         or self._p("image_height        ") ) and \
                ( self.create_time           == o.create_time          or self._p("create_time         ") ) and \
                ( self.exposure_time         == o.exposure_time        or self._p("exposure_time       ") ) and \
                ( self.f_number              == o.f_number             or self._p("f_number            ") ) and \
                ( self.iso                   == o.iso                  or self._p("iso                 ") ) and \
                ( self.focal_length_in_35mm  == o.focal_length_in_35mm or self._p("focal_length_in_35mm") ) and \
                ( self.gps_latitude          == o.gps_latitude         or self._p("gps_latitude        ") ) and \
                ( self.gps_longitude         == o.gps_longitude        or self._p("gps_longitude       ") ) and \
                ( self.gps_altitude          == o.gps_altitude         or self._p("gps_altitude        ") ) and \
                ( self.duration              == o.duration             or self._p("duration            ") )

    def __ne__(self, o):
        return not self.__eq__(o)

def parse_time_by_filename(path):
    # try to parse file name as time, e.g.:
    # 20120607_061356
    # 2012-03-18 20.28.51.JPG

    if not path:
        return None

    ret = None
    name = os.path.basename(path)
    name = os.path.splitext(name)[0]

    # ' ' can match multiple spaces
    name = re.sub(r'[-_.]', ' ', name)
    TIME_FORMATS = [
        '%Y%m%d %H%M%S',
        '%Y %m %d %H %M %S',
    ]

    for fmt in TIME_FORMATS:
        try:
            ret = datetime.datetime.strptime(name, fmt)
            break
        except ValueError:
            pass

    return ret
        
    # try:
    #     if len(name) >= 15:
    #         year = int(name[:4])
    #         month = int(name[4:6])
    #         day = int(name[6:8])
    #         hour = int(name[9:11])
    #         minute = int(name[11: 13])
    #         second = int(name[13:15])

    #         if year >= 1900 \
    #            and month >= 1 and month <= 12 \
    #            and day >= 1 and day <= 31 \
    #            and hour >= 0 and hour < 24 \
    #            and minute >= 0 and minute < 60 \
    #            and second >= 0 and second < 60:
    #             ret = datetime.datetime(
    #                 year=year, month=month, day=day,
    #                 hour=hour, minute=minute, second=second
    #             )
    # except ValueError:
    #     pass

    return ret

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

# check if there are some jpg files that can be extract time info
# by exiftool but can not extract time info by myexif
def check_get_time(path):
    path = os.path.abspath(path)
    for root, dirs, files in os.walk(path, topdown=True):
        for name in files:
            file_path = os.path.join(root, name)
            if not file_path.lower().endswith('.jpg'):
                continue
                
            exif = get_exif_info(encode_text(file_path))
            if not exif:
                exif = get_exif_by_exiftool(file_path)
                if exif and get_exif_time(exif):
                    print exif
            
if __name__ == '__main__':
    import sys

    path = sys.argv[1]

    if os.path.isdir(path):
        check_get_time(path)
        exit(0)
    
    print ExifInfo(path)

    import timeit
    def testit():
        ExifInfo(path)
    # print timeit.timeit('testit()',
    #               'from __main__ import testit',
    #               number=10000)

    # exiftool: 10 times 1.38 seconds
    # myexif: 10000 times 0.97 seconds


