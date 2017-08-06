#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function
import zlib
import sys
import os
import platform
import sqlite3
import hashlib
import exiftool
import json
import datetime
import re

'''
find . -type f | sed -E 's/.+[\./]([^/\.]+)/\1/' | sort -u
'''
MEDIA_EXTENSIONS = set([ '.'+e.lower() for e in 
'''
ARW
AVI
GIF
JPG
MOV
MP4
NEF
PNG
m4v
'''.split()])

VIDEO_EXTENSIONS = set([ '.'+e.lower() for e in 
'''
AVI
GIF
MOV
MP4
m4v
'''.split()])

#_db = sqlite3.connect(':memory:')
#_db = sqlite3.connect('medias.db')


BUF_SIZE = 65536

def get_meta_by_tags(metadata, tags):
    for tag in tags:
        if metadata.get(tag):
            return metadata.get(tag)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Md5ConflictError(Exception):
    pass
class FileExistedError(Exception):
    pass
class FileMovedError(Exception):
    pass

def parse_date(s):
    if s:
        try:
            return datetime.datetime.strptime(s, '%Y:%m:%d %H:%M:%S')
        except ValueError:
            try:
                return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return None
    return None

def get_date_from_meta(metadata):
    date = get_meta_by_tags(metadata, (
        'EXIF:DateTimeOriginal', 
        'MakerNotes:DateTimeOriginal',
        'EXIF:CreateDate', 
        'QuickTime:CreateDate',
        #'EXIF:ModifyDate', 
        ) )
    return parse_date(date)

def guess_date_from_path(path):
    # try to parse file name as time, e.g.:
    # 20120607_061356
    # 2012-03-18 20.28.51.JPG
    # FxCam_1283244566287.jpg

    if not path:
        return None

    name = os.path.basename(path)
    name = os.path.splitext(name)[0]

    # strip all non-numeric characters
    name = re.sub("[^0-9]", "", name)

    # try FxCam_1283244566287
    if len(name) == 13:
        try:
            timestamp = float(name)/1000.0
            return datetime.datetime.fromtimestamp(timestamp)
        except ValueError:
            pass

    if len(name) == 14:
        fmt = '%Y%m%d%H%M%S'

        try:
            return datetime.datetime.strptime(name, fmt)
        except ValueError:
            pass

class MediaFile(object):
    db_names = ('path', 'name', 'size', 'extension', 'mime', 'mime_sub', 'date', 'make', 'model', 'md5')

    def __init__(self, db=None, root=None, path=None, row=None):
        self.db = db
        self.root = root
        if path:
            self.load_from_path(path)
        elif row:
            self.load_from_row(row)


    def load_from_row(self, row):
        for i in xrange(len(row)):
            setattr(self, MediaFile.db_names[i], row[i])

        self.mime_type = ''
        if self.mime:
            self.mime_type = '/'.join((self.mime, self.mime_sub))

        d = self.date
        self.date = parse_date(d)
        if d is not None and self.date is None:
            eprint( '[date error] load from row %s %s' % (d, self.full_path,) )
        self.inum = self.get_inum()

    def get_inum(self):
        try:
            return os.stat(self.full_path).st_ino
        except OSError:
            return 0


    def asdict(self):
        d = dict([(k, getattr(self, k)) for k in MediaFile.db_names if k != 'md5'])
        d['date'] = self.date_str
        d['md5'] = self._md5
        return d

    def asrow(self):
        d = self.asdict()
        return [d[name] for name in MediaFile.db_names]

    @property
    def full_path(self):
        path = self.path
        if self.root:
            path = os.path.join(self.root, path)
        return path

    @property
    def date_str(self):
        return self.format_date(self.date) if self.date else None

    def format_date(self, d):
        return datetime.datetime.strftime(d, '%Y:%m:%d %H:%M:%S')

    def load_from_path(self, path):
        self.path = path
        # name, size, extension, mime, mime_sub, date, make, model
        name = os.path.basename(path)
        size = os.path.getsize(self.full_path)
        _, extension = os.path.splitext(name)
        with exiftool.ExifTool() as et:
            metadata = et.get_metadata(self.full_path)

            mime, mime_sub = None, None
            MIMEType = metadata.get('File:MIMEType')
            if MIMEType:
                mime, mime_sub = MIMEType.split('/')

            date = get_date_from_meta(metadata)
            if date is None:
                date = guess_date_from_path(name)
            if date is None:
                eprint( '[date error] %s' % (self.full_path,) )

            make = get_meta_by_tags(metadata, (
                'EXIF:Make',
                'QuickTime:Make', 
                'MakerNotes:Make', 
                ))
            model = get_meta_by_tags(metadata, (
                'EXIF:Model', 
                'QuickTime:Model',
                'MakerNotes:Model', 
                ))

            self.mime = mime
            self.mime_sub = mime_sub
            self.mime_type = MIMEType
            self.date = date
            self.make = make
            self.model = model

        self.name = name
        self.extension = extension
        self.size = size
        self.inum = self.get_inum()
        self._md5 = None

    def __hash__(self):
        return hash((self.size, self.mime_type, self.date, self.make, self.model))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.inum != 0 and self.inum == other.inum:
                return True
            return hash(self) == hash(other) and self.md5 == other.md5
        return False

    def has_md5(self):
        return self._md5 is not None

    @property
    def md5(self):
        if self._md5 is None:
            self._md5 = md5_file(self.full_path)
        return self._md5

    @md5.setter
    def md5(self, m):
        self._md5 = m

    def __str__(self):
        return json.dumps(self.tojson(), indent=True)

    def tojson(self):
        return dict([(unicode(k), unicode(getattr(self, k)) if k == 'date' else getattr(self, k)) for k in 
            ['path', 'name', 'size', 'mime_type', 'date', 'make', 'model']])

    def save(self):
        c = self.cursor
        try:
            self.insert()
        except FileExistedError:
            params_fmt = ','.join(['%s=?'%name for name in MediaFile.db_names])
            c.execute('update media set %s where path=?' % params_fmt, self.asrow() + [self.path] )
        except Md5ConflictError as e:
            eprint( '[conflict] %s\t== %s' % (e.args[0].path, self.path) )

    def delete(self):
        c = self.cursor
        c.execute('delete from media where path=?', (self.path,))
        self.commit()

    def insert(self):
        c = self.cursor
        c.execute('select * from media where path=? COLLATE NOCASE', (self.path,))
        if c.fetchone():
            raise FileExistedError()

        c.execute('select * from media where size=? and date=? and make=? and model=?', 
                (self.size, self.date_str, self.make, self.model))
        for row in c:
            mf = MediaFile(db=self.db, row=row)

            if os.path.isfile(mf.full_path):

                if self == mf:
                    mf.save()
                    mf.commit()
                    raise Md5ConflictError(mf)
            else:
                # file may has been renamed or moved
                pass

        sql = 'insert into media values(%s)' % ','.join(['?']*len(MediaFile.db_names))
        try:
            c.execute(sql, self.asrow())
        except sqlite3.IntegrityError as e:
            sql = 'select path from media where md5=?'
            c.execute(sql, (self.md5,))
            found = c.fetchone()
            if found:
                raise Md5ConflictError(found)
            else:
                eprint( '[insert error]: %s %s' % (self.path.encode('utf-8'), e,) )


    def commit(self):
        self.db.commit()

    @property
    def cursor(self):
        if not hasattr(self, '_cursor'):
            self._cursor = self.db.cursor()
        return self._cursor


def db_find_same(main_db, main_root, path):
    L = []
    c = main_db.cursor()
    mf = MediaFile(path=path)
    c.execute('select * from media where size=? and date=? and make=? and model=?', 
            (mf.size, mf.date_str, mf.make, mf.model,))
    for row in c:
        mf2 = MediaFile(db=main_db, root=main_root, row=row)
        if mf == mf2:
            L.append(mf2)
        mf2.save()

    main_db.commit()
    return L

def get_file_list(media_dir):
    L = []
    media_dir = os.path.abspath(media_dir)
    for root, dirs, files in os.walk(media_dir, topdown=True):
        for name in files:
            if name[0] == '.':
                continue
            _, ext = os.path.splitext(name)
            if ext.lower() in MEDIA_EXTENSIONS:
                file_path = os.path.join(root, name)
                file_path = file_path.decode('utf-8')
                relpath = os.path.relpath(file_path, media_dir)
                L.append(relpath)
    return L

def db_has_path(db, path):
    c = db.cursor()
    sql = 'select 1 from media where path=?'
    c.execute(sql, (path,))
    return c.fetchone() is not None

def db_cleanup(db, root, dry):
    c = db.cursor()
    c.execute('select path from media')
    to_delete = []
    for row in c:
        path = row[0]
        full_path = os.path.join(root, path)
        if os.path.isfile(full_path):
            continue
        else:
            print('cleanup %s' % full_path.encode('utf-8'))
            if dry:
                pass
            else:
                to_delete.append(path)

    for p in to_delete:
        c.execute('delete from media where path=?', (p,))

    if len(to_delete) > 0:
        db.commit()

def db_update_db(db, media_dir):
    relpath_list = get_file_list(media_dir)
    for relpath in relpath_list:
        if not db_has_path(db, relpath):
            print('Load file %s'%relpath.encode('utf-8'))
            mf = MediaFile(db=db, root=media_dir, path=relpath)
            print(json.dumps(mf.asdict(), indent=True))
            mf.save()
            mf.commit()

def db_update_time(main_db, main_root):
    c = main_db.cursor()
    sql = 'select * from media where date is null'
    c.execute(sql)
    for row in c:
        mf = MediaFile(db=main_db, root=main_root, row=row)
        with exiftool.ExifTool() as et:
            metadata = et.get_metadata(mf.full_path)
            mf.date = get_date_from_meta(metadata)
            if mf.date is None:
                mf.date = guess_date_from_path(mf.name)
            if mf.date is None:
                eprint( '[date error] %s' % (mf.full_path,) )
            else:
                print('%s %s'%(mf.date, mf.path.encode('utf-8')))
                mf.save()
                mf.commit()

def upgrade_db(_db):
    c = _db.cursor()
    user_version = c.execute('pragma user_version').fetchone()
    if user_version[0] == 0:
        c.execute('pragma user_version=1')
        _db.commit()

def db_find_by_relpath(_db, path):
    c = _db.cursor()
    sql = 'select * from media where path=?'
    c.execute(sql, (path,))
    found = c.fetchone()
    if found:
        return MediaFile(db=_db, row=found)

def db_init_db(_db):
    c = _db.cursor()
    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS media
             (path text unique, name text, size integer, extension text, mime text, mime_sub text, date text, make text, model text, md5 text unique)''')
    _db.commit()


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

def crc_file(path):
    crcvalue = 0
    with open(path, 'rb') as afile:
        buffr = afile.read(BUF_SIZE)
        while len(buffr) > 0:
            crcvalue = zlib.crc32(buffr, crcvalue)
            buffr = afile.read(BUF_SIZE)

    return crcvalue

def md5_file(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(BUF_SIZE), ""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def iter_media_files(path_list, cb):
    for path in path_list:
        for root, dirs, files in os.walk(path):
            for name in files:
                p = os.path.join(root, name)
                p = os.path.abspath(p)
                if os.path.islink(p):
                    # Ignore symbolic link
                    continue
                elif is_hard_link(p):
                    # Ignore hard link
                    continue
                
                _, ext = os.path.splitext(name)
                ext = ext.lower()
                if ext in MEDIA_EXTENSIONS:
                    size = os.path.getsize(p)
                    created = creation_date(p)
                    cb(p, size, created, ext)

def is_hard_link(path):
    if os.name == 'nt':
        return False
    inum = os.stat(path).st_ino
    _c = _db.cursor()
    _c.execute('select path from files where inum=?', (inum, ))
    return _c.fetchone() is not None

def file_handler(path, size, created, ext):
    crc = None
    md5 = None
    path = path.decode('gb18030')
    _c = _db.cursor()
	
	
    _c.execute('select path from files where path=?', (path,))
    target = _c.fetchone()
    if target:
        crc, md5 = target[5], target[6]

    _c.execute('select path, crc32, md5 from files where size=? and extension=? and path<>?', (size, ext, path))
    for row in _c.fetchall():
        if not os.path.isfile(row[0]):
            # TODO
            continue

        if row[1]:
            matched_crc = row[1]
        else:
            matched_crc = crc_file(row[0])
            _c.execute('update files set crc32=? where path=?', (matched_crc, row[0]))
        if crc is None:
            crc = crc_file(path)
            if target:
                _c.execute('update files set crc32=? where path=?', (crc, path))
        if matched_crc == crc:
            if row[2]:
                matched_md5 = row[2]
            else:
                matched_md5 = md5_file(row[0])

                _c.execute('select path from files where md5=?', (matched_md5,))
                found = _c.fetchone()
                if found:
                    if os.path.isfile(found[0]):
                        # repeated file
                        print('%s\t== %s' % (found[0].encode('gb18030'), row[0].encode('gb18030')))
                else:
                    _c.execute('update files set md5=? where path=?', (matched_md5, row[0]))
            if md5 is None:
                md5 = md5_file(path)
                if target:
                    _c.execute('update files set md5=? where path=?', (md5, path))
            if matched_md5 == md5:
                if os.path.isfile(row[0]):
                    # repeated file
                    print('%s\t== %s' % (row[0].encode('gb18030'), path.encode('gb18030')))

    if not target:
        inum = None
        if os.name != 'nt':
            inum = os.stat(path).st_ino
        _c.execute('insert into files values (?,?,?,?,?,?,?,?)', 
            (path, os.path.basename(path), size, created, ext, crc, md5, inum))
        # print 'add file %s' % path
    _db.commit()

def main():
    c = _db.cursor()

    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS files
        # name, size, extension, mime, mime_sub, date, make, model
             (path text unique, name text, size integer, extension text, mime text, mime_sub text, date text, extension text, crc32 integer, md5 text)''')

    user_version = c.execute('pragma user_version').fetchone()
    if user_version[0] == 0:
        # Add field inum
        c.execute('alter table files add column inum')
        c.execute('pragma user_version=1')
        _db.commit()

    sql = "CREATE UNIQUE INDEX IF NOT EXISTS index_inum ON files(inum);"
    c.execute(sql)
    sql = "CREATE INDEX IF NOT EXISTS index_size ON files (size);"
    c.execute(sql)
    sql = "CREATE INDEX IF NOT EXISTS index_crc ON files (crc32);"
    c.execute(sql)
    sql = "CREATE INDEX IF NOT EXISTS index_ext ON files (extension);"
    c.execute(sql)
    sql = "CREATE INDEX IF NOT EXISTS index_md5 ON files (md5);"
    c.execute(sql)

    _db.commit()

    iter_media_files(sys.argv[1:], file_handler)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
#db1.row_factory = dict_factory

def log_files_only_db1(root1, db1, root2, db2):
    c1 = db1.cursor()
    c2 = db2.cursor()

    c1.execute('select * from media')
    
    for item in c1:
        mf1 = MediaFile(db=db1, row=item, root=root1)
        c2.execute('select * from media where size=? and date=? and make=? and model=?', 
                (mf1.size, mf1.date_str, mf1.make, mf1.model,))
        for row in c2:
            mf2 = MediaFile(db=db2, root=root2, row=row)
            if mf1 == mf2:
                eprint('= %s' % mf1.path.encode('utf-8'))
            else:
                print(mf1.path.encode('utf-8'))
            mf2.save()

        mf1.save()

    db1.commit()
    db2.commit()

def parse_cmd_args():
    import argparse

    parser = argparse.ArgumentParser(
        description='Media file database manager')

    parser.add_argument(
        '-u', '--update',
        action='store_true',
        help='update database', 
    )

    parser.add_argument(
        '--load-date',
        dest='load_date',
        action='store_true',
        help='load date for db record whose date is null', 
    )

    parser.add_argument(
        '--cleanup',
        dest='cleanup',
        action='store_true',
        help='cleanup database, print the ID list of records \
                which are not existed in filesystem', 
    )

    parser.add_argument(
        '--root', 
        default='.',
        help='specify main root directory', 
    )

    parser.add_argument(
        '--db', '--main-db',
        default=None,
        dest='main_db',
        help='specify main database path', 
    )

    parser.add_argument(
        '--diff',
        dest='print_new',
        action='store_true',
        help='diff db with another directory, \
                print files which are only in another directory to standard output, \
                print files which are in both directory to error output',
    )

    parser.add_argument(
        '--another-root',
        dest='other_root',
        help='specify another root directory', 
    )
    parser.add_argument(
        '--another-db',
        default=None,
        dest='other_db',
        help='specify another db', 
    )

    parser.add_argument(
        '--add',
        help='add path', 
    )

    parser.add_argument(
        '--find',
        help='find same file', 
    )

    parser.add_argument(
            '--dry',
            action='store_true',
            help='dry run', 
            )

    return parser.parse_args()

if __name__ == '__main__':
    #print MediaFile('/data/01Photos/2016/20160722-湘鄂川自驾游/VIDEO/DSC_0628.MOV')
    #print MediaFile('/home/min/photo-acer-2010-2013/nobody_rehearsal.AVI')
    #print MediaFile('/home/min/photo-acer-2010-2013/Milestone-2010-2012/Camera/2010-08-10_18-45-59_615.jpg')
    #print MediaFile('/home/min/photo-acer-2010-2013/jing-nokia-photo/201101/201101A0/20110111258.jpg')
    #mf = MediaFile('/home/min/photo-acer-2010-2013/jing-nokia-video/201106/201106A0/20110606005.mp4')
    #print mf, hash(mf)
    #p = '/data/01Photos/2016/201601/20160101/JPG/IMG_1577.JPG'
    #print MediaFile(p)
    #p = '/data/01Photos/2007/200705/20070502/JPG/IMG_7404.JPG'

    #p = sys.argv[1]
    #print MediaFile(p)

    DEFAULT_DB_NAME = 'medias.db'

    args = parse_cmd_args()

    main_root = os.path.abspath(args.root)
    main_db_path = args.main_db

    if main_db_path is None:
        main_db_path = os.path.join(main_root, DEFAULT_DB_NAME)

    main_db = sqlite3.connect(main_db_path)

    if args.update:
        db_init_db(main_db)
        db_update_db(main_db, main_root)
    elif args.load_date:
        db_update_time(main_db, main_root)
    elif args.add:
        db_update_db(main_db, main_root)
    elif args.find:
        path = os.path.abspath(args.find)
        relpath = os.path.relpath(path, main_root)
        files = db_find_same(main_db, main_root, path)
        for f in files:
            print(json.dumps(f.asdict(), indent=True))
    elif args.print_new:
        other_root = args.other_root
        other_db_path = args.other_db
        if other_db_path is None:
            other_db_path = os.path.join(other_root, DEFAULT_DB_NAME)
        other_db = sqlite3.connect(other_db_path)

        log_files_only_db1(other_root, other_db, main_root, main_db)
        other_db.close()
    elif args.cleanup:
        db_cleanup(main_db, main_root, args.dry)

    main_db.close()
