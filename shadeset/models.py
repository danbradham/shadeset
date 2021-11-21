# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Standard library imports
import os
import shutil
from collections import defaultdict

# Third party imports
from maya import cmds

# Local imports
from . import library
from .decorators import maintains_selection
from .packages import yaml


class ShadeSet(dict):
    '''A dictionary subclass used to gather, export, and load shading data.

    Arguments:
        path (str): Path to shadeset yml file.

    Examples:
        Gather and export from scene::

            >>> look = ShadeSet.gather()
            >>> look.export('some/folder/look_v001.yml')

        Load and apply a shadeset from a file::

            >>> look = Shadeset.load('some/folder/look_v001.yml')
            >>> look.reference()
            >>> look.apply()
    '''

    registry = set()

    def __init__(self, path=None, *args, **kwargs):

        # Init instance path when provided
        self.path = path
        self.root = None
        self.name = None
        if self.path:
            self.root = os.path.dirname(self.path)
            self.name = os.path.splitext(os.path.basename(self.path))[0]

        # Init dict
        super(ShadeSet, self).__init__(*args, **kwargs)

    def relative(self, path):
        '''Get a file path relative to this Shadeset.'''

        return os.path.join(self.root, path)

    @classmethod
    def load(cls, shade_path):
        '''Load scene shading data from an exported shadeset'''

        with open(shade_path, 'r') as f:
            shade_data = yaml.load(f.read())

        if shade_data.get('schema_version') is None:
            # TODO: Migrate schema to latest
            pass

        return cls(shade_path, shade_data)

    @classmethod
    def gather(cls, selection=True, render_layers=False):
        '''Gather shading data from a scene using all registered
        `Subsets`.

        Arguments:
            selection (bool): Gather shading data for the selected transforms

        Returns:
            ShadeSet object containing the gathered shading data.
        '''

        shade_set = cls()

        if render_layers:
            layers_data = defaultdict(dict)

            with RenderLayers(RenderLayer.names()) as layers:

                for layer in layers:
                    layer.activate()

                    for subset in cls.registry:
                        data = subset.gather(selection=selection)
                        layers_data[layer.name].update(data)

            if layers_data:
                shade_set['render_layers'] = dict(layers_data)

        for subset in cls.registry:
            data = subset.gather(selection=selection)
            shade_set.update(data)

        return shade_set

    @maintains_selection
    def reference(self):
        '''Reference subset dependencies.'''

        for subset in self.registry:
            subset.reference(self)

    @maintains_selection
    def import_(self):
        '''Import subset dependencies.'''

        for subset in self.registry:
            subset.import_(self)

    @maintains_selection
    def apply(self, selection=False, render_layers=False):
        '''Apply this `ShadeSet` to the currently opened scene'''

        for subset in self.registry:
            subset.apply(self, selection=selection)

        if not render_layers:
            return

        render_layers = self.get('render_layers', None)
        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:

                    if not layer.exists:
                        layer.create()
                    layer.activate()

                    for subset in self.registry:
                        subset.apply(
                            render_layers[layer.name],
                            selection=selection
                        )

    @maintains_selection
    def export(self, outdir, name):
        '''Export this `ShadeSet` to a directory

        Arguments:
            outdir (str): Output directory
            name (str): Basename of output files
        '''

        if not os.path.exists(outdir):
            os.makedirs(outdir)

        self._export(outdir, name)

    def _export(self, outdir, name):
        '''Export subsets by calling their `export` method.'''

        for subset in self.registry:
            subset.export(self, outdir, name)

        shade_path = os.path.join(outdir, name + '.yml')
        encoded = yaml.safe_dump(dict(self), default_flow_style=False)

        with open(shade_path, 'w') as f:
            f.write(encoded)


class SubSet(object):
    '''Base class for all subsets of shading data.'''

    def gather(self, selection):
        raise NotImplementedError()

    def import_(self, shade_set):
        pass

    def reference(self, shade_set):
        pass

    def export(self, shade_set, outdir, name):
        pass

    def apply(self, shade_set, selection=False):
        raise NotImplementedError()
