'''
This module has tests for the DataModel class
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import pytest

from contextlib    import contextmanager
from contextlib    import ExitStack
from pathlib       import Path
from rx_common     import Mass
from rx_common     import Cuts, Trigger, Qsq, Region, Project
from rx_common     import Component
from rx_selection  import selection as sel
from dmu           import LogStore
from dmu.stats     import ParameterLibrary as PL
from dmu.stats     import zfit, ModelFactory, Model
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import utilities as sut
from dmu.workflow  import Cache
from fitter        import DataModel
from fitter        import FitModelConf
from fitter        import CCbarConfTF

log=LogStore.add_logger('fitter:test_data_model')

type zpdf = zfit.pdf.BasePDF

_TRIGGERS : list[tuple[Trigger,Trigger]] = [
    (Trigger.rk_ee_os  , Trigger.rk_mm_os  ),
    (Trigger.rkst_ee_os, Trigger.rkst_mm_os),
]
# ----------------------
class TestCCbarConfTF(CCbarConfTF, frozen = True):
    def get_pdf(
        self,
        obs_name: str,
        project : Project,
        pdfs    : dict[Component, zpdf]) -> zpdf:
        _     = project
        _     = pdfs

        name  = 'name'
        obs   = zfit.Space(obs_name, 4600, 6000)
        mu    = zfit.Parameter(f"{name}_mu", 5280.0, 5000.0, 5500.0)
        sigma = zfit.Parameter(f"{name}_sigma", 20.0, 0.1, 100.0)
        pdf   = zfit.pdf.Gauss(mu=mu, sigma=sigma, obs=obs, name=name)

        return pdf
# ----------------------
class TestSimFitter:
    _mass = 'Mass'
    # ----------------------
    def __init__(
        self,
        name      : str,
        component : Component,
        trigger   : Trigger,
        q2bin     : str,
        cfg       : str):

        self._name      = name
        self._component = component
        self._trigger   = trigger

        _ = q2bin
        _ = cfg
    # ----------------------
    @property
    def pdfs(self) -> list[Model]:
        if self._component == Component.comb:
            return [Model.exp]

        return [Model.gauss]
    # ----------------------
    @property
    def values(self) -> dict[str, tuple[float,float,float]]:
        signals         = {Component.bpkpee, Component.bpkpmm, Component.bdkstkpimm}
        signal_shape    = {'mu' : (5280., 5200., 5350.), 'sg' : (50., 5., 100.)}

        part_reco       = {Component.bsphiee, Component.bpkxkpipiee}
        part_reco_shape = {'mu' : (5000., 4800., 5200.), 'sg' : (200., 100., 300.)}

        leak_down       = {Component.bpkpjpsiee, Component.bdkstkpijpsiee}
        leak_down_shape = {'mu' : (4800., 4500., 5000.), 'sg' : (400., 200., 600.)}

        if self._component == Component.comb:
            return {'c' : (-0.001, -0.01, 0.00)}

        if self._component in signals:
            return signal_shape

        if self._component == Component.bdkstkpiee and self._trigger == Trigger.rk_ee_os:
            return part_reco_shape 

        if self._component == Component.bdkstkpiee and self._trigger == Trigger.rkst_ee_os:
            return signal_shape

        if self._component in part_reco:
            return part_reco_shape

        if self._component in leak_down:
            return leak_down_shape


        raise ValueError(f'No values for {self._component}/{self._trigger}')
    # ----------------------
    @classmethod
    @contextmanager
    def mass(cls, value : Mass):
        old_value  = cls._mass
        cls._mass = value
        try:
            yield
        finally:
            cls._mass = old_value
    # ----------------------
    def get_model(self) -> zpdf | None:
        log.warning('Using mock SimFitter PDF')
        skipped = {
            Component.ccbar, 
            Component.bpkppsi2ee, 
            Component.bpkstkpiee,
            Component.bdkstkpipsi2ee}

        if self._component in skipped:
            return None

        name  = f'{self._component}_{self._name}'
        obs   = zfit.Space(self._mass, 4600, 6000)
        mfc   = ModelFactory(
            obs     = obs,
            preffix = name,
            l_float = [],
            l_shared= [],
            values  = self.values,
            l_pdf   = self.pdfs)

        log.debug(f'Component: {self._component}')

        return mfc.get_pdf()
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
    files  = {'rkst/rare_electron.yaml' : 'rkst/rare_electron_simultaneous.yaml'}
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
        'rkst/rare_muon.yaml'     : 'rkst/rare_muon_simultaneous.yaml',
        'rkst/rare_electron.yaml' : 'rkst/rare_electron_simultaneous.yaml',
        'rk/rare_muon.yaml'       : 'rk/rare_muon_simultaneous.yaml',
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
