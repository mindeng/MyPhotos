#! /usr/bin/env python

import sqlite3
from mediafile import MediaFile
from utils import *
import os
import logging
import re
import json
import string
from exif import equal_file

MIN_FILE_SIZE = 10 * 1024
TYPE_IMAGE, TYPE_VIDEO = 'image', 'video'
_CURRENT_DB_VERSION = 1

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

    CONFLICT  = 0
    SUCCESS   = 1
    EXISTS    = 2
    REPEATED  = 3
    INVALID   = 4

    def __init__(self, path=":memory:"):
        self._db_path = os.path.abspath(path)
        self._db_dir = os.path.dirname(self._db_path)

        self._init_db()
        self._create_table()

        self._fs_nocase = is_fs_case_insensitive() and 'COLLATE NOCASE' or ''

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
            return [decode_text(v) for v in parameters], None
        else:
            return None, None

    IS_NOT_NULL = ('is not null',)
    IS_NULL     = ('is null',)
    CMP_GTE     = ('>=',)
    CMP_LTE     = ('<=',)
    CMP_GT      = ('>',)
    CMP_LT      = ('<',)
    CMP_NE      = ('<>',)

    ORDER_BY     = 'order by'
    DESC        = 'desc'

    # check if v is a placeholder value
    def _is_placeholder(self, v):
        return type(v) == type(MediaDatabase.IS_NOT_NULL)
    def _is_placeholder_cmp(self, v):
        return type(v) == type(MediaDatabase.IS_NOT_NULL) and v[0][0][0] in '><'

    def _execute(self, cursor, sql, parameters=None, kwparameters=None):
        # Remove placeholder values, e.g.: IS_NOT_NULL
        if kwparameters:
            # leave placeholder values in kwparameters is OK
            # kwparameters = dict(( (k,v) for k,v in kwparameters.items() if not self._is_placeholder(v) ))
            pass
        elif parameters:
            try:
                parameters = filter(lambda v: not self._is_placeholder(v), parameters)
            except ValueError:
                pass

        try:
            if not (parameters or kwparameters):
                return cursor.execute(sql)
            else:
                parameters, kwparameters = self._decode_values(parameters, kwparameters)
                return cursor.execute(sql, kwparameters or parameters)
        except Exception:
            raise
        
    def _query(self, sql, *parameters, **kwparameters):
        """Returns a row list for the given sql and parameters."""
        cursor = self._cursor()
        self._execute(cursor, sql, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        return [MediaFile(zip(column_names, row)) for row in cursor]

    def _make_where_clause(self, kv):
        if not kv:
            return ''

        order_by_clause = self._make_order_clause(kv)

        if not kv:
            return order_by_clause

        if 'path' in kv:
            raise Exception("Should not query by column path.")

        express_list = []
        for k, v in kv.items():
            express = None

            col = k
            try:
                # get correct column name from key word
                col = k[:k.rindex('-')]
                # get crorrect key name from key word 
                # by replacing '-' to '_', because '-' will cause sql error
                k = k.replace('-', '_')
                kv[k] = v
            except ValueError:
                pass

            if v in (MediaDatabase.IS_NOT_NULL, MediaDatabase.IS_NULL):
                express = '%s %s' % (col, v[0])
            elif self._is_placeholder_cmp(v):
                express = '%s%s:%s' % (col, v[0][0], k)
                # set the actual value for the key
                kv[k] = v[1]
            elif v:
                no_case = k in self._nocase_columns and self._fs_nocase or ''
                express = '%s=:%s %s' % (col, k, no_case)

            if express:
                express_list.append(express)

        where = ''
        if express_list:
            where = ' where ' + ' and '.join(express_list)
        return where + order_by_clause

        #return ' and '.join(('%s=:%s'%(k,k) 
        #    if (v is not None and v != MediaDatabase.IS_NOT_NULL) 
        #    else '%s is %s' % (k, 
        #        'not null' if v == MediaDatabase.IS_NOT_NULL else 'null')
        #                     for k, v in kv.items()))

    def _make_set_clause(self, kv):
        return ','.join(('%s=:%s'%(k,k) for k in kv))

    def _make_order_clause(self, kv):
        order_by = None
        desc = ''
        for k,v in kv.items():
            if k == MediaDatabase.ORDER_BY:
                order_by = v
                del kv[k]
            elif k == MediaDatabase.DESC:
                desc = 'desc'
                del kv[k]

        if order_by is None:
            return ''
        else:
            return ' order by %s %s' % (order_by, desc)

    def update(self, id, **kwparameters):
        if kwparameters:
            sql = "update medias set %s where id=:id" % \
                    self._make_set_clause(kwparameters)
            kwparameters["id"] = id
        else:
            return
        cursor = self._cursor()
        self._execute(cursor, sql, None, kwparameters)

    def iter(self, *parameters, **kwparameters):
        """Returns an iterator for the media items specified by the kwparameters."""
        sql = "select * from medias %s" % \
                self._make_where_clause(kwparameters)

        #print sql, kwparameters
        cursor = self._cursor()
        self._execute(cursor, sql, parameters, kwparameters)
        column_names = [d[0] for d in cursor.description]
        for row in cursor:
            yield MediaFile(zip(column_names, row))

    def count(self, *parameters, **kwparameters):
        sql = "select count(*) from medias %s" % \
                self._make_where_clause(kwparameters)
        #print sql, kwparameters
        cursor = self._cursor()
        row = self._execute(cursor, sql, parameters, kwparameters).fetchone()
        return row and row[0] or 0

    def query(self, *parameters, **kwparameters):
        sql = "select * from medias %s" % \
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
            logging.error( 'rows: %s' % (rows,))
            raise Exception(
                "Multiple rows returned for Database.get() query")
        else:
            return rows[0]

    def del_file(self, **kwparameters):
        sql = 'delete from medias %s' % \
              self._make_where_clause(kwparameters)
        self._execute(self._cursor(), sql, None, kwparameters)

    def del_mf(self, mf):
        self.del_file(middle_md5=mf.middle_md5)

    def update_mf(self, id, mf):
        kwparameters = dict(mf)
        kwparameters.update(mf._exif_info)
        try:
            del kwparameters['id']
        except KeyError:
            pass
        self.update(id, **kwparameters)

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

    def add_mf(self, mf):
        return self._save(mf)

    def add_file(self, path, no_exif=False):
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        if not is_valid_media_file(path):
            return MediaDatabase.INVALID

        relative_path = self.relpath(path)

        if self.has(relative_path=relative_path):
            return MediaDatabase.EXISTS
            
        #log("+ %s" % relative_path)
        
        mf = MediaFile(path=path, relative_path=relative_path, no_exif=no_exif)
        return self._save(mf)

    def has(self, **kw):
        sql = 'select count(*) from medias %s' % self._make_where_clause(kw)
        row = self._execute(self._cursor(), sql, None, kw).fetchone()
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
            return MediaDatabase.SUCCESS
        except sqlite3.IntegrityError:
            mf2 = self.get(middle_md5=mf.middle_md5)
            if equal_file(self.abspath(mf.relative_path), self.abspath(mf2.relative_path)):
                # Repeated file, ignore it
                logging.info(
                    'File %s repeated with %s, ignore it.'
                    % (mf.relative_path, mf2.relative_path))
                return MediaDatabase.REPEATED
            else:
                logging.error(
                    'Add file failed(IntegrityError): %s conflict with: %s'
                    % (mf.relative_path, mf2.relative_path))
                return MediaDatabase.CONFLICT

    def commit(self):
        self._db.commit()

    def _cursor(self):
        return self._db.cursor()

    # Upgrade database if user_version < _CURRENT_DB_VERSION
    def _upgrade_db(self):
        cursor = self._cursor()
        db_version = self._execute(cursor,
                'pragma user_version').fetchone()[0]
        if db_version == 0:
            # version 0 -> 1
            # Add column "duration"
            try:
                self._execute(cursor,
                        'ALTER TABLE medias ADD COLUMN duration integer')
            except sqlite3.OperationalError, e:
                logging.error('Upgrade to database version 1 failed: %s' % e)

        # Database has been upgraded
        if db_version < _CURRENT_DB_VERSION:
            self._execute(cursor, 'pragma user_version=%d' % _CURRENT_DB_VERSION)
            self.commit()

    def _create_table(self):
        cursor = self._cursor()
        self._execute(cursor, "SELECT name FROM sqlite_master WHERE type='table' AND name='medias';")
        if cursor.fetchone():
            # Table medias exists, upgrade it if it's an old version db
            self._upgrade_db()

        # Specify no case columns for case insensitive filesystem
        self._nocase_columns = set(['filename', 'relative_path'])

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
        
        self._execute(cursor, 'pragma user_version=%d' % _CURRENT_DB_VERSION)
        self.commit()
            
    def close(self):
        self._db.close()
