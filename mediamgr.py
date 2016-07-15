#! /usr/bin/env python

from utils import *
from mediadb import MediaDatabase
from exif import ExifInfo
from mediafile import MediaFile
import re

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
        help='Query media files which gps info is not empty".'
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
        '--update-gps',
        dest='update_gps',
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

def reload_exif_info_for_file(mdb, path, dry_run):
    if not MediaDatabase.is_valid_media_file(path):
        return False
        
    relative_path = mdb.relpath(path)
    mf = mdb.get(relative_path=relative_path)
    return reload_exif_info_for_mf(mdb, mf, dry_run)

def reload_md5_for_mf(mdb, mf, dry_run):
    if not mf:
        return False

    path = mdb.abspath(mf.relative_path)
    if not os.path.isfile(path):
        log("Cannot find file %s." % mf.relative_path)
        return False

    path = mdb.abspath(mf.relative_path)
    new_mf = MediaFile()
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

    mdb.update(
            mf.id,
            path=new_mf.path,
            file_size=new_mf.file_size,
            middle_md5=new_mf.middle_md5
            )
    return True

def reload_exif_info_for_mf(mdb, mf, dry_run):
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

def reload_exif_info_for_dir(mdb, media_dir, dry_run):
    count = 0
    for root, dirs, files in os.walk(media_dir, topdown=True):
        for name in files:
            file_path = os.path.join(root, name)
            if reload_exif_info_for_file(mdb, file_path, dry_run):
                count += 1
                #log("Updated %s" % mdb.relpath(file_path))
            
    mdb.commit()

    log("Updated %d files." % count)


def parse_gps_values(text):
    gps_values = re.split(r'[, ]', text)
    return [float(v) if v else None for v in gps_values]

def do_update(mdb, args):
    mf = None
    dry_run = args.dry
    
    if args.path:
        if os.path.isdir(args.path) and args.reload_exif:
            reload_exif_info_for_dir(mdb, args.media_dir, dry_run)
            exit(0)
        else:
            mf = mdb.get(relative_path=mdb.relpath(args.path))
    elif args.relpath:
        mf = mdb.get(relative_path=args.relpath)
    elif args.md5:
        mf = mdb.get(middle_md5=args.md5)

    if mf is None:
        print "Can't find the specified item in the media database."
        exit(1)

    updated = False
        
    if args.reload:
        # udpate all info for the specified item
        mdb.del_file(relative_path=mf.relative_path)
        mdb.add_file(mdb.abspath(mf.relative_path))
        updated = True
    elif args.reload_exif:
        updated = reload_exif_info_for_mf(mdb, mf, dry_run)
    elif args.reload_md5:
        updated = reload_md5_for_mf(mdb, mf, dry_run)
    elif args.update_gps:
        gps_values = parse_gps_values(text)
        mdb.update(mf.id,
                   gps_latitude=gps_values[0],
                   gps_longitude=gps_values[1],
                   gps_altitude=gps_values[2]
        )
        updated = True

    mdb.commit()
    if updated:
        mf = mdb.get(relative_path=mf.relative_path)
        log("Updated media file:\n%s" % mf)
    else:
        log("Nothing to update.")

def do_query(mdb, args):
    values = [args.filename, args.md5, args.relpath, args.exif_make, args.path]
    keys = ["filename", "middle_md5", "relative_path", "exif_make", "path"]

    if args.gps:
        gps_values = parse_gps_values(args.gps)
        values += gps_values
        keys += ['gps_latitude', 'gps_longitude', 'gps_altitude']

    for i in xrange(len(values)):
        if not values[i]:
            keys[i] = None
        elif keys[i] == 'path':
            # convert abstract path to relative path, so that the file can be found even if the root directory changed
            keys[i] = "relative_path"
            values[i] = mdb.relpath(args.path)

    keys = filter(None, keys)
    values = filter(None, values)
    
    if args.has_gps:
        keys += ['gps_latitude']
        values += [MediaDatabase.IS_NOT_NULL]

    if values == []:
        log("Please specify a query condition.")
        exit(1)

    kwparameters = dict(zip(keys, values))
    it = mdb.iter(**kwparameters)
    count = 0
    for item in it:
        print item
        count += 1
    print 'Found %d files.' % count

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
