'''
Module with PFNDownloader class
'''

from typing import Protocol

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
