import sys
import os

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

def log(s):
    print encode_text(s)
    sys.stdout.flush()

def decode_text(text):
    ret = text
    try:
        if type(text) == type(''):
            ret = text.decode('utf-8')
    except UnicodeDecodeError, e:
        try:
            ret = text.decode('gb18030')
        except UnicodeDecodeError, e:
            log('Failed to decode %s' % text)
            log(e)
    return ret

def encode_text(text):
    if type(text) == type(u''):
        return text.encode('utf-8')
    return text

def is_media_file(path):
    extension = os.path.splitext(path)[1].lower()
    return extension in _IMAGE_EXTS or \
        extension in _VIDEO_EXTS

def is_image_file(path):
    extension = os.path.splitext(path)[1].lower()
    return extension in _IMAGE_EXTS
