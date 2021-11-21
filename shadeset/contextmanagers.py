# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Standard library imports
import contextlib

# Third party imports
from maya import cmds
import maya.api.OpenMaya as om


def MFnDependencyNode(node):
    sel = om.MSelectionList()
    sel.add(node)
    return om.MFnDependencyNode(sel.getDependNode(0))


@contextlib.contextmanager
def no_namespaces(nodes):
    '''
    Returns a context manager that removes namespaces from the provided
    nodes for the duration of a with block.
    '''

    mfns = [MFnDependencyNode(node) for node in nodes]
    old_names = [mfn.name() for mfn in mfns]
    tmp_names = [name.rpartition(':')[-1] for name in old_names]
    try:
        for mfn, tmp_name in zip(mfns, tmp_names):
            mfn.setName(tmp_name)
        yield
    finally:
        for mfn, old_name in zip(mfns, old_names):
            mfn.setName(old_name)


@contextlib.contextmanager
def selection(*args, **kwargs):
    '''
    Returns a context manager that sets the scene selection for the duration
    of the with block.
    '''

    old_selection = cmds.ls(sl=True, long=True)
    try:
        cmds.select(*args, **kwargs)
        yield
    finally:
        cmds.select(old_selection)


@contextlib.contextmanager
def undo_chunk():
    '''
    Returns a context manager that wraps the operations performed in a with
    block in an undoChunk.
    '''

    try:
        cmds.undoInfo(openChunk=True)
    finally:
        cmds.undoInfo(closeChunk=True)


@contextlib.contextmanager
def undo_on_error():
    '''
    Returns a context manager that undoes all operations performed in a with
    block if an exception occurs during execution.
    '''

    try:
        cmds.undoInfo(openChunk=True)
    except Exception:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()
        raise
    else:
        cmds.undoInfo(closeChunk=True)
