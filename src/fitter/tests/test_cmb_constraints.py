'''
Module used to test CmbConstraints class
'''
import pytest 

from contextlib   import ExitStack
from pathlib      import Path
from dmu          import LogStore
from dmu.workflow import Cache
from dmu.generic  import UnpackerModel, utilities           as gut
from dmu.stats    import ConstraintND
from dmu.stats    import ParameterLibrary as PL

from rx_common    import Cuts, Qsq, Region
from rx_selection import selection           as sel

from fitter       import CmbConstraints
from fitter       import CombinatorialConf

log=LogStore.add_logger('test_cmb_constraints')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:cmb_constraints', 10)
    LogStore.set_level('dmu:stats:minimizers'  , 10)
    LogStore.set_level('dmu:stats:fitter'      , 10)
# ----------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_simple(q2bin : Qsq, tmp_path : Path):
    '''
    Simplest test of CmbConstraints
    '''
    region = Region.brem_x12
    data   = gut.load_data(
        package= 'fitter_data', 
        fpath  = 'rare/rk/ee/comb.yaml')

    with ExitStack() as stack:
        stack.enter_context(UnpackerModel.package(name = 'fitter_data'))
        cfg = CombinatorialConf(**data)
        cfg = cfg.specialize(q2bin = q2bin)

    d_sel = {Cuts.cmb : 'mva_cmb > 0.6 && mva_cmb < 0.9'}
    with ExitStack() as stack:
        stack.enter_context(Cache.cache_root(path = tmp_path))
        stack.enter_context(sel.custom_selection(d_sel = d_sel))
        stack.enter_context(PL.parameter_schema(cfg = cfg.constraints.mod_cfg.yields))

        calc      = CmbConstraints(
            reg   = region,
            cfg   = cfg,
            q2bin = q2bin)

        constraint = calc.get_constraint()

    assert isinstance(constraint, ConstraintND)

    print(constraint)
# ----------------------
