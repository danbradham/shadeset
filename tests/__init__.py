import os
from functools import partial

data_path = partial(
    os.path.join,
    os.path.abspath(os.path.dirname(__file__)),
    'data')
