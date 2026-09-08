'''
Module with DataStore class
'''
import numpy
import numpy.typing as npt
import pandas       as pnd

from pathlib        import Path
from contextlib     import contextmanager
from contextvars    import ContextVar
from dmu            import LogStore
from dmu.generic    import utilities as sut
from rx_q2          import Q2SmearCorrector
from rx_common      import Cuts, Qsq, Trigger, Component, Mass
from .database_conf import DatabaseConf

log           = LogStore.add_logger('hqm:data_store')
type NpFltArr = npt.NDArray[numpy.float64]

_SELECTION    : ContextVar[dict[str,str] | None] = ContextVar('_SELECTION'   , default = None) 
_SMEAR_MASSES : ContextVar[bool                ] = ContextVar('_SMEAR_MASSES', default = True) 
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

        self.__full_sel : dict[str,int] = dict()

        df = self._load_df()

        if self._comp.is_mc and _SMEAR_MASSES.get():
            df = self.__smear_masses(df = df) 
        else:
            log.info(f'Not smearing masses for: {self._comp}')

        self.__df = self._select_data(df = df)
    # ----------------------------------
    @property
    def columns(self) -> list[str]:
        '''
        List of columns in already preprocessed dataframe
        '''
        return self.__df.columns.to_numpy().tolist()
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
        cutflow : dict[str,int] = dict()
        cutflow['none'] = len(df)
        for name, expr in sel.items():
            log.debug(f'{name:<20}{expr}')

            if expr != 'true':
                df = df.query(expr)

            cutflow[expr] = len(df)

        self.__full_sel.update(cutflow)

        return df
    # ----------------------------------
    @classmethod
    def selection(
        cls, 
        update : bool,
        sel    : dict[str,str]):
        '''
        Parameters
        -------------
        sel   : Dictionary mapping cut object (label) to cut expression, use 'true' to skip cut
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
    @classmethod
    def smear_masses(cls, value : bool):
        '''
        Parameters
        -------------
        value: If true (default) will run smearing of masses before selection
        '''
        if value is False:
            log.warning('Turning off smearing')

        @contextmanager
        def _context():
            token = _SMEAR_MASSES.set(value)
            try:
                yield
            finally:
                _SMEAR_MASSES.reset(token)

        return _context()
    # ----------------------------------
    def save_selection(self, path : Path) -> None:
        '''
        Parameters
        ----------------
        path: Path to JSON file where output will go
        '''
        sut.dump_json(
            exists_ok = True,
            path      = path,
            data      = self.__full_sel)
    # ----------------------------------
    def __smear_masses(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        df: Dataframe with data to smear

        Returns
        --------------
        DataFrame with smeared columns. 
        q2 column is smeared and original kept around as `q2_org`
        '''
        smr = Q2SmearCorrector(channel = self._trig.channel, add_original = True)
        log.info(f'Smearing masses for: {self._comp}')
        df  = smr.get_df(
            replace = True,
            df      = df)

        df['q2_org'] = df['q2'].to_numpy()
        df['q2'    ] = df['Jpsi_Mass'] * df['Jpsi_Mass']

        return df
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
