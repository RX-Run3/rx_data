'''
Module with utilities for caching
'''
import os
import json

from typing                import Any
from dmu.generic           import hashing
from dmu.generic           import utilities as gut

from dmu.logging.log_store import LogStore

log=LogStore.add_logger('dmu:generic:caching')
# ----------------------
def cache_data(obj : Any, hash_obj : Any) -> None:
    '''
    Will save data to a text file using a name from a hash

    Parameters
    -----------
    obj      : Object that can be saved to a text file, e.g. list, number, dictionary
    hash_obj : Object that can be used to get hash e.g. immutable
    '''
    try:
        json.dumps(obj)
    except Exception as exc:
        raise ValueError('Object is not JSON serializable') from exc

    val  = hashing.hash_object(hash_obj)
    path = f'/tmp/dmu/cache/{val}.json'
    gut.dump_json(obj, path, exists_ok=True)
# ----------------------
def load_cached(hash_obj : Any, on_fail : Any = None) -> Any:
    '''
    Loads data corresponding to hash from hash_obj

    Parameters
    ---------------
    hash_obj: Object used to calculate hash, which is in the file name
    on_fail : Value returned if no data was found.
              By default None, and it will just raise a FileNotFoundError
    '''
    val  = hashing.hash_object(hash_obj)
    path = f'/tmp/dmu/cache/{val}.json'
    if os.path.isfile(path):
        data = gut.load_json(path)
        return data

    if on_fail is not None:
        return on_fail

    raise FileNotFoundError(f'Cannot find cached data at: {path}')
# ----------------------
