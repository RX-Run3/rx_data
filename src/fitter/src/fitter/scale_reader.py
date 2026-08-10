'''
Module holding ScaleReader class
'''
import os
import math
import pandas as pnd
import jacobi

from dmu       import LogStore
from typing    import Final
from pathlib   import Path
from rx_common import Block, Brem, Correction

log=LogStore.add_logger('fitter:scale_reader')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
_FITDIR : Final[str]  = 'reso_no_dtf-latest' # Name of directory with fits providing scales
# -------------------------------------
class ScaleReader:
    '''
    Class in charge of accessing mass scales, resolutions, brem fractions, etc
    and making them available
    '''
    # ----------------------
    def __init__(
        self, 
        version : str = 'latest') -> None:
        '''
        Parameters
        ---------------
        version: Version of scales
        '''
        data_path = _ANADIR / f'fits/data/{_FITDIR}/{version}/rk_ee/plots/scales.json'
        if not data_path.exists():
            raise FileNotFoundError(f'Cannot find scales file: {data_path}')

        df         = pnd.read_json(data_path)
        df['brem'] = df['brem'].apply(lambda x : str(Brem.from_int(value = x)))

        self._df = df
    # ----------------------
    def get_scale(
        self,
        corr  : Correction,
        block : Block,
        brem  : Brem) -> tuple[float,float]:
        '''
        Parameters
        -------------
        corr : Type of correction
        block: E.g. 1...8
        brem : E.g. 1, 2

        Returns
        -------------
        Tuple with value and error of scale
        '''
        if brem == Brem.brx12:
            val_1, err_1 = self.get_scale(
                corr  = corr, 
                block = block, 
                brem  = Brem.one)

            val_2, err_2 = self.get_scale(
                corr  = corr, 
                block = block, 
                brem  = Brem.two)

            val, var = jacobi.propagate(
                lambda x : (x[0] + x[1]) / 2,  
                [val_1, val_2],                     # type: ignore
                [[err_1 ** 2, 0], [0, err_2 ** 2]]) # type: ignore
            val = float(val)
            err = math.sqrt(var)

            return val, err

        df = self._df
        try:
            df = df.query(f'block == {block}')
            df = df.query(f'brem  == \"{str(brem)}\"')
        except Exception as exc:
            log.error(df)
            raise ValueError(f'Cannot filter by block/brem: {block}/{brem}') from exc

        if len(df) != 1:
            log.error(df)
            raise ValueError(f'Not found one and only one row for block/brem: {block}/{brem}')

        try:
            sr  = df.iloc[0]
            val = sr[f'{corr}_val']
            err = sr[f'{corr}_err']
        except Exception as exc:
            log.error(df)
            raise ValueError('Cannot read scale from dataframe') from exc

        return val, err 
# -------------------------------------
