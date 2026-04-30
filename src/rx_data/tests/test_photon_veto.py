'''
Module with tests for PhotonVeto class
'''

import numpy
import pytest
import pandas as pnd

from dmu     import LogStore
from rx_data import PhotonVeto
from rx_data import EcalCell

log = LogStore.add_logger('rx_data:test_photon_veto')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:photon_veto', 10)
# ----------------------
@pytest.mark.parametrize('name'   , ['L1', 'L2'])
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_from_pandas(name : str, version : str):
    '''
    Simplest test
    '''
    size = 1000
    data                         = dict()
    data[f'{name}_BREMHYPOAREA'] = numpy.random.choice(a = [0, 1, 2], size = size)
    data[f'{name}_BREMHYPOROW' ] = numpy.random.randint(low = -60, high = 60, size = size)
    data[f'{name}_BREMHYPOCOL' ] = numpy.random.randint(low =  14, high = 49, size = size)

    df  = pnd.DataFrame(data)
    obj = PhotonVeto(version = version)
    for _, row in df.iterrows():
        obj.veto(
            row = row,
            lepton_name = name)

    if version == 'v0':
        assert obj.nvetoed == 0
    else:
        assert obj.nvetoed >  0

    log.info(f'Photons vetoed: {obj.nvetoed}/{obj.ntotal}')
# ----------------------
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_from_cell(version : str):
    '''
    Simplest test
    '''
    size= 1000
    obj = PhotonVeto(version = version)
    for _ in range(size):
        cell = EcalCell.random()
        obj.veto_cell(cell = cell)

    if version == 'v0':
        assert obj.nvetoed == 0
    else:
        assert obj.nvetoed >  0

    log.info(f'Photons vetoed: {obj.nvetoed}/{obj.ntotal}')
