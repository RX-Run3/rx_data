'''
Module containing utility functions for ML tools
'''

import hashlib
from typing import Literal, Union, overload

import numpy
import pandas as pnd

from dmu.logging.log_store import LogStore

log = LogStore.add_logger('dmu:ml:utilities')
# ---------------------------------------------
# Patch dataframe with features
# ---------------------------------------------
def tag_nans(
    df      : pnd.DataFrame,
    indexes : str) -> pnd.DataFrame:
    '''
    Parameters
    ----------------
    df      : Pandas dataframe
    indexes : Name of dataframe attribute where array of indices of NaN rows should go

    Returns
    ----------------
    Dataframe:

    - After filtering, i.e. with dropped rows.
    - With array of indices dropped as attribute at `patched_indices`
    '''

    l_nan = df.index[df.isna().any(axis=1)].tolist()
    nnan  = len(l_nan)
    if nnan == 0:
        log.debug('No NaNs found')
        return df

    log.warning(f'Found {nnan} NaNs')

    df_nan_frq = df.isna().sum()
    df_nan_frq = df_nan_frq[df_nan_frq > 0]

    log.info(df_nan_frq)
    log.warning(f'Attaching array with NaN {nnan} indexes and removing NaNs from dataframe')

    arr_index_2 = numpy.array(l_nan)
    if indexes in df.attrs:
        arr_index_1 = df.attrs[indexes]
        arr_index   = numpy.concatenate((arr_index_1, arr_index_2))
        arr_index   = numpy.unique(arr_index)
    else:
        arr_index   = arr_index_2

    df.attrs[indexes] = arr_index

    return df
# ---------------------------------------------
# Cleanup of dataframe with features
# ---------------------------------------------
def cleanup(df : pnd.DataFrame) -> pnd.DataFrame:
    '''
    Takes pandas dataframe with features for classification
    Removes repeated entries and entries with nans
    Returns dataframe
    '''
    df = _remove_repeated(df)
    df = _remove_nans(df)

    return df
# ---------------------------------------------
def _remove_nans(df : pnd.DataFrame) -> pnd.DataFrame:
    if not df.isna().any().any():
        log.debug('No NaNs found in dataframe')
        return df

    sr_is_nan = df.isna().any()
    l_na_name = sr_is_nan[sr_is_nan].index.tolist()

    log.info('Found columns with NaNs')
    for name in l_na_name:
        nan_count = df[name].isna().sum()
        log.info(f'{nan_count:<10}{name}')

    ninit = len(df)
    df    = df.dropna()
    nfinl = len(df)

    log.warning(f'NaNs found, cleaning dataset: {ninit} -> {nfinl}')

    return df
# ---------------------------------------------
def _remove_repeated(df : pnd.DataFrame) -> pnd.DataFrame:
    l_hash = get_hashes(df, rvalue='list')
    s_hash = set(l_hash)

    ninit = len(l_hash)
    nfinl = len(s_hash)

    if ninit == nfinl:
        log.debug('No overlap between training and application found')
        return df

    log.warning(f'Overlap between training and application found, cleaning up: {ninit} -> {nfinl}')

    df['hash_index'] = l_hash
    df               = df.set_index('hash_index', drop=True)
    df_clean         = df[~df.index.duplicated(keep='first')]

    if not isinstance(df_clean, pnd.DataFrame):
        raise ValueError('Cleaning did not return pandas dataframe')

    return df_clean
# ----------------------------------
# ---------------------------------------------
@overload
def get_hashes(df_ft : pnd.DataFrame, rvalue : Literal['set'])  -> set[str]:...
@overload
def get_hashes(df_ft : pnd.DataFrame, rvalue : Literal['list']) -> list[str]:...
def get_hashes(df_ft : pnd.DataFrame, rvalue : str)  -> Union[set[str], list[str]]:
    '''
    Will return hashes for each row in the feature dataframe

    rvalue (str): Return value, can be a set or a list
    '''

    if   rvalue == 'set':
        res = { hash_from_row(row) for _, row in df_ft.iterrows() }
    elif rvalue == 'list':
        res = [ hash_from_row(row) for _, row in df_ft.iterrows() ]
    else:
        log.error(f'Invalid return value: {rvalue}')
        raise ValueError

    return res
# ----------------------------------
def hash_from_row(row : pnd.Series) -> str:
    '''
    Will return a hash in the form or a string from a pandas dataframe row
    corresponding to an event
    '''
    l_val   = [ str(val) for val in row ]
    row_str = ','.join(l_val)
    row_str = row_str.encode('utf-8')

    hsh = hashlib.sha256()
    hsh.update(row_str)

    hsh_val = hsh.hexdigest()

    return hsh_val
# ----------------------------------
def index_with_hashes(df):
    '''
    Will:
    - take dataframe with features
    - calculate hashes and add them as the index column
    - drop old index column
    '''

    l_hash = get_hashes(df, rvalue='list')
    ind_hsh= pnd.Index(l_hash)

    df = df.set_index(ind_hsh, drop=True)

    return df
# ----------------------------------
