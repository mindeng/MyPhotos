#! /usr/bin/env python

import sqlite3
from mediafile import MediaFile
from utils import *
import os
import logging
import re
import json
import string

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
            return [decode_text(v) for v in parameters], None
        else:
            return None, None

    IS_NOT_NULL = ('is not null',)
    IS_NULL     = ('is null',)
    CMP_GTE     = ('>=',)
    CMP_LTE     = ('<=',)
    CMP_GT      = ('>',)
    CMP_LT      = ('<',)

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
                express = '%s=:%s' % (col, k)

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
            
        #if size < MIN_FILE_SIZE:
        #    log('Ignore small file: %s' % path)
        #    return False

        return True

    def add_mf(self, mf):
        return self._save(mf)

    def add_file(self, path):
        if not os.path.isabs(path):
            path = os.path.abspath(path)
            
        if not MediaDatabase.is_valid_media_file(path):
            return False

        relative_path = self.relpath(path)

        if self.has(relative_path=relative_path):
            return False
            
        #log("+ %s" % relative_path)
        
        mf = MediaFile(path=path, relative_path=relative_path)
        return self._save(mf)

    def build(self, path):
        path = os.path.abspath(path)
        total_count = 0
        count = 0
        for root, dirs, files in os.walk(path, topdown=True):
            for name in files:
                file_path = os.path.join(root, name)
                if self.add_file(file_path):
                    logging.info("+ %s" % file_path)
                    total_count += 1
                    count += 1
                    
                    if count >= 1000:
                        self.commit()
                        count = 0
                        # log("Added %d files." % total_count)
                
        self.commit()

        logging.info("Total added %d files." % total_count)

    def has(self, middle_md5=None, relative_path=None):
        if middle_md5:
            sql = 'select count(*) from medias where middle_md5=?'
            values = (middle_md5,)
        elif relative_path:
            sql = 'select count(*) from medias where relative_path=?'
            values = (relative_path,)
            
        row = self._execute(self._cursor(), sql, values).fetchone()
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
