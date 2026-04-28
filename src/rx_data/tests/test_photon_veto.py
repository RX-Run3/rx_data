'''
Module with tests for PhotonVeto class
'''

import pytest
import pandas as pnd

from rx_data import PhotonVeto

@pytest.mark.parametrize('name', ['L1', 'L2'])
def test_simple(name : str):
    '''
    Simplest test
    '''
    row = pnd.Series({})

    obj = PhotonVeto()
    obj = obj.veto(row = row, lepton_name = name)
