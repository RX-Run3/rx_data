'''
Module with tests for BkkChecker class
'''
import pytest

from ap_utilities import LogStore
from ap_utilities import BkkChecker
from ap_utilities import SampleConfig 
from dmu.generic  import utilities     as gut

log = LogStore.add_logger('ap_utilities:tests:test_bkk_check')
# ----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('ap_utilities:bkk_checker', 10)
# ----------------------------------------
def test_simple():
    '''
    Will save list of samples to YAML
    '''
    obj = SampleConfig(
        settings = '2024_sim10g',
        samples  = 'by_priority')
    cfg = obj.get_config(categories=['sim10g'])

    obj= BkkChecker(
        name = 'test', 
        dry  = True,
        cfg  = cfg)
    df = obj.save()

    assert len(df) > 0

    log.info('\n' + str(df))
# ----------------------------------------
def test_nick_evt():
    '''
    Will test reading when there are both evt_type and nickname sections 
    '''
    d_cfg        = gut.load_conf(package='ap_utilities_data', fpath='tests/nick_evt.yaml')
    d_sections   = d_cfg['sections']
    for name, d_section in d_sections.items():
        log.info(f'Processing section: {name}')
        obj=BkkChecker(name, d_section)
        obj.save(dry=True)
# ----------------------------------------
def test_multithreaded():
    '''
    Will save list of samples to YAML using 4 threads
    '''
    d_cfg    = gut.load_conf(package='ap_utilities_data', fpath='tests/rd_samples.yaml')
    d_config = d_cfg['sections']
    for name, cfg in d_config.items():
        log.info(f'Processing section: {name}')
        obj=BkkChecker(name=name, cfg=cfg)
        obj.save(dry=True, nthreads=4)
# ----------------------------------------
@pytest.mark.parametrize('settings', ['2024_sim10d', '2024_sim10f'])
def test_with_sample_config(settings : str):
    '''
    Tests using config made with SampleConfig
    '''
    obj = scf.SampleConfig(settings=settings, samples='by_priority')
    cfg = obj.get_config(categories=['high', 'medium', 'low'])

    for name, section in cfg.sections.items():
        log.info(f'Processing section: {name}')
        obj=BkkChecker(name, section)
        obj.save(dry=True)

