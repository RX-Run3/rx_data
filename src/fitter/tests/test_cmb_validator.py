'''
Module needed to test Combinatorial validator class
'''
import pytest

from fitter    import CmbValidatorConf
from fitter    import CmbInputConfig, CmbValidatorConf, CmbValidationConfig
from rx_common import Component, Mass, Qsq, Trigger
from dmu       import LogStore
from dmu.stats import Model

log=LogStore.add_logger('fitter:test_cmb_validator')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:cmb_validator', 10)
# ----------------------
@pytest.mark.parametrize('mass'   , [Mass.bp_bcor])
@pytest.mark.parametrize('model'  , [Model.exp   ])
@pytest.mark.parametrize('cutflow', ['cmb'       ])
def test_config(
    mass   : Mass,
    model  : Model,
    cutflow: str):
    '''
    Validate configuration
    '''
    input      = CmbInputConfig(
        q2bin   = Qsq.central,
        mass    = mass,
        model   = model,
        trigger = Trigger.rk_ee_ss,
        sample  = Component.data_24,
        cutflow = cutflow,
    )

    validation = CmbValidationConfig.from_file(fname = 'combinatorial/config.yaml') 

    return CmbValidatorConf(
        input      = input,
        validation = validation)
# ----------------------
