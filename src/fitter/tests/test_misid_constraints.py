'''
Module containing tests for MisIDConstraints class
'''
import pytest

from pathlib       import Path
from rx_common     import Cuts, Qsq
from rx_selection  import selection as sel
from rx_data       import RDFGetter
from dmu           import LogStore
from dmu.workflow  import Cache
from dmu.generic   import UnpackerModel, utilities     as gut
from fitter        import MisIDConstraints
from fitter        import FitModelConf

log=LogStore.add_logger('fitter:test_misid_constraints')
# --------------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:workflow:cache'      , 30)
    LogStore.set_level('fitter:base_fitter'      , 30)
    LogStore.set_level('fitter:sim_fitter'       , 10)
    LogStore.set_level('fitter:data_preprocessor', 10)
    LogStore.set_level('rx_misid:sample_weighter', 20)
# ----------------------
@pytest.mark.skip(reason = 'Turn off very slow tests for now')
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_simple(q2bin : Qsq, tmp_path : Path) -> None:
    '''
    Basic test for building misID component
    '''
    data = gut.load_data(package='fitter_data', fpath='misid/rk/ee/data_misid.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    with sel.custom_selection(d_sel={Cuts.brem : 'nbrem != 0'}),\
         RDFGetter.max_entries(value = -1),\
         Cache.cache_root(path = tmp_path):
            obj = MisIDConstraints(
                cfg      = cfg,
                q2bin    = q2bin)
            constraints = obj.get_constraints()

    print(constraints)
# ----------------------
