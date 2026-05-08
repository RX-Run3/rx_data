'''
Module with PFNDownloader class
'''

from post_ap import Samples

# ---------------------------------
class PFNDownloader:
    '''
    Class meant to download PFNs
    '''
    def __init__(self, samples : Samples):
        '''
        Parameters
        ---------------
        samples: Object representing samples in the AnalysisProductions
        '''
        self._samples = samples
# ---------------------------------
