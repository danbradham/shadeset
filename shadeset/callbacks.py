# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Standard library imports
from collections import defaultdict
import os
import re
import tempfile

# Third party imports
from maya import mel, cmds


# Initialize shared cache
# Ensures that within a maya session this module will operate on the same data.
# You can reload it, vendor it in other python packages, rename it, whatever.
if not hasattr(mel, '__MEL_FILE_CACHE__'):
    mel.__MEL_FILE_CACHE__ = {}
    mel.__MEL_PROC_CACHE__ = {}

MEL_FILE_CACHE = mel.__MEL_FILE_CACHE__
MEL_PROC_CACHE = mel.__MEL_PROC_CACHE__


def find_file_from_mel_proc(mel_proc):
    '''Looks up which file a mel procedure was defined in.'''

    if mel_proc in MEL_PROC_CACHE:
        return MEL_PROC_CACHE[mel_proc]['file']

    what_is_result = mel.eval('whatIs ' + mel_proc)
    if 'found in: ' in what_is_result:
        return what_is_result.split('found in: ')[-1]
    elif what_is_result == 'Unknown':
        raise Exception('Mel procedure is unknown.')
    else:
        raise Exception('Mel procedure is not defined in a file.')


def get_mel_file_data(mel_file):
    '''Reads a mel file and returns a dict containing the files contents,
    path, and dict of all procedures defined in the file.
    '''

    data = {
        'file': mel_file,
        'procs': {},
    }
    with open(mel_file, 'r') as f:
        data['contents'] = f.read()

    global_procs = re.findall(
        r'((global\s+)?proc\s+([A-Za-z0-9_]+)\s*\(.*\))[^\{]+\{',
        data['contents'],
    )
    for proc in global_procs:
        data['procs'][proc[2]] = {
            'name': proc[2],
            'global': 'global' in proc[1],
            'def': proc[0],
            'args': re.findall(r'\$\w+', proc[0]),
            'file': mel_file,
        }

    return data


def cache_mel_file(mel_file):
    '''Cache a mel file all of the procedures found in the file.'''

    mel_file_data = get_mel_file_data(mel_file)
    MEL_FILE_CACHE[mel_file] = mel_file_data
    MEL_PROC_CACHE.update(mel_file_data['procs'])
    return mel_file_data


def cache_mel_proc(mel_proc):
    '''Cache a mel procedure, it's file, and related procedures.'''

    mel_file = find_file_from_mel_proc(mel_proc)
    mel_file_data = get_mel_file_data(mel_file)
    MEL_FILE_CACHE[mel_file] = mel_file_data
    MEL_PROC_CACHE.update(mel_file_data['procs'])
    return MEL_PROC_CACHE.get(mel_proc)


def get_mel_proc(mel_proc):
    '''Get mel_proc data.'''

    if mel_proc not in MEL_PROC_CACHE:
        cache_mel_proc(mel_proc)

    return MEL_PROC_CACHE.get(mel_proc)


def get_mel_proc_file(mel_proc):
    '''Get mel_proc file data.'''

    if mel_proc not in MEL_PROC_CACHE:
        cache_mel_proc(mel_proc)

    return MEL_FILE_CACHE.get(MEL_PROC_CACHE[mel_proc]['file'])


def get_mel_proc_code(mel_proc, mel_file):

    if mel_proc.get('code'):
        return mel_proc['code']

    match = re.search(re.escape(mel_proc['def']), mel_file['contents'])
    if not match:
        raise Exception(
            'Could not find %s in %s.' % (mel_proc['name'], mel_proc['file'])
        )

    chars = []
    depth = 0
    entered_block = False
    for char in mel_file['contents'][match.end(0):]:
        if entered_block and depth == 0:
            break

        if char == '{':
            depth += 1
            entered_block = True
        if char == '}':
            depth -= 1

        chars.append(char)

    mel_proc['code'] = ''.join(chars)
    return mel_proc['code']


def globalize_mel_proc(proc):
    '''Globalize a mel procedure from the cache. This can be used after
    insert_mel_proc_callback to make local procs global. This is required
    by a procedure like dagMenuProc.
    '''

    mel_proc = get_mel_proc(proc)
    mel_file = get_mel_proc_file(proc)
    proc_code = mel_proc.get(
        'code_modified',
        get_mel_proc_code(mel_proc, mel_file),
    )
    def_modified = mel_proc.get('def_modified', '')

    if mel_proc['global'] or def_modified.startswith('global'):
        return

    print('shadeset: Globalizing ' + proc)
    mel_proc['def_modified'] = 'global ' + mel_proc['def']
    mel.eval(mel_proc['def_modified'] + proc_code)


def insert_mel_proc_callback(proc, hook, owner='PyCallbacks'):
    '''Insert `callbacks` hook into the desired mel procedure.

    This function uses the builtin mel callbacks command::
        callbacks -executeCallbacks -hook <hook> -owner <owner> $arg...
    '''

    mel_proc = get_mel_proc(proc)
    mel_file = get_mel_proc_file(proc)
    proc_code = get_mel_proc_code(mel_proc, mel_file)
    proc_code_modified = mel_proc.get('code_modified') or ''

    mel_callback = (
        'callbacks -executeCallbacks -hook "{hook}" -owner "{owner}" {args};'
    ).format(
        hook=hook,
        owner=owner,
        args=' '.join(mel_proc['args']),
    )

    if re.search(re.escape(mel_callback), proc_code_modified):
        print('shadeset: Callback already inserted...')
        return

    if proc_code_modified:
        proc_code_modified = '    {code}{callback}\n}}'.format(
            code=proc_code_modified.rpartition('}')[0],
            callback=mel_callback,
        )
    else:
        proc_code_modified = '    {code}{callback}\n}}'.format(
            code=proc_code.rpartition('}')[0],
            callback=mel_callback,
        )
    mel_proc['code_modified'] = proc_code_modified

    print('shadeset: Evaluating modified code of ' + proc)
    mel.eval(mel_proc['def'] + mel_proc['code_modified'])


def list_mel_proc_callbacks(mel_proc, hook=None, owner=None):
    '''List all registered python callbacs with a mel procedure.'''

    owner = owner or 'PyCallbacks'
    hook = hook or mel_proc + owner

    return cmds.callbacks(hook=hook, owner=owner, listCallbacks=True) or []


def register_mel_proc_callback(mel_proc, callback, hook=None, owner=None):
    '''Add python callback to a mel procedure.'''

    owner = owner or 'PyCallbacks'
    hook = hook or mel_proc + owner

    # Ensure hook is installed in mel procedure
    insert_mel_proc_callback(mel_proc, hook, owner)

    # Add callback
    if callback not in list_mel_proc_callbacks(mel_proc, hook, owner):
        cmds.callbacks(addCallback=callback, hook=hook, owner=owner)


def unregister_mel_proc_callback(mel_proc, callback, hook=None, owner=None):
    '''Remove a python callback from a mel procedure.'''

    owner = owner or 'PyCallbacks'
    hook = hook or mel_proc + owner

    if callback in list_mel_proc_callbacks(mel_proc, hook, owner):
        cmds.callbacks(removeCallback=callback, hook=hook, owner=owner)


def clear_mel_proc_callbacks(mel_proc, hook=None, owner=None):
    '''Clear all python callbacks from a mel procedure.'''

    owner = owner or 'PyCallbacks'
    hook = hook or mel_proc + owner

    cmds.callbacks(hook=hook, owner=owner, clearCallbacks=True)


class MelProcCallback(object):
    '''This class wraps the lower level `*_mel_proc_callback` functions
    to provide a simple interface for registering and unregistering python
    callbacks with a single Mel procedure.

    Behind the scenes, this class will insert a Mel `callbacks` call into a
    Mel Procedure and evaluate it in the global Mel namespace. Since we are
    not modifying any Mel files, just modifying and evaluating Mel procedures,
    this is all non-destructive.
    '''

    mel_proc = 'MelProcName'
    installed = False

    @classmethod
    def before_install(cls):
        '''Some mel procedures require additional setup before installing the
        hook. Subclasses can overwrite this method to run code once before
        installing the callbacks hook.

        See also:: ModelEditorRMBMenu.pre_install.
        '''
        return

    @classmethod
    def after_install(cls):
        '''Some mel procedures require additional setup after installing the
        hook. Subclasses can overwrite this method to run code once after
        installing the callbacks hook.

        See also:: ModelEditorRMBMenu subclasses for reference.
        '''
        return

    @classmethod
    def register(cls, callback, owner=None):
        if not cls.installed:
            cls.before_install()

        register_mel_proc_callback(
            cls.mel_proc,
            callback,
            owner=owner,
        )

        if not cls.installed:
            cls.after_install()

        cls.installed = True

    @classmethod
    def unregister(cls, callback, owner=None):
        unregister_mel_proc_callback(
            cls.mel_proc,
            callback,
            owner=owner,
        )

    @classmethod
    def list(cls, callback, owner=None):
        return list_mel_proc_callbacks(
            cls.mel_proc,
            owner=owner,
        )

    @classmethod
    def clear(cls, owner=None):
        clear_mel_proc_callbacks(
            cls.mel_proc,
            owner=owner,
        )


class OutlinerRMBMenu(MelProcCallback):
    '''Register callbacks with the Outliners RMB Menu.

    This class overwrites the OutlinerEdMenuCommand mel procedure.
    '''

    mel_proc = 'OutlinerEdMenuCommand'


class ModelEditorRMBMenu(MelProcCallback):
    '''Register callbacks with the 3D Viewports RMB Menu.

    This class overwrites the dagMenuProc mel procedure.
    '''

    mel_proc = 'dagMenuProc'

    @classmethod
    def before_install(cls):
        '''Ensure that dagMenuProc is sourced prior to installing callbacks.'''

        mel.eval('catchQuiet(`buildObjectMenuItemsNow ""`)')

    @classmethod
    def after_install(cls):
        '''Globalize missing procedures from dagMenuProc.mel'''

        globalize_mel_proc('optionalDagMenuProc')


class ModelEditorViewMenu(MelProcCallback):
    '''Register callbacks with the 3D Viewports View Menu.

    This class overwrites the postModelEditorViewMenuCmd mel procedure.
    '''

    mel_proc = 'postModelEditorViewMenuCmd_Old'
