# -*- coding: utf-8 -*-
from __future__ import print_function

# Standard library imports
import re
from collections import defaultdict

# Third party imports
from maya import mel


# Initialize shared MelProcCallback state
if not hasattr(mel, '_MEL_PROC_CALLBACKS'):
    mel._MEL_PROC_CALLBACKS = defaultdict(list)
    mel._MEL_PROC_CACHE = {}


class MelProcCallback(object):
    '''
    Maintains a registry of python callbacks for mel global procedures.
    '''

    _proc_callbacks = mel._MEL_PROC_CALLBACKS
    _proc_cache = mel._MEL_PROC_CACHE
    _hook_tmpl_no_params = (
        'python("'
            'from shadeset.callbacks import MelProcCallback;'
            'MelProcCallback.execute(\'{}\');'
        '");'
    )
    _hook_tmpl = (
        'python("'
            'from shadeset.callbacks import MelProcCallback;'
            'MelProcCallback.execute(\'{}\', \'" + {} + "\');'
        '");'
    )

    @classmethod
    def add(cls, mel_proc, callback):
        '''Add callback to mel procedure'''

        if mel_proc not in cls._proc_cache:
            mel_file, mel_code, params = cls.get_mel_proc_data(mel_proc)
            cls._proc_cache[mel_proc] = mel_file, mel_code, params
        else:
            mel_file, mel_code, params = cls._proc_cache[mel_proc]

        if params:
            py_hook = cls._hook_tmpl.format(
                mel_proc, ' + "\', \'" + '.join(params)
            )
        else:
            py_hook = cls._hook_tmpl_no_params.format(mel_proc)

        if py_hook not in mel_code:
            mel_code = mel_code[:-1] + py_hook + mel_code[-1]

            try:
                mel.eval(mel_code)
            except Exception as e:
                print('Failed to add python callback hook')
                print(e)
                return

        cls._proc_callbacks[mel_proc].append(callback)

    @classmethod
    def remove(cls, mel_proc, callback):
        '''Remove callback from mel procedure'''

        try:
            cls._proc_callbacks[mel_proc].remove(callback)
        except ValueError:
            pass

        if not cls._proc_callbacks[mel_proc] and mel_proc in cls._proc_cache:
            mel.eval(cls._proc_cache[mel_proc][1])

    @classmethod
    def clear(cls, mel_proc=None):
        '''Clear callbacks and execute original mel procedures code.'''

        if mel_proc and mel_proc in cls._proc_cache:
            (_, mel_code, _) = cls._proc_cache[mel_proc]
            mel.eval(mel_code)

            cls._proc_callbacks[mel_proc][:] = []
        else:
            for mel_proc, (_, mel_code, _) in cls._proc_cache.items():
                mel.eval(mel_code)

            cls._proc_callbacks.clear()

    @classmethod
    def execute(cls, mel_proc, *mel_proc_args):
        '''Execute all callbacks for mel procedure'''

        for callback in cls._proc_callbacks[mel_proc]:
            callback(*mel_proc_args)

    @classmethod
    def get_mel_proc_data(cls, mel_proc):
        '''Get the mel code and parameters of global mel procedure'''

        mel_file = mel.eval('whatIs ' + mel_proc)
        if mel_file == 'Unknown':
            raise Exception('Mel procedure is unknown')
        elif 'found in: ' in mel_file:
            mel_file = mel_file.split('found in: ')[-1]
        else:
            raise Exception(
                'Mel procedure is not defined in a file, can not add callback'
            )

        with open(mel_file, 'r') as f:
            file_contents = f.read()

        mel_code = []

        pattern = re.compile(r'global\s+proc\s+%s\s+\(.*\)\s+?\{' % (mel_proc))
        match = pattern.search(file_contents)
        if not match:
            raise Exception('Can not find global proc ' + mel_proc)

        mel_def = match.group(0)
        mel_def_end = match.end(0)
        pattern = re.compile(r'\$\w+')
        params = pattern.findall(mel_def)

        mel_code.append(mel_def)
        depth = 1
        for char in file_contents[mel_def_end:]:
            if depth == 0:
                break

            mel_code.append(char)
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1

        return mel_file, ''.join(mel_code), params


def add_mel_proc_callback(mel_proc, callback):
    MelProcCallback.add(mel_proc, callback)


def remove_mel_proc_callback(mel_proc, callback):
    MelProcCallback.remove(mel_proc, callback)


def clear_mel_proc_callbacks(mel_proc=None):
    MelProcCallback.clear(mel_proc)
