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
from rx_common       import Trigger
from rx_common       import Qsq, Component
from rx_data         import RDFGetter
from fitter          import NLLConf
from fitter          import LikelihoodFactory
from zfit.core.loss  import ExtendedUnbinnedNLL
from fitter          import FitModelConf
from fitter          import ParametricConf

from patch_classes   import TestDataPreprocessor, TestDataModel

log=LogStore.add_logger('fitter:test_likelihood_factory')
# ----------------------
def _get_nll(trigger : Trigger, tmp_path : Path) -> NLLConf:
    data = gut.load_data(
        package= 'fitter_data',
        fpath  =f'rare/{trigger.project}/{trigger.channel}/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    obs = zfit.Space('B_Mass_smr', limits=(5000, 6000))
    with PL.parameter_schema(cfg=cfg.yields),\
         Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=100_000):

        ftr = LikelihoodFactory(
            name   = trigger,
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.jpsi,
            cfg    = cfg)
        nll = ftr.run()

    return nll
# ----------------------
@pytest.fixture(autouse=True)
def initialize(monkeypatch):
    '''
    This runs before any test
    '''
    monkeypatch.setattr(
        'fitter.likelihood_factory.DataPreprocessor',
        TestDataPreprocessor)

    monkeypatch.setattr(
        'fitter.likelihood_factory.DataModel',
        TestDataModel)

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
    nll = _get_nll(
        trigger = Trigger.rk_ee_os,
        tmp_path= tmp_path)

    assert isinstance(nll.nll, ExtendedUnbinnedNLL)
# -------------------------------------------
def test_simultaneous(tmp_path : Path):
    '''
    Load likelihoods with shared parameters, for simultaneous fits
    '''
    files  = {
        'rkst/rare_muon.yaml'     : 'rkst/rare_muon_simultaneous.yaml',
        'rkst/rare_electron.yaml' : 'rkst/rare_electron_simultaneous.yaml',
        'rk/rare_muon.yaml'       : 'rk/rare_muon_simultaneous.yaml',
    }

    with UnpackerModel.replacements(files = files):
        nll_ee = _get_nll(
            trigger = Trigger.rk_ee_os,
            tmp_path= tmp_path)

        nll_mm = _get_nll(
            trigger = Trigger.rk_mm_os,
            tmp_path= tmp_path)

        nll = nll_ee.nll + nll_mm.nll
# -------------------------------------------
