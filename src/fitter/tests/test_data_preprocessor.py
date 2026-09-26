'''
Module meant to hold tests for the DataPreprocessor class
'''
import pytest
import matplotlib.pyplot as plt

from contextlib    import ExitStack
from pathlib       import Path
from dmu.stats     import zfit
from dmu.generic   import utilities as gut
from dmu.stats     import utilities as sut
from dmu           import LogStore
from dmu.workflow  import Cache
from rx_common     import Correction, Cuts, Qsq, Region, Trigger, Component
from rx_data       import RDFGetter
from rx_misid      import MisIDSampleWeights
from zfit.data     import Data      as zdata
from fitter        import DataPreprocessor

log=LogStore.add_logger('fitter:test_data_preprocessor')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:data_preprocessor', 10)
# -------------------------------------------------
@pytest.mark.fixture(autouse=True)
def max_entries():
    '''
    This fixture runs for all the tests in this module
    '''
    with RDFGetter.max_entries(value=100_000):
        yield
# -------------------------------------------------
def _validate_data(
    data     : zdata, 
    tmp_path : Path) -> None:
    '''
    Makes validation plots from zfit data
    '''
    plt_path = tmp_path / 'plot.png'

    arr_data = data.numpy()
    rng      = sut.range_from_obs(obs=data.space)
    if data.weights is None:
        arr_wgt = None
    else:
        arr_wgt = data.weights.numpy()

    log.info(f'Saving to: {plt_path}')
    plt.hist(arr_data, histtype='step', bins=100, range=rng, weights=arr_wgt)
    plt.savefig(plt_path)
    plt.close()
# -------------------------------------------------
def test_database(tmp_path : Path):
    '''
    Test reading from database
    '''
    obs = zfit.Space('B_Mass', limits=(5180, 6000))

    ctx_1 = Cache.cache_root(path = tmp_path)
    ctx_2 = DataPreprocessor.use_database()

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        prp = DataPreprocessor(
            name   = 'main',
            obs    = obs,
            sample = Component.bpkpjpsiee,
            trigger= Trigger.rk_ee_os,
            wgt_cfg= None,
            q2bin  = Qsq.jpsi)
        dat = prp.get_data()

    _validate_data(data=dat, tmp_path = tmp_path)
# -------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpjpsimm])
def test_mc(
    tmp_path : Path, 
    component: Component):
    '''
    Test MC over few entries
    '''
    obs = zfit.Space('B_Mass', limits=(5180, 6000))

    ctx_1 = Cache.cache_root(path = tmp_path)
    ctx_2 = RDFGetter.max_entries(value = 1000)

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        prp = DataPreprocessor(
            name   = 'main',
            obs    = obs,
            sample = component,
            trigger= Trigger.rk_mm_os,
            wgt_cfg= None,
            q2bin  = Qsq.jpsi)
        dat = prp.get_data()

    _validate_data(data=dat, tmp_path = tmp_path)
# -------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpjpsimm])
def test_cache(
    tmp_path : Path, 
    component: Component):
    '''
    Tests caching of dataset
    '''
    obs = zfit.Space('B_Mass', limits=(5180, 6000))

    ctx_1 = Cache.cache_root(path = tmp_path)
    ctx_2 = RDFGetter.max_entries(value = 1000)

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        prp_1 = DataPreprocessor(
            name   = 'main',
            obs    = obs,
            sample = component,
            trigger= Trigger.rk_mm_os,
            wgt_cfg= None,
            q2bin  = Qsq.jpsi)
        prp_1.get_data()

        prp_2 = DataPreprocessor(
            name   = 'main',
            obs    = obs,
            sample = component,
            trigger= Trigger.rk_mm_os,
            wgt_cfg= None,
            q2bin  = Qsq.jpsi)
        prp_1.get_data()

        assert prp_1.hash == prp_2.hash
# -------------------------------------------------
@pytest.mark.parametrize('component', [
    Component.data_24_md_c2,
    Component.bpkpjpsimm])
def test_muon(
    tmp_path : Path, 
    component: Component):
    '''
    Tests class with toys
    '''
    obs = zfit.Space('B_Mass', limits=(5180, 6000))

    with Cache.cache_root(path = tmp_path):
        prp = DataPreprocessor(
            name   = 'main',
            obs    = obs,
            sample = component,
            trigger= Trigger.rk_mm_os,
            wgt_cfg= None,
            q2bin  = Qsq.jpsi)
        dat = prp.get_data()

    _validate_data(data=dat, tmp_path = tmp_path)
# -------------------------------------------------
@pytest.mark.parametrize('component', [
    Component.data_24_md_c2,
    Component.bpkpjpsiee])
@pytest.mark.parametrize('brem_cat', [0, 1, 2])
def test_brem_cat_data(
    tmp_path : Path, 
    component: Component, 
    brem_cat : int):
    '''
    Tests class with toys
    '''
    obs = zfit.Space('B_Mass', limits=(4500, 6000))
    cut = {Cuts.brem : f'nbrem == {brem_cat}'}

    with Cache.cache_root(path = tmp_path):
        prp = DataPreprocessor(
            name      = 'main',
            obs       = obs,
            sample    = component, 
            trigger   = Trigger.rk_ee_os,
            wgt_cfg   = None,
            selection = cut, 
            q2bin     = Qsq.jpsi)
        dat = prp.get_data()

    _validate_data(data=dat, tmp_path = tmp_path)
# -------------------------------------------------
@pytest.mark.parametrize('component', [
    Component.bpkkk,
    Component.bpkpipi])
@pytest.mark.parametrize('region', [Region.bpkk, Region.bppipi])
@pytest.mark.parametrize('kind'  , ['signal'   ,     'control'])
def test_with_pid_weights(
    tmp_path : Path,
    component: Component,
    region   : Region, 
    kind     : str) -> None:
    '''
    Parameters
    -------------
    sample: MC sample, weights are not applied to data
    region: Kind of control region
    kind  : Either 'signal' or 'control'
    '''
    data = gut.load_data(package='fitter_data', fpath='model/weights/weights.yaml')
    cfg  = MisIDSampleWeights(**data)

    with Cache.cache_root(path = tmp_path):
        prp  = DataPreprocessor(
            name      = 'main',
            obs       = region.obs,
            sample    = component,
            trigger   = Trigger.rk_ee_nopid,
            wgt_cfg   = {Correction.pid : cfg},
            selection = {Cuts.pid_l : '(1)'}, 
            is_sig    = kind == 'signal',
            q2bin     = Qsq.jpsi)
        dat  = prp.get_data()

    _validate_data(data=dat, tmp_path = tmp_path)
# -------------------------------------------------
