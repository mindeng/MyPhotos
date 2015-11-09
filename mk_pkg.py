#! /usr/bin/env python

'''
Make packages for backup, in the following steps:
* Package photos into tgz format in a specified pkg size, in the time order
* Randomly generate a 128-bit key, and using AES algorithm to encrypt the packages
* Using a specified password to encrypt the 128-bit key, and store the encrypted key to a file
* Generate a csv file to store the information of the photos in packages

Input:
    photos_dir: the root directory of the photos which will be packaged
    pkg_size: max size for a photo package
    password: password used to encrypt the AES key
    backup_dir: directory where packages will store in
    working_dir: working directory, there will be some temporary files generated there, 
                and will be finally deleted if the packages has been made successfully
'''

import os
import time
import datetime
import PIL.Image
import PIL.ExifTags
from get_exif import get_time_of_file

import sqlite3
import zlib
import hashlib
import uuid

from cp import copyfile

SZ_M = 1024 * 1024

class CTError(Exception):
    def __init__(self, errors):
        self.errors = errors

def init_db(c):
    c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='photos'""")
    if c.fetchone():
        # table exists
        return

    c.execute('''CREATE TABLE IF NOT EXISTS photos 
            (id integer primary key, 
            pkg_path text, 
            arcname text, 
            date text, 
            timestamp integer, 
            size integer, 
            md5 text)''')
    c.execute('''CREATE UNIQUE INDEX index_md5 ON photos (md5)''')
    c.execute('''CREATE INDEX index_timestamp ON photos (timestamp)''')

class PhotoInfo(object):

    def __init__(self, path, size, fileTime, photoTime=None):
        self.path = path
        self.size = size
        self.fileTimestamp = time.mktime(fileTime.timetuple())
        self.photoTime = photoTime

        self.filename = os.path.basename(path)
        self.photoTimestamp = 0
        if self.photoTime:
            self.photoTimestamp = time.mktime(self.photoTime.timetuple())

        name, ext = os.path.splitext(self.filename)
        self.arcname = '%s_%d%s' % (name, self.timestamp, ext)

    def calc_md5(self):
        with open(self.path, 'rb') as f:
            content = f.read()
            #photo.checksum = zlib.adler32(content)
            self.md5 = hashlib.md5(content).hexdigest()

class PhotoPacker(object):

    def __init__(self):
        pass

    def pack(src, dst, tmp=None, pkg_size=1000*SZ_M):
        photos = self.load_photos_info(src)
        photos.sort(key=lambda i: i.photoTimestamp)

        print 'Total original size:', reduce(lambda x,y: x.size if type(x)!=int else x + y.size if type(y)!=int else y, photos)
        print 'Files without original date:', sum([0 if i.originalTime else 1 for i in photos])

        for i in xrange(0, len(photos), 1000):
            pass

    def load_photos_info(self, path):
        photos = []
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                file_path = os.path.join(root, name)
                #print file_path

                _, ext = os.path.splitext(file_path)
                if ext.upper() == '.AAE':
                    # ignore .AAE files
                    continue

                fileTime, originalTime = get_time_of_file(file_path)
                filesize = os.path.getsize(file_path)
                photos.append(PhotoInfo(file_path, filesize, fileTime, originalTime))
        return photos

    db_file = os.path.join(backup_dir, 'photos.sqlite3')
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    init_db(c)

    pkg_name = uuid.uuid4().hex
    pkg_path = os.path.join(working_dir, pkg_name)
    photos, copied_size = copy_files_until_size(c, sorted_photos, pkg_path, pkg_size)
    # TODO: tar czf

    checksum_conflicts = 0
    for photo in sorted_photos:
        c.execute('SELECT (md5) FROM photos WHERE checksum=?', (photo.checksum,))
        row = c.fetchone()
        need_insert = True
        if row:
            if row[0] == photo.md5:
                # has been inserted
                need_insert = False
            else:
                # conflict
                checksum_conflicts += 1

        if need_insert:
            c.execute('insert into photos (arcname, date, timestamp, size, checksum, md5) values (?, ?, ?, ?, ?)', 
                    (photo.arcname, photo.date.strftime('%F %T'), photo.timestamp, photo.size, photo.checksum, photo.md5))

    conn.commit()
    conn.close()

    print 'Checksum confilicts: %d' % checksum_conflicts



def is_photo_packaged(cursor, photo):
    cursor.execute('SELECT (md5) FROM photos WHERE checksum=?', (photo.checksum,))
    row = cursor.fetchone()
    packaged = False
    if row:
        photo.md5 = hashlib.md5(photo.bytes).hexdigest()
        if row[0] == photo.md5:
            packaged = True
        else:
            # conflict
            pass
    return packaged

def copy_files_until_size(cursor, sorted_photos, dst, max_size):
    if not os.path.exists(dst):
        os.makedirs(dst)

    L = []
    copied_size = 0
    for p in sorted_photos:
        load_photo(p)
        packaged = is_photo_packaged(cursor, p)

        if conflicted:
            checksum_conflicts += 1

        if packaged:
            print 'Ingore packaged photo: %s' % p.path
        else:
            srcname = p.path
            dstname = os.path.join(dst, p.arcname)
            copyfile(srcname, dstname)

            copied_size += p.size
            L.append(p)

            if copied_size >= max_size:
                break

    return L, copied_size

if __name__ == '__main__':
    import sys

    backup_dir = sys.argv[2]
    working_dir = sys.argv[2]
    mk_pkgs(sys.argv[1], '123', backup_dir, working_dir)

    def test_sort_files_by_time():
        sorted_filenames, nonOriginalNum = sort_photos_by_time(sys.argv[1])
        print len(sorted_filenames), nonOriginalNum
        def print_info(item):
            print item[0], item[1], item[2]
        print_info(sorted_filenames[0])
        print_info(sorted_filenames[1])
        print_info(sorted_filenames[-1])

        def is_tuple(x):
            return hasattr(x, '__getitem__')
        print 'total original size:', reduce(lambda x,y: x[2] if is_tuple(x) else x + y[2] if is_tuple(y) else y, sorted_filenames)
