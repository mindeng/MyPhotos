#! /usr/bin/env python

import os
import filecmp
import shutil

def find_types(top, types = []):
    ret = set()
    for root, dirs, files in os.walk(top):
        for name in files:
            _, ext = os.path.splitext(name)
            if ext.lower() in types:
                path = os.path.join(root, name)
                ret.add(path)
    return ret

def find_not_existed(top, target_files=[]):
    found = set()
    names = [(p, os.path.basename(p)) for p in target_files]
    for root, dirs, files in os.walk(top):
        for name in files:
            path = os.path.join(root, name)
            for i in names:
                if name == i[1] and filecmp.cmp(path, i[0]):
                    #print 'Found %s == %s' % (path, i[0])
                    found.add(i[0])
                    break
    print 'Imported files:', len(found)
    #output(found, '/tmp/2')
    #print found.issubset(set(target_files))
    return set(target_files) - found

def output(lines, path):
    with open(path, 'w') as f:
        for line in lines:
            f.write(line+'\n')

def cp_files(files, dst):
    copied_num = 0
    for path in files:
        name = os.path.basename(path)
        dst_file = os.path.join(dst, name)
        if os.path.exists(dst_file):
            if filecmp.cmp(path, dst_file):
                print 'Ingore repeated files %s' % path
                continue
            else:
                while os.path.exists(dst_file):
                    raw_name, ext = os.path.splitext(dst_file)
                    dst_file = '%s%s%s' % (raw_name, '_1', ext)
                print 'Files with same name, rename %s to %s' % (name, os.path.basename(dst_file))
        shutil.copy2(path, dst_file)
        copied_num += 1
    print 'Copied files:', copied_num

if __name__ == '__main__':
    import sys
    path1 = sys.argv[1]
    path2 = sys.argv[2]
    types = set(['.mov', '.mp4'])
    #types = set(['.mp4'])
    found_files = find_types(path1, types)
    print 'Target files:', len(found_files)
    #output(found_files, '/tmp/1')

    non_matched = find_not_existed(path2, found_files)
    print 'Not imported files:', len(non_matched)
    files_with_size = [(f, os.path.getsize(f)) for f in non_matched]
    files_with_size.sort(key=lambda i: i[1], reverse=True)
    output_list = ['%s %.2fK' % (i[0], i[1]/1024.0) for i in files_with_size]
    output(output_list, '/tmp/not-imported.txt')

    if len(sys.argv) >= 4:
        dst = sys.argv[3]
        cp_files(non_matched, dst)

