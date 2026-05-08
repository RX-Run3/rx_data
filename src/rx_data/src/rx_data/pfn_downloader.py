'''
Module with PFNDownloader class
'''

from functools import cached_property
import os
import tqdm

from typing  import Protocol
from pathlib import Path
from dmu     import LogStore

log=LogStore.add_logger('rx_data:pfn_downloader')
# ---------------------------------
class PFNHolder(Protocol):
    '''
    Class meant to represent object that can provide PFNs
    '''
    def pfns(self) -> list[str]:
        ...
# ---------------------------------
class PFNDownloader:
    '''
    Class meant to download PFNs
    '''
    def __init__(self, samples : PFNHolder):
        '''
        Parameters
        ---------------
        samples: Object representing samples in the AnalysisProductions
        '''
        self._samples = samples
    # ------------------------------------
    def run(self) -> None:
        '''
        Starts download
        '''
        if not self._samples.pfns:
            raise ValueError('No PFNs found')
# ---------------------------------
