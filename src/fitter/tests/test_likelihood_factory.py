'''
Module meant to test DataFitter class
'''
import pytest

from pathlib         import Path
from dmu             import LogStore
from dmu.stats       import ParameterLibrary as PL
from dmu.stats       import zfit
from dmu.generic     import UnpackerModel, utilities  as gut
from dmu.workflow    import Cache
from rx_common       import Cuts, Mass, Qsq, Component, Region
from rx_data         import RDFGetter
from rx_selection    import selection  as sel
from fitter          import LikelihoodFactory
from zfit.core.loss  import ExtendedUnbinnedNLL
from fitter          import FitModelConf
from fitter          import ParametricConf

log=LogStore.add_logger('fitter:test_likelihood_factory')

_DATA_PREPROCESSOR_TARGET = 'fitter.likelihood_factory.DataPreprocessor'
mark_data_preprocessor    = pytest.mark.usefixtures('_patch_data_preprocessor')

_DATA_MODEL_TARGET = 'fitter.likelihood_factory.DataModel'
mark_data_model    = pytest.mark.usefixtures('_patch_data_model')

pytestmark = [mark_data_preprocessor, mark_data_model]
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('dmu:stats:fitter'         , 10)
    LogStore.set_level('rx_data:rdf_getter'       , 30)
    LogStore.set_level('rx_misid:sample_weighter' , 10)
    LogStore.set_level('fitter:sim_fitter'        , 10)
    LogStore.set_level('fitter:data_model'        , 10)
    LogStore.set_level('fitter:data_preprocessor' , 10)
    LogStore.set_level('fitter:likelihood_factory', 10)

    with RDFGetter.max_entries(value = 100_000):
        yield
# ----------------------
def _update_block(
    cfg       : FitModelConf, 
    q2bin     : Qsq,
    component : Component) -> FitModelConf:
    '''
    Parameters
    -------------
    cfg      : Fit config as loaded from YAML file 
    component: Name of component whose block will be updated

    Returns
    -------------
    config with updated category name 
    '''
    conf = cfg.components[q2bin][component]
    if not isinstance(conf, ParametricConf):
        raise ValueError('Invalid config')

    block = 1
    conf.add_category_suffix(suffix = f'b{block}')

    return cfg
# -------------------------------------------
def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='rare/rk/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    obs = zfit.Space('B_Mass_smr', limits=(5000, 6000))
    with PL.parameter_schema(cfg=cfg.yields),\
         Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=100_000):

        ftr = LikelihoodFactory(
            name   = 'muon',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.jpsi,
            cfg    = cfg)
        nll = ftr.run()

    assert isinstance(nll.nll, ExtendedUnbinnedNLL)
# -------------------------------------------
