# -*- coding: utf-8 -*-

from .models import ShadeSet
from .utils import selection, get_shapes_in_hierarchy
from maya import cmds

__all__ = [
    'clear_registry',
    'gather',
    'gather_hierarchy',
    'load',
    'register_subset',
    'unregister_subset',
]


def gather(**kwargs):
    '''Gather shading data from a scene using all registered
    `Subsets`.

    Arguments:
        selection (bool): Gather shading data for the selected transforms

    Returns:
        ShadeSet object containing the gathered shading data.
    '''

    return ShadeSet.gather(**kwargs)


def gather_hierarchy(**kwargs):
    '''Gather shading data from the selected hierarchy.'''

    kwargs['selection'] = True

    selected = cmds.ls(sl=True, long=True, transforms=True)
    shapes = []
    for node in selected:
        shapes.extend(get_shapes_in_hierarchy(node))

    with selection(shapes):
        shade_set = ShadeSet.gather(**kwargs)

    return shade_set


def load(shade_path):
    '''Load a ShadeSet from disk.

    Arguments:
        shade_path (str): Path to shadeset.yml file
    '''

    return ShadeSet.load(shade_path)


def save(shade_set, outdir, name):
    '''Save a Shadeset to disk.

    Arguments:
        shade_set (ShadeSet): shading data to save to write
        outdir (str): Output directory
        name (str): basename of Shadeset
    '''

    shade_set.export(outdir, name)


def register_subset(subset):
    '''Register a subset derived from SubSet'''

    ShadeSet.registry.add(subset)


def unregister_subset(subset):
    '''Unregister a subset derived from SubSet'''

    ShadeSet.registry.discard(subset)


def clear_registry():
    '''Unregister all SubSet'''

    ShadeSet.registry.clear()
