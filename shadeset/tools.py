# -*- coding: utf-8 -*-

# Third party imports
from maya import cmds

# Local imports
from .ui import res

class Clipboard:
    shadeset = None


def copy_shadeset():
    from . import api
    Clipboard.shadeset = api.gather_hierarchy()


def paste_shadeset():
    if Clipboard.shadeset:
        Clipboard.shadeset.apply(selection=True)


def create_outliner_menu(outline_editor):

    outline_editor_menu = outline_editor + 'Popup'
    object_name = cmds.outlinerEditor(
        outline_editor,
        query=True,
        feedbackItemName=True,
    )
    shadeset_menu = outline_editor_menu + 'Shadeset'

    if cmds.menuItem(shadeset_menu, exists=True):
        cmds.deleteUI(shadeset_menu, menuItem=True)

    node_type = cmds.nodeType(object_name)
    print('SHADESET OUTLINER MENU> ' + node_type)

    cmds.menuItem(
        shadeset_menu,
        label='Shadeset',
        image=res.get_path('shadesets_sm.png'),
        subMenu=True,
    )
    cmds.menuItem(
        label='Copy Shading Assignments',
        image=res.get_path('copy.png'),
        command='shadeset.tools.copy_shadeset()',
        sourceType='python',
    )
    if Clipboard.shadeset:
        cmds.menuItem(
            label='Paste Shading Assignments',
            image=res.get_path('paste.png'),
            command='shadeset.tools.paste_shadeset()',
            sourceType='python',
        )

    cmds.setParent('..', menu=True)
