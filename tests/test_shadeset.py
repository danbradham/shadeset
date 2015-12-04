# -*- coding: utf-8 -*-

import unittest
from maya import standalone, cmds
from shadeset import ShadeSet


class TestShadeSet(unittest.TestCase):

    def setUp(self):
        try:
            standalone.initialize()
        except:
            pass
        self.sample_scene = "Z:/Active_Projects/15-133-FORD_Q1_EVENT/SEQUENCES/sandbox/RND/Lighting/MAYA/WORK/lgt_RND_matlib.v001.ma"

    def test_gather(self):

        cmds.file(self.sample_scene, open=True)
        cmds.select('*_sphere')
        shade_set = ShadeSet.gather(selection=True, render_layers=False)
        import pprint
        pprint.pprint(shade_set)
