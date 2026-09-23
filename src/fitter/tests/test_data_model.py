'''
This module has tests for the DataModel class
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import pytest

from pathlib       import Path
from rx_common     import Cuts, Trigger, Qsq, Region
from rx_selection  import selection as sel
from dmu           import LogStore
from dmu.stats     import ParameterLibrary as PL
from dmu.stats     import zfit
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import utilities as sut
from dmu.workflow  import Cache
from fitter        import DataModel
from fitter        import FitModelConf

log=LogStore.add_logger('fitter:test_data_model')

type zpdf = zfit.pdf.BasePDF
# ----------------------
class TestSimFitter:
    def __init__(
        self,
        name      : str,
        component : str,
        trigger   : str,
        q2bin     : str,
        cfg       : str):

        self._name      = name     
        self._component = component

        _ = trigger  
        _ = q2bin    
        _ = cfg      
    # ----------------------
    def get_model(self) -> zpdf:
        log.warning('Using mock SimFitter PDF')
        name  = f'{self._component}_{self._name}'

        obs   = zfit.Space('Mass', 4600, 6000)
        mu    = zfit.Parameter(f"{name}_mu", 5280.0, 5000.0, 5500.0)
        sigma = zfit.Parameter(f"{name}_sigma", 20.0, 0.1, 100.0)
        pdf   = zfit.pdf.Gauss(mu=mu, sigma=sigma, obs=obs, name=name)

        return pdf
# ----------------------
@pytest.fixture(autouse=True)
def initialize(monkeypatch):
    '''
    This runs before any test
    '''
    monkeypatch.setattr(
        'fitter.data_model.SimFitter',
        TestSimFitter)

    LogStore.set_level('fitter:data_preprocessor' , 10)
    LogStore.set_level('fitter:data_model'        , 10)
    LogStore.set_level('fitter:sim_fitter'        , 10)
    LogStore.set_level('rx_data:rdf_getter'       , 30)

    with DataModel.skip_components(names = ['kkk', 'kpipi']):
        yield
# --------------------------
@pytest.mark.parametrize('kind, trigger', [
    ('reso/rk/mm'  , Trigger.rk_mm_os  ), 
    ('reso/rk/ee'  , Trigger.rk_ee_os  ), 
    ('reso/rkst/mm', Trigger.rkst_mm_os),
    ('reso/rkst/ee', Trigger.rkst_ee_os),
])
def test_resonant(kind : str, trigger : Trigger, tmp_path : Path):
    '''
    Simplest test
    '''
    region = Region.brem_xx0 if trigger.is_muon else Region.brem_xx1

    data= gut.load_data(
        package='fitter_data',
        fpath  =f'{kind}/data.yaml')

    q2bin = Qsq.jpsi
    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)
        cfg = cfg.specialize(q2bin = q2bin)

    with Cache.cache_root(path = tmp_path),\
        PL.parameter_schema(cfg=cfg.yields):
        dmd = DataModel(
            name    = region,
            cfg     = cfg,
            obs     = cfg.obs,
            trigger = trigger, 
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
@pytest.mark.parametrize('q2bin'  , [Qsq.low, Qsq.central])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_rare_electron(
    tmp_path : Path, 
    trigger  : Trigger,
    q2bin    : Qsq):
    '''
    Simplest test for rare electron mode
    '''
    data       = gut.load_data(
        package= 'fitter_data',
        fpath  =f'rare/{trigger.project}/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)
        cfg = cfg.specialize(q2bin = q2bin)

    with PL.parameter_schema(cfg=cfg.yields),\
        Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel = {Cuts.mass : '(1)', Cuts.brem : 'nbrem != 0'}):
        dmd = DataModel(
            name    = Region.brem_x12,
            cfg     = cfg,
            obs     = cfg.obs,
            trigger = trigger,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
@pytest.mark.skip(reason='These tests require smear friend trees for noPID samples')
@pytest.mark.parametrize('region' , Region.hadronic_misid()   )
@pytest.mark.parametrize('q2bin'  , ['low', 'central', 'high'])
def test_misid_rare(
    region   : Region, 
    q2bin    : Qsq, 
    tmp_path : Path):
    '''
    Test getting model for misid control region
    '''
    obs = zfit.Space(region.mass, limits=region.mass.limits)
    data= gut.load_data(
        package='fitter_data',
        fpath  ='misid/rk/ee/data_misid.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)

    with PL.parameter_schema(cfg=cfg.yields),\
        Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel = {
        Cuts.brem : 'nbrem != 0',
        Cuts.mass : '(1)',
        Cuts.cmb  : 'mva_cmb > 0.80 && mva_prc > 0.60'}):
        dmd = DataModel(
            name    = region,
            cfg     = cfg,
            obs     = obs,
            trigger = Trigger.rk_ee_nopid,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
