'''
Module with functions needed to test functions in generic/hashing.py module
'''

import pandas as pnd

from omegaconf   import OmegaConf
from dmu.generic import hashing
from dmu         import LogStore

log=LogStore.add_logger('dmu:test_hashing')
# --------------------------------------
def test_hash_simple():
    '''
    Function testing the hashing of a s list of python objects
    '''
    obj = [1, 'name', [1, 'sub', 'list'], {'x' : 1}]
    val = hashing.hash_object(obj)

    log.info(f'Hash: {val}')

    assert len(val) == 10
# --------------------------------------
def test_hash_pandas():
    '''
    Function testing the hashing of a pandas dataframe
    '''

    data = {
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Age' : [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
        }

    df  = pnd.DataFrame(data)
    val = hashing.hash_object(obj=df)

    log.info(f'Hash: {val}')

    assert len(val) == 10
# --------------------------------------
def test_hash_file():
    '''
    Tests the hashing of a file
    '''
    val = hashing.hash_file(path=__file__)

    assert isinstance(val, str)
# --------------------------------------
def test_hash_omegadict():
    '''
    Tests hashing when the dictionary
    is an OmegaConf DictConfig
    '''
    data = OmegaConf.create({'a' : 1})

    hashing.hash_object(obj=data)
