'''
Module holding tests for SysPlotter class
'''
import pytest
import mplhep
import matplotlib.pyplot as plt

from rx_common   import Project
from systematics import SysPlotter, SysPlotterCfg

# -------------------------------------
@pytest.fixture(autouse = True)
def style():
    plt.style.use(mplhep.style.LHCb2)
# -------------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_load_config(project : Project):
    '''
    Test loading configuration
    '''
    SysPlotterCfg.from_location(loc = f'tests/{project}_syst_plot.yaml')

