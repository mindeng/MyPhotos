from distutils.core import setup, Extension

module1 = Extension('myexif',
                    sources = [
                        'myexifmodule.cpp',
                        'myexif.cpp',
                        'exif.cpp',
                    ],
extra_compile_args=['-O2',
                    '-pedantic',
                    '-Wall',
                    '-Wextra',
                    '-ansi',
                    '-std=c++11'])

setup (name = 'myexif',
       version = '1.0',
       description = 'My exif tool',
       ext_modules = [module1])
