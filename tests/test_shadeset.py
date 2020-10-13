# -*- coding: utf-8 -*-
import unittest
import os
from shadeset import ShadeSet
from . import data_path
from maya import standalone, cmds


def setUpModule():
    standalone.initialize()


def tearDownModule():
    standalone.uninitialize()


class TestShadeSet(unittest.TestCase):

    def setUp(self):
        self.base_scene = data_path('base_scene.mb')
        self.noshader_scene = data_path('noshaders_scene.mb')

    def test_gather_selection(self):
        '''Test gather shadeset from selection'''

        cmds.file(self.base_scene, open=True)
        cmds.select('pSphere*')
        shade_set = ShadeSet.gather(selection=True, render_layers=False)
        expected_shade_set = {
            'geometry': {
                '|pSphere1': 'phongE1',
                '|pSphere2': 'phong1',
                '|pSphere3': 'blinn1',
                '|pSphere4': 'rampShader1',
                '|pSphere5': 'surfaceShader1'},
            'shaders': {
                'blinn1': 'shaders/blinn1.mb',
                'phong1': 'shaders/phong1.mb',
                'phongE1': 'shaders/phongE1.mb',
                'rampShader1': 'shaders/rampShader1.mb',
                'surfaceShader1': 'shaders/surfaceShader1.mb'}
        }
        assert shade_set == expected_shade_set

    def test_gather_noselection(self):
        '''Test gather shadeset no selection'''

        cmds.file(self.base_scene, open=True)
        shade_set = ShadeSet.gather(selection=False, render_layers=False)
        expected_shade_set = {
            'geometry': {
                '|pSphere1': 'phongE1',
                '|pSphere2': 'phong1',
                '|pSphere3': 'blinn1',
                '|pSphere4': 'rampShader1',
                '|pSphere5': 'surfaceShader1'},
            'shaders': {
                'blinn1': 'shaders/blinn1.mb',
                'phong1': 'shaders/phong1.mb',
                'phongE1': 'shaders/phongE1.mb',
                'rampShader1': 'shaders/rampShader1.mb',
                'surfaceShader1': 'shaders/surfaceShader1.mb'}
        }
        assert shade_set == expected_shade_set

    def test_gather_noshaders(self):
        '''Test gather shadeset with no shaders'''

        cmds.file(self.noshader_scene, open=True)
        cmds.select('pSphere*')
        shade_set = ShadeSet.gather(selection=True, render_layers=False)
        expected_shade_set = {
            'geometry': {
                '|pSphere1': 'lambert1',
                '|pSphere2': 'lambert1',
                '|pSphere3': 'lambert1',
                '|pSphere4': 'lambert1',
                '|pSphere5': 'lambert1'},
            'shaders': {'lambert1': 'shaders/lambert1.mb'}
        }
        assert shade_set == expected_shade_set

    def test_round_trip(self):
        '''Test shadeset round-trip'''

        cmds.file(self.base_scene, open=True)
        cmds.select('pSphere*')
        pre_shade_set = ShadeSet.gather(selection=True, render_layers=False)
        export_path = data_path('testset')
        pre_shade_set.export(export_path)

        expected_files = (
            data_path('testset', 'shadeset.yml'),
            data_path('testset', 'shaders', 'phongE1.mb'),
            data_path('testset', 'shaders', 'phong1.mb'),
            data_path('testset', 'shaders', 'blinn1.mb'),
            data_path('testset', 'shaders', 'rampShader1.mb'),
            data_path('testset', 'shaders', 'surfaceShader1.mb'),
        )

        assert all([os.path.exists(f) for f in expected_files])

        cmds.file(self.noshader_scene, open=True)
        shade_set = ShadeSet.load(data_path('testset'))

        assert pre_shade_set == shade_set

        shade_set.apply()

        cmds.select('pSphere*', replace=True)
        post_shade_set = ShadeSet.gather(selection=True, render_layers=False)

        assert pre_shade_set == post_shade_set
