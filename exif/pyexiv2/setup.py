from distutils.core import setup, Extension
import os
import platform

architecture = platform.architecture()
OS_MAC, OS_LINUX = 1, 2
OS = OS_MAC
if not architecture[0].startswith('64'):
    print 'Only support 64bit architecture currently, abort.'
    exit(1)

if platform.mac_ver()[0]:
    # MAC OS X
    OS = OS_MAC
elif platform.linux_distribution()[0]:
    OS = OS_LINUX
else:
    print 'Only support Mac OS X and Linux currently, abort.'
    exit(1)

# Default params for OS X
extra_objects = [ 'libexiv2-osx.a', ]
libraries = [
        "iconv",
        "expat",
        "crypto",
        "ssl",
        ]

if OS is OS_LINUX:
    extra_objects = [ 'libexiv2-linux-amd64.a', ]
    libraries = [
            "expat",
            "crypto",
            "ssl",
            ]

EXIV2_PATH = os.getenv('EXIV2_PATH')
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

def link_so():
    module_path = os.path.abspath( os.path.dirname( os.path.realpath(__file__) ) )
    so = 'myexif.so'
    if OS is OS_MAC:
        so_relpath = os.path.join('build/lib.macosx-10.11-x86_64-2.7/', so)
    else:
        so_relpath = os.path.join('build/lib.linux-x86_64-2.7/', so)
    so_abspath = os.path.join(module_path, so_relpath)
    dst = os.path.join(module_path, '..', so)
    print 'ln -s %s %s' % (so_abspath, dst)
    os.unlink(dst)
    os.symlink(so_abspath, dst)

import sys
if len(sys.argv) > 1 and sys.argv[1] == 'build':
    link_so()
