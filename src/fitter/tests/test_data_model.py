'''
This module has tests for the DataModel class
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import pytest

from contextlib    import ExitStack
from pathlib       import Path
from rx_common     import Cuts, Trigger, Qsq, Region
from rx_common     import Component
from rx_selection  import selection as sel
from dmu           import LogStore
from dmu.stats     import ParameterLibrary as PL
from dmu.stats     import zfit
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import utilities as sut
from dmu.workflow  import Cache
from fitter        import DataModel
from fitter        import FitModelConf

from patch_classes import TestCCbarConfTF, TestSimFitter

log=LogStore.add_logger('fitter:test_data_model')

type zpdf = zfit.pdf.BasePDF

_TRIGGERS : list[tuple[Trigger,Trigger]] = [
    (Trigger.rk_ee_os  , Trigger.rk_mm_os  ),
    (Trigger.rkst_ee_os, Trigger.rkst_mm_os),
]
# ----------------------
def _get_model(
    q2bin     : Qsq,
    trigger   : Trigger,
    region    : Region,
    cache_dir : Path) -> zpdf:
    '''
    Retrieves full PDF for signal region fit
    '''
    data       = gut.load_data(
        package= 'fitter_data',
        fpath  =f'rare/{trigger.project}/{trigger.channel}/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)
        cfg = cfg.specialize(q2bin = q2bin)

    ctx_1 = PL.parameter_schema(cfg=cfg.yields)
    ctx_2 = Cache.cache_root(path = cache_dir)
    ctx_3 = sel.custom_selection(d_sel = {Cuts.mass : '(1)'})

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)

        dmd = DataModel(
            name    = region,
            cfg     = cfg,
            obs     = cfg.obs,
            trigger = trigger,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)

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
    region     = Region.brem_x12
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
            name    = region,
            cfg     = cfg,
            obs     = cfg.obs,
            trigger = trigger,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
def test_rare_electron_high(tmp_path : Path):
    '''
    Simplest test for rare electron mode
    '''
    trigger    = Trigger.rk_ee_os
    region     = Region.brem_x12
    q2bin      = Qsq.high

    data       = gut.load_data(
        package= 'fitter_data',
        fpath  =f'rare/{trigger.project}/ee/data.yaml')

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = FitModelConf(**data)
        cfg = cfg.specialize(q2bin = q2bin)

    cfg_qsq = cfg.components[q2bin]
    cfg_qsq[Component.ccbar] = TestCCbarConfTF(kind = 'CCbarPDFTF')

    with PL.parameter_schema(cfg=cfg.yields),\
        Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel = {Cuts.mass : '(1)', Cuts.brem : 'nbrem != 0'}):
        dmd = DataModel(
            name    = region,
            cfg     = cfg,
            obs     = cfg.obs,
            trigger = trigger,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
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

    ctx_1 = PL.parameter_schema(cfg=cfg.yields)
    ctx_2 = Cache.cache_root(path = tmp_path)
    ctx_3 = TestSimFitter.mass(value = region.mass)
    ctx_4 = sel.custom_selection(d_sel = {
        Cuts.brem : 'nbrem != 0',
        Cuts.mass : '(1)',
        Cuts.cmb  : 'mva_cmb > 0.80 && mva_prc > 0.60'})

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)
        stack.enter_context(ctx_4)

        dmd = DataModel(
            name    = region,
            cfg     = cfg,
            obs     = obs,
            trigger = Trigger.rk_ee_nopid,
            q2bin   = q2bin)
        pdf = dmd.get_model()

    sut.print_pdf(pdf)
# --------------------------
@pytest.mark.parametrize('etrig, mtrig', _TRIGGERS)
def test_simultaneous_rk(
    etrig    : Trigger,
    mtrig    : Trigger,
    tmp_path : Path):
    '''
    Tests reparametrization of yields for rk/rkst extraction
    '''
    PL.clear()

    q2bin   = Qsq.low
    region  = Region.brem_x12

    pdf_ee  = _get_model(
        q2bin    = q2bin,
        trigger  = etrig,
        region   = region,
        cache_dir= tmp_path / 'ee')

    region  = Region.brem_xx0
    proj    = etrig.project

    files = {f'{proj}/rare_muon.yaml' : f'{proj}/rare_muon_simultaneous.yaml'}
    with UnpackerModel.replacements(files = files):
        pdf_mm  = _get_model(
            q2bin    = q2bin,
            trigger  = mtrig,
            region   = region,
            cache_dir= tmp_path / 'mm')

    pars_ee = pdf_ee.get_params()
    pars_mm = pdf_mm.get_params()

    common  = pars_ee & pars_mm

    assert len(common) == 1

    log.info('Common parameters')
    for par in common:
        log.info(par.name)

    sut.print_pdf(pdf = pdf_ee)
    sut.print_pdf(pdf = pdf_mm)
# --------------------------
def test_simultaneous_electron(tmp_path : Path):
    '''
    Tests reparametrization of yields for extraction of electron yields
    '''
    PL.clear()

    q2bin  = Qsq.low
    region = Region.brem_x12
    files  = {'rk/rare_electron.yaml' : 'rk/rare_electron_simultaneous.yaml'}
    with UnpackerModel.replacements(files = files):
        pdf_rk       = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rk_ee_os,
            region   = region,
            cache_dir= tmp_path / 'ee')

        pdf_rkst     = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rkst_ee_os,
            region   = region,
            cache_dir= tmp_path / 'ee')

    pars_rk   = pdf_rk.get_params()
    pars_rkst = pdf_rkst.get_params()
    common    = pars_rk & pars_rkst

    sut.print_pdf(pdf = pdf_rk)
    sut.print_pdf(pdf = pdf_rkst)

    log.info('Common parameters')
    for par in common:
        log.info(par.name)

    assert len(common) == 1
# --------------------------
def test_simultaneous_rx(tmp_path : Path):
    '''
    Tests reparametrization of yields for rk/rkst extraction
    '''
    PL.clear()

    q2bin  = Qsq.low
    files  = {
        'rkst/rare_muon.yaml'   : 'rkst/rare_muon_simultaneous.yaml',
        'rk/rare_muon.yaml'     : 'rk/rare_muon_simultaneous.yaml',
        'rk/rare_electron.yaml' : 'rk/rare_electron_simultaneous.yaml',
    }

    with UnpackerModel.replacements(files = files):
        pdf_ee_rk    = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rk_ee_os,
            region   = Region.brem_x12,
            cache_dir= tmp_path / 'ee')

        pdf_ee_rkst  = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rkst_ee_os,
            region   = Region.brem_x12,
            cache_dir= tmp_path / 'ee')

        pdf_mm_rk    = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rk_mm_os,
            region   = Region.brem_xx0,
            cache_dir= tmp_path / 'mm')

        pdf_mm_rkst  = _get_model(
            q2bin    = q2bin,
            trigger  = Trigger.rkst_mm_os,
            region   = Region.brem_xx0,
            cache_dir= tmp_path / 'mm')

    pars_ee_rk   = pdf_ee_rk.get_params()
    pars_ee_rkst = pdf_ee_rkst.get_params()
    pars_mm_rk   = pdf_mm_rk.get_params()
    pars_mm_rkst = pdf_mm_rkst.get_params()

    common_rkst  = pars_ee_rkst & pars_mm_rkst
    common_rk    = pars_ee_rk   & pars_mm_rk
    common       = common_rk    & common_rkst

    log.info('Common parameters for full model')
    for par in common:
        log.info(par.name)

    log.info('Common parameters for rkst')
    for par in common_rkst:
        log.info(par.name)

    assert len(common_rkst) == 2 # noqa: PLR2004
    assert len(common     ) == 1
# --------------------------
