# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Standard library imports
from itertools import cycle

# Third party imports
from maya import cmds, mel

# Local imports
from . import materials
from .ui import res


try:
    basestring
except NameError:
    basestring = (str, bytes)

missing = object()


class Clipboard:
    shadesets = []
    materials = []


def log(message, details=None):
    '''Show a message in the active viewport and log to console.'''

    # Show message in viewport
    cmds.inViewMessage(
        amg=message,
        pos='midCenter',
        fade=True,
    )

    # Log message and details to script editor
    print('shadeset: %s' % message)
    if details:
        print(details)


def get_selected_transforms(default=missing):
    '''Convenience method to get selected transforms or a default value.'''

    selection = cmds.ls(selection=True, long=True, transforms=True)
    if selection:
        return selection

    if default is missing:
        return []

    if isinstance(default, basestring):
        return cmds.ls(default, long=True, transforms=True)

    return default


def copy_shadeset(objects=missing):
    '''Copy shadesets from selected hierarchies to clipboard.'''

    selection = get_selected_transforms(objects)

    # Clear shadeset clipboard
    Clipboard.shadesets[:] = []

    # Collect assignments and append to clipboard
    for root in selection:
        shadeset = materials.collect_material_assignments(root)
        Clipboard.shadesets.append(shadeset)

    message = [
        'Nothing selected.',
        'Copied Shadeset to clipboard.',
        'Copied %d Shadesets to clipboard' % len(Clipboard.shadesets)
    ][min(len(Clipboard.shadesets), 2)]
    log(message)

def paste_shadeset(objects=missing):
    '''Paste shadesets from clipboard to selected hierarchies.'''

    selection = get_selected_transforms(objects)

    for shadeset, root in zip(cycle(Clipboard.shadesets), selection):
        materials.apply_material_assignments(shadeset, root)

    message = [
        'Nothing selected.',
        'Applied Shadest from clipboard.',
        'Applied %d Shadesets to %d hierarchies.' % (
            len(Clipboard.shadesets), len(selection)
        ),
    ][min(len(selection), 2)]
    log(message)


def copy_materials(objects=missing):
    '''Copies material from selected objects to clipboard.'''

    selection = get_selected_transforms(objects)

    # Clear shadeset clipboard
    Clipboard.materials[:] = []

    for src in selection:
        shading_engine = materials.get_shading_engine(src)
        if shading_engine:
            Clipboard.materials.append(shading_engine)

    message = [
        'Nothing selected.',
        'Copied material to clipboard.',
        'Copied %d materials to clipboard.' % len(Clipboard.materials)
    ][min(len(Clipboard.materials), 2)]
    log(
        message,
        details=Clipboard.materials
    )


def paste_materials(objects=missing):
    '''Apply materials from clipboard to selected objects.'''

    selection = get_selected_transforms(objects)

    results = []
    for shading_engine, dst in zip(cycle(Clipboard.materials), selection):
        dst_shape = materials.get_shape(dst)
        if not dst_shape:
            continue

        materials.assign_shading_engine(
            shading_engine,
            [dst_shape],
        )
        results.append('Assigned %s -> %s' % (shading_engine, dst_shape))

    message = [
        'Nothing selected.',
        'Applied Material from clipboard.',
        'Applied %d Materials to %d objects.' % (
            len(Clipboard.materials), len(selection)
        ),
    ][min(len(selection), 2)]
    log(
        message,
        details='\n'.join(results),
    )


def export_shadeset(objects=missing):
    selection = get_selected_transforms(objects)

    log('Export Shadeset')


def import_shadeset(objects=missing):
    selection = get_selected_transforms(objects)

    log('Apply Shadeset')


def is_menu_available(node):
    if not node:
        return False

    node_type = cmds.nodeType(node)
    acceptable_node_types = [
        'transform',
        'mesh',
        'nurbsSurface',
        'aiStandin',
        'gpuCache',
    ]
    if node_type not in acceptable_node_types:
        return False

    return not cmds.listRelatives(node, shapes=True, type='mayaUsdProxyShape')


def create_tools_outliner_menu(outline_editor):
    '''Create the Tools menu within the Outliner. This function should be used
    as a callback for the mel proc OutlinerEdMenuCommand.'''
    print('shadeset: create_tools_outliner_menu')

    outline_editor_menu = outline_editor + 'Popup'
    outliner_item = cmds.outlinerEditor(
        outline_editor,
        query=True,
        feedbackItemName=True,
    )

    if outliner_item and is_menu_available(outliner_item):
        cmds.menuItem(divider=True)
        mel.eval('buildShaderMenus("%s")' % outliner_item)

    outliner_menu_name = outline_editor_menu + 'Shadeset'
    create_tools_menu(outline_editor, outliner_item, outliner_menu_name)


def create_tools_dag_menu(parent, item):
    '''Create the tools menu within the dagMenuProc. This function should be
    used as a callback for the mel proc dagMenuProc.'''
    print('shadeset: create_tools_dag_menu')

    dag_proc_menu_name = parent + 'Shadeset'
    create_tools_menu(parent, item, dag_proc_menu_name)


def create_tools_menu(parent, item, menu_name=None):
    '''Create the Shadeset Tools Menu.

    Shadeset_________________________
        |  |Copy Shadeset            |
        |  |Paste Shadeset           |
         ----------------------------
        |  |Copy Materials           |
        |  |Paste Materials          |
        |----------------------------|
        |  |Export Shadeset          |
        |  |Apply Shadeset           |
         ----------------------------
    '''

    print(parent, item, menu_name)

    # Validate item selection
    if not is_menu_available(item):
        return

    # Clean up existing menu
    if menu_name and cmds.menuItem(menu_name, exists=True):
        cmds.deleteUI(menu_name, menuItem=True)
        menu_args = (menu_name,)
    else:
        menu_args = ()

    # Build menu
    cmds.menuItem(divider=True)

    cmds.menuItem(
        *menu_args,
        **dict(
            label='Shadeset',
            image=res.get_path('shadeset.png'),
            subMenu=True,
        )
    )

    cmds.menuItem(
        label='Copy Shadesets',
        image=res.get_path('copy_shadeset.png'),
        command='shadeset.tools.copy_shadeset("%s")' % item,
        sourceType='python',
        annotation=(
            'Copy shading assignments from selected hierarchies to clipboard.'
        ),
    )
    cmds.menuItem(
        label='Paste Shadesets',
        image=res.get_path('paste_shadeset.png'),
        command='shadeset.tools.paste_shadeset("%s")' % item,
        sourceType='python',
        annotation=(
            'Apply shading assignments from clipboard to selected hierarchies.'
        ),
        enable=bool(Clipboard.shadesets),
    )

    cmds.menuItem(divider=True)

    cmds.menuItem(
        label='Copy Materials',
        image=res.get_path('copy_materials.png'),
        command='shadeset.tools.copy_materials("%s")' % item,
        sourceType='python',
        annotation='Copy materails assigned to selected objects to clipboard.',
    )
    cmds.menuItem(
        label='Paste Materials',
        image=res.get_path('paste_materials.png'),
        command='shadeset.tools.paste_materials("%s")' % item,
        sourceType='python',
        enable=bool(Clipboard.materials),
        annotation='Apply materials from clipboard to selected objects.'
    )

    cmds.menuItem(divider=True)

    cmds.menuItem(
        label='Export Shadeset',
        image=res.get_path('export_shadeset.png'),
        command='shadeset.tools.export_shadeset()',
        sourceType='python',
    )
    cmds.menuItem(
        label='Apply Shadeset',
        image=res.get_path('import_shadeset.png'),
        command='shadeset.tools.apply()',
        sourceType='python',
    )

    cmds.setParent('..', menu=True)
