'''
This module contains the ParameterReader class
'''
import os
import re
import math
import numpy
import jacobi
import pandas as pnd

from typing     import Final
from contextlib import contextmanager
from pathlib    import Path
from dmu        import LogStore
from dmu.stats  import Measurement
from rx_common  import Block, Brem, Component, Project, Trigger 
from rx_common  import Qsq
from .mva_conf  import MVAWp 

log=LogStore.add_logger('fitter:parameter_reader')

_NBREM : Final[int] = 2
# ------------------------------------
class FitMeasurement(Measurement):
    '''
    Class meant to represent the measurements associated to a fit
    i.e. the fit parameters
    '''
    @property
    def candidates(self) -> tuple[float,float]:
        return 1, 1
# ------------------------------------
class ParameterReader:
    '''
    This class is meant to be an interface to the dataframe
    containing the fitting parameters
    '''
    _pars_path : Path | None = None
    # ----------------------
    def __init__(
        self, 
        suffix : str | None = None,
        name   : str | None = None):
        '''
        Parameters
        -------------
        suffix: Used to pick up parameters_{SUFFIX}.parquet, can be None
        name  : Fit name, e.g. mid_window 
        '''
        self._suffix = suffix

        if name is None and self._pars_path is None:
            raise ValueError('No name was passed and no path to parameters exists')

        self._df = self._get_dataframe(name = name)
    # ----------------------
    def print(
        self, 
        extra_columns : list[str] | None = None,
        rows = 100) -> None:
        '''
        Parameters
        --------------------
        rows: Number of rows to print
        extra_columns: Columns to add to printout beyond metadata
        '''
        df = self._df
        for column in df.columns:
            df = df.sort_values(by=column, ascending=False)

        df = df.reset_index()

        self._print_info(
            df            = df, 
            extra_columns = extra_columns,
            rows          = rows)
    # ----------------------
    def _get_dataframe(self, name : str | None = None) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        name: Label for fits

        Returns
        -------------
        Dataframe with fit parameters 
        '''
        if self._pars_path:
            log.info(f'Using user defined path: {self._pars_path}')
            return pnd.read_parquet(self._pars_path)

        ana_dir   = Path(os.environ['ANADIR'])

        if self._suffix is None:
            pars_path = ana_dir / f'fits/data/{name}/parameters.parquet'
        else:
            pars_path = ana_dir / f'fits/data/{name}/parameters_{self._suffix}.parquet'

        log.debug(f'Using path: {pars_path}')
        if not pars_path.exists():
            raise FileNotFoundError(f'Cannot find: {pars_path}')

        return pnd.read_parquet(path = pars_path)
    # ----------------------
    def _print_info(
        self, 
        df : pnd.DataFrame, 
        extra_columns : list[str] | None = None,
        rows          : int              = 20) -> None:
        '''
        This method will print the sample information

        Parameters
        -------------
        df  : DataFrame with fit information
        rows: Number of rows to print
        extra_columns: Columns to add to printout beyond metadata
        '''
        ext_cols = [] if extra_columns is None else extra_columns
        columns  = [
            'project',
            'kind',
            'mva_cmb',
            'mva_prc',
            'brem', 
            'block', 
            'q2bin', 
            'channel'] + ext_cols

        try:
            df_info = df[columns]
        except KeyError as exc:
            for col in df.columns:
                log.error(col)
            raise KeyError('Cannot find at least one column') from exc

        with pnd.option_context(
            'display.width', 
            None,
            'display.max_colwidth',
            None,
            'display.max_rows', 
            rows):
            log.info('\n' + str(df_info))
    # ----------------------
    def _query(self, df : pnd.DataFrame, cut : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        cut: Selection used to filter dataframe

        Returns
        -------------
        Filtered DataFrame
        '''
        df_out = df.query(cut)

        if len(df_out) == 0:
            log.warning('Querying:')
            self._print_info(df = df)
            log.warning('From main:')
            self.print()
            raise ValueError(f'No entries pass: {cut}')

        return df_out
    # ----------------------
    def _format_data(
        self, 
        brem : Brem,
        data : dict[str, float]) -> dict[str,tuple[float,float]]:
        '''
        Parameters
        -------------
        brem: Brem category
        data: Dictionary mapping quantity with value, value is a float, i.e. dictionary has been filtered

        Returns
        -------------
        Dictionary mapping quantity with tuple where first element is value and second one is the error
        '''
        output_data : dict[str, list[float]] = dict()
        for key, val in data.items():
            if math.isnan(val):
                continue

            if key in ['brem', 'block', 'channel', 'project', 'q2bin', 'mva_cmb', 'mva_prc']:
                continue

            index    = 0 if key.endswith('_value') else 1
            var_name = key.removesuffix('_value').removesuffix('_error')

            if var_name not in output_data:
                output_data[var_name] = [-999.0, -999.0]

            output_data[var_name][index] = val

        res = { key : (value[0], value[1]) for key, value in output_data.items() } 

        name, val, err = self._extract_brem(brem = brem, data = data)

        res[name] = val, err

        return res
    # ----------------------
    def _extract_brem(
        self, 
        brem : Brem, 
        data : dict[str, float]) -> tuple[str,float,float]:
        '''
        Parameters
        -------------
        brem: brem category, i.e. 1 or 2
        data: Dictionary with variable name and value

        Returns
        -------------
        Tuple with value of brem fraction, error and name of variable
        '''
        keys = [ key for key in data if 'fraction' in key ]
        if len(keys) != 2:
            for key in data:
                log.error(key)
            raise ValueError('Expected two entries corresponding to brem fraction')

        [val] = [ data[key] for key in keys if key.endswith('_value') ]
        [err] = [ data[key] for key in keys if key.endswith('_error') ]

        if brem == 2:
            val = 1 - val # fraction stored is brem 1 one

        # Fraction needs to be named as mu and sg to be used for scales
        key    = keys[0]
        regex  = r'(\w+)_fraction_(value|error)'
        mtch   = re.match(regex, key)
        if not mtch:
            raise ValueError(f'Canot extract signal name from: {key}')

        signal = mtch.group(1) 

        return f'fr_{signal}_brem_{brem}', val, err
    # ----------------------
    def __call__(
        self, 
        signame   : str,
        brem      : Brem,
        block     : Block,
        cmb       : str,
        prc       : str,
        kind      : str,
        project   : Project,
        q2bin     : Qsq,
        trigger   : Trigger) -> FitMeasurement:
        '''
        Parameters
        -------------
        signame  : Identifier for signal parameter, e.g. jpsi 
        brem     : Brem category, e.g. 0, 1, 2
        block    : Block number in 2024, e.g. 1, 2, 3...8
        cmb/prc  : String specifying working point, e.g. 050
        kind     : Either dat or sim
        project  : E.g. rk, rkst 
        q2bin    : E.g. jpsi
        trigger  : HLT2 trigger, used to pick channel, etc

        Returns
        -------------
        FitMeasurement instance, i.e. container with parameter names, values and errors
        '''
        channel = info.channel_from_trigger(trigger=trigger, lower_case = True)
        df      = self._df
        df      = self._query(df = df, cut = f'kind    == \"{kind}\"'   )
        df      = self._query(df = df, cut = f'mva_cmb == \"{cmb}\"'    )
        df      = self._query(df = df, cut = f'mva_prc == \"{prc}\"'    )
        df      = self._query(df = df, cut = f'q2bin   == \"{q2bin}\"'  )
        df      = self._query(df = df, cut = f'channel == \"{channel}\"')
        df      = self._query(df = df, cut = f'project == \"{project}\"')
        df      = self._query(df = df, cut = f'brem    == \"{brem}\"'   )
        df_all  = df.copy() # Data after all requirements, but with all blocks 
        df      = self._query(df = df, cut = f'block   ==   {block}'    )

        if len(df) != 1:
            self._print_info(df=df)
            raise ValueError('Not found one and only one row')

        raw_data = df.iloc[0].to_dict()
        flt_data = { key : value for key, value in raw_data.items() if isinstance(value, float) }
        data     = self._format_data(
            brem = brem,
            data = flt_data) # type: ignore

        # for simultaneous fits, this removes brem_002 parameters when one needs brem_001
        # and viceversa
        data     = { key : value for key, value in data.items() if f'brem_{brem}' in key }

        data[f'bk_{signame}'] = (math.nan, math.nan) if kind == 'sim' else self._get_block_fraction(
            signame = signame,
            df      = df_all, 
            brem    = brem,
            block   = block) 

        return FitMeasurement(data = data)
    # ----------------------
    def _get_block_fraction(
        self,
        signame: str,
        df     : pnd.DataFrame,
        brem   : Brem,
        block  : Block) -> tuple[float,float]:
        '''
        Block fraction is the fraction of signal in a block, WRT the full year
        these are the sums over the brem categories

        Parameters
        -------------
        signame : Name of signal parameter, needed to extract yield, e.g. yld_{signame}_value
        df      : DataFrame for real data with all blocks, but all cuts applied otherwise
        block   : Block number within dataset
        brem    : Brem category

        Returns
        -------------
        Value and error of block fraction for real data
        '''
        arr_blk          = df['block'].to_numpy()
        arr_val, arr_err = self._get_brem_yields(
            df      = df, 
            brem    = brem,
            signame = signame)

        iblock   = numpy.argmax(arr_blk == block.to_int())
        def fun(vals):
            val = vals[iblock]

            return val / sum(vals)

        cov      = numpy.diag(arr_err ** 2)
        val, var = jacobi.propagate(fun, arr_val, cov) # type: ignore

        val      = float(val)
        err      = math.sqrt(var)

        log.debug(f'Block {block}, fraction {val:.3f}+/-{err:.3f}')

        return val, err 
    # ----------------------
    def _get_brem_yields(
        self, 
        df      : pnd.DataFrame, 
        brem    : Brem, 
        signame : str) -> tuple[numpy.ndarray, numpy.ndarray]:
        '''
        Parameters
        -------------
        df     : DataFrame with yields and fractions information
        brem   : Brem category
        signame: Name of signal, e.g. jpsik

        Returns
        -------------
        Tuple with yields and yield errors for given brem category
        '''

        # NOTE: Uncertainties are very small, might not matter if we use
        # covariance between fraction and yield or assume zero correlation
        arr_yld_val = df[f'yld_{signame}_brem_x12_value'].to_numpy()
        arr_yld_err = df[f'yld_{signame}_brem_x12_error'].to_numpy()
        arr_frc_val = df[f'{signame}_fraction_value'    ].to_numpy()
        arr_frc_err = df[f'{signame}_fraction_error'    ].to_numpy()

        # Fits are parametrized with total yield and brem 1 fractions 
        # NOTE: Uncertainty on ERR is uncertainty on 1 - ERR
        if brem == Brem.two:
            arr_frc_val = 1 - arr_frc_val

        val =  arr_yld_val * arr_frc_val
        var = (arr_yld_val * arr_frc_err) ** 2 + (arr_frc_val * arr_yld_err) ** 2
        err = numpy.sqrt(var)

        return val, err
    # ----------------------
    @classmethod
    def inputs_from(cls, pars_path : Path):
        '''
        Parameters
        -------------
        pars_path: Path to parquet file with parameters 

        Returns
        -------------
        Context manager
        '''
        old_val = cls._pars_path

        @contextmanager
        def _context():
            try:
                cls._pars_path = pars_path
                yield
            finally:
                cls._pars_path = old_val

        return _context()
# ------------------------------------
