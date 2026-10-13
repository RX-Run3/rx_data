'''
Module with Reader class used to read weights to normalize between inclusive samples
'''

import os
import pandas    as pnd

from typing    import Final
from functools import lru_cache
from dmu       import LogStore
from rx_common import Component
from .         import pdg_utils as pu

log = LogStore.add_logger('rx_fitter:inclusive_sample_weights')

_FU      : Final[float] = 0.408
_FS      : Final[float] = 0.100

_BD_PROC : Final[set[Component]]= {Component.bdjpsixee, Component.bdjpsixmm}
_BU_PROC : Final[set[Component]]= {Component.bpjpsixee, Component.bpjpsixmm}
_BS_PROC : Final[set[Component]]= {Component.bsjpsixee, Component.bsjpsixmm}
#---------------------------
class Reader:
    '''
    Class used to add weights that normalize inclusive samples
    '''
    #---------------------------
    def __init__(self, df : pnd.DataFrame):
        self._df = df
    #---------------------------
    @lru_cache(maxsize=10)
    @staticmethod
    def _get_br_wgt(proc : Component) -> float:
        '''
        Will return ratio:

        decay file br / pdg_br
        '''

        #--------------------------------------------
        #Decay B+sig
        #0.1596  MyJ/psi    K+           SVS ;
        #--------------------------------------------
        #Decay B0sig
        #0.1920  MyJ/psi    MyK*0        SVV_HELAMP PKHplus PKphHplus PKHzero PKphHzero PKHminus PKphHminus ;
        #--------------------------------------------
        #Decay B_s0sig
        #0.1077  MyJ/psi    Myphi        PVV_CPLH 0.02 1 Hp pHp Hz pHz Hm pHm;
        #--------------------------------------------

        if proc in _BU_PROC:
            return pu.get_bf('B+ --> J/psi(1S) K+') / 0.1596

        if proc in _BD_PROC:
            return pu.get_bf('B0 --> J/psi(1S) K*(892)0') / 0.1920

        if proc in _BS_PROC:
            return pu.get_bf('B_s()0 --> J/psi(1S) phi') / 0.1077

        raise ValueError(f'Invalid process {proc}')
    #---------------------------
    @lru_cache(maxsize = 10)
    @staticmethod
    def _get_hd_wgt(proc : Component) -> float:
        '''
        Will return hadronization fractions used as weights
        '''
        log.info(f'Getting hadronization weights for sample {proc}')

        if proc in _BS_PROC:
            return _FS

        if proc in _BU_PROC | _BD_PROC:
            return _FU

        raise ValueError(f'Invalid process: {proc}')
    #---------------------------
    def _get_stats(self, path : str) -> tuple[str, pnd.DataFrame]:
        proc = os.path.basename(path).replace('.json', '')
        df   = pnd.read_json(path)

        return proc, df
    #---------------------------
    def _good_rows(self, r1 : pnd.Series, r2 : pnd.Series) -> bool:
        if {r1.Polarity, r2.Polarity} != {'MagUp', 'MagDown'}:
            log.error('Latest rows are not of opposite polarities')
            return False

        if r1.Events <= 0 or r2.Events <= 0:
            log.error('Either polarity number of events is negative')
            return False

        return True
    #---------------------------
    @lru_cache(maxsize=10)
    @staticmethod
    def _get_st_wgt(proc : Component) -> float:
        '''
        Parameters
        ---------------
        proc: Name of process

        Returns
        ---------------
        Weight representing statistics of sample, i.e. number of events in MCDecayTree
        Three samples have same size, will use 1 for now
        '''
        _ = proc

        return 1
    #---------------------------
    def _get_weight(self, row : pnd.Series) -> float:
        '''
        Parameters
        --------------
        row: Row representing an event

        Returns
        --------------
        Product of statistics, hadronization fraction and branching fraction weights
        '''
        w1 = Reader._get_st_wgt(row.proc)
        w2 = Reader._get_hd_wgt(row.proc)
        w3 = Reader._get_br_wgt(row.proc)

        return w1 * w2 * w3
    #---------------------------
    def get_weights(self) -> pnd.Series:
        '''
        Returns:

        Pandas series with sample weights
        '''
        sr_wgt = self._df.apply(self._get_weight, axis=1)

        return sr_wgt
#---------------------------
