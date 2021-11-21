# -*- coding: utf-8 -*-
'''
shadeset lite
-------------
'''

# Standard library imports
from collections import defaultdict
import json
import re
import uuid

# Third party imports
from maya import cmds


try:
    basestring
except NameError:
    basestring = (str, bytes)


def get_selected():
    '''Get selected dag nodes.'''

    return cmds.ls(selection=True, dag=True, long=True)


def get_hierarchy(root):
    '''Get a list all child dag nodes under root.'''

    args = () if root == '|' else (root,)
    return cmds.ls(
        *args,
        dag=True,
        noIntermediate=True,
        long=True,
    )


def get_shading_engines(*nodes):
    '''Get a list of all shadingEngines assigned to nodes.'''

    return list(set(cmds.ls(
        cmds.listHistory(nodes, future=True),
        type='shadingEngine',
    )))


def get_members(shading_engine):
    '''Get a list of all members included in a shadingEngine.'''

    results = []
    members = cmds.ls(cmds.sets(shading_engine, query=True), long=True)
    for member in members:
        # Expand members with face assignments to their shape nodes
        if '.' in member:
            obj, comp = member.split('.')
            obj = cmds.ls(
                obj,
                long=True,
                dag=True,
                leaf=True,
                noIntermediate=True,
            )[0]
            member = obj + '.' + comp
        results.append(member)
    return results


def filter_members_in_hierarchy(members, hierarchy):
    '''Get a filtered list of members that are in a hierarchy.'''

    results = []
    for member in members:
        if member.split('.')[0] in hierarchy:
            results.append(member)
    return results


def get_relative_paths(paths, root):
    '''Get a list of dag paths relative to a root path.'''

    if '|' in root:
        anchor = root.rstrip('|').rpartition('|')[-1]

    results = []
    for path in paths:
        if path.startswith(root):
            path = path.replace(root, '', 1).lstrip('|')
            results.append(anchor + '|' + path)
        else:
            results.append(path)
    return results


def remove_namespaces(names):
    '''Get a list of names with namespaces removed.'''

    results = []
    for name in names:
        obj, comp = name, ''
        if '.' in name:
            obj, comp = name.split('.')

        obj = re.sub(r'[A-Za-z0-9_]+\:', '', obj)

        if comp:
            obj = obj + '.' + comp

        results.append(obj)

    return results


def format_members(members):
    '''Get a list of shadingEngine members.

    Returns:
        list of dicts with path and components keys. Path being the dag path to
        the set member and components being a list of faces like "f[5:10]".

            [{'path': str, 'components': [str...]}...]
    '''

    components_map = {}
    for member in members:
        if '.' in member:
            obj, comp = member.split('.')
            components_map.setdefault(obj, [])
            components_map[obj].append(comp)
        else:
            components_map.setdefault(member, [])

    return [{'path': k, 'components': v} for k, v in components_map.items()]


def get_uuid(path):
    '''Get the nodes uuid stored in an attributed named meta_uuid.'''

    attr = path + '.meta_uuid'

    if not cmds.objExists(attr):
        return

    return cmds.getAttr(attr)


def assign_uuid(path, force=False):
    '''Assign and return a uuid to an attribute named meta_uuid.'''

    attr = path + '.meta_uuid'

    if not cmds.objExists(attr):
        cmds.addAttr(path, ln='meta_uuid', dt='string')
        cmds.setAttr(attr, str(uuid.uuid4()), type='string')
        return cmds.getAttr(attr)

    if force:
        cmds.setAttr(attr, str(uuid.uuid4()), type='string')

    return cmds.getAttr(attr)


def collect_material_assignments(root, update_uuids=False):
    '''Get a dict of shading assignments under a root dag path.

    This method will add a meta_uuid attribute to the collected shadingEngines,
    making them easier to lookup in your scene.

    Arguments:
        root (str): Collect all material assignments under this dag path.
        update_uuids (bool): Assign new uuids to shadingEngines.

    Returns:
        Dict containing shadingEngines and their members.

    Example Return Value::

        {
            'aiStandardSurface1':
                'uuid': 'c398795d-aa03-48d0-8f33-4e7490e099dd',
                'members': [
                    {'path': '|geo|aShape1': 'components': []},
                    {'path': '|geo|bShape2': 'components': ['f[3:5]']},
                ],
        }
    '''

    results = {}
    hierarchy = get_hierarchy(root)
    shading_engines = get_shading_engines(*hierarchy)

    for shading_engine in shading_engines:

        # Collect and sanitize members
        members = get_members(shading_engine)
        members = filter_members_in_hierarchy(members, hierarchy)
        members = get_relative_paths(members, root)
        members = remove_namespaces(members)
        members = format_members(members)
        results[shading_engine] = {
            'meta_uuid': assign_uuid(shading_engine, force=update_uuids),
            'members': members,
        }

    return results


def find_matching_paths(path, root='|', namespace=None, strict=False):
    '''Find matching dag paths in the current scene.

    Arguments:
        path (str): Dag path to lookup.
        root (str): Get dag paths under this root path. Defaults to '|'.
        strict (bool): When strict is false, the first element of the path is
            removed, allowing members in hierarchies that match but may be
            under a different root path. Defaults to False.

    Returns:
        List of dag paths to matching members.
    '''

    results = []

    path = path.lstrip('|')
    if strict:
        pattern = '*|' + path
    else:
        pattern = '*|' + path.partition('|')[-1]

    for match in cmds.ls(pattern, long=True, recursive=True):
        if namespace and not match.rpartition('|')[-1].startswith(namespace):
            continue
        if not match.startswith(root):
            continue
        results.append(match)

    return results


def assign_shading_engine(shading_engine, members):
    '''Assign members to a shadingEngine.'''

    cmds.sets(members, edit=True, forceElement=shading_engine)


def find_shading_engine(shading_engine, uuid=None, namespace=None):
    '''Find a shadingEngine.

    Optionally provide a uuid for lookup and a namespace for filtering results.

    Arguments:
        shading_engine (str): Name of shadingEngine.
        uuid (str): UUID to match against the meta_uuid attribute.
        namespace (str): Namespace to lookup shadingEngines in.

    Returns:
        str: First matching shadingEngine.
    '''

    if namespace:
        name_lookup = namespace + shading_engine
        uuid_lookup = namespace + '*.meta_uuid'
    else:
        name_lookup = shading_engine
        uuid_lookup = '*.meta_uuid'

    name_matches = cmds.ls(name_lookup, recursive=True)
    if len(name_matches) == 1:
        return name_matches[0]

    uuid_matches = []
    if uuid:
        paths = cmds.ls(uuid_lookup, objectsOnly=True, recursive=True)
        for path in paths:
            path_uuid = get_uuid(path)
            if path_uuid == uuid:
                uuid_matches.append(path)
        if len(uuid_matches) == 1:
            return uuid_matches[0]

    if name_matches:
        return name_matches[0]

    if uuid_matches:
        return uuid_matches[0]


def apply_material_assignments(
    assignments,
    root='|',
    member_namespace=None,
    material_namespace=None,
    strict=False,
):
    '''Apply shadingEngines to members listed in an assignments dict.

    Arguments:
        assignments (dict): Like the results of collect_material_assignments
        root (str): Apply shadingEngines only to members found under this
            dag path. Defaults to '|' matching any node in the scene.
        strict (bool): When strict is False, the first element of the member is
            removed, allowing members in hierarchies that match but may be
            under a different root node. Defaults to False.
        member_namespace (str): Namespace containing shadingEngine set members.
        material_namespace (str): Namespace containing shadingEngines.
    '''

    for shading_engine, data in assignments.items():

        matching_shading_engine = find_shading_engine(
            shading_engine.rpartition(':')[-1],
            data['meta_uuid'],
            material_namespace,
        )
        if not shading_engine:
            print(
                'Warning: Could not find shadingEngine named %s.' %
                shading_engine
            )
            continue

        for member in data['members']:

            matches = find_matching_paths(
                member['path'],
                root,
                member_namespace,
                strict,
            )
            if not matches:
                continue

            if member['components']:
                assignees = []
                for match in matches:
                    assignees.extend([
                        f'{match}.{comp}'
                        for comp in member['components']
                    ])
            else:
                assignees = matches

            assign_shading_engine(matching_shading_engine, assignees)


def get_attr(path, attr):
    attr_path = path + '.' + attr
    if not cmds.attributeQuery(attr, node=path, exists=True):
        return

    value = cmds.getAttr(attr_path)
    if isinstance(value, list) and isinstance(value[0], tuple):
        value = value[0]

    return value


def get_type_kwarg_from_value(value):
    if not isinstance(value, (list, tuple)):
        value = [value]
    type_key = tuple([type(v) for v in value])
    return {
        (str,): {'dt': 'string'},
        (float,): {'at': 'double'},
        (float,float): {'at': 'double2'},
        (float,float,float): {'at': 'double3'},
        (int,): {'at': 'long'},
        (int,int): {'at': 'long2'},
        (int,int,int): {'at': 'long3'},
        (bool,): {'at': 'bool'},
    }.get(type_key)


def get_type_flag(type, compound=False):
    if compound:
        return 'attributeType'
    return ('attributeType', 'dataType')[type in {
        'matrix', 'string', 'stringArray', 'doubleArray', 'Int32Array',
        'reflectance', 'spectrum', 'float2', 'float3', 'double2',
        'double3', 'long2', 'long3', 'short2', 'short3', 'vectorArray',
        'nurbsCurve', 'nurbsSurface', 'mesh', 'lattice', 'pointArray'
    }]


def is_unpackable(type):
    return type in {
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray'
    }


def is_typeable(type):
    return type in {
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray', 'string', 'byte'
    }


def get_attr_schema(path, attr):
    if not cmds.attributeQuery(attr, node=path, exists=True):
        return

    children = []
    child_attrs = cmds.attributeQuery(attr, node=path, listChildren=True) or []
    for child_attr in child_attrs:
        children.append(
            {
                'type': cmds.getAttr(path + '.' + child_attr, type=True),
                'longName': child_attr,
                'keyable': cmds.attributeQuery(child_attr, node=path, k=True),
                'parent': attr,
            }
        )

    enumName = cmds.attributeQuery(attr, node=path, listEnum=True)
    if enumName:
        enumName = enumName[0]

    attr_path = path + '.' + attr
    return {
        'type': cmds.getAttr(attr_path, type=True),
        'longName': attr,
        'shortName': cmds.attributeName(attr_path, short=True),
        'niceName': cmds.attributeName(attr_path, nice=True),
        'children': children,
        'enumName': enumName,
        'keyable': (
            cmds.getAttr(attr_path, keyable=True) or
            cmds.getAttr(attr_path, channelBox=True)
        ),
        'usedAsColor': cmds.attributeQuery(attr, node=path, usedAsColor=True),
    }


def get_attrs_with_prefix(path, prefix):
    '''Get all attributes with the specified prefix'''

    return [attr for attr in cmds.listAttr(path) if attr.startswith(prefix)]


def collect_attributes(root, attributes, attribute_prefixes=None):
    '''Collect attributes from a hierarchy.

    Arguments:
        root (str): Root dag path.
        attributes (list): List of attributes to collect.
        attribute_prefixes (list): List of attribute_prefixes to collect.

    Returns:
        dict containing attribute schemas and attribute values by dag path.

    Example Return Value::

        {
            'schemas': {
                'visibility': {
                    'type': 'bool',
                    'type_option': 'attributeType',
                    'keyable': True,
                }
            },
            'values': {
                '|geo|aShape1': {
                    'visibility': True,
                }
            },
        }
    '''

    results = {'schemas': defaultdict(dict), 'values': defaultdict(dict)}

    attribute_prefixes = attribute_prefixes or []
    hierarchy = get_hierarchy(root)

    for path in hierarchy:
        clean_path = get_relative_paths([path], root)[0]
        clean_path = remove_namespaces([clean_path])[0]
        for attr in attributes:

            if attr not in results['schemas']:
                schema = get_attr_schema(path, attr)
                if schema:
                    results['schemas'][attr] = schema

            value = get_attr(path, attr)
            if value is not None:
                results['values'][clean_path][attr] = value

        for attr_prefix in attribute_prefixes:
            for attr in get_attrs_with_prefix(path, attr_prefix):

                if cmds.attributeQuery(attr, node=path, listParent=True):
                    # Skip child attributes assuming that the attributes
                    # parent will already be collected.
                    continue

                if attr not in results['schemas']:
                    schema = get_attr_schema(path, attr)
                    if schema:
                        results['schemas'][attr] = schema

                value = get_attr(path, attr)
                if value is not None:
                    results['values'][clean_path][attr] = value

    return results


def add_attr_from_schema(path, schema=None):

    # Setup schema for addAttr
    schema = dict(schema)
    children = schema.pop('children', [])
    attr_type = schema.pop('type')
    schema[get_type_flag(attr_type, compound=bool(children))] = attr_type
    if schema['enumName'] is None:
        schema.pop('enumName')

    # Add attribute
    cmds.addAttr(path, **schema)

    # Add child attributes
    for child in children:
        child_schema = dict(child)
        child_type = child_schema.pop('type')
        child_schema[get_type_flag(child_type)] = child_type
        cmds.addAttr(path, **child_schema)


def set_attr(path, attr, value, schema=None):
    args = [path + '.' + attr]
    kwargs = {}

    if schema:
        attr_type = schema['type']
        if is_unpackable(attr_type):
            args.extend(value)
        else:
            args.append(value)

        if is_typeable(attr_type):
            kwargs['type'] = schema['type']
    else:
        if isinstance(type, (list, tuple)):
            args.extend(value)
        else:
            args.append(value)
        if isinstance(type, basestring):
            kwargs['type'] = 'string'

    try:
        cmds.setAttr(*args, **kwargs)
    except RuntimeError as e:
        if 'locked or connected' in str(e):
            cmds.warning(str(e).split(':', 1)[-1].rstrip())


def apply_attributes(
    attributes,
    root='|',
    namespace=None,
    strict=False,
):
    '''Set attributes on dag paths listed in an attributes dict.

    Arguments:
        attributes (dict): Like the results of collect_attributes
        root (str): Apply shadingEngines only to members found under this
            dag path. Defaults to '|' matching any node in the scene.
        namespace (str): Namespace containing dag paths to set attrs on.
        strict (bool): When strict is False, the first element of a path is
            removed, allowing members in hierarchies that match but may be
            under a different root node. Defaults to False.
    '''

    for path, attrs in attributes['values'].items():

        matching_paths = find_matching_paths(path, root, namespace, strict)

        for attr, value in attrs.items():

            schema = attributes['schemas'].get(attr)

            for path in matching_paths:
                attr_path = path + '.' + attr
                if not cmds.attributeQuery(attr, node=path, exists=True):
                    if schema:
                        add_attr_from_schema(path, schema)
                    else:
                        kwargs = {'ln': attr, 'k': True}
                        kwargs.update(get_type_kwarg_from_value(value))
                        cmds.addAttr(path, **kwargs)

                set_attr(path, attr, value, schema)