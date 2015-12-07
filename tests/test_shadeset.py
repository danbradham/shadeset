# -*- coding: utf-8 -*-
import unittest
from . import data_path
from shadeset import ShadeSet
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
