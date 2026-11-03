
'''
This module contains tests for the FitConfig class
'''

import pytest
from pathlib      import Path
from dmu          import LogStore
from dmu.generic  import utilities as gut
from rx_common    import Qsq

from fitter       import RXFitConfig
from fitter       import FitModelConf
from rx_common    import MVAWp

log=LogStore.add_logger('fitter:test_fit_config')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:fit_config', 10)
# ----------------------
def test_save(tmp_path : Path):
    '''
    Tests saving config
    '''
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        cfg = RXFitConfig(
            name    = 'test',
            group   = 'test',
            mva_cmb = MVAWp(0.),
            mva_prc = MVAWp(0.),
            q2bin   = Qsq.central,
            mod_cfg = FitModelConf.default(),
        )
        cfg.save()
