'''
Module with DataStore class
'''
import numpy
import numpy.typing as npt
import pandas       as pnd

from contextlib     import contextmanager
from contextvars    import ContextVar
from dmu            import LogStore
from rx_common      import Cuts, Qsq, Trigger, Component, Mass
from .database_conf import DatabaseConf

log      = LogStore.add_logger('rx_hqm:data_store')
NpFltArr = npt.NDArray[numpy.float64]

_SELECTION : ContextVar[dict[Cuts,str] | None] = ContextVar('_SELECTION', default = None) 
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

        df = pnd.read_parquet(path = path)
        df = self._select_data(df = df)

        return df
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
    def _select_data(self, df : pnd.DataFrame) -> pnd.DataFrame:
        sel = _SELECTION.get()
        if sel is None:
            raise ValueError('No selection used')

        log.debug('Applying selection')
        for name, expr in sel.items():
            log.debug(f'{name:<20}{expr}')
            df = df.query(expr)

        return df
    # ----------------------------------
    @classmethod
    def selection(
        cls, 
        update : bool,
        sel    : dict[Cuts,str]):
        '''
        Parameters
        -------------
        sel   : Dictionary mapping cut object (label) to cut expression
        update: If True it will add this selection to existing one
                If False will use this selection as the only selection
                If False and selection already exists will raise exception
        '''
        old_sel = _SELECTION.get()
        if old_sel and not update:
            raise ValueError('Selection already found')

        if old_sel and update:
            sel = {**old_sel, **sel}

        @contextmanager
        def _context():
            token = _SELECTION.set(sel)
            try:
                yield
            finally:
                _SELECTION.reset(token)

        return _context()
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
            log.debug('Using ones as weights')
            weights = numpy.ones_like(masses)
        else:
            log.debug('Calculating MC weights')
            weights = self._get_mc_weights()

        return masses, weights
# ----------------------------------
