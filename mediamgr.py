#! /usr/bin/env python

from utils import *
from mediadb import MediaDatabase
from exif import ExifInfo
from mediafile import MediaFile
import re
import sqlite3

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
        help='Media manager command. Valid commands: %s' % ', '.join(_COMMANDS)
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
    parser.add_argument('--exif-make',
                        help='Query by exif make info'
    )
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
        '--all',
        action='store_true',
        help='Query all media files.'
        )

    # args for specified operation file
    parser.add_argument(
        '--md5',
        help='Specified operation file by md5')
    parser.add_argument(
        '--relpath',
        help='Specified operation file by relative path')
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
            '--dry',
            action='store_true',
            help='Dry run the update command.'
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
    parser.add_argument(
        '--only-inleft',
        dest='only_inleft',
        action='store_true',
        help='Print files only in left in diff mode'
    )
    parser.add_argument(
        '--only-inright',
        dest='only_inright',
        action='store_true',
        help='Print files only in right in diff mode'
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
    for key,value in vars(args).iteritems():
        if value:
            setattr(args, key, decode_text(value))


    # NOTE: Make sure all path (except relpath) is abstract path.
    fix_path = lambda path: os.path.abspath(path) if path else None
    args.path = fix_path(args.path)
    args.media_dir = fix_path(args.media_dir)
    args.db_path = fix_path(args.db_path)

    if args.db_path is None:
        args.db_path = os.path.join(args.media_dir, _DB_FILE)

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
        return True

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
        return True

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
        return True

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
        return True

    mdb.update_mf(mf.id, mf)
    return True

### do command functions ###

def do_update(mdb, args):
    mf = None
    dry_run = args.dry

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
    for item in it:
        print item
        count += 1
    log('Found %d file%s.' % (count, 's' if count>1 else ''))

def query_by_args(mdb, args):
    values = [args.filename, args.md5, args.relpath, args.exif_make, args.path, args.id]
    keys = ["filename", "middle_md5", "relative_path", "exif_make", "path", "id"]

    if args.gps:
        gps_values = parse_gps_values(args.gps)
        values += gps_values
        keys += ['gps_latitude', 'gps_longitude', 'gps_altitude']

    for i in xrange(len(values)):
        if not values[i]:
            keys[i] = None
        elif keys[i] == 'path':
            # Convert abstract path to relative path, so that the file
            # can be found even if the root directory changed
            keys[i] = "relative_path"
            values[i] = mdb.relpath(args.path)

    keys = filter(None, keys)
    values = filter(None, values)
    
    if args.has_gps:
        keys += ['gps_latitude']
        values += [MediaDatabase.IS_NOT_NULL]
    elif args.non_gps:
        keys += ['gps_latitude']
        values += [None]

    if args.has_time:
        keys += ['create_time']
        values += [MediaDatabase.IS_NOT_NULL]
    elif args.non_time:
        keys += ['create_time']
        values += [None]

    # If no query is specified, return empty result
    if not args.all and not keys:
        return []

    kwparameters = dict(zip(keys, values))
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
            mdb.add_file(args.path)

    if args.command == 'update':
        do_update(mdb, args)

    if args.command == 'query':
        do_query(mdb, args)

def do_multi_dirs(args):
    left_db = os.path.join(args.left, _DB_FILE)
    right_db = os.path.join(args.right, _DB_FILE)

    if not os.path.isfile(left_db) or \
       not os.path.isfile(right_db):
        exit(2)
    
    left_mdb = MediaDatabase(left_db)
    right_mdb = MediaDatabase(right_db)

    def log_files_only_db1(db1, db2):
        count_only_in_db1 = 0
        count_same = 0
        items = db1.iter()
        for item in items:
            if not db2.get(
                    middle_md5=item.middle_md5,
                    file_size=item.file_size,
                    create_time=item.create_time
            ):
                log('- %s %s' % (item.path, item.middle_md5))
                count_only_in_db1 += 1
            else:
                count_same += 1
        return count_only_in_db1, count_same

    count_only_in_left, count_only_in_right = None, None
    if args.command == 'diff':
        if not args.only_inright:
            count_only_in_left, count_same = log_files_only_db1(left_mdb, right_mdb)
        if not args.only_inleft:
            count_only_in_right, count_same = log_files_only_db1(right_mdb, left_mdb)
        
        log('Same files: %d' % count_same)
        if count_only_in_left:
            log('Only in %s: %d' % (args.left, count_only_in_left))
        if count_only_in_right:
            log('Only in %s: %d' % (args.right, count_only_in_right))

def parse_gps_values(text):
    gps_values = re.split(r'[, ]', text)
    return [float(v) if v else None for v in gps_values]

def main():
    args = parse_cmd_args()

    if args.command in ['build', 'update', 'query']:
        do_single_dir(args)

    if args.command == 'diff':
        do_multi_dirs(args)

if __name__ == '__main__':
    import timeit

    start = timeit.default_timer()

    main()

    elapsed = timeit.default_timer() - start
    log( 'Elapsed time: %s %s' % (
        elapsed / 60.0 if elapsed >= 60.0 else elapsed,
        'minutes' if elapsed >= 60.0 else 'seconds' ) )
