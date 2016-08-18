from distutils.core import setup, Extension
import os
import platform
from linkso import *

OS = get_os()

# Default params for OS X
extra_objects = [ 'libexiv2-osx.a', ]
libraries = [
        "iconv",
        "expat",
        "crypto",
        "ssl",
        ]

# Params for OS X
if OS is OS_LINUX:
    extra_objects = [ 'libexiv2-linux-amd64.a', ]
    libraries = [
            "expat",
            "crypto",
            "ssl",
            ]

EXIV2_PATH = os.getenv('EXIV2_PATH')
if not EXIV2_PATH:
    print 'Please set env EXIV2_PATH first.'
    exit(2)

EXIV2_INCLUDE_PATH = os.path.join(EXIV2_PATH, 'include')

module1 = Extension('myexif',
        libraries=libraries,
                    sources = [
                        'pyexiv2module.cpp',
                        'myexiv2.cpp',
                        'Jzon.cpp',
                    ],
                    extra_objects = extra_objects,

extra_compile_args=['-O2',
                    '-I%s'%EXIV2_INCLUDE_PATH,
                    '-std=c++11',
                    '-fPIC',
                    ])
#extra_link_args=[
#        "-L.",
#        ]

setup (name = 'myexif',
       version = '1.0',
       description = 'My exif tool',
       ext_modules = [module1])

import sys
if len(sys.argv) > 1 and sys.argv[1] == 'build':
    link_so(True)
