'''
Module needed to test Combinatorial validator class
'''
import pytest

from fitter import CmbValidatorConf
from fitter import CmbValidator

# ----------------------
@pytest.mark.parametrize('sel', ['default'])
@pytest.mark.parametrize('fit', ['default'])
@pytest.mark.parametrize('cut', ['cmb'])
def test_simple(sel : str, fit : str, cut : str):
    '''
    Entry point
    '''
    cfg = CmbValidatorConf(
        sel = sel,
        fit = fit,
        cut = cut)

    obj = CmbValidator(cfg = cfg)
    obj.run()
# ----------------------
