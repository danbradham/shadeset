# -*- coding: utf-8 -*-

from .models import ShadeSet
from .utils import selection, get_shapes_in_hierarchy
from maya import cmds

__all__ = ['gather', 'load', 'register_subset', 'unregister_subset']


def gather(**kwargs):
    '''Gather shading data from a scene using the registered
    :class:`Subset` s. Returns a new :class:`ShadeSet` object containing
    the gathered data.

    :param selection: if True gather shading data for the selected transforms
    :param render_layers: if True gather shading data for all render layers
    '''

    return ShadeSet.gather(**kwargs)


def load(shade_path):
    '''Load a :class:`ShadeSet` from disk.

    :param shade_path: Path to shadeset.yml file
    '''

    return ShadeSet.load(shade_path)


def gather_hierarchy(**kwargs):
    '''Gather shadeing data from the selected hierarchy

    :param render_layers: if True gather shading data for all render layers
    '''

    selected = cmds.ls(sl=True, long=True, transforms=True)
    shapes = []
    for node in selected:
        shapes.extend(get_shapes_in_hierarchy(node))

    with selection(shapes):
        ss = ShadeSet.gather(selection=True, **kwargs)

    return ss


def load_hierarchy(shade_path):
    '''Load a :class:`ShadeSet` from disk, only under the selected hierarchy.

    :param shade_path: Path to shadeset.yml file
    '''

    pass


def register_subset(subset):
    '''Register a subset derived from :class:`SubSet`'''

    ShadeSet.registry.add(subset)


def unregister_subset(subset):
    '''Unregister a subset derived from :class:`SubSet`'''

    ShadeSet.registry.discard(subset)


def clear_registry():
    '''Unregister all :class:`SubSet`s'''

    ShadeSet.registry.clear()
