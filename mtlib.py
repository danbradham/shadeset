# -*- coding: utf-8 -*-
from __future__ import print_function

# Standard library imports
from itertools import cycle

# Third party imports
from maya import cmds


VALID_SHAPES = ('mesh', 'nurbsSurface', 'aiStandIn', 'gpuCache')
CLIPBOARD = []


def is_valid_shape(shape):
    return cmds.nodeType(shape) in VALID_SHAPES


def clear_clipboard():
    CLIPBOARD[:] = []


def log(message, details=None):

    # Show message in viewport
    cmds.inViewMessage(
        amg=message,
        pos='midCenter',
        fade=True,
    )

    # Log message and details to script editor
    print('mtlib: %s' % message)
    if details:
        print(details)


def get_shading_engine(shape):
    shading_engines = cmds.listConnections(shape, type='shadingEngine')
    if shading_engines:
        return shading_engines[0]


def get_shape(xform):
    if is_valid_shape(xform):
        return xform
    shapes = cmds.listRelatives(
        xform,
        shapes=True,
        noIntermediate=True,
        fullPath=True,
    )
    if shapes and is_valid_shape(shapes[0]):
        return shapes[0]


def copy_paste_materials():
    '''Copy and paste materials between selected pairs.

    Given:
        Active Selection: [obj_a, obj_b, obj_c, obj_d]

    Then:
        Apply material from obj_a to obj_b
        Apply material from obj_c to obj_d
    '''

    selected = cmds.ls(sl=True, long=True)
    for src, dst in zip(selected[::2], selected[1::2]):

        src_shape = get_shape(src)
        dst_shape = get_shape(dst)
        if not src_shape or not dst_shape:
            continue

        shading_engine = get_shading_engine(src_shape)
        if not shading_engine:
            continue

        cmds.sets(
            dst_shape,
            edit=True,
            forceElement=shading_engine,
        )


def copy_material():
    '''Copies material from the selected object to clipboard.'''

    selected = cmds.ls(sl=True, long=True)
    if not selected:
        raise RuntimeError('Please make an object selection first.')

    clear_clipboard()

    for src in selected:
        src_shape = get_shape(src)
        if src_shape:
            shading_engine = get_shading_engine(src_shape)
        else:
            shading_engine = get_shading_engine(src)

        if shading_engine:
            CLIPBOARD.append(shading_engine)

    if not CLIPBOARD:
        return

    log(
        message=[
            'Copied %s to clipboard.' % CLIPBOARD[0],
            'Copied %s materials to clipboard.' % len(CLIPBOARD),
        ][len(CLIPBOARD) > 1],
        details=CLIPBOARD,
    )


def paste_material():
    '''Applies material from clipboard to selected objects.'''

    if not CLIPBOARD:
        return

    results = []
    selected = cmds.ls(sl=True, long=True)
    for shading_engine, dst in zip(cycle(CLIPBOARD), selected):
        dst_shape = get_shape(dst)
        if not dst_shape:
            continue

        cmds.sets(
            dst_shape,
            edit=True,
            forceElement=shading_engine,
        )
        results.append('Assigned %s -> %s' % (shading_engine, dst_shape))

    log(
        message='Pasted %s materials to %s objects.' % (
            len(CLIPBOARD),
            len(selected),
        ),
        details=CLIPBOARD,
    )
