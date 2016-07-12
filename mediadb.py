#! /usr/bin/env python

import sqlite3
from mediafile import MediaFile
from utils import *
import os
import logging
from exif import ExifInfo

MIN_FILE_SIZE = 10 * 1024
TYPE_IMAGE, TYPE_VIDEO = 'image', 'video'

class Row(dict):
    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    # def save(self):
    #     self._db.update(self.id, self)
    

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
        self._execute(cursor, query, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        return [Row(zip(column_names, row)) for row in cursor]

    def _make_where_clause(self, kv):
        return ' and '.join(('%s=:%s'%(k,k) if v is not None else
                             '%s is null'%k
                             for k, v in kv.items()))

    def _make_set_clause(self, kv):
        return ' and '.join(('%s=:%s'%(k,k) for k in kv))

    def update(self, id, **kwparameters):
        if kwparameters:
            query = "update medias set %s where id=:id" % \
                    self._make_set_clause(kwparameters)
            kwparameters["id"] = id
        else:
            return -1
        cursor = self._cursor
        rowid = self._execute(cursor, query, None, kwparameters)
        return rowid

    def iter(self, *parameters, **kwparameters):
        """Returns an iterator for the given query and parameters."""
        if kwparameters:
            query = "select * from medias where %s" % \
                    self._make_where_clause(kwparameters)
        else:
            query = "select * from medias"
        cursor = self._cursor
        self._execute(cursor, query, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        for row in cursor:
            yield Row(zip(column_names, row))

    def query(self, *parameters, **kwparameters):
        query = "select * from medias where %s" % \
                self._make_where_clause(kwparameters)
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

    def del_file(self, **kwparameters):
        sql = 'delete from medias where %s' % \
              self._make_where_clause(kwparameters)
        self._execute(self._cursor, sql, None, kwparameters)

    def relpath(self, path):
        return decode_text(os.path.relpath(path, self._db_dir))

    @staticmethod
    def is_valid_media_file(path):
        file_path = path
        name = os.path.basename(path)
        
        if not os.path.isfile(file_path):
            # Ignore non-files, e.g. symbol links
            return False
            
        if name.startswith('.'):
            #log('Ignore hidden file: %s' % file_path)
            return False

        size = os.path.getsize(file_path)
        
        if not MediaFile.is_media_file(file_path):
            return False
            
        if size < MIN_FILE_SIZE:
            log('Ignore small file: %s' % path)
            return False

        return True

    def add_file(self, path):
        if not MediaDatabase.is_valid_media_file(path):
            return False

        relative_path = self.relpath(path)

        if self.has(relative_path=relative_path):
            return False
            
        log("+ %s" % relative_path)
        
        mf = MediaFile(path, relative_path)
        return self._save(mf)

    def build(self, path):
        path = os.path.abspath(path)
        total_count = 0
        count = 0
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                file_path = os.path.join(root, name)
                if self.add_file(file_path):
                    total_count += 1
                    count += 1
                    
                    if count >= 1000:
                        self.commit()
                        count = 0
                        # log("Added %d files." % total_count)
                
        self.commit()

        log("Total added %d files." % total_count)

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

    def _save(self, mf):
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

        try:
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
            return True
        except sqlite3.IntegrityError:
            mf2 = self.get(middle_md5=mf.middle_md5)
            logging.error(
                'Add file failed(IntegrityError): %s conflict with: %s'
                % (mf.relative_path, mf2.relative_path))

        return False

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
    'add',
    'update',
    'query',
    'diff',
]

_DB_FILE = 'media.sqlite3'

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
                        help='Query or delete by relative path')
    parser.add_argument('--exif-make',
                        help='Query by exif make info'
    )

    # args for add, update
    parser.add_argument(
        '--path',
        help='File path to add or update.'
    )
    parser.add_argument(
        '--update-time',
        action='store_true',
        help='Update collumn time for all files.'
    )

    # args for diff
    parser.add_argument(
        '--left',
        help='Left media directory in diff mode'
    )
    parser.add_argument(
        '--right',
        help='Right media directory in diff mode'
    )

    args = parser.parse_args()

    if args.command not in _COMMANDS:
        log("Invalid command: %s" % args.command)
        exit(0)

    return args

def update_time_for_all_files(mdb, media_dir):
    count = 0
    for root, dirs, files in os.walk(media_dir, topdown=True):
        for name in files:
            file_path = os.path.join(root, name)
            if not MediaDatabase.is_valid_media_file(file_path):
                continue
                
            exif_info = ExifInfo(file_path)
            
            relative_path = mdb.relpath(file_path)
            mf = mdb.get(relative_path=relative_path)
            
            if mf and mf.create_time == exif_info.create_time:
                continue
            elif mf:
                # update
                rowid = mdb.update(mf.id, create_time=exif_info.create_time)
                if rowid > 0:
                    count += 1
                else:
                    logging.error("Update failed: %s" % mf.relative_path)
            
    mdb.commit()

    log("Updated %d files." % count)


def do_single_dir(args):
    db_path = args.db_path
    if db_path is None:
        db_path = os.path.join(args.media_dir, "media.sqlite3")

    if args.command != 'build' and not os.path.isfile(db_path):
        print "Error: please build media database first."
        exit(1)

    mdb = MediaDatabase(db_path)

    if args.command == 'build':
        mdb.build(args.media_dir)

    if args.command == 'add':
        if args.path:
            mdb.add_file(args.path)

    if args.command == 'update':
        if args.path:
            mdb.del_file(path=args.path)
            mdb.add_file(args.path)
        elif args.relpath:
            mdb.del_file(relpath=args.relpath)
            mdb.add_file(args.relpath)
        elif args.update_time:
            update_time_for_all_files(mdb, args.media_dir)
            
    if args.command == 'query':
        values = [args.filename, args.md5, args.relpath, args.exif_make]
        keys = ["filename", "middle_md5", "relative_path", "exif_make"]
        for i in xrange(len(values)):
            if not values[i]:
                keys[i] = None
        values = filter(None, values)
        keys = filter(None, keys)

        kwparameters = dict(zip(keys, values))
        it = mdb.iter(**kwparameters)
        count = 0
        for item in it:
            print item
            count += 1
        print 'Found %d files.' % count

def do_multi_dirs(args):
    left_db = os.path.join(args.left, _DB_FILE)
    right_db = os.path.join(args.right, _DB_FILE)

    if not os.path.isfile(left_db) or \
       not os.path.isfile(right_db):
        exit(2)
    
    left_mdb = MediaDatabase(left_db)
    right_mdb = MediaDatabase(right_db)

    if args.command == 'diff':
        left_items = left_mdb.iter()
        for item in left_items:
            if not right_mdb.get(
                    middle_md5=item.middle_md5,
                    file_size=item.file_size,
                    create_time=item.create_time
            ):
                log('- %s %s' % (item.path, item.middle_md5))

        right_items = right_mdb.iter()
        for item in right_items:
            if not left_mdb.get(
                    middle_md5=item.middle_md5,
                    file_size=item.file_size,
                    create_time=item.create_time
            ):
                log('+ %s %s' % (item.path, item.middle_md5))
        

if __name__ == '__main__':
    args = parse_cmd_args()

    if args.command in ['build', 'update', 'query']:
        do_single_dir(args)

    if args.command == 'diff':
        do_multi_dirs(args)
