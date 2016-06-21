import os
import uuid
from contextlib import contextmanager
import maya.cmds as cmds


def get_shape(node):
    '''Get a non-intermediate mesh shape from a transform

    :param node: Name of transform node
    '''

    children = cmds.listRelatives(
        node,
        shapes=True,
        noIntermediate=True,
        type='mesh',
        fullPath=True,
    )

    if not children:
        return

    return children[0]


@contextmanager
def selection(*args, **kwargs):
    '''Set a selection, then restore the previous selection afterward.

    usage::

        with selection('pSphere1'):
            # do something
    '''

    old_selection = cmds.ls(sl=True, long=True)
    try:
        cmds.select(*args, **kwargs)
        yield
    except:
        raise
    finally:
        cmds.select(old_selection)


def export_shader(nodes, out_file):
    '''Export the selected shader

    :param node: Name of maya shader to export
    :param out_file: Filepath of output maya file
    '''

    with selection(nodes, replace=True, noExpand=True):
        cmds.file(
            out_file,
            exportSelected=True,
            channels=True,
            expressions=True,
            shader=True,
            type='mayaBinary',
            force=True,
        )


def import_shader(in_file):
    '''Import a maya file containing a shader

    :param in_file: Filepath of maya file
    '''

    name = os.path.splitext(os.path.basename(in_file))[0]
    nodes = cmds.file(
        in_file,
        i=True,
        rdn=True,
        rpr=name,
        mergeNamespacesOnClash=False,
        ignoreVersion=True,
        rnn=True
    )
    return cmds.ls(nodes, materials=True)[0]


def reference_shader(in_file, namespace=None):
    '''Import a maya file containing a shader

    :param in_file: Filepath of maya file
    '''

    ref_found = False
    name = os.path.splitext(os.path.basename(in_file))[0]
    valid_name = name.replace('.', '_')
    if namespace:
        namespace = namespace + '_' + valid_name
    else:
        namespace = valid_name

    for ref in cmds.ls(references=True):
        path = cmds.referenceQuery(ref, filename=True)
        if os.path.abspath(path) == os.path.abspath(in_file):
            ref_found = True

    if not ref_found:
        cmds.file(in_file, reference=True, namespace=namespace)


def get_shader(node):
    '''Get the shader applied to a transform or mesh

    :param node: Transform or mesh shape
    '''

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


def node_from_id(_id):

    nodes = cmds.ls('*.meta_id', objectsOnly=True, recursive=True, long=True)
    for node in nodes:
        node_id = cmds.getAttr(node + '.meta_id')
        if str(node_id) == str(_id):
            return node


def add_id(node):

    attr = node + '.meta_id'
    if not cmds.objExists(attr):
        cmds.addAttr(node, ln='meta_id', dt='string')

    identifier = str(uuid.uuid1())
    cmds.setAttr(attr, identifier, type='string')

    return identifier


def get_shading_groups(node):
    '''Get the shader applied to a transform or mesh

    :param node: Transform or mesh shape
    '''

    node_type = cmds.nodeType(node)

    if node_type == 'transform':
        shape = get_shape(node)
        if not shape:
            return

    elif node_type == 'mesh':
        shape = node

    shading_engines = cmds.listConnections(shape, type='shadingEngine')
    return shading_engines


def strip_namespaces(nodes):
    for node in nodes:

        component = None
        if '.' in node:
            node, component = node.split('.')

        if ':' in node:
            no_namespace = str(node.split(':')[-1])
        else:
            no_namespace = str(node)

        if component:
            no_namespace = '.'.join([no_namespace, component])

        yield no_namespace


def short_names(nodes):
    shorts = []
    for node in strip_namespaces(nodes):
        if '|' in node:
            shorts.append(node.split('|')[-1])
        else:
            shorts.append(node)
    return shorts


def find_members(members):
    found = []
    for member in members:
        ms = cmds.ls(member, recursive=True, long=True)
        found.extend(ms)
    return found


def apply_shader(shape, shader):
    '''Apply a shader to the specified shape

    :param shape: Shape used in shader assignment
    :param shader: Shader to apply
    '''

    sg = cmds.listConnections(shader, type='shadingEngine')
    if not sg:
        sg = cmds.sets(name=shader + 'SG', renderable=True, nss=True)
        cmds.connectAttr(shader + '.outColor', sg + '.surfaceShader', f=True)
    else:
        sg = sg[0]

    if not cmds.sets(shape, isMember=sg):
        cmds.sets(shape, forceElement=sg)


def assign_shading_group(shading_group, members):
    cmds.sets(members, edit=True, forceElement=shading_group)
