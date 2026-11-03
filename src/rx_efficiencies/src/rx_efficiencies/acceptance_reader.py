'''
Module holding AcceptanceReader class
'''

import os
import pandas as pnd

from pathlib     import Path
from dmu         import LogStore
from dmu.generic import get_last_version
from rx_common   import Component, Project

log=LogStore.add_logger('rx_efficiencies:acceptance_reader')
#----------------------------------
class AcceptanceReader:
    '''
    Class meant to read Geometric acceptances calculated from rapidsim ntuples
    '''
    #----------------------------------
    def __init__(
        self,
        year   : str,
        project: Project,
        sample : Component):
        '''
        Parameters
        ---------------
        year   : E.g. 2024, needed to pick correct file
        project: E.g. rk, rkst
        sample : E.g. Bd_psi2SKst_mm_eq_DPC
        '''
        self._year    = year
        self._sample  = sample
        self._project = project
        self._ana_dir = Path(os.environ['ANADIR'])
    #----------------------------------
    def _get_energy(self) -> str:
        '''
        Returns
        -----------------
        Center of mass energy string associated to _year
        '''
        d_energy  = {
                '2011' : '7TeV',
                '2012' : '8TeV',
                '2015' : '13TeV',
                '2016' : '13TeV',
                '2017' : '13TeV',
                '2018' : '13TeV',
                '2024' : '14TeV', # TODO: This needs to be updated, when 13.6 TeV files be available
                                  # Will average 2018 and 2024 for now.
                }

        if self._year not in d_energy:
            raise ValueError(f'Invalid year: {self._year}')

        return d_energy[self._year]
    #----------------------------------
    def read(self) -> float:
        '''
        Reads JSON files, returns acceptance value
        '''
        prc_dir = self._ana_dir / 'efficiencies/acceptances'
        vers    = get_last_version(dir_path=prc_dir, version_only=True)
        energy  = self._get_energy()
        prc_path= prc_dir / f'{vers}/{self._project}/acceptances_{energy}.json'

        if not prc_path.exists():
            raise FileNotFoundError(f'File not found: {prc_path}')

        log.info(f'Loading acceptances from: {prc_path}')
        df          = pnd.read_json(prc_path)
        df_filtered = df[ df.Sample == self._sample.original.value ]
        if len(df_filtered) == 0:
            log.info(df)
            raise ValueError(f'Process {self._sample} not found in {prc_path}')

        try:
            [val] = df_filtered.Physical.tolist()
        except ValueError as exc:
            raise ValueError(f'More than one acceptance for process: {self._sample}') from exc

        return val
#----------------------------------
