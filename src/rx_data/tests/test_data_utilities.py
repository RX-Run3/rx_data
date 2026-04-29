'''
Script meant to be used to test functions in utilities.py module
'''
import os
import re
import glob
import pytest

from dmu         import LogStore
from dmu.generic import version_management as vman
from rx_common   import Trigger
from rx_data     import utilities as ut

log=LogStore.add_logger('rx_data:test_utilities')
# -----------------------------------------
class Data:
    '''
    Data class
    '''
# -----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_data:utilities'     , 10)
    LogStore.set_level('rx_data:test_utilities', 10)
# -----------------------------------------
def _right_trigger(path : str, trigger : str) -> bool:
    fname = os.path.basename(path)

    # If this is a derived trigger (TRIGGER_cal, TRIGGER_noPID)
    # This is not the right trigger
    # optional \w{10} should take into account MC samples
    regex = f'.*{trigger}' + r'(_[A-Z,a-z]+)(_\w{10})?.root'
    if re.match(regex, fname):
        return False

    return True
# -----------------------------------------
def _get_test_paths(sample : str, trigger : str) -> list[str]:
    '''
    Returns list of paths to ROOT files for a given sample and trigger
    '''
    ana_dir = os.environ['ANADIR']
    path_ver= f'{ana_dir}/Data/rk/main'
    path_ver= vman.get_last_version(dir_path=path_ver, version_only=False)

    path_wc = f'{path_ver}/*{sample}_{trigger}*.root'
    l_path  = glob.glob(path_wc)
    l_path  = [ path for path in l_path if _right_trigger(path=path, trigger=trigger) ]

    if len(l_path) == 0:
        raise FileNotFoundError(f'Not found any path in: {path_wc}')

    return l_path
# -----------------------------------------
@pytest.mark.parametrize('sample, trigger', [
('DATA_24_MagDown_24c2', Trigger.rk_ee_os),
('Bu_JpsiK_mm_eq_DPC'  , Trigger.rk_mm_os)])
def test_info_from_path(sample : str, trigger : Trigger):
    '''
    Tests extraction of information from paths to ROOT files
    '''
    log.info('')
    sample = sample.lower()
    log.info(f'{sample}/{trigger}')

    l_path = _get_test_paths(sample, trigger)

    for path in l_path:
        v1, v2 = ut.info_from_path(path)

        log.debug(f'{v1} == {sample}' )
        log.debug(f'{v2} == {trigger}')

        assert sample  == v1
        assert trigger == v2
# -----------------------------------------

