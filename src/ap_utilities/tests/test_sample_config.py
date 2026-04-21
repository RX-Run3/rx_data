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
def test_simple():
    '''
    Simplest test
    '''
    obj = scf.SampleConfig(settings='2024_sim10d', samples='by_priority')
    cfg = obj.get_config(categories=[
        'high_priority', 
        'medium_priority', 
        'low_priority',
        'very_low_priority'])

    yaml_str = OmegaConf.to_yaml(cfg)
    print(yaml_str)

    assert isinstance(cfg, DictConfig)
