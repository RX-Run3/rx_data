'''
Script meant to be used to test functions in utilities.py module
'''
import os
import yaml
import pytest

from dmu.logging.log_store import LogStore
from rx_data               import utilities as ut

log=LogStore.add_logger('rx_data:test_utilities')
# -----------------------------------------
class Data:
    '''
    Data class
    '''
    d_sample : str
# -----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('rx_data:utilities', 10)

    ana_dir   = os.environ['ANADIR']
    yaml_path = f'{ana_dir}/Data/samples/main.yaml'
    with open(yaml_path, encoding='utf-8') as ifile:
        Data.d_sample = yaml.safe_load(ifile)
# -----------------------------------------
def _get_test_paths(sample : str, trigger : str) -> list[str]:
    l_path = Data.d_sample[sample][trigger]

    return l_path
# -----------------------------------------
@pytest.mark.parametrize('sample, trigger', [
('DATA_24_MagDown_24c2', 'Hlt2RD_BuToKpEE_MVA'),
('Bu_JpsiK_mm_eq_DPC'  , 'Hlt2RD_BuToKpMuMu_MVA')])
def test_info_from_path(sample : str, trigger : str):
    '''
    Tests extraction of information from paths to ROOT files
    '''
    log.info('')
    log.info(f'{sample}/{trigger}')

    l_path = _get_test_paths(sample, trigger)

    for path in l_path[:1]:
        v1, v2 = ut.info_from_path(path)

        log.info(v1)
        log.info(v2)
# -----------------------------------------
def test_is_ee():
    '''
    Test that trigger is recognized as electron trigger
    '''
    assert ut.is_ee(trigger='Hlt2RD_BuToKpEE_MVA')
    assert ut.is_ee(trigger='Hlt2RD_BuToKpEE_SameSign_MVA')
    assert ut.is_ee(trigger='Hlt2RD_BuToKpEE_MVA_misid')

    assert not ut.is_ee(trigger='Hlt2RD_BuToKpMuMu_MVA')
    assert not ut.is_ee(trigger='Hlt2RD_BuToKpMuMu_SameSign_MVA')
    assert not ut.is_ee(trigger='Hlt2RD_B0ToKpPimMuMu_MVA')
    assert not ut.is_ee(trigger='Hlt2RD_B0ToKpPimMuMu_SameSign_MVA')
# -----------------------------------------
def test_is_reso():
    '''
    Tests is_reso
    '''
    assert not ut.is_reso(q2bin='low')
    assert not ut.is_reso(q2bin='central')
    assert not ut.is_reso(q2bin='high')

    assert ut.is_reso(q2bin='jpsi')
    assert ut.is_reso(q2bin='psi2')
# -----------------------------------------
