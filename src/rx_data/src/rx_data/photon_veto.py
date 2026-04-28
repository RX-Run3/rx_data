'''
Module containing PhotonVeto class
'''
import pandas as pnd

# ------------------------------------
class PhotonVeto:
    '''
    Class meant to veto photons based on
    location in calorimeter
    '''
    # ------------------------------------
    def __init__(self):
        pass
    # ------------------------------------
    def veto(
        self, 
        lepton_name : str,
        row         : pnd.Series) -> bool:
        '''
        Parameters
        ---------------
        lepton_name: E.g. L1 or L2
        row        : Pandas series with information on Lepton and its photon

        Return
        ---------------
        True if photon is meant to be picked, False otherwise
        '''

        return True
# ------------------------------------
