'''
Module with DataStore class
'''
import numpy
import numpy.typing as npt
import pandas       as pnd

from dmu            import LogStore
from rx_common      import Qsq, Trigger, Component, Mass
from .database_conf import DatabaseConf

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

        self.__cfg= DatabaseConf.load()
        self.__df = self._load_df()
    # ----------------------------------
    def _load_df(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        Pandas dataframe with data
        '''
        path = self.__cfg.get_path(comp = self._comp, trig = self._trig)

        if not path.exists():
            raise ValueError(f'No path found: {path}')

        log.debug(f'Loading data from: {path}')

        return pnd.read_parquet(path = path)
    # ----------------------------------
    def _get_mc_weights(self) -> NpFltArr:
        '''
        Returns
        ------------
        Array of weights needed to correct simulation
        '''
        result = self.__df.eval(self.__cfg.weight)
        weights= numpy.asarray(result, dtype = numpy.float64)

        return weights
    # ----------------------------------
    def get_array(self, mass : Mass) -> tuple[NpFltArr, NpFltArr]:
        '''
        Parameters
        ----------------
        mass: Name of column denoting Mass, e.g. B_Mass

        Returns
        ----------------
        Tuple with array of floats:

        - Representing masses
        - Representing weights
        '''
        if mass not in self.__df.columns:
            raise ValueError(f'Mass column {mass} not found')

        masses = self.__df[mass].to_numpy()

        if not self._comp.is_mc:
            weights = numpy.ones_like(masses)
        else:
            weights = self._get_mc_weights()

        return masses, weights
# ----------------------------------
