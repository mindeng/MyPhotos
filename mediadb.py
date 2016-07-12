#! /usr/bin/env python

import sqlite3
from mediafile import MediaFile
from utils import *
import os
import logging

MIN_FILE_SIZE = 10 * 1024
TYPE_IMAGE, TYPE_VIDEO = 'image', 'video'

class Row(dict):
    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    

class MediaDatabase(object):

    def __init__(self, path=":memory:"):
        self._db_path = os.path.abspath(path)
        self._db_dir = os.path.dirname(self._db_path)

        self._init_db()
        self._create_table()

    def __del__(self):
        self.close()

    def _init_db(self):
        # def dict_factory(cursor, row):
        #     d = {}
        #     for idx, col in enumerate(cursor.description):
        #         d[col[0]] = row[idx]
        #         return d

        self._db = sqlite3.connect(
            self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        # self._db.row_factory = dict_factory

    def _execute(self, cursor, query, parameters, kwparameters):
        try:
            return cursor.execute(query, kwparameters or parameters)
        except Exception:
            self.close()
            raise
        
    def _query(self, query, *parameters, **kwparameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor
        try:
            self._execute(cursor, query, parameters, kwparameters)
            column_names = [d[0] for d in cursor.description]
            return [Row(zip(column_names, row)) for row in cursor]
        finally:
            pass

    def query(self, *parameters, **kwparameters):
        query = "select * from medias where %s" % (
            ' and '.join(('%s=:%s'%(k,k) for k in kwparameters))
        )
        return self._query(query, *parameters, **kwparameters)

    def get(self, *parameters, **kwparameters):
        """Returns the (singular) row returned by the given query.
        If the query has no results, returns None.  If it has
        more than one result, raises an exception.
        """
        rows = self.query(*parameters, **kwparameters)
        
        if not rows:
            return None
        elif len(rows) > 1:
            print rows
            raise Exception(
                "Multiple rows returned for Database.get() query")
        else:
            return rows[0]

    def build(self, path):
        path = os.path.abspath(path)
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                file_path = os.path.join(root, name)

                if not os.path.isfile(file_path):
                    # Ignore non-files, e.g. symbol links
                    continue
                
                relative_path = os.path.relpath(file_path, self._db_dir)

                if name.startswith('.'):
                    #log('Ignore hidden file: %s' % file_path)
                    continue

                size = os.path.getsize(file_path)
                
                if not MediaFile.is_media_file(file_path):
                    continue
                
                if size < MIN_FILE_SIZE:
                    log('Ignore small file: %s' % relative_path)
                    continue

                if self.has(relative_path=relative_path):
                    continue

                log("+ %s" % relative_path)
                
                mf = MediaFile(file_path, relative_path)
                self.save(mf)
                
        self.commit()

    def has(self, middle_md5=None, relative_path=None):
        if middle_md5:
            sql = 'select count(*) from medias where middle_md5=?'
            values = (middle_md5,)
        elif relative_path:
            sql = 'select count(*) from medias where relative_path=?'
            values = (relative_path,)
            
        self._cursor.execute(sql, values)
        row = self._cursor.fetchone()
        return row and row[0] > 0

    def save(self, mf):
        sql = '''insert into medias(
        filename            ,
        path                ,
        relative_path       ,
        create_time         ,
        file_size           ,
        media_type          ,
        file_extension      ,
        exif_make           ,
        exif_model          ,
        gps_latitude        ,
        gps_longitude       ,
        gps_altitude        ,
        image_width         ,
        image_height        ,
        f_number            ,
        exposure_time       ,
        iso                 ,
        focal_length_in_35mm,
        middle_md5          ,
        tags                ,
        description
        )
        values (%s)''' % (','.join('?'*21),)

        self._cursor.execute(sql, (
            mf.filename            ,
            mf.path                ,
            mf.relative_path       ,
            mf.create_time         ,
            mf.file_size           ,
            mf.media_type          ,
            mf.file_extension      ,
            mf.exif_make           ,
            mf.exif_model          ,
            mf.gps_latitude        ,
            mf.gps_longitude       ,
            mf.gps_altitude        ,
            mf.image_width         ,
            mf.image_height        ,
            mf.f_number            ,
            mf.exposure_time       ,
            mf.iso                 ,
            mf.focal_length_in_35mm,
            mf.middle_md5          ,
            mf.tags                ,
            mf.description         ,
        ))

    def commit(self):
        self._db.commit()

    @property
    def _cursor(self):
        if getattr(self, "_db_cursor", None) is None:
            self._db_cursor = self._db.cursor()
        return self._db_cursor

    def _create_table(self):
        # Create table medias
        self._cursor.execute('''CREATE TABLE IF NOT EXISTS medias 
                  (id integer primary key,
                  filename text,
                  path text unique,
                  relative_path text unique,
                  create_time timestamp,
                  file_size integer,
                  media_type text,
                  file_extension text,
                  exif_make text,
                  exif_model text,
                  gps_latitude real,
                  gps_longitude real,
                  gps_altitude real,
                  image_width integer,
                  image_height integer,
                  f_number real,
                  exposure_time real,
                  iso integer,
                  focal_length_in_35mm integer,
                  middle_md5 text unique,
                  tags text,
                  description text)''')
        
        # c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS _idx_medias_middle_md5 ON medias (middle_md5)''')
        self.commit()
            
    def close(self):
        self._db.close()

_COMMANDS = [
    'build',
    'update',
    'query',
]

def parse_cmd_args():
    import argparse

    parser = argparse.ArgumentParser(
        description='Media file database manager')

    # command: build, update, query
    parser.add_argument(
        'command',
        help='Media manager command.'
    )
    parser.add_argument(
        '--media-dir',
        default='.',
        help='Specify medias directory.'
    )
    parser.add_argument(
        '--db',
        dest='db_path',
        help='Database file path',
        default=None
    )

    # args for query
    parser.add_argument('--filename',
                        help='Query by filename')
    parser.add_argument('--md5',
                        help='Query by md5')
    parser.add_argument('--relpath',
                        help='Query by relative path')

    args = parser.parse_args()

    if args.command not in _COMMANDS:
        log("Invalid command: %s" % args.command)
        exit(0)

    return args

if __name__ == '__main__':
    args = parse_cmd_args()

    db_path = args.db_path
    if db_path is None:
        db_path = os.path.join(args.media_dir, "media.sqlite3")

    mdb = MediaDatabase(db_path)

    if args.command in ['build', 'update']:
        mdb.build(args.media_dir)

    if args.command == 'query':
        values = [args.filename, args.md5, args.relpath]
        keys = ["filename", "middle_md5", "relative_path"]
        for i in xrange(len(values)):
            if not values[i]:
                keys[i] = None
        values = filter(None, values)
        keys = filter(None, keys)

        kwparameters = dict(zip(keys, values))
        result = mdb.query(**kwparameters)
        print 'matched: %d' % len(result)
        print result

    mdb.close()
