'''
Module with tests for BkkChecker class
'''
import pytest

from ap_utilities import LogStore
from ap_utilities import BkkChecker
from ap_utilities import SampleConfig

log = LogStore.add_logger('ap_utilities:tests:test_bkk_check')
# ----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('ap_utilities:bkk_checker', 10)
# ----------------------------------------
@pytest.mark.parametrize('update', [True, False])
def test_simple(update : bool):
    '''
    Will save list of samples to YAML
    '''
    obj = SampleConfig(
        settings = '2024_sim10g',
        samples  = 'by_priority')
    cfg = obj.get_config(category = 'high_priority')

    obj= BkkChecker(
        name = 'test',
        dry  = True,
        cfg  = cfg)
    dsi= obj.save(update = update)

    assert len(dsi.df) > 0

    log.info('\n' + str(dsi.df))
# ----------------------------------------
@pytest.mark.parametrize('update', [True, False])
def test_with_hash(update : bool):
    '''
    Will save list of samples to YAML
    '''
    obj = SampleConfig(
        settings = '2024_sim10g',
        samples  = 'by_priority')
    cfg = obj.get_config(category = 'sim10g')

    obj= BkkChecker(
        name = 'test',
        dry  = True,
        cfg  = cfg)
    dsi= obj.save(update = update)

    assert len(dsi.df) > 0

    log.info('\n' + str(dsi.df))
# ----------------------------------------
