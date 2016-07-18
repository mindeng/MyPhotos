#! /usr/bin/env python

from utils import *
from mediadb import MediaDatabase
from exif import ExifInfo, get_file_time, hex_middle_md5
from mediafile import MediaFile
import re
import sqlite3
from exif import copy_file
import logging
import datetime
import string

_COMMANDS = [
    'build',
    'add',
    'update',
    'query',
    'diff',
    'merge',
    'get',  # get information from file
]

_DB_FILE = 'media.sqlite3'

def parse_cmd_args():
    import argparse

    parser = argparse.ArgumentParser(
        description='Media file database manager')

    # command: build, update, query
    parser.add_argument(
        'command',
        nargs='?', default='query',
        help='Media manager command. Valid commands: %s' % ', '.join(_COMMANDS)
    )
    parser.add_argument(
        'media_dir',
        nargs='?', default=os.getcwd(),
        help='Media root directory.'
    )
    parser.add_argument(
        'dst_dir',
        nargs='?', default=None,
        help='Destination media root directory in diff/merge mode'
    )

    # args for query
    parser.add_argument(
            '--filename',
            help='Query by filename')
    parser.add_argument(
            '--exif-make',
            dest='exif_make',
            help='Query by exif make info')
    parser.add_argument(
            '--exif-model',
            dest='exif_model',
            help='Query by exif model info')
    parser.add_argument(
            '--gps',
            help='Query by gps info. gps info is specified in format "latitude,longtitude,altitude".'
            )
    parser.add_argument(
        '--has-gps',
        dest='has_gps',
        action='store_true',
        help='Query media files which gps info is not empty.'
    )
    parser.add_argument(
        '--non-gps',
        dest='non_gps',
        action='store_true',
        help='Query media files which gps info is empty.'
    )
    parser.add_argument(
        '--has-time',
        dest='has_time',
        action='store_true',
        help='Query media files which create time is not empty.'
    )
    parser.add_argument(
        '--non-time',
        dest='non_time',
        action='store_true',
        help='Query media files which create time is empty.'
    )
    parser.add_argument(
        '--type',
        help='Query media files by type, valid types are: image, video.'
        )
    parser.add_argument(
        '--ext',
        help='Query media files by file extension.'
        )
    parser.add_argument(
        '--date',
        help='Query media files which are created at the specified DATE.'
        )
    parser.add_argument(
        '--min-size',
        dest='min_size',
        help='Query media files which size are equal or greater than MIN_SIZE.'
        )
    parser.add_argument(
        '--max-size',
        dest='max_size',
        help='Query media files which size are equal or less than MAX_SIZE.'
        )
    parser.add_argument(
        '--min-date',
        dest='min_date',
        help='Query media files which are created at or after the specified MIN_DATE.'
        )
    parser.add_argument(
        '--max-date',
        dest='max_date',
        help='Query media files which are created at or before the specified MAX_DATE.'
        )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Query all media files.'
        )
    parser.add_argument(
        '--only-count',
        dest='only_count',
        action='store_true',
        help='Only print the number of matched media files.'
            )

    # args for get
    parser.add_argument(
            '--get-md5',
            dest='get_md5',
            action='store_true',
            help='Calculate a partial md5 for file, using a specific algorithm.'
            )

    # args for specified operation file
    parser.add_argument(
        '--md5',
        help='Specified operation file by md5')
    parser.add_argument(
        '--relpath',
        help='Specified operation file by path relatived to the media root directory.')
    parser.add_argument(
        '--path',
        help='Specified operation file by path.'
    )
    parser.add_argument(
        '--id',
        help='Specified operation file by id.'
    )

    # args for update
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Reload the specified media file.'
    )
    parser.add_argument(
        '--reload-exif',
        action='store_true',
        help='Reload exif info for the specified media file.'
    )
    parser.add_argument(
        '--reload-md5',
        action='store_true',
        help='Reload md5 info (including md5, path, file_size) for the specified media file.'
    )
    parser.add_argument(
        '--set-gps',
        dest='set_gps',
        help='Set gps for the specified media file. gps info is specified in format "latitude,longtitude,altitude".'
    )
    parser.add_argument(
            '--dry-run',
            dest='dry_run',
            action='store_true',
            help='Dry run the update command.'
            )

    # args for diff
    parser.add_argument(
        '--only-insrc',
        dest='only_inleft',
        action='store_true',
        help='Print files only in source directory in diff/merge mode'
    )
    parser.add_argument(
        '--only-inright',
        dest='only_inright',
        action='store_true',
        help='Print files only in right in diff mode'
    )

    # Don't display elapsed time
    parser.add_argument(
            '--no-timeit',
            dest='no_timeit',
            action='store_true',
            help='Donnot display elapsed time.'
            )

    args = parser.parse_args()

    if args.command not in _COMMANDS:
        log("Invalid command: %s.\nCommands: %s" % 
                (args.command, ', '.join(_COMMANDS)))
        exit(0)

    # NOTE: 
    # It's important to make sure all input args are decoded, or these
    # exceptions may occur:
    # * sqlite3 may raise exception sqlite3.ProgrammingError.
    # * Comparation between encoded text and decoded text may failed.
    # * Some system call related with path (e.g.: os.path.join,
    #   os.path.relpath) may raise exception UnicodeDecodeError.
    for key, value in vars(args).iteritems():
        if value:
            if type(value) == type(True) and key.startswith('non_'):
                # translate non_* values to IS_NULL
                setattr(args, key, MediaDatabase.IS_NULL)
            elif type(value) == type(True) and key.startswith('has_'):
                # translate has_* values to IS_NOT_NULL
                setattr(args, key, MediaDatabase.IS_NOT_NULL)
            else:
                # try to decode all user input values
                setattr(args, key, decode_text(value))


    # NOTE: Make sure all path (except relpath) is abstract path.
    fix_path = lambda path: os.path.abspath(path) if path else None
    args.media_dir = fix_path(args.media_dir)
    args.dst_dir = fix_path(args.dst_dir)
    args.path = fix_path(args.path)

    if os.path.isdir(args.media_dir):
        args.db_path = os.path.join(args.media_dir, _DB_FILE)
    else:
        log("No such file or directory: %s" % args.path)
        exit(1)
    args.left = args.media_dir
    args.right = args.dst_dir

    return args

### operation functions for update command ###

def op_reload_md5(mdb, args, mf, dry_run):
    if not mf:
        return False

    path = mdb.abspath(mf.relative_path)
    if not os.path.isfile(path):
        log("Cannot find file %s." % mf.relative_path)
        return False

    path = mdb.abspath(mf.relative_path)
    new_mf = MediaFile(mf)
    new_mf.load_file_info(path)

    if \
            new_mf.path == mf.path and \
            new_mf.file_size == mf.file_size and \
            new_mf.middle_md5 == mf.middle_md5:
                return False

    # update file info

    log("Updating: %s" % mdb.abspath(mf.relative_path))
    log("old: %s" % mf)
    log("new: %s" % new_mf)

    if dry_run:
        return False

    try:
        mdb.update(
                mf.id,
                path=new_mf.path,
                file_size=new_mf.file_size,
                middle_md5=new_mf.middle_md5
                )
    except sqlite3.IntegrityError:
        conflict_mf = mdb.get(middle_md5=new_mf.middle_md5)
        logging.warn('IntegrityError: middle_md5 conflict with: %s' % conflict_mf)
        return False

    return True

def op_reload_exif(mdb, args, mf, dry_run):
    if not mf:
        return False

    exif_info = ExifInfo(mdb.abspath(mf.relative_path))

    if exif_info == mf:
        return False

    # update exif info
    log("Updating: %s" % mdb.abspath(mf.relative_path))
    log("old: %s" % mf._exif_info)
    log("new: %s" % exif_info)

    if dry_run:
        return False

    mdb.update(
            mf.id,
            create_time=exif_info.create_time,
            exif_make=exif_info.exif_make,
            exif_model=exif_info.exif_model,
            gps_latitude=exif_info.gps_latitude,
            gps_longitude=exif_info.gps_longitude,
            gps_altitude=exif_info.gps_altitude,
            image_width=exif_info.image_width,
            image_height=exif_info.image_height,
            f_number=exif_info.f_number,
            exposure_time=exif_info.exposure_time,
            iso=exif_info.iso,
            focal_length_in_35mm=exif_info.focal_length_in_35mm,
            duration=exif_info.duration
            )
    return True

def op_reload(mdb, args, mf, dry_run):
    new_mf = MediaFile(path=mdb.abspath(mf.relative_path), relative_path=mf.relative_path)
    if mf == new_mf:
        return False

    log("Updating: %s" % mdb.abspath(mf.relative_path))
    log("old: %s" % mf)
    log("new: %s" % new_mf)

    if dry_run:
        return False

    # udpate all info for the specified item
    mdb.update_mf(mf.id, new_mf)
    return True

def op_set_gps(mdb, args, mf, dry_run):
    gps_values = parse_gps_values(args.set_gps)

    if \
            mf.gps_latitude     == gps_values[0] and \
            mf.gps_longitude    == gps_values[1] and \
            mf.gps_altitude     == gps_values[2] :
        return False

    log("Updating: %s" % mdb.abspath(mf.relative_path))
    log("old: %s" % mf._exif_info)

    mf.gps_latitude     = gps_values[0];
    mf.gps_longitude    = gps_values[1];
    mf.gps_altitude     = gps_values[2];

    log("new: %s" % mf._exif_info)

    if dry_run:
        return False

    mdb.update_mf(mf.id, mf)
    return True

### do command functions ###

def do_update(mdb, args):
    mf = None
    dry_run = args.dry_run

    action_ops = {
            "reload": op_reload,
            "reload_exif": op_reload_exif,
            "reload_md5": op_reload_md5,
            "set_gps": op_set_gps,
            }

    update_op = None
    for k, v in action_ops.iteritems():
        if getattr(args, k, False):
            update_op = v

    if update_op:
        it = query_by_args(mdb, args)

        count = 0
        success_count = 0
        for mf in it:
            count += 1
            if update_op(mdb, args, mf, dry_run):
                success_count += 1

        mdb.commit()

        log("Found %d file%s, %d updated." % (count, 's' if count>1 else '', success_count))

def do_query(mdb, args):
    it = query_by_args(mdb, args)
    count = 0

    if args.only_count:
        count = it
    else:
        for item in it:
            log(item)
            count += 1
    log('Found %d file%s.' % (count, 's' if count>1 else ''))

def do_get(args):

    path = args.path

    if args.get_md5:
        log(hex_middle_md5(path))

def query_by_args(mdb, args):

    def parse_user_input_date(v):
        v = v.replace('-', '')
        try:
            if len(v) == len('2016'):
                return datetime.datetime.strptime(v, '%Y')
            elif len(v) == len('201601'):
                return datetime.datetime.strptime(v, '%Y%m')
            else:
                return datetime.datetime.strptime(v, '%Y%m%d')
        except ValueError:
            log("Invalid date format: %s. Please input date like '2016', '201607', '2010716', or '2016-07-16'." % v)
            exit(3)

    def parse_user_input_size(v):
        multiplier = 1
        size = v
        unit = None
        if v[-1] not in string.digits:
            unit = v[-1].lower()
            size = v[:-1]

        if unit == 'k':
            multiplier = 1024
        elif unit == 'm':
            multiplier = 1024 * 1024

        try:
            return float(size) * multiplier
        except ValueError:
            log("Invalid size: %s. Please input size like 1m, 500k, 88888." % v)

        return 0

    def handle_arg_date(v):
        t1 = parse_user_input_date(v)
        d = datetime.timedelta(days=1)
        v = v.replace('-', '')
        if len(v) == len('2016'):
            t2 = datetime.datetime(year=t1.year+1, month=1, day=1)
        elif len(v) == len('201601'):
            if t1.month < 12:
                t2 = datetime.datetime(year=t1.year, month=t1.moth+1, day=1)
            else:
                t2 = datetime.datetime(year=t1.year+1, month=t1.moth, day=1)
        return (MediaDatabase.CMP_GTE, t1), (MediaDatabase.CMP_LT, t2)

    def handle_arg_max_date(v):
        t = parse_user_input_date(v)
        t += datetime.timedelta(days=1)
        return (MediaDatabase.CMP_LT, t)

    # normalize arg file extension
    # TODO: query by multiple extensions
    def handle_arg_ext(v):
        v = v.lower()
        if not v.startswith('.'):
            v = '.%s' % v
        return v

    query_args = [
            ( "filename"                                 ,    ( args.filename,     None),                       ),  
            ( "relative_path"                            ,    ( args.path,         lambda v: mdb.relpath(v)),   ),  # Only using relative_path to query, because the root directory may has been moved.
            ( "relative_path"                            ,    ( args.relpath,      None),                       ),
            ( "create_time-0,create_time-1"              ,    ( args.date,         handle_arg_date),            ),
            ( "create_time-2"                            ,    ( args.min_date,     lambda v: ( MediaDatabase.CMP_GTE, parse_user_input_date(v) ) ),  ),
            ( "create_time-3"                            ,    ( args.max_date,     handle_arg_max_date),        ),
            ( "create_time"                              ,    ( args.has_time,     None),                       ),
            ( "create_time"                              ,    ( args.non_time,     None),                       ),
            ( "file_size"                                ,    ( args.min_size,     lambda v: ( MediaDatabase.CMP_GTE, parse_user_input_size(v) ) ),  ),
            ( "file_size"                                ,    ( args.max_size,     lambda v: ( MediaDatabase.CMP_LTE, parse_user_input_size(v) ) ),  ),
            ( "media_type"                               ,    ( args.type,         lambda v: v.lower()),        ),
            ( "file_extension"                           ,    ( args.ext,          handle_arg_ext),             ),
            ( "exif_make"                                ,    ( args.exif_make,    None),                       ),
            ( "exif_model"                               ,    ( args.exif_model,   None),                       ),
            ( "gps_latitude"                             ,    ( args.has_gps,      None),                       ),
            ( "gps_latitude"                             ,    ( args.non_gps,      None),                       ),
            ( "gps_latitude,gps_longitude,gps_altitude"  ,    ( args.gps,          parse_gps_values),           ),
            ( "middle_md5"                               ,    ( args.md5,          None),                       ),
            ( "id"                                       ,    ( args.id,           None),                       ),  
            ]

    kwparameters = dict()
    for k, v in query_args:
        keys = k.split(',')

        if not v[0]: continue

        if v[1]:
            values = v[1](v[0])
        else:
            values = v[0]

        if values:
            if len(keys) > 1:
                kwparameters.update(zip(keys, values))
            else:
                kwparameters[keys[0]] = values

    # If no query is specified, return empty result
    if not args.all and not kwparameters:
        log("Needs at least one query option.")
        exit(1)

    if args.only_count:
        return mdb.count(**kwparameters)
    else:
        return mdb.iter(**kwparameters)

def do_single_dir(args):
    if args.command != 'build' and not os.path.isfile(args.db_path):
        print "Error: please build media database first."
        exit(1)

    mdb = MediaDatabase(args.db_path)

    if args.command == 'build':
        mdb.build(args.media_dir)

    if args.command == 'add':
        if args.path:
            if mdb.add_file(args.path):
                log("+ %s" % args.path)

    if args.command == 'update':
        do_update(mdb, args)

    if args.command == 'query':
        do_query(mdb, args)

def do_diff(left_mdb, right_mdb, args):
    def log_files_only_db1(db1, db2, prefix):
        count_only_in_db1 = 0
        count_same = 0
        it = db1.iter()
        for item in it:
            if not db2.get(
                    middle_md5=item.middle_md5,
                    file_size=item.file_size,
                    create_time=item.create_time
            ):
                log('%s %s %s' % (prefix, item.path, item.middle_md5))
                count_only_in_db1 += 1
            else:
                count_same += 1
        return count_only_in_db1, count_same

    count_only_in_left, count_only_in_right = None, None
    if not args.only_inright:
        count_only_in_left, count_same = log_files_only_db1(left_mdb, right_mdb, '-')
    if not args.only_inleft:
        count_only_in_right, count_same = log_files_only_db1(right_mdb, left_mdb, '+')
    
    log('Same files: %d' % count_same)
    if count_only_in_left:
        log('Only in src: %d' % (args.left, count_only_in_left))
    if count_only_in_right:
        log('Only in dst: %d' % (args.right, count_only_in_right))

def do_merge(left_mdb, right_mdb, args):
    dst_root = args.right
    it = left_mdb.iter()
    count_only_in_left = 0
    count_same = 0
    copied = 0

    for src_mf in it:
        if right_mdb.get(
                middle_md5  = src_mf.middle_md5,
                file_size   = src_mf.file_size,
                create_time = src_mf.create_time
                ):
            count_same += 1
        else:
            count_only_in_left += 1
            src = left_mdb.abspath(src_mf.relative_path)
            file_time = src_mf.create_time or get_file_time(src)
            dst_dir = os.path.join(dst_root, 
                    file_time.strftime('%Y'), 
                    file_time.strftime('%Y%m'),
                    file_time.strftime('%Y%m%d'),
                    src_mf.file_extension[1:])
            dst = os.path.join(dst_dir, src_mf.filename)

            log('%s -> %s' % (src, dst))

            if not os.path.isdir(dst_dir):
                os.makedirs(dst_dir)

            dst_mf = None
            if os.path.isfile(dst):
                dst_mf = MediaFile(path=dst, relative_path=right_mdb.relpath(dst))
                if dst_mf.middle_md5 == src_mf.middle_md5:
                    logging.warn('File %s exists, database will be updated.' % dst)
                    right_mdb.add_mf(dst_mf)
                else:
                    logging.warn('File %s exists, copy aborted.' % dst)
                    dst_mf = None
            elif not args.dry_run:
                if copy_file(src, dst):
                    dst_mf = MediaFile(path=dst, relative_path=right_mdb.relpath(dst))
                    # copied file's middle_md5 should be same as the src_mf's middle_md5
                    if dst_mf.middle_md5 == src_mf.middle_md5:
                        right_mdb.add_mf(dst_mf)
                        copied += 1
                    else:
                        logging.error("Copied file's middle_md5 dose not match, copy failed: %s." % src)
                        os.unlink(dst)

    right_mdb.commit()

    log('Same files: %d' % count_same)
    log('Only in src: %d' % count_only_in_left)
    log('Copied files: %d' % copied)

def do_multi_dirs(args):

    def get_db_file(media_dir):
        if not os.path.isdir(media_dir):
            log('%s is not a directory.' % media_dir)
            exit(2)

        db_path = os.path.join(media_dir, _DB_FILE)
        if not os.path.isfile(db_path):
            log('Please run command "mediamgr.py build %s" to build media ' \
                    'database first.' % db_path)
            exit(2)
        return db_path

    left_db_file = get_db_file(args.left)
    right_db_file = get_db_file(args.right)
    
    left_mdb = MediaDatabase(left_db_file)
    right_mdb = MediaDatabase(right_db_file)

    if args.command == 'diff':
        do_diff(left_mdb, right_mdb, args)
    elif args.command == 'merge':
        do_merge(left_mdb, right_mdb, args)

def parse_gps_values(text):
    gps_values = re.split(r'[, ]', text)
    return [float(v) if v else None for v in gps_values]

def main(args):
    if args.command in ['build', 'update', 'query']:
        do_single_dir(args)

    if args.command in ['diff', 'merge']:
        do_multi_dirs(args)

    if args.command in ['get']:
        do_get(args)

if __name__ == '__main__':
    import timeit
    start = timeit.default_timer()

    args = parse_cmd_args()
    main(args)

    if not args.no_timeit:
        elapsed = timeit.default_timer() - start
        log( 'Elapsed time: %s %s' % (
            elapsed / 60.0 if elapsed >= 60.0 else elapsed,
            'minutes' if elapsed >= 60.0 else 'seconds' ) )
