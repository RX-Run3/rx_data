'''
Module with code needed to retrieve X, Y position from ECAL cell ID
'''

import pandas as pnd

from typing              import overload
from importlib.resources import files
from dmu                 import LogStore

log=LogStore.add_logger('ecal_calibration:calo_translator')
# --------------------------------
def _cast_column(column, ctype) -> pnd.Series:
    column = pnd.to_numeric(column, errors='coerce')
    column = column.fillna(-100_000)
    column = column.astype(ctype)

    return column
# --------------------------------
def get_data() -> pnd.DataFrame:
    '''
    Returns pandas dataframe with x,y and row and column values
    '''
    data_path = files('ecal_calibration_data').joinpath('brem_correction/coordinates.csv')
    df      = pnd.read_csv(str(data_path))
    df['a'] = _cast_column(df.a, int)
    df['x'] = _cast_column(df.x, float)
    df['y'] = _cast_column(df.y, float)
    df['z'] = _cast_column(df.z, float)
    df['r'] = _cast_column(df.r, int)
    df['c'] = _cast_column(df.c, int)

    return df
# ------------------------------------------------------
@overload
def from_id_to_xy(
    row : int,
    col : int,
    det : str,
    area: int) -> tuple[float,float]: ...
@overload
def from_id_to_xy(
    row : int | None = ...,
    col : int | None = ...,
    det : str | None = ...,
    area: int | None = ...) -> pnd.DataFrame: ...
def from_id_to_xy(
    row : int | None = None,
    col : int | None = None,
    det : str | None = None,
    area: int | None = None) -> tuple[float,float] | pnd.DataFrame:
    '''
    Function taking position in ECAL
    Parameters
    --------------
    row: Row index
    col: Column index
    det: Name of subdetector, Inner, Middle, Outer
    area: Index of subdetector 0 (Inner), 1 (Middle), 2 (Outer)

    Returns
    --------------
    Either:
        - tuple[float,float]: With the x,y coordinates, if the region in the detector is fully specified.
        - df                : Pandas dataframe with the location information, if the region is not fully specified
    '''
    if det not in [
            None,
            'Inner',
            'Middle',
            'Outer']:
        raise ValueError(f'Invalid subdetector name: \"{det}\"')

    df = get_data()
    if area is not None:
        df = df[df.a==area]

    if det is not None:
        df = df[df.n==det]

    if row is not None:
        df = df[df.r==row]

    if col is not None:
        df = df[df.c==col]

    are = area

    has_row = row is not None
    has_col = col is not None
    has_det = det is not None
    has_are = are is not None

    full_description = has_row and has_col and (has_det or has_are)

    if not full_description and len(df) <= 1:
        log.error(df)
        raise ValueError('Expected dataframe with more than one row')

    if not full_description and len(df) > 1:
        return df

    if full_description and len(df) != 1:
        log.error(df)
        log.info(f'{"Row":<10}{row}')
        log.info(f'{"Col":<10}{col}')
        log.info(f'{"Det":<10}{det}')
        log.info(f'{"Reg":<10}{are}')
        raise ValueError('Expected dataframe with one row')

    x = df.iloc[0]['x']
    y = df.iloc[0]['y']

    return x, y
# ------------------------------------------------------
