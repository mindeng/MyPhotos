#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import unittest
import exiftool
import warnings
import os

import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 

from media import *

class TestMedia(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_get_metadata(self):
        expected_data = [
                {
                    u"name": u"20110606005.mp4", 
                    u"make": None, 
                    u"date": u"2011-06-05 16:22:33", 
                    u"path": u"./test/20110606005.mp4", 
                    u"model": None, 
                    u"mime_type": u"video/mp4", 
                    u"size": 2185392
                    },

                {
                    u"name": u"ST830862.JPG", 
                    u"make": u"SAMSUNG TECHWIN CO., LTD.", 
                    u"date": u"2008-10-01 16:32:36", 
                    u"path": u"./test/ST830862.JPG", 
                    u"model": u"VLUU L83T/ Samsung L83T", 
                    u"mime_type": u"image/jpeg", 
                    u"size": 2927536
                    },
                ]
        script_path = os.path.dirname(__file__)
        for d in expected_data:
            path = os.path.join(script_path, d['name'])
            self.assertTrue(os.path.exists(path))

            mf = MediaFile(path=path)
            self.assertEqual(mf.tojson(), d)

            self.assertEqual(mf, MediaFile(path=path))

            if path.endswith('JPG'):
                print 'test eq'
                other = os.path.join(script_path, 'ST830862-dup.JPG')
                self.assertEqual(mf, MediaFile(path=other))

            other = os.path.join(script_path, '20110111259.jpg')
            self.assertNotEqual(mf, MediaFile(path=other))

if __name__ == '__main__':
    unittest.main()
