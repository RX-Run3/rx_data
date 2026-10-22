'''
Module holding tests for SysPlotter class
'''
import pytest
import mplhep
import matplotlib.pyplot as plt

from systematics import SysPlotter, SysPlotterCfg

# -------------------------------------
@pytest.fixture(autouse = True)
def style():
    plt.style.use(mplhep.style.LHCb2)
# -------------------------------------
def test_load_config():
    '''
    Test loading configuration
    '''
    SysPlotterCfg.from_location(loc = 'tests/syst_plot.yaml')

