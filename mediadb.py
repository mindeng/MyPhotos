#! /usr/bin/env python

import sqlite3
from mediafile import MediaFile
from utils import *
import os
import logging
import re
import json

MIN_FILE_SIZE = 10 * 1024
TYPE_IMAGE, TYPE_VIDEO = 'image', 'video'
_LAST_DB_VERSION = 1

#class Row(dict):
#    """A dict that allows for object-like property access syntax."""
#    def __getattr__(self, name):
#        try:
#            return self[name]
#        except KeyError:
#            raise AttributeError(name)
#
#    # def save(self):
#    #     self._db.update(self.id, self)
#
#    def __str__(self):
#        return json.dumps(
#            self,
#            sort_keys=True,
#            indent=4, separators=(',', ': '),
#            ensure_ascii=False).encode('utf-8')
    

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

    # NOTE: Make sure the value pass into sqlite3 is decoded or sqlite3 will raise
    # exception: sqlite3.ProgrammingError: You must not use 8-bit bytestrings
    # unless you use a text_factory that can interpret 8-bit bytestrings (like
    # text_factory = str). 
    def _decode_values(self, parameters, kwparameters):
        if kwparameters:
            return None, dict((k, decode_text(v)) for k, v in
                    kwparameters.iteritems())
        elif parameters:
            return (decode_text(v) for v in parameters), None
        else:
            return None, None

    IS_NOT_NULL = (True,)

    def _execute(self, cursor, sql, parameters=None, kwparameters=None):
        # Remove placeholder values, e.g.: IS_NOT_NULL
        if kwparameters:
            kwparameters = dict(( (k,v) for k,v in kwparameters.items() if type(v) != type([]) ))
        elif parameters:
            try:
                parameters.remove(MediaDatabase.IS_NOT_NULL)
            except ValueError:
                pass

        try:
            if not (parameters or kwparameters):
                return cursor.execute(sql)
            else:
                parameters, kwparameters = self._decode_values(parameters, kwparameters)
                return cursor.execute(sql, kwparameters or parameters)
        except Exception:
            self.close()
            raise
        
    def _query(self, sql, *parameters, **kwparameters):
        """Returns a row list for the given sql and parameters."""
        cursor = self._cursor()
        self._execute(cursor, sql, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        return [MediaFile(zip(column_names, row)) for row in cursor]

    def _make_where_clause(self, kv):
        return ' and '.join(('%s=:%s'%(k,k) 
            if (v is not None and v != MediaDatabase.IS_NOT_NULL) 
            else '%s is %s' % (k, 
                'not null' if v == MediaDatabase.IS_NOT_NULL else 'null')
                             for k, v in kv.items()))

    def _make_set_clause(self, kv):
        return ','.join(('%s=:%s'%(k,k) for k in kv))

    def update(self, id, **kwparameters):
        if kwparameters:
            sql = "update medias set %s where id=:id" % \
                    self._make_set_clause(kwparameters)
            kwparameters["id"] = id
        else:
            return -1
        cursor = self._cursor()
        self._execute(cursor, sql, None, kwparameters)

    def iter(self, *parameters, **kwparameters):
        """Returns an iterator for the media items specified by the kwparameters."""
        if kwparameters:
            sql = "select * from medias where %s" % \
                    self._make_where_clause(kwparameters)
        else:
            sql = "select * from medias"
        cursor = self._cursor()
        self._execute(cursor, sql, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        for row in cursor:
            yield MediaFile(zip(column_names, row))

    def query(self, *parameters, **kwparameters):
        sql = "select * from medias where %s" % \
                self._make_where_clause(kwparameters)
        return self._query(sql, *parameters, **kwparameters)

    def get(self, *parameters, **kwparameters):
        """Returns the (singular) row specified by the given kwparameters.
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
        self._execute(self._cursor(), sql, None, kwparameters)

    # Return path relatived with db dir
    def relpath(self, path):
        # NOTE: Make sure the path & self._db_dir are all encoded or all decoded, or
        # the os.path.relpath will raise UnicodeDecodeError.
        if not os.path.isabs(path):
            raise Exception("%s is not a abstract path." % path)
        return os.path.relpath(path, self._db_dir)

    # Return path joined with db dir
    def abspath(self, path):
        # NOTE: Make sure the path & self._db_dir are all encoded or all decoded, or
        # the os.path.join will raise UnicodeDecodeError.
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self._db_dir, path))

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
        
        if not is_media_file(file_path):
            return False
            
        if size < MIN_FILE_SIZE:
            log('Ignore small file: %s' % path)
            return False

        return True

    def add_file(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
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
            
        cursor = self._query(self._cursor(), sql, values)
        row = cursor.fetchone()
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
        description         ,
        duration
        )
        values (%s)''' % (','.join('?'*22),)

        try:
            self._execute(self._cursor(), sql, (
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
                mf.duration            ,
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

    def _cursor(self):
        return self._db.cursor()

    def _create_table(self):
        cursor = self._cursor()
        # Create table medias
        self._execute(cursor,
                '''CREATE TABLE IF NOT EXISTS medias 
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
                  description text,
                  duration integer)''')
        
        self.commit()

        # Alter db to add duration fild if user_version == 0
        self._db_version = self._execute(cursor,
                'pragma user_version').fetchone()[0]
        if self._db_version == 0:
            self._execute(cursor,
                    'ALTER TABLE medias ADD COLUMN duration integer')
            self._execute(cursor, 'pragma user_version=1')
            self.commit()
        
            
    def close(self):
        self._db.close()
