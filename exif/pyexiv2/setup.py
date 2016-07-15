from distutils.core import setup, Extension
import os

EXIV2_PATH = os.getenv('EXIV2_PATH')
EXIV2_INCLUDE_PATH = os.path.join(EXIV2_PATH, 'include')

module1 = Extension('myexif',
        libraries=[
            "iconv",
            "z",
            "expat",
            ],
                    sources = [
                        'pyexiv2module.cpp',
                        'myexiv2.cpp',
                        'Jzon.cpp',
                    ],
                    extra_objects = [
                        'libexiv2.a',
                        ],

extra_compile_args=['-O2',
                    '-I%s'%EXIV2_INCLUDE_PATH,
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
    so_relpath = os.path.join('build/lib.macosx-10.11-x86_64-2.7/', so)
    so_abspath = os.path.join(module_path, so_relpath)
    dst = os.path.join(module_path, '..', so)
    print 'ln -s %s %s' % (so_abspath, dst)
    os.symlink(so_abspath, dst)

link_so()
