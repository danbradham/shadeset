from contextlib import contextmanager
import maya.cmds as cmds


def get_shader(node):

    node_type = cmds.nodeType(node)

    if node_type == 'transform':
        shape = get_shape(node)
        if not shape:
            return
    elif node_type == 'mesh':
        shape = node

    try:
        shading_engine = cmds.listConnections(shape, type='shadingEngine')[0]
    except IndexError:
        raise Exception('{} is not attached to a shading engine'.format(shape))

    try:
        shader = cmds.listConnections(shading_engine + '.surfaceShader')[0]
    except IndexError:
        raise Exception('{} shadingEngine has no surfaceShader attached'.format(shading_engine))

    return shader


def get_shape(node):

    children = cmds.listRelatives(
        node,
        shapes=True,
        noIntermediate=True,
    )

    if not children:
        raise Exception('{} has no shape nodes')

    return children[0]


@contextmanager
def selection(*args, **kwargs):

    old_selection = cmds.ls(sl=True, long=True)
    try:
        cmds.select(*args, **kwargs)
        yield
    except:
        raise
    finally:
        cmds.select(old_selection)


def export_material(node, out_file):

    with selection(node):
        cmds.file(
            out_file,
            exportSelected=True,
            channels=True,
            expressions=True,
            shader=True,
            type='mayaBinary',
            force=True,
        )
