'''
Module containing tests for SampleConfig class
'''
import pytest

from dmu          import LogStore
from ap_utilities import SampleConfig
from ap_utilities import SettingsConf

log=LogStore.add_logger('ap_utilities:test_sample_config')
# ----------------------
@pytest.fixture(autouse=True)
def initialize():
    LogStore.set_level('ap_utilities:sample_config', 10)
# ----------------------
@pytest.mark.parametrize('settings', ['2024_sim10d', '2024_sim10f', '2024_sim10g'])
@pytest.mark.parametrize('category', [
        'high_priority',
        'medium_priority',
        'low_priority',
        'very_low_priority'])
def test_simple(
    category : str,
    settings : str):
    '''
    Simplest test
    '''
    obj = SampleConfig(settings=settings, samples='by_priority')
    cfg = obj.get_config(category = category)

    assert isinstance(cfg, SettingsConf)
