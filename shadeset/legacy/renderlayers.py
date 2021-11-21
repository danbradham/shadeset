# -*- coding: utf-8 -*-
from __future__ import print_function

from maya import cmds


class RenderLayer(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return str(self) == str(other)

    @property
    def exists(self):
        return self.name in self.names()

    def create(self):
        if self.exists:
            raise Exception('This layer already exists...')

        cmds.createRenderLayer(name=self.name, empty=True)

    def activate(self):
        cmds.editRenderLayerGlobals(currentRenderLayer=self.name)

    @property
    def members(self):
        return cmds.editRenderLayerMembers(self.name, q=True, fullNames=True)

    def remove_members(self, *members):
        args = [self.name] + list(members)
        cmds.editRenderLayerMembers(*args, remove=True)

    def add_members(self, *members):
        args = [self.name] + list(members)
        cmds.editRenderLayerMembers(*args, noRecurse=True)

    @classmethod
    def names(cls):
        return cmds.ls(type='renderLayer')

    @classmethod
    def all(cls):
        for layer in cls.names():
            return cls(layer)

    @classmethod
    def active(cls):
        return cls(cmds.editRenderLayerGlobals(crl=True, q=True))


@contextmanager
def RenderLayers(layers):
    '''Context manager that yields a RenderLayer generator. Restores the
    previously active render layer afterwards.'''

    old_layer = RenderLayer.active()

    try:
        yield (RenderLayer(layer) for layer in layers)
    finally:
        old_layer.activate()
