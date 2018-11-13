# -*- coding: utf-8 -*-

from .models import ShadeSet
from .utils import selection, get_shapes_in_hierarchy
from maya import cmds

__all__ = [
    'gather',
    'gather_hierarchy',
    'load',
    'register_subset',
    'unregister_subset',
    'clear_registry']


def gather(**kwargs):
    '''Gather shading data from a scene using the registered
    :class:`Subset` s. Returns a new :class:`ShadeSet` object containing
    the gathered data.

    :param selection: if True gather shading data for the selected transforms
    :param render_layers: if True gather shading data for all render layers
    '''

    return ShadeSet.gather(**kwargs)


def gather_hierarchy(**kwargs):
    '''Gather shading data from the selected hierarchy

    :param render_layers: if True gather shading data for all render layers
    '''

    kwargs['selection'] = True

    selected = cmds.ls(sl=True, long=True, transforms=True)
    shapes = []
    for node in selected:
        shapes.extend(get_shapes_in_hierarchy(node))

    with selection(shapes):
        shade_set = ShadeSet.gather(**kwargs)

    return shade_set


def load(shade_path):
    '''Load a :class:`ShadeSet` from disk.

    :param shade_path: Path to shadeset.yml file
    '''

    return ShadeSet.load(shade_path)


def save(shade_set, outdir, name):
    '''Save a :class:`Shadeset` to disk.

    :shade_set: :class:`ShadeSet` instance to save
    :param outdir: Output directory of shadeset
    :param name: basename of shadeset
    '''

    shade_set.export(outdir, name)


def register_subset(subset):
    '''Register a subset derived from :class:`SubSet`'''

    ShadeSet.registry.add(subset)


def unregister_subset(subset):
    '''Unregister a subset derived from :class:`SubSet`'''

    ShadeSet.registry.discard(subset)


def clear_registry():
    '''Unregister all :class:`SubSet`s'''

    ShadeSet.registry.clear()
