'''
Module holding DatabaseBuilder and its config
'''
from rx_common import Qsq, Trigger, Component

from dmu import LogStore

log=LogStore.add_logger('hqm:database_builder')
# ----------------------
class DatabaseBuilderConf:
    '''
    Class meant to hold configuration for DatabaseBuilder
    '''
    # ----------------------
    @classmethod
    def load(cls) -> 'DatabaseBuilderConf':
        return cls()
# ----------------------
class DatabaseBuilder:
    '''
    Class meant to create parquet files with data needed by
    DataStore
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
    # ----------------------------------
    def run(self, cfg : DatabaseBuilderConf) -> None:
        '''
        Parameters
        ----------------
        cfg: Config object
        '''
# ----------------------
