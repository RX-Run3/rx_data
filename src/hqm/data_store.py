'''
Module with DataStore class
'''
import os
import numpy
import numpy.typing as npt
import pandas       as pnd

from pathlib   import Path
from dmu       import LogStore
from rx_common import Qsq, Trigger, Component, Mass

log      = LogStore.add_logger('rx_hqm:data_store')
NpFltArr = npt.NDArray[numpy.float64]
# ----------------------------------
class DataStore:
    '''
    Class used to provide arrays with masses
    '''
    # ----------------------------------
    def __init__(
        self, 
        qsq   : Qsq, 
        trig  : Trigger,
        comp  : Component):
        '''
        Parameters
        ----------------
        qsq : q2-bin where data will be picked up
        trig: Hlt2 trigger
        comp: Sample used to read data from
        '''
        self._qsq = qsq
        self._trig= trig
        self._comp= comp

        self.__df = self._load_df()
    # ----------------------------------
    def _load_df(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        Pandas dataframe with data
        '''
        anadir = Path(os.environ['ANADIR'])
        path   = anadir / f'DB/hqm/{self._comp}_{self._trig}_{self._qsq}.parquet'

        if not path.exists():
            raise ValueError(f'No path found: {path}')

        log.debug(f'Loading data from: {path}')

        return pnd.read_parquet(path = path)
    # ----------------------------------
    def get_array(self, mass : Mass) -> NpFltArr:
        '''
        Parameters
        ----------------
        mass: Name of column denoting Mass, e.g. B_Mass

        Returns
        ----------------
        Array of floats representing masses
        '''
        if mass not in self.__df.columns:
            raise ValueError(f'Mass column {mass} not found')

        return self.__df[mass].to_numpy()
# ----------------------------------
