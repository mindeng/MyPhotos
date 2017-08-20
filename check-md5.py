#!/usr/bin/env python

from __future__ import print_function
import sqlite3
import sys
import os
import hashlib

BUF_SIZE = 1024 * 1024 * 32

def md5_file(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(BUF_SIZE), ""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

root = sys.argv[1]
db_path = os.path.join(root, 'medias.db')
db = sqlite3.connect(db_path)
c = db.cursor()

sql = 'select * from media where md5 is not NULL'
c.execute(sql)

#db_names = ('path', 'name', 'size', 'extension', 'mime', 'mime_sub', 'date', 'make', 'model', 'md5', 'mtime')

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

for row in c:
    path = os.path.join(root, row[0])
    md5 = md5_file(path)
    if md5 != row[-2]:
        eprint('[error] %s' % (path, ))


