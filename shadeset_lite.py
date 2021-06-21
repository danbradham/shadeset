# -*- coding: utf-8 -*-
'''
shadeset lite
-------------
'''

# Standard library imports
import json
import re
from itertools import cycle

# Third party imports
from maya import cmds


CLIPBOARD = {'assignments': []}


def copy_shading_assignments():
    '''Copy shading assignments from selected hierarchies to clipboard.'''

    CLIPBOARD['assignments'][:] = []
    for root in get_selected():
        CLIPBOARD['assignments'].append(collect_shading_assignments(root))


def paste_shading_assignments():
    '''Apply shading assignments from clipboard to selected hierarchies.'''

    if not CLIPBOARD['assignments']:
        print('Clipboard empty...')
        return

    roots = get_selected()
    for assignments, root in zip(cycle(CLIPBOARD['assignments']), roots):
        apply_shading_assignments(root, assignments)


def get_selected():
    '''Get selected dag nodes.'''

    return cmds.ls(selection=True, dag=True, long=True)


def get_hierarchy(root):
    '''Get a list all child dag nodes under root.'''

    return cmds.ls(
        root,
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


def get_relative_paths(paths, root, root_replacment='<root>'):
    '''Get a list of dag paths relative to a root path.'''

    results = []
    for path in paths:
        if not path.startswith(root):
            results.append(path)
        else:
            results.append(path.replace(root, root_replacement, 1))
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


def collect_shading_assignments(root):
    '''Get a dict of shading assignments under a root dag node.

    Returns:
        dict containing shadingEngine and member list pairs.

            {
                'aiStandardSurface1': [
                    {'path': '<root>|pSphereShape1': 'components': []},
                    {'path': '<root>|pSphereShape2': 'components': ['f[3:5]']},
                ],
            }
    '''

    assignments = {}

    hierarchy = get_hierarchy(root)
    shading_engines = get_shading_engines(*hierarchy)

    for shading_engine in shading_engines:

        # Collect and sanitize members
        members = get_members(shading_engine)
        members = filter_members_in_hierarchy(members, hierarchy)
        members = get_relative_paths(members, root)
        members = remove_namespaces(members)
        members = format_members(members)
        assignments[shading_engine] = members

    return assignments


def find_member_in_hierarchy(root, member):
    results = []
    if '.' in member:
        obj, comp = member.split('.')
    else:
        obj, comp = member, ''

    if not root.endswith('|'):
        root = root + '|'

    pattern = obj.replace('<root>', '*')
    for match in cmds.ls(pattern, long=True, recursive=True):
        if not match.startswith(root):
            continue
        if comp:
            match = match + '.' + comp
        results.append(match)

    return results


def assign_shading_engine(shading_engine, members):
    cmds.sets(members, edit=True, forceElement=shading_engine)


def apply_shading_assignments(root, assignments):

    for shading_engine, members in assignments.items():
        for member in members:

            matches = find_member_in_hierarchy(root, member['path'])
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

            assign_shading_engine(shading_engine, assignees)


def serialize_assignments(assignments):
    return json.dumps(assignments, indent=True)


if __name__ == '__main__':
    assignments = collect_shading_assignments(get_selected()[0])
    print(serialize_assignments(assignments))
