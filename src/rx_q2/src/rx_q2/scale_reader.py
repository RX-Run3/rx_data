'''
Module holding ScaleReader class
'''
import os
import math
import pandas as pnd
import jacobi

from dmu            import LogStore
from dmu.pdataframe import utilities as put
from typing         import Final
from pathlib        import Path
from rx_common      import Block, Brem, Channel, Component, Correction

log=LogStore.add_logger('rx_q2:scale_reader')

_ANADIR : Final[Path]      = Path(os.environ['ANADIR'])
_FITDIR : Final[str]       = 'reso_no_dtf-latest' # Name of directory with fits providing scales
_DATA   : Final[Component] = Component.data_24    # Used to pick data or mc parameters
# -------------------------------------
class ScaleReader:
    '''
    Class in charge of accessing mass scales, resolutions, brem fractions, etc
    and making them available
    '''
    # ----------------------
    def __init__(
        self,
        channel : Channel,
        version : str = 'latest') -> None:
        '''
        Parameters
        ---------------
        version: Version of scales
        '''
        self.__channel  = channel
        self._df_scales = self._get_dataframe(name = 'scales'    , version = version)
        self._df_params = self._get_dataframe(name = 'parameters', version = version)

        self._cache : dict[str,tuple[float,float]] = dict()
    # ----------------------
    def _get_dataframe(self, name : str, version : str) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        name   : Name of JSON file with the data, e.g. scales, parameters
        version: Version of fit output, usually `latest`

        Returns
        ---------------
        Dataframe with contents of JSON file
        '''
        data_path = _ANADIR / f'fits/data/{_FITDIR}/{version}/rk_{self.__channel}/plots/{name}.json'
        if not data_path.exists():
            raise FileNotFoundError(f'Cannot find scales file: {data_path}')

        log.debug(f'Loading parameters from: {data_path}')
        df         = pnd.read_json(data_path)
        df['brem'] = df['brem'].apply(lambda x : str(Brem.from_int(value = x)))

        return df
    # ----------------------
    def _get_combined_entry(
        self,
        df       : pnd.DataFrame,
        quantity : str,
        block    : Block) -> tuple[float,float]:
        '''
        Parameters
        -------------
        quantity : Name of queried quantity in `{quantity}_val` columns
        block    : E.g. 1...8

        Returns
        -------------
        Tuple with value and error of quantity after merging them
        from blocks 1 and 2
        '''
        val_1, err_1 = self._query_entry(
            df       = df,
            quantity = quantity,
            block    = block,
            brem     = Brem.one)

        val_2, err_2 = self._query_entry(
            df       = df,
            quantity = quantity,
            block    = block,
            brem     = Brem.two)

        val, var = jacobi.propagate(
            lambda x : (x[0] + x[1]) / 2,
            [val_1, val_2],                     # type: ignore
            [[err_1 ** 2, 0], [0, err_2 ** 2]]) # type: ignore
        val = float(val)
        err = math.sqrt(var)

        return val, err
    # ----------------------
    def _query_entry(
        self,
        df      : pnd.DataFrame,
        quantity: str,
        block   : Block,
        brem    : Brem) -> tuple[float,float]:

        df_org = df
        try:
            df = put.query(df = df, expr = f'block == {block}')
            df = put.query(df = df, expr = f'brem  == \"{str(brem)}\"')
        except Exception as exc:
            log.error(df)
            raise ValueError(f'Cannot filter by block/brem: {block}/{brem}') from exc

        if len(df) != 1:
            log.error(f'Original:\n{df_org}')
            log.error(f'Result:\n{df}')
            raise ValueError(f'Not found one and only one row for block/brem: {block}/{brem}')

        try:
            sr  = df.iloc[0]
            val = sr[f'{quantity}_val']
            err = sr[f'{quantity}_err']
        except Exception as exc:
            log.error(df)
            raise ValueError('Cannot read scale from dataframe') from exc

        return val, err
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
        key = f'{corr}-{block}-{brem}'
        if key in self._cache:
            return self._cache[key]

        df = self._df_scales

        if brem == Brem.brx12:
            return self._get_combined_entry(quantity = corr, block = block, df = df)

        val = self._query_entry(
            df       = df,
            quantity = corr,
            brem     = brem,
            block    = block)

        self._cache[key] = val

        return val
    # ----------------------
    def get_param(
        self,
        is_mc : bool,
        param : str,
        block : Block,
        brem  : Brem) -> tuple[float,float]:
        '''
        Parameters
        -------------
        is_mc: If true will return MC parameters, otherwise data
        param: Parameter name, e.g. mu
        block: E.g. 1...8
        brem : E.g. 1, 2

        Returns
        -------------
        Tuple with value and error of parameter
        '''
        key = f'{is_mc}-{param}-{block}-{brem}'
        if key in self._cache:
            return self._cache[key]

        expr = f'sample != "{_DATA.value}"' if is_mc else f'sample == "{_DATA.value}"'
        df   = self._df_params.query(expr)

        if brem == Brem.brx12:
            return self._get_combined_entry(quantity = param, block = block, df = df)

        value = self._query_entry(
            df       = df,
            quantity = param,
            brem     = brem,
            block    = block)

        self._cache[key] = value

        return value
# -------------------------------------
