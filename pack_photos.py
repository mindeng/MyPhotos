#! /usr/bin/env python

'''
Pack photos/videos for backup purpose, in the following steps:
* Pack photos/videos into packages in .tar file type, with a specified pkg size, and ordered by time
* Create a sqlite3 db file to store md5 message of all packed photos/videos, so there won't be duplicate files in your packages
* Randomly generate a 128-bit key, and using AES algorithm to encrypt the packages
* Using a specified password to encrypt the 128-bit key, and store the encrypted key into the sqlite3 db file
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
import tarfile
import sys

from enc_file import *

SZ_M = 1024 * 1024
_ARCH_KEY_LEN = 16

class CTError(Exception):
    def __init__(self, errors):
        self.errors = errors

def init_photo_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # Create table photos
    c.execute('''CREATE TABLE IF NOT EXISTS photos 
            (id integer primary key, 
            path text,
            md5 text,
            arch text)''')
    c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS _idx_photos_path ON photos (path)''')
    c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS _idx_photos_md5 ON photos (md5)''')
    #c.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='photos'""")
    #if not c.fetchone():

    # Create table keystore
    c.execute('''CREATE TABLE IF NOT EXISTS keystore
            (id integer primary key, 
            aes_key text,
            verify_key text)''')

    conn.commit()

    return conn

class PhotoInfo(object):

    def __init__(self, path, md5):
        self.path = path
        self.md5 = md5
        self.load_info()

    def load_info(self):
        path = self.path
        fileTime, photoTime = get_time_of_file(path)
        size = os.path.getsize(path)

        self.size = size
        self.fileTime = fileTime
        self.photoTime = photoTime

        self.filename = os.path.basename(path)
        if self.photoTime:
            self.datetime = photoTime
        else:
            self.datetime = fileTime
        self.timestamp = time.mktime(self.datetime.timetuple())

def calc_md5(path):
    md5 = None
    with open(path, 'rb') as f:
        content = f.read()
        #checksum = zlib.adler32(content)
        md5 = hashlib.md5(content).hexdigest()
    return md5

def touch_file(path):
    with open(path, 'wb') as f:
        pass

class PackInfo(object):

    def __init__(self, arch_dir, photos, ext='.tar'):
        self.arch_dir = arch_dir
        self.photos = photos
        self.ext = ext

    def gen_name(self, appendix):
        first = self.photos[0]
        last = self.photos[-1]
        tfm = '%Y%m'

        return '%s-%s_%s' % (first.datetime.strftime(tfm), last.datetime.strftime(tfm), appendix)

    @property
    def name(self):
        return self._name

    @property
    def archive_name(self):
        return self._name + self.ext

    @name.setter
    def name(self, name):
        self._name = name
        self.path = os.path.join(self.arch_dir, self.archive_name)

        if os.path.isfile(self.path):
            log( 'archive %s exists, abort.' % self.path )
            exit(1)

    def do_pack(self, key, tmp_dir):
        if os.path.isfile(self.path):
            log( 'archive %s exists, abort.' % self.path )
            exit(1)

        path = self.path
        if tmp_dir and key:
            path = os.path.join(tmp_dir, self.archive_name)

        # compression on images is not worth
        with tarfile.open(path, "w") as tar:
            arcname_set = set()
            for p in self.photos:
                arcname = p.filename
                name, ext = os.path.splitext(arcname)
                # get a arcname which dose not exists
                while arcname in arcname_set:
                    arcname = '%s_%s%s' % (name, uuid.uuid4().hex[:4], ext)
                arcname_set.add(arcname)
                # add parent dir name
                arcname = '%s/%s'%(self.name, arcname)
                tar.add(p.path, arcname=arcname)

        # encrypt
        if key:
            src = path
            dst = self.path + '.enc'
            log( 'Encrypt %s to %s' % (src, dst) )
            with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
                encrypt_file(in_file, out_file, key, _ARCH_KEY_LEN)

            # remove the un-ecrypted archive
            log( 'Remove %s' % src )
            os.unlink(src)

def log(s):
    print s
    sys.stdout.flush()
def log_elapsed(s, start):
    elapsed = time.time() - start
    td = datetime.timedelta(seconds=elapsed)
    print '%s elapsed %s' % (s, td)
    sys.stdout.flush()

def decode_text(text):
    ret = None
    try:
        try:
            if type(text) == type(''):
                ret = text.decode('utf-8')
        except UnicodeDecodeError, e:
            ret = text.decode('gb18030')
    except UnicodeDecodeError, e:
        log('Failed to decode %s' % text)
        log(e)
    return ret

class PhotoPacker(object):

    def __init__(self, db, ignore_prefix=None, key=None, exclude_dir=None):
        self.db = db
        self.ignore_prefix = ignore_prefix
        self.key = key
        self.exclude_dir = exclude_dir

    def pack(self, src, dst, tmp=None, pkg_size=500*SZ_M):
        log('start loading info ...')
        start = time.time()
        photos = self.load_photos_info(src)
        photos.sort(key=lambda i: i.timestamp)
        log_elapsed('end loading info.', start)

        log('Total original size: %.2fG' % (reduce(lambda x,y: x.size if type(x)!=int else x + y.size if type(y)!=int else y, photos, 0)/1024.0/1024.0/1024.0,))
        log('Files without original date: %d' % sum([0 if i.photoTime else 1 for i in photos]))

        packs = []
        while len(photos) > 0:
            pack_photos, pack_size = self.slice_photos_for_pack(photos, pkg_size)
            packs.append(PackInfo(dst, pack_photos))

        self.gen_names_for_packs(packs)

        log('Archive num: %d' % len(packs))

        i = 0;
        for pack in packs:
            i += 1
            log('=== start packing %d/%d %s ===' % (i, len(packs), pack.name))
            start = time.time()
            pack.do_pack(self.key, tmp)
            log_elapsed('end packing.', start)

            log('updating db ...')
            start = time.time()
            self.update_db(pack)
            log_elapsed('end updating db.', start)

            log('\n')

    def gen_names_for_packs(self, packs):
        c = self.db.cursor()
        for pack in packs:
            name = ''
            while True:
                appendix = uuid.uuid4().hex[:4]
                name = pack.gen_name(appendix)
                c.execute('SELECT id FROM photos WHERE arch=?', (name,))
                if not c.fetchone():
                    break
            pack.name = name

    def update_db(self, pack):
        c = self.db.cursor()
        for p in pack.photos:
            c.execute('update photos set arch=? where md5=?', (pack.archive_name, p.md5))

        self.db.commit()

    def slice_photos_for_pack(self, photos, pkg_size):
        pack_size = 0
        pack_photos = []
        while len(photos) > 0 and pack_size < pkg_size:
            p = photos.pop(0)
            pack_size += p.size
            pack_photos.append(p)

        return pack_photos, pack_size

    def get_retrieve_path(self, path):
        retrieve_path = path
        if self.ignore_prefix and path.startswith(self.ignore_prefix):
            retrieve_path = path[len(self.ignore_prefix):]
        return retrieve_path
    def get_decode_retrieve_path(self, path):
        retrieve_path = self.get_retrieve_path(path)
        decode_path = decode_text(retrieve_path)
        if decode_path is None:
            log('Failed to query photo %s' % path)
            exit(1)
        return decode_path

    def query_photo(self, path):
        decode_path = self.get_decode_retrieve_path(path)
        c = self.db.cursor()
        c.execute('SELECT arch, md5 FROM photos WHERE path=?', (decode_path,))
        row = c.fetchone()
        return row if row else (None, None)

    def save_md5(self, path, md5):
        decode_path = self.get_decode_retrieve_path(path)
        c = self.db.cursor()
        try:
            c.execute('insert into photos (path, md5) values (?, ?)', (decode_path, md5))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            conflict_path = self.query_photo_path_by_md5(md5)
            if conflict_path is None:
                c.execute('update photos set path=? where md5=?', (decode_path, md5))
                self.db.commit()
            else:
                log('Ignore duplicated file: %s md5: %s \n\tDuplicated with %s' % (decode_path, md5, conflict_path))
            return False

    def query_photo_path_by_md5(self, md5):
        c = self.db.cursor()
        c.execute('SELECT path FROM photos WHERE md5=?', (md5,))
        row = c.fetchone()
        return row[0] if row else None

    def load_photos_info(self, path):
        photos = []
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                if name.startswith('.'):
                    continue

                file_path = os.path.join(root, name)

                if self.exclude_dir:
                    my_dir = os.path.basename(os.path.dirname(file_path))
                    if my_dir == self.exclude_dir:
                        log( 'Ignore excluded file %s' % file_path )
                        continue

                _, ext = os.path.splitext(file_path)
                if ext.upper() == '.AAE':
                    # ignore .AAE files
                    continue

                arch, md5 = self.query_photo(file_path)
                if arch:
                    log( 'Ignore archived photo: %s' % file_path )
                    continue

                if not md5:
                    md5 = calc_md5(file_path)
                    if not self.save_md5(file_path, md5):
                        log( 'Ignore conflict photo: %s' % file_path )
                        continue

                p = PhotoInfo(file_path, md5)
                photos.append(p)

        return photos

from Crypto import Random
import hashlib

def gen_aes_key():
    return Random.new().read(16)

def gen_verify_key(password, salt=None):
    if not salt:
        salt = gen_aes_key()
    verify_key = hashlib.sha256(hashlib.md5(password + salt).digest()).digest()
    return base64.b64encode(salt+verify_key)
def verify_password(verify_key, password):
    _key = base64.b64decode(verify_key)
    salt = _key[:16]
    return verify_key == gen_verify_key(password, salt)

def save_key(db, raw, password):
    cipher_text = encrypt_str(raw, password)
    verify_key = gen_verify_key(password)
    c = db.cursor()
    c.execute('insert into keystore (aes_key, verify_key) values (?, ?)', (cipher_text, verify_key))
    db.commit()
def retrieve_encrypted_keys(db):
    c = db.cursor()
    c.execute('SELECT aes_key, verify_key FROM keystore')
    row = c.fetchone()
    return row if row else (None, None)
def has_key(db):
    return retrieve_encrypted_keys(db)[0] is not None
def load_key(db, password):
    aes_key, verify_key = retrieve_encrypted_keys(db)
    if not verify_password(verify_key, password):
        return None
    aes_key = decrypt_str(aes_key, password)
    return aes_key

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Pack photos for backup.')
    parser.add_argument('src', help='Source path or directory. In pack mode(default), this specify the photos/videos directory which will be packed; in decrypt mode(-d), this specify the archive file which will be decrypted.')
    parser.add_argument('-o', '--output', 
            help='Output directory or path. In pack mode(default), this specify the output directory of encrypted archives; in decrypt mode(-d), this specify the output path or directory for the decrypted archive file.',
            default='.')
    parser.add_argument('--db', dest='db_path', help='Database file path', default='db.sqlite3')
    parser.add_argument('--ignore-prefix', help='Ignore the specified path prefix when caching md5')
    parser.add_argument('-p', '--password', help='Password to encrypt the AES key')
    parser.add_argument('--no-encrypt', help='No need to encrypt the archive files')
    parser.add_argument('--tmp', help='Temporary working directory')
    parser.add_argument('--exclude-dir', help='Excldue directory')

    parser.add_argument('-d', '--decrypt', dest='decrypt_flag', action='store_const', const=True, help='Decrypt the specified archive file.')

    args = parser.parse_args()
    #log( args )

    db_path = args.db_path
    ignore_prefix = args.ignore_prefix
    src = args.src
    dst = args.output
    password = args.password
    tmp = args.tmp
    decrypt_flag = args.decrypt_flag

    if not tmp:
        tmp = dst

    db = init_photo_db(db_path)

    if decrypt_flag or (password is None and not args.no_encrypt):
        password = user_input_password(not has_key(db))

    key = None
    if password:
        if has_key(db):
            key = load_key(db, password)
            if not key:
                print 'Error: load key failed'
                exit(1)
        else:
            key = gen_aes_key()
            save_key(db, key, password)

    if decrypt_flag:
        if os.path.isdir(dst):
            arch_name = os.path.basename(src)
            arch_name, _ = os.path.splitext(arch_name)
            dst = os.path.join(dst, arch_name)

        if os.path.isfile(dst):
            choice = raw_input('File %s exists, overwrite? (y/n) ' % dst)
            if choice != 'y':
                exit(1)

        with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
            ret = decrypt_file(in_file, out_file, key)
            if not ret:
                print 'Decrpt failed!'
    else:
        if not os.path.isdir(dst):
            os.makedirs(dst)

        packer = PhotoPacker(db, ignore_prefix, key, args.exclude_dir)
        log( 'pack %s to %s ...' % (src, dst) )
        packer.pack(src, dst, tmp)
