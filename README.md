MyPhotos V2.0
===================

Currently only support Mac OS X/Linux platforms.

```
$ mediamgr.py -h
usage: mediamgr.py [-h] [--filename FILENAME] [--exif-make EXIF_MAKE]
                   [--exif-model EXIF_MODEL] [--gps GPS] [--has-gps]
                   [--non-gps] [--has-time] [--non-time]
                   [--type {image,video}] [--ext EXT] [--date DATE]
                   [--min-size MIN_SIZE] [--max-size MAX_SIZE]
                   [--min-date MIN_DATE] [--max-date MAX_DATE]
                   [--sort-by {date,size}] [--reverse] [--all] [--only-count]
                   [--get-md5] [--md5 MD5] [--relpath RELPATH] [--path PATH]
                   [--id ID] [--reload] [--reload-abspath] [--reload-exif]
                   [--reload-md5] [--set-gps SET_GPS] [--cleanup]
                   [--rearrange-dir] [--dry-run] [--only-insrc] [--only-indst]
                   [--overwrite] [--no-timeit]
                   [{build,add,update,query,diff,merge,get}] [media_dir]
                   [dst_dir]

Media file database manager

positional arguments:
  {build,add,update,query,diff,merge,get}
                        Media manager command.
  media_dir             Media root directory.
  dst_dir               Destination media root directory in diff/merge mode

optional arguments:
  -h, --help            show this help message and exit
  --filename FILENAME   Query by filename
  --exif-make EXIF_MAKE
                        Query by exif make info
  --exif-model EXIF_MODEL
                        Query by exif model info
  --gps GPS             Query by gps info. gps info is specified in format
                        "latitude,longtitude,altitude".
  --has-gps             Query media files which gps info is not empty.
  --non-gps             Query media files which gps info is empty.
  --has-time            Query media files which create time is not empty.
  --non-time            Query media files which create time is empty.
  --type {image,video}  Query media files by type.
  --ext EXT             Query media files by file extension.
  --date DATE           Query media files which are created at the specified
                        DATE.
  --min-size MIN_SIZE   Query media files which size are equal or greater than
                        MIN_SIZE.
  --max-size MAX_SIZE   Query media files which size are equal or less than
                        MAX_SIZE.
  --min-date MIN_DATE   Query media files which are created at or after the
                        specified MIN_DATE.
  --max-date MAX_DATE   Query media files which are created at or before the
                        specified MAX_DATE.
  --sort-by {date,size}
                        Sort media files by the specified key.
  --reverse             Combine with --sort-by option, reverse the sort order.
  --all                 Query all media files.
  --only-count          Only print the number of matched media files.
  --get-md5             Calculate a partial md5 for file, using a specific
                        algorithm.
  --md5 MD5             Specified operation file by md5
  --relpath RELPATH     Specified operation file by path relatived to the
                        media root directory.
  --path PATH           Specified operation file by path.
  --id ID               Specified operation file by id.
  --reload              Reload the specified media file.
  --reload-abspath      Reload the abstract path for the specified media
                        files. It's useful when the media root directory has
                        been changed.
  --reload-exif         Reload exif info for the specified media files.
  --reload-md5          Reload md5 info (including md5, path, file_size) for
                        the specified media files.
  --set-gps SET_GPS     Set gps for the specified media file. gps info is
                        specified in format "latitude,longtitude,altitude".
  --cleanup             Cleanup database items whose related file is not
                        existing in filesystem.
  --rearrange-dir       Rerrange directory for media files, directory created
                        by user will not be affected.
  --dry-run             Dry run the update command.
  --only-insrc          Print files only in source directory in diff mode
  --only-indst          Print files only in right in diff mode
  --overwrite           Copy file any way and overwrite any existed files in
                        merge mode.
  --no-timeit           Donnot display elapsed time.
```

