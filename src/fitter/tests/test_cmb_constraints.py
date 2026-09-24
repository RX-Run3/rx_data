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

from rx_common    import Brem, Component, Qsq
from rx_selection import selection as sel

from rx_common    import MVAWp
from fitter       import CmbConstraints
from fitter       import RXFitConfig, FitModelConf

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

    with UnpackerModel.package(name = 'fitter_data'):
        yield
# --------------------------------------------------------------
def _get_fit_config(q2bin : Qsq) -> RXFitConfig:
    '''
    Parameters
    -------------
    q2bin: E.g. central

    Returns
    -------------
    Object storing fit configuration
    '''
    data    = gut.load_data(package='fitter_data', fpath = 'rare/rk/ee/data.yaml')
    mod_cfg = FitModelConf(**data)

    return RXFitConfig(
        name    = 'test',
        group   = 'test',
        mod_cfg = mod_cfg, 
        mva_cmb = MVAWp(0.9),
        mva_prc = MVAWp(0.8),
        q2bin   = q2bin,
        log_lvl = 10,
    )
# ----------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_simple(q2bin : Qsq, tmp_path : Path):
    '''
    Simplest test of CmbConstraints
    '''
    brem   = Brem.brx12
    signal = Component.bpkpee
    cfg_fit= _get_fit_config(q2bin = q2bin)

    with ExitStack() as stack:
        stack.enter_context(Cache.cache_root(path = tmp_path))
        stack.enter_context(sel.custom_selection(d_sel = cfg_fit.overriding_selection))
        stack.enter_context(PL.parameter_schema(cfg = cfg_fit.mod_cfg.yields))

        calc        = CmbConstraints(
            brem    = brem,
            signal  = signal,
            cfg_fit = cfg_fit)

        constraint = calc.get_constraint()

    assert isinstance(constraint, ConstraintND)

    print(constraint)
# ----------------------
