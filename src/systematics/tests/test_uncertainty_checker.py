'''
Module with test for UncertaintyChecker class
'''
import numpy
import pytest
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from typing      import Final
from pytest      import MonkeyPatch
from pathlib     import Path
from systematics import UncertaintyChecker, UncertaintyCheckerCfg
from dmu.generic import rxran

_SIZE : Final[int] = 5000
# -------------------------------------
@pytest.fixture(autouse = True)
def initialize():
    plt.style.use(mplhep.style.LHCb2)
    with rxran.seed(value = 42):
        yield
# ----------------------------------------
def _get_df() -> pnd.DataFrame:
    df           = pnd.DataFrame()
    df['nFixed'] = numpy.random.choice(a = [0, 1, 2, 3], size = _SIZE)
    df['Gen'   ] = 1.00

    pars = {
        0 : 'None',
        1 : 'a',
        2 : 'b',
        3 : 'c',
    }

    errors = {
        0: (0.30, 0.05),
        1: (0.20, 0.03),
        2: (0.10, 0.02),
        3: (0.05, 0.01),
    }

    df['Fixed'] = df['nFixed'].map(pars)
    df['Error'] = numpy.nan

    for n_fixed, (mean, width) in errors.items():
        mask   = df['nFixed'] == n_fixed
        errors = numpy.random.normal(loc=mean, scale=width, size=mask.sum())

        df.loc[mask, 'Error'] = errors

    return df
# ----------------------------------------
def test_config():
    '''
    Tests loading config
    '''
    cfg = UncertaintyCheckerCfg.from_package(
        package = 'systematics_data',
        loc     = 'tests/rk_uncertainty_plot.yaml')

    assert isinstance(cfg, UncertaintyCheckerCfg)
# ----------------------------------------
def test_checker(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path):
    '''
    Test plotting though UncertaintyChecker
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    cfg = UncertaintyCheckerCfg.from_package(
        package = 'systematics_data',
        loc     = 'tests/rk_uncertainty_plot.yaml')

    df = _get_df()
    chk= UncertaintyChecker(
        df = df,
        cfg= cfg)
    chk.run()
# ----------------------------------------
