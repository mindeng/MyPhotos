#! /usr/bin/env python
# encoding: utf-8

import os
import sys

path = '你好'
print os.path.isfile(path)
print os.path.isfile(path.decode('utf-8'))

def parse_cmd_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p'
    )

    return parser.parse_args()

args = parse_cmd_args()
print vars(args)
print os.path.abspath(os.path.join(args.p, '哈哈'))
print os.path.abspath(os.path.join(path, '哈哈'))
print os.path.abspath(os.path.join(path.decode('utf-8'), u'哈哈'))
print os.path.abspath(os.path.join(path.decode('utf-8'), '哈哈'))
