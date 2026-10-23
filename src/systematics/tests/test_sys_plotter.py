'''
Module holding tests for SysPlotter class
'''
import numpy
import pytest
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from typing      import Final
from pathlib     import Path
from rx_common   import Project
from dmu.generic import rxran
from systematics import SysPlotter, SysPlotterCfg

_SIZE : Final[int] = 5000
# -------------------------------------
@pytest.fixture(autouse = True)
def initialize():
    plt.style.use(mplhep.style.LHCb2)
    with rxran.seed(value = 42):
        yield
# -------------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_load_config(project : Project):
    '''
    Test loading configuration
    '''
    SysPlotterCfg.from_location(loc = f'tests/{project}_syst_plot.yaml')
# -------------------------------------
def _get_df() -> pnd.DataFrame:
    '''
    Returns dataframe as expected from outputs of systematic toys
    '''
    df           = pnd.DataFrame()
    df['rk_nom'] = numpy.random.normal(loc = 1.00, scale = 0.01, size = _SIZE)
    df['rk_s1' ] = numpy.random.normal(loc = 1.03, scale = 0.01, size = _SIZE)
    df['rk_s2' ] = numpy.random.normal(loc = 0.90, scale = 0.01, size = _SIZE)

    return df
# -------------------------------------
def test_plotter(monkeypatch, tmp_path : Path):
    '''
    Test plotter
    '''
    monkeypatch.setenv('ANADIR', tmp_path)

    df  = _get_df()
    cfg = SysPlotterCfg.from_location(loc = 'tests/rk_syst_plot.yaml')
    ptr = SysPlotter(
        cfg = cfg,
        df  = df)
    syst = ptr.run()

    s1_exp = 2.978417768181100
    s2_exp = 9.958889599473252

    assert numpy.isclose(syst['rk_s1'], s1_exp)
    assert numpy.isclose(syst['rk_s2'], s2_exp)

    print(syst)
# -------------------------------------
