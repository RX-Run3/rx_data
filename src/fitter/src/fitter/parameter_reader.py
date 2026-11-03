'''
This module contains the ParameterReader class
'''
import os

from typing     import Final
from contextlib import contextmanager
from pathlib    import Path
from dmu        import LogStore
from dmu.stats  import FitResult
from rx_common  import Block, Brem, Component, Trigger
from rx_common  import Qsq

from .fit_metadata import FitMetadata
from .fit_summary  import FitSummary
from rx_common     import MVAWp

log=LogStore.add_logger('fitter:parameter_reader')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
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
        name : str | None = None):
        '''
        Parameters
        -------------
        name : Fit name, e.g. mid_window
        '''
        if name is None and self._pars_path is None:
            raise ValueError('No name was passed and no path to parameters exists')

        self._summary = self.__get_summary(name = name)
    # ----------------------
    @property
    def summary(self) -> FitSummary:
        return self._summary
    # ----------------------
    def __get_summary(self, name : str | None = None) -> FitSummary:
        '''
        Parameters
        -------------
        name: Label for fits

        Returns
        -------------
        Summary object with fit information
        '''
        if self._pars_path:
            log.info(f'Using user defined path: {self._pars_path}')
            return FitSummary.from_json(path = self._pars_path)

        pars_path = _ANADIR / f'fits/data/{name}/fit_summary.json'
        log.debug(f'Using path: {pars_path}')
        if not pars_path.exists():
            raise FileNotFoundError(f'Cannot find: {pars_path}')

        return FitSummary.from_json(path = pars_path)
    # ----------------------
    def __call__(
        self,
        comp    : Component,
        brem    : Brem,
        block   : Block,
        cmb     : MVAWp,
        prc     : MVAWp,
        q2bin   : Qsq,
        trigger : Trigger) -> FitResult:
        '''
        Parameters
        -------------
        comp    : Component associated to fitted dataset
        brem    : Brem category, e.g. 0, 1, 2
        block   : Block number in 2024, e.g. 1, 2, 3...8
        cmb/prc : MVA working point
        q2bin   : E.g. jpsi
        trigger : HLT2 trigger, used to pick channel, etc

        Returns
        -------------
        Measurement instance, i.e. container with parameter names, values and errors
        '''
        meta = FitMetadata(
            component = comp,
            cmb       = cmb,
            prc       = prc,
            block     = block,
            project   = trigger.project,
            channel   = trigger.channel,
            q2bin     = q2bin,
            brem      = brem,
            stats     = (1, 1),
        )

        fres = self._summary.at(meta)

        return fres
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
