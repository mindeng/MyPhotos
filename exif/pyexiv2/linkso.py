import os
import platform

OS_MAC, OS_LINUX = 1, 2

def get_os():
    architecture = platform.architecture()
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
    return OS

def link_so(force=False):
    OS = get_os()
    module_path = os.path.abspath( os.path.dirname( os.path.realpath(__file__) ) )
    so = 'myexif.so'
    if OS is OS_MAC:
        so_relpath = os.path.join('build/lib.macosx-10.11-x86_64-2.7/', so)
    else:
        so_relpath = os.path.join('build/lib.linux-x86_64-2.7/', so)
    so_abspath = os.path.join(module_path, so_relpath)
    dst = os.path.join(module_path, '..', so)

    if os.path.exists(dst):
        if force:
            os.unlink(dst)
        else:
            return

    #print 'ln -s %s %s' % (so_abspath, dst)
    os.symlink(so_abspath, dst)
