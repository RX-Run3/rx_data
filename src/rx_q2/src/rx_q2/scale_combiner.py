'''
Module holding ScaleCombiner class
'''
import os
import math
from typing import Final
import pandas as pnd
from pathlib import Path

from dmu.logging.log_store import LogStore
from dmu.generic           import typing_utilities as tut

log=LogStore.add_logger('rx_q2:scale_combiner')

QUANTITIES : Final[list[str]] = ['mu', 'sg']
# -------------------------------------
class ScaleCombiner:
    '''
    Class in charge of:

    - Load scales from each sample, given a version
    - Combine them statistically
    - Write combined scales to JSON file
    '''
    # ----------------------
    def __init__(self, version : str) -> None:
        '''
        Parameters
        -------------
        version: Version of fits, e.g. v2
        '''
        self._version = version
    # ----------------------
    def _get_dataframes(self, measurement : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        measurement: Directory where measurement is found, e.g. rk_ee

        Returns
        -------------
        DataFrame with the scales
        '''
        ana_dir = Path(os.environ['ANADIR'])
        jsn_path= ana_dir / f'q2/fits/{self._version}/plots/{measurement}/parameters.json'

        if not jsn_path.exists():
            raise FileNotFoundError(f'Cannot find {jsn_path}')

        log.info(f'Getting dataframe for: {measurement}')

        df = pnd.read_json(jsn_path)
        df = df.sort_values(by=['brem', 'block', 'sample'])
        df = df.reset_index(drop=True)

        log.debug(df)

        return df
    # ----------------------
    def _combine_quantity(
        self,
        name  : str,
        row_1 : pnd.Series,
        row_2 : pnd.Series) -> tuple[float,float]:
        '''
        Parameters
        ------------------
        name   : Name of quantity in rows that needs to be averaged
        row_1/2: Pandas series representing candidate

        Returns
        ------------------
        Tuple with value and error of combined quantity
        '''
        val_1 = tut.numeric_from_series(row_1, f'{name}_val', float)
        val_2 = tut.numeric_from_series(row_2, f'{name}_val', float)

        var_1 = tut.numeric_from_series(row_1, f'{name}_err', float) ** 2
        var_2 = tut.numeric_from_series(row_2, f'{name}_err', float) ** 2

        is_nan_1 = math.isnan(val_1) or math.isnan(var_1)
        is_nan_2 = math.isnan(val_2) or math.isnan(var_2)

        if is_nan_1 and     is_nan_2:
            log.error(row_1)
            log.error(row_2)
            raise ValueError(f'Both elements in combination of {name} are NaN')

        if is_nan_1 and not is_nan_2:
            log.warning(f'First measurement of {name} is Nan: {row_1}')
            return val_2, var_2

        if is_nan_2 and not is_nan_1:
            log.warning(f'Second measurement of {name} is Nan: {row_2}')
            return val_1, var_1

        den   = 1 / var_1 + 1 / var_2

        avg   = (val_1 / var_1 + val_2 / var_2) / den
        err   = 1 / math.sqrt(den)

        return avg, err
    # ----------------------
    def _combine_measurement(
        self,
        row  : pnd.Series,
        ncol : int) -> pnd.Series:
        '''
        Parameters
        -------------
        ncol: Number of columns in dataframes to combine

        Returns
        -------------
        row resulting from combination
        '''
        row_1 = row[:ncol]
        row_2 = row[ncol:]
        row_3 = row_1.copy()

        for quantity in QUANTITIES:
            val, err = self._combine_quantity(name=quantity, row_1=row_1, row_2=row_2)

            row_3[f'{quantity}_val'] = val
            row_3[f'{quantity}_err'] = err

        return row_3
    # ----------------------
    def _combine(
        self,
        df_1 : pnd.DataFrame,
        df_2 : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df_1/2 : Dataframes with scales that need to be combined

        Returns
        -------------
        Dataframe with combination
        '''
        ncol   = len(df_1.columns)
        df_tmp = pnd.concat([df_1, df_2], axis=1)

        df_combined = df_tmp.apply(self._combine_measurement, axis=1, args=(ncol,))

        return df_combined
    # ----------------------
    def _validate(self, l_df : list[pnd.DataFrame]) -> None:
        '''
        Validates dataframes

        Parameters
        -------------
        l_df: List of dataframes with scales to combine
        '''
        nmeas = len(l_df)
        if nmeas != 2:
            raise ValueError(f'Can only combine two measurements, found {nmeas}')

        log.info(f'Combining {nmeas} measurements')

        nrows = { len(df)         for df in l_df }
        ncols = { len(df.columns) for df in l_df }

        if len(nrows) != 1:
            log.warning(f'Multiple sizes for dataframes: {nrows}')

        if len(ncols) != 1:
            raise ValueError(f'Multiple sizes for dataframes: {ncols}')

        log.debug(f'Dataframes rows/columns: {nrows}/{ncols}')
    # ----------------------
    def _save_combination(
        self,
        name: str,
        df  : pnd.DataFrame) -> None:
        '''
        Saves combination to JSON file

        Parameters
        -------------
        name: Name of JSON file where combination is saved
        df  : DataFrame with combined scales
        '''
        ana_dir = Path(os.environ['ANADIR'])
        jsn_path= ana_dir / f'q2/fits/{self._version}/{name}'

        log.info(f'Saving combination to: {jsn_path}')

        df.to_json(jsn_path, indent=2)
    # ----------------------
    def combine(
        self,
        name         : str,
        measurements : list[str]) -> pnd.DataFrame:
        '''
        Writes the combined scales to JSON

        Parameters
        -------------
        name: Name of file where combination is stored
        measurements: List of strings with names of directories with measurements to combine, e.g. rk_ee

        Returns
        -------------
        Dataframe with combined scales
        '''
        l_df = [ self._get_dataframes(measurement=measurement) for measurement in measurements ]
        self._validate(l_df = l_df)

        df   = self._combine(df_1=l_df[0], df_2=l_df[1])

        self._save_combination(name=name, df=df)

        return df
# -------------------------------------
