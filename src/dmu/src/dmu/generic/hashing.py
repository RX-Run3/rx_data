'''
Module with functions needed to provide hashes
'''

import os
import hashlib
import pandas as pnd

from typing                import Any, Literal, overload
from pathlib               import Path
from dmu.logging.log_store import LogStore
from dmu.generic           import utilities as gut

log=LogStore.add_logger('dmu:generic.hashing')
# ------------------------------------
@overload
def hash_object(obj : Any, as_int : Literal[True ]        ) -> int: ...
@overload
def hash_object(obj : Any, as_int : Literal[False] =   ...) -> str: ...
def hash_object(obj : Any, as_int :           bool = False) -> str | int:
    '''
    Function taking a python object and returning
    a string representing the hash
    '''
    if isinstance(obj, pnd.DataFrame):
        obj = obj.to_dict()

    if isinstance(obj, str):
        string = obj
    else:
        string = gut.object_to_string(obj=obj)

    string_bin = string.encode('utf-8')
    hsh        = hashlib.sha256(string_bin)
    value      = hsh.hexdigest()
    if as_int:
        return int(value, 16)

    value      = value[:10]

    return value
# ------------------------------------
def hash_file(path : str | Path) -> str:
    '''
    Parameters
    ----------------
    path: Path to file whose content has to be hashed

    Returns
    ----------------
    A string representing the hash
    '''
    if isinstance(path, Path):
        path = str(path)

    if not os.path.isfile(path):
        raise FileNotFoundError(f'Cannot find: {path}')

    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)

    value = h.hexdigest()

    return value[:10]
# ------------------------------------
