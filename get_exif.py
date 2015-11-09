#! /usr/bin/env python

import PIL
import PIL.Image
import PIL.ExifTags
import datetime
import os

def get_time_of_file(path):
    fileTime, originalTime = None, None

    _, ext = os.path.splitext(path)
    if ext.lower() == '.mov':
        originalTime = get_creation_datetime_for_mov(path)
    elif ext.lower() in ( '.mp4', '.avi', '.m4v' ):
        metadata = processFile(path)
        try:
            originalTime = metadata.get('creation_date')
        except ValueError:
            pass
    else:
        # Better performance than get_original_datetime_of_file
        try:
            originalTime = get_original_datetime_of_photo(path)
        except IOError:
            print 'Failed to get original time from %s . Maybe it is not a image.' % path
            exit(1)

    fileTime = get_ctime(path)

    return fileTime, originalTime

def get_original_datetime_of_file(path):
    TAG_NAME = 'EXIF DateTimeOriginal'
    with open(path, 'rb') as f:
        tags = exifread.process_file(f)
        return tags.get(TAG_NAME)
    return None

_EXIF_TAG_TIME_ORIGINAL = 'DateTimeOriginal'
_EXIF_ID_TIME_ORIGINAL = next((k for k, v in PIL.ExifTags.TAGS.items() if v == _EXIF_TAG_TIME_ORIGINAL))
_EXIF_TIME_FORMAT = '%Y:%m:%d %H:%M:%S'
def get_original_datetime_of_photo(path):
    img = PIL.Image.open(path)
    try:
        exif = img._getexif()
        if exif is None:
            return None
        return datetime.datetime.strptime(exif[_EXIF_ID_TIME_ORIGINAL], _EXIF_TIME_FORMAT)
    except (AttributeError, KeyError):
        return None
    except (Exception) as e:
        print 'Fail to get exif: %s' % path
    return None

def get_ctime(path):
    return datetime.datetime.fromtimestamp(os.path.getctime(path))

import struct

def get_creation_datetime_for_mov(path):
    ATOM_HEADER_SIZE = 8
    # difference between Unix epoch and QuickTime epoch, in seconds
    EPOCH_ADJUSTER = 2082844800

    # open file and search for moov item
    with open(path, "rb") as f:
        while 1:
            atom_header = f.read(ATOM_HEADER_SIZE)
            if atom_header[4:8] == 'moov':
                break
            else:
                atom_size = struct.unpack(">I", atom_header[0:4])[0]
                f.seek(atom_size - 8, 1)

        # found 'moov', look for 'mvhd' and timestamps
        atom_header = f.read(ATOM_HEADER_SIZE)
        if atom_header[4:8] == 'cmov':
            #print "moov atom is compressed"
            return None
        elif atom_header[4:8] != 'mvhd':
            #print "expected to find 'mvhd' header"
            return None
        else:
            f.seek(4, 1)
            creation_date = struct.unpack(">I", f.read(4))[0]
            modification_date = struct.unpack(">I", f.read(4))[0]
            #print "creation date:",
            #print datetime.datetime.utcfromtimestamp(creation_date - EPOCH_ADJUSTER)
            #print "modification date:",
            #print datetime.datetime.utcfromtimestamp(modification_date - EPOCH_ADJUSTER)
            return datetime.datetime.fromtimestamp(creation_date - EPOCH_ADJUSTER)
    return None

try:
    from hachoir_core.error import error, HachoirError
    from hachoir_core.cmd_line import unicodeFilename
    from hachoir_core.i18n import getTerminalCharset, _
    from hachoir_core.benchmark import Benchmark
    from hachoir_core.stream import InputStreamError
    from hachoir_core.tools import makePrintable
    from hachoir_parser import createParser, ParserList
    import hachoir_core.config as hachoir_config
    from hachoir_metadata import config
except ImportError, err:
    raise
    print >>sys.stderr, "Unable to import an Hachoir module: %s" % err
    sys.exit(1)
from hachoir_metadata import extractMetadata
from hachoir_metadata.metadata import extractors as metadata_extractors
def processFile(filename, quality=0.5):
    charset = getTerminalCharset()
    filename, real_filename = unicodeFilename(filename, charset), filename

    # Create parser
    try:
        tags = None
        parser = createParser(filename, real_filename=real_filename, tags=tags)
    except InputStreamError, err:
        error(unicode(err))
        return False
    if not parser:
        error(_("Unable to parse file: %s") % filename)
        return False

    # Extract metadata
    try:
        return extractMetadata(parser, quality)
    except HachoirError, err:
        error(unicode(err))
        parser.error(_("Hachoir can't extract metadata, but is able to parse: %s")
            % filename)

    return None


def print_exif(path):
    img = PIL.Image.open(path)
    exif = img._getexif()
    d = {
        PIL.ExifTags.TAGS[k]: v
        for k, v in exif.items()
        if k in PIL.ExifTags.TAGS
        }
    print d

from PIL.ExifTags import TAGS, GPSTAGS

def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value

    return exif_data

def _get_if_exist(data, key):
    if key in data:
        return data[key]
        
    return None
    
def _convert_to_degress(value):
    """Helper function to convert the GPS coordinates stored in the EXIF to degress in float format"""
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)

    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return d + (m / 60.0) + (s / 3600.0)

def get_lat_lon(exif_data):
    """Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)"""
    lat = None
    lon = None

    if "GPSInfo" in exif_data:      
        gps_info = exif_data["GPSInfo"]

        gps_latitude = _get_if_exist(gps_info, "GPSLatitude")
        gps_latitude_ref = _get_if_exist(gps_info, 'GPSLatitudeRef')
        gps_longitude = _get_if_exist(gps_info, 'GPSLongitude')
        gps_longitude_ref = _get_if_exist(gps_info, 'GPSLongitudeRef')

        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = _convert_to_degress(gps_latitude)
            if gps_latitude_ref != "N":                     
                lat = 0 - lat

            lon = _convert_to_degress(gps_longitude)
            if gps_longitude_ref != "E":
                lon = 0 - lon

    return lat, lon


if __name__ == '__main__':
    import sys

    path = sys.argv[1]
    #print_exif(path)

    #img = PIL.Image.open(path)
    #exif_data = get_exif_data(img)
    #print get_lat_lon(exif_data)

    import exifread
    # Open image file for reading (binary mode)
    f = open(path, 'rb')

    # Return Exif tags
    tags = exifread.process_file(f)
    print tags#['DateTimeOriginal']

    metadata = processFile(path)
    print metadata.get('creation_date')

    print get_time_of_file(path)
