'''
Module needed to test Combinatorial validator class
'''
import pytest

from fitter import CmbValidatorConf
from fitter import CmbValidator

from dmu import LogStore

log=LogStore.add_logger('fitter:test_cmb_validator')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:cmb_validator', 10)
# ----------------------
@pytest.mark.parametrize('sel', ['default'])
@pytest.mark.parametrize('fit', ['default'])
@pytest.mark.parametrize('cut', ['cmb'    ])
@pytest.mark.parametrize('mod', ['expo'   ])
def test_simple(
    mod : str,
    sel : str, 
    fit : str, 
    cut : str):
    '''
    Entry point
    '''
    cfg = CmbValidatorConf(
        mod = mod,
        sel = sel,
        fit = fit,
        cut = cut)

    _ = cfg.selection
    _ = cfg.fit_cfg
    _ = cfg.cutflow

    obj = CmbValidator(cfg = cfg)
    obj.run()
# ----------------------
