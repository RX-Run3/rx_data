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
    Test using toy data
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='tests/likelihood_factory/data.yaml')

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

    assert isinstance(nll, ExtendedUnbinnedNLL)
# -------------------------------------------
def test_config(tmp_path : Path):
    '''
    Tests the config method
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='reso/rk/mm/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg  = FitModelConf(**data)

    obs = zfit.Space('B_Mass', limits=(4500, 7000))
    with PL.parameter_schema(cfg=cfg.yields),\
         sel.custom_selection(d_sel = {Cuts.cmb : '(1)'}),\
         Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=100_000):

        ftr = LikelihoodFactory(
            name   = 'likelihood_factory',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.jpsi,
            cfg    = cfg)
        cfg = ftr.run()

    assert 'default' in cfg.selection
    assert 'fit'     in cfg.selection
# -------------------------------------------
def test_reso_muon(tmp_path : Path):
    '''
    Test resonant muon fit with
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='reso/rk/mm/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg  = FitModelConf(**data)

    obs = zfit.Space(Mass.bp_dtf_jpsi, limits=(5000, 6000))
    with PL.parameter_schema(cfg=cfg.yields),\
         sel.custom_selection(d_sel = {Cuts.cmb : '(1)'}), \
         Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=20_000):

        ftr = LikelihoodFactory(
            name   = 'main',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.jpsi,
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
@pytest.mark.parametrize('q2bin', ['central'])
def test_rare_muon(q2bin : str, tmp_path : Path):
    '''
    Test using toy data
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='rare/rk/mm/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg  = FitModelConf(**data)

    obs = zfit.Space('B_Mass', limits=(5000, 6000))
    with Cache.cache_root(path = tmp_path),\
         PL.parameter_schema(cfg=cfg.yields):
        ftr = LikelihoodFactory(
            name   = 'main',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq(value = q2bin),
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
def test_reso_electron(tmp_path : Path):
    '''
    Test fitting resonant electron channel
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='reso/rk/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)
        
    cfg = _update_block(cfg = cfg, q2bin = Qsq.jpsi, component = Component.bppijpsiee)
    cfg = _update_block(cfg = cfg, q2bin = Qsq.jpsi, component = Component.bpkpjpsiee)
    cfg = _update_block(cfg = cfg, q2bin = Qsq.jpsi, component = Component.bpkppsi2ee)

    obs = zfit.Space(Mass.bp_dtf_jpsi, limits=(5100, 5800))
    with PL.parameter_schema(cfg=cfg.yields),\
         RDFGetter.max_entries(value = 200_000),\
        Cache.cache_root(path = tmp_path):

        ftr = LikelihoodFactory(
            name   = 'main',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.jpsi,
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_rare_electron(q2bin : Qsq, tmp_path : Path):
    '''
    Test fitting rare electron channel
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='rare/rk/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    obs = zfit.Space('B_Mass_smr', limits=(4500, 7000))
    with PL.parameter_schema(cfg=cfg.yields),\
         Cache.cache_root(path = tmp_path),\
         sel.custom_selection(d_sel={
            Cuts.brem : 'nbrem != 0',
            Cuts.cmb  : 'mva_cmb > 0.60',
            Cuts.prc  : 'mva_prc > 0.40'}):
        ftr = LikelihoodFactory(
            name   = 'main',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = q2bin,
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
def test_high_q2_track(tmp_path : Path):
    '''
    Test fitting rare electron in high q2
    with track based cut and adding brem 0 category
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='rare/rk/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    obs = zfit.Space('B_Mass_smr', limits=(4500, 7000))

    with PL.parameter_schema(cfg=cfg.yields),\
         Cache.cache_root(path = tmp_path),\
         sel.custom_selection(d_sel={
            Cuts.q2 : 'q2_track > 14300000 && q2 < 22000000',
            Cuts.cmb: 'mva_cmb > 0.60',
            Cuts.prc: 'mva_prc > 0.40'}):
        ftr = LikelihoodFactory(
            name   = 'main',
            obs    = obs,
            sample = Component.data_24,
            q2bin  = Qsq.high,
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
@pytest.mark.parametrize('q2bin' , [Qsq.central])
@pytest.mark.parametrize('region, tag_cut', [
    (Region.bpkk  , 'PROBNN_K > 0.1'), 
    (Region.bppipi, 'PROBNN_K < 0.1')])
def test_rare_misid_electron(
    q2bin   : Qsq,
    region  : Region, 
    tag_cut : str,
    tmp_path: Path):
    '''
    Test building likelihood in misid control regions
    '''
    data = gut.load_data(
        package='fitter_data',
        fpath  ='misid/rk/ee/data_misid.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    l1_in_cr = f'((L1_ProbNNe < 0.2) || (L1_PIDe < 3.0)) && L1_{tag_cut}'
    l2_in_cr = f'((L2_ProbNNe < 0.2) || (L2_PIDe < 3.0)) && L2_{tag_cut}'

    with PL.parameter_schema(cfg=cfg.yields),\
         RDFGetter.max_entries(value = -1),\
         Cache.cache_root(path = tmp_path),\
         sel.custom_selection(d_sel={Cuts.pid_l : f'({l1_in_cr}) && ({l2_in_cr})'}):
        ftr = LikelihoodFactory(
            obs    = region.obs,
            name   = region,
            sample = Component.data_24,
            q2bin  = q2bin,
            cfg    = cfg)
        ftr.run()
# -------------------------------------------
