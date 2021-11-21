# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

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

VALID_SHAPES = ('mesh', 'nurbsSurface', 'aiStandIn', 'gpuCache')


def is_valid_shape(shape):
    return cmds.nodeType(shape) in VALID_SHAPES


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


def get_selected():
    '''Get selected dag nodes.'''

    return cmds.ls(selection=True, dag=True, long=True)


def get_hierarchy(root):
    '''Get a list all child dag nodes under root.'''

    args = () if root == '|' else (root,)
    return cmds.ls(
        *args,
        **dict(
            dag=True,
            noIntermediate=True,
            long=True,
        )
    )


def get_shading_engine(node):
    shading_engines = cmds.ls(
        cmds.listHistory(node, future=True),
        type='shadingEngine',
    )
    if shading_engines:
        return shading_engines[0]


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
        # Only match direct descendants of root
        # pattern = root.rstrip('|') + '|' + path.partition('|')[-1]

        # Match deep
        pattern = '*|' + path.partition('|')[-1]

    for match in cmds.ls(pattern, long=True, recursive=True):
        if namespace and not match.rpartition('|')[-1].startswith(namespace):
            continue
        if not match.startswith(root.rstrip('|') + '|'):
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


def apply_material_assignments_v0(
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
                        '{}.{}'.format(match, comp)
                        for comp in member['components']
                    ])
            else:
                assignees = matches

            assign_shading_engine(matching_shading_engine, assignees)


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

    matched_member_assignments = defaultdict(list)
    best_shading_assignments = defaultdict(list)

    import json

    print('============ASSIGNMENTS=============')
    print(json.dumps(assignments, indent=4))

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

            for match in matches:
                matched_member_assignments[match].append({
                    'member': member,
                    'shadingEngine': shading_engine,
                })

    print('============MATCHED_MEMBER_ASSIGNMENTS=============')
    print(json.dumps(matched_member_assignments, indent=4))

    for path, assignments in matched_member_assignments.items():
        # The best assignment is the one that matches the most parts of
        # the path.
        best_assignment = max(
            assignments,
            key=lambda x: x['member']['path'].count('|')
        )

        # If there are multiple assignments matching the best path,
        # we are dealing with component assignments and we need to grab all
        # those assignments.
        best_path = best_assignment['member']['path']
        for assignment in assignments:
            if assignment['member']['path'] == best_path:
                best_shading_assignments[assignment['shadingEngine']].append({
                    'path': path,
                    'components': assignment['member']['components'],
                })

    print('============BEST_SHADING_ASSIGNMENTS=============')
    print(json.dumps(best_shading_assignments, indent=4))

    for shading_engine, members in best_shading_assignments.items():
        assignees = []
        for member in members:
            if member['components']:
                assignees.extend([
                    '{}.{}'.format(member['path'], comp)
                    for comp in member['components']
                ])
            else:
                assignees.append(member['path'])

        assign_shading_engine(shading_engine, assignees)
