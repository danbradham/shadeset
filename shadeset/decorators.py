# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Standard library imports
from functools import wraps

# Third party imports
from maya import cmds


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
