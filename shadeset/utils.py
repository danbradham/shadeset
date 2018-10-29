# -*- coding: utf-8 -*-

import os
import uuid
from contextlib import contextmanager
from functools import wraps
import maya.cmds as cmds


def get_shapes_in_hierarchy(node):
    '''Get all valid shapes underneath the node

    :param node: Name of transform node'''

    shapes = set()

    children = cmds.ls(node, dag=True, type='transform', long=True)
    for child in children:
        shape = get_shape(child)
        if shape:
            shapes.add(shape)

    return list(shapes)


def get_parents(node):

    result = []

    parent = cmds.listRelatives(node, parent=True, fullPath=True)
    while parent:
        result.append(parent[0])
        parent = cmds.listRelatives(parent[0], parent=True, fullPath=True)

    return result


def get_shape(node):
    '''Get a non-intermediate mesh shape from a transform

    :param node: Name of transform node
    '''

    print(node)
    valid_types = ['mesh', 'nurbsSurface']
    if cmds.nodeType(node) in valid_types:
        node = cmds.listRelatives(node, parent=True, fullPath=True)

    for typ in valid_types:
        children = cmds.listRelatives(
            node,
            shapes=True,
            noIntermediate=True,
            type=typ,
            fullPath=True,
        )

        if children:
            return children[0]


def maintains_selection(fn):
    '''A Decorator that ensures maya selection before and after function
    execution is the same.
    '''
    @wraps(fn)
    def wrapper(*args, **kwargs):
        old_selection = cmds.ls(sl=True, long=True)
        result = fn(*args, **kwargs)
        cmds.select(old_selection, replace=True)
        return result
    return wrapper


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


def update_reference(ref_node, in_file, namespace=None):

    namespace = make_namespace(in_file, namespace)
    cmds.file(unloadReference=ref_node)
    cmds.file(cleanReference=ref_node)
    cmds.file(in_file, loadReference=ref_node)
    path = cmds.referenceQuery(ref_node, filename=True)
    cmds.file(path, edit=True, namespace=namespace)
    cmds.lockNode(ref_node, lock=False)
    cmds.rename(ref_node, namespace + 'RN')
    cmds.lockNode(namespace + 'RN', lock=True)


def reference_shader(in_file, namespace=None):
    '''Import a maya file containing a shader

    :param in_file: Filepath of maya file
    '''

    namespace = make_namespace(in_file, namespace)

    if not reference_in_scene(in_file):
        cmds.file(in_file, reference=True, namespace=namespace)


def make_namespace(in_file, namespace=None):
    name = os.path.splitext(os.path.basename(in_file))[0]
    valid_name = name.replace('.', '_')
    if namespace:
        namespace = namespace + '_' + valid_name
    else:
        namespace = valid_name
    return namespace.replace('_shadingGroups', '').upper()


def reference_in_scene(in_file):

    for ref in cmds.ls(references=True):
        path = cmds.referenceQuery(ref, filename=True)
        if os.path.abspath(path) == os.path.abspath(in_file):
            return True
    return False


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

    elif node_type in ['mesh', 'nurbsSurface']:
        shape = node

    shading_engines = cmds.listConnections(shape, type='shadingEngine')
    return shading_engines


def strip_namespaces(nodes):
    '''Fuck da namespaces'''

    return (strip_namespace(node) for node in nodes)


def strip_namespace(node):
    '''Fuck da namespace'''

    component = None
    if '.' in node:
        node, component = node.split('.')

    if ':' in node:
        no_namespace = str(node.split(':')[-1])
    else:
        no_namespace = str(node)

    if component:
        no_namespace = '.'.join([no_namespace, component])

    return no_namespace


def filter_bad_face_assignments(nodes):
    '''Removes bad face assignments.

    We consider a bad face assignment to be an assignment
    to every single face of a shape.

    For example if a an object has 10 faces, "node.f[0:9]", is a bad face
    assignment. We will just shorten this to "node".
    '''
    import re
    pattern = re.compile(r'\.f\[0:(\d+)\]$')

    shorts = []
    for node in nodes:
        match = pattern.search(node)
        if match:
            short_name = node.replace(match.group(0), '')
            end = int(match.group(1))
            num_faces = cmds.polyEvaluate(short_name, face=True)
            if end + 1 == num_faces:
                shorts.append(short_name)
                continue
        shorts.append(node)
    return shorts


def shorten_name(node):
    '''Shorten name, removing namespaces and hierarchical components'''

    if '|' in node:
        nodes = node.split('|')
        stripped = [strip_namespace(n) for n in nodes]
        return '|'.join(stripped)

    return strip_namespace(node)


def shorten_names(nodes):
    '''Shortens names, removing namespaces and hierarchical components'''

    return [shorten_name(node) for node in nodes]


def get_members(shading_group):
    '''Get all shading group members

    :param shading_group: Name of shadingEngine/Group
    '''

    return cmds.sets(shading_group, query=True)


def find_shape(shape):
    '''Find a shape node, or it's deformed shape '''

    match = cmds.ls(shape, recursive=True, long=True)
    if not match:
        match = cmds.ls(shape + '*', recursive=True, long=True)

    return match


def find_members(members):
    found = []
    for member in members:

        # Original lookup failed when Deformers were added in rig/animation
        # ms = cmds.ls(member, recursive=True, long=True)
        # if ms:
        #     found.extend(ms)
        #     continue

        # Cast a broader net
        parts = member.split('.')
        member = parts[0] + '*'
        if len(parts) == 2:
            component = parts[1]
            member += '.' + component
        if len(parts) > 2:
            raise NameError('Too many parts in name: ' + member)

        ms = cmds.ls(member, recursive=True, long=True)
        found.extend(ms)

    return found


def member_in_hierarchy(member, *candidates):
    for candidate in candidates:
        if candidate in get_parents(member):
            return True


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
        # force initial shading assignment first...
        cmds.sets(shape, edit=True, forceElement="initialShadingGroup")
        cmds.sets(shape, edit=True, forceElement=sg)


def assign_shading_group(shading_group, members):
    if not members:
        # TODO log no members
        return
    cmds.sets(members, edit=True, forceElement=shading_group)


def get_prefixed_attrs(node, prefix):
    '''Get all node attributes with the specified prefix'''

    return [attr for attr in cmds.listAttr(node) if attr.startswith(prefix)]


def get_enum_options(node, attr):
    '''Get enum options'''

    return cmds.attributeQuery(attr, node=node, listEnum=True)


def get_child_attrs(node, attr):
    '''Get child attribute data'''

    children = cmds.attributeQuery(attr, node=node, listChildren=True)
    if not children:
        return
    return [
        dict(
            name=c,
            type=cmds.getAttr(node + '.' + c, type=True),
            keyable=cmds.attributeQuery(c, node=node, keyable=True)
        )
        for c in children
    ]


def get_attr_data(node, attr):
    '''Gets data for attribute'''

    path = node + '.' + attr
    if cmds.objExists(path):
        children = get_child_attrs(node, attr)
        value = cmds.getAttr(path)
        if isinstance(value, list):
            value = value[0]
        return dict(
            name=attr,
            value=value,
            type=cmds.getAttr(path, type=True),
            short=cmds.attributeName(path, short=True),
            nice=cmds.attributeName(path, nice=True),
            compound=bool(children),
            children=children,
            options=get_enum_options(node, attr),
            keyable=cmds.attributeQuery(attr, node=node, keyable=True)
        )


def add_attr_kwargs(attr_data):
    '''Get kwargs suitable for adding an attribute'''

    type_flag = 'at'
    dt_attrs = [
        'matrix', 'string', 'stringArray', 'doubleArray', 'Int32Array',
        'reflectance', 'spectrum', 'float2', 'float3', 'double2',
        'double3', 'long2', 'long3', 'short2', 'short3', 'vectorArray',
        'nurbsCurve', 'nurbsSurface', 'mesh', 'lattice', 'pointArray'
    ]
    if attr_data['type'] in dt_attrs:
        type_flag = 'dt'
    if attr_data['compound']:
        type_flag = 'at'

    kwargs = dict(
        longName=attr_data['name'],
        shortName=attr_data['short'],
        niceName=attr_data['nice'],
        keyable=attr_data['keyable']
    )
    kwargs[type_flag] = attr_data['type']

    if attr_data['options']:
        kwargs['enumName'] = ':'.join(attr_data['options'])

    return kwargs


def unpackable(attr_data):
    unpackable_types = [
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray'
    ]
    return attr_data['type'] in unpackable_types


def typeable(attr_data):
    typeable_attrs = [
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray', 'string', 'byte'
    ]
    return attr_data['type'] in typeable_attrs


def set_attr_data(node, attr_data):
    '''Sets an attribute from data retrieved by get_attr_data'''

    path = node + '.' + attr_data['name']
    if not cmds.objExists(path):
        kwargs = add_attr_kwargs(attr_data)
        cmds.addAttr(node, **kwargs)
        if attr_data['children']:
            for child in attr_data['children']:
                cmds.addAttr(
                    node,
                    ln=child['name'],
                    at=child['type'],
                    keyable=child['keyable'],
                    parent=attr_data['name']
                )
    args = [path]
    if unpackable(attr_data):
        args.extend(attr_data['value'])
    else:
        args.append(attr_data['value'])

    kwargs = {}
    if typeable(attr_data):
        kwargs['type'] = attr_data['type']
    try:
        cmds.setAttr(*args, **kwargs)
    except RuntimeError as e:
        if 'locked or connected' in str(e):
            cmds.warning(str(e).split(':', 1)[-1].rstrip())
