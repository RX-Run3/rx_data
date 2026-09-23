'''
This module is meant to test the SimFitter class
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import pytest
import numpy

from typing        import Final
from contextlib    import ExitStack
from pathlib       import Path
from dmu           import LogStore
from dmu.stats     import ParsHolder, print_pdf
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import zfit, utilities as sut
from dmu.workflow  import Cache

from rx_common     import Channel
from rx_common     import Component, Cuts, Mass, Qsq, Region
from rx_common     import Trigger
from rx_data       import RDFGetter
from rx_selection  import selection as sel
from fitter        import ObservableConf
from fitter        import CombinatorialConf
from fitter        import SimFitter
from fitter        import ParametricConf
from fitter        import CCbarConf
from fitter        import NonParametricConf
from fitter        import MisIDConf
from fitter        import SignalConstraints

log=LogStore.add_logger('fitter:test_sim_fitter')

_RNG                    = numpy.random.default_rng(seed = 42)
_DATA_SIZE : Final[int] = 1000

type zdat = zfit.data.Data
type zsum = zfit.pdf.SumPDF
# ---------------------------------------------------
class TestDataPreprocessor:
    def __init__(
        self,
        name      : str,
        wgt_cfg   : str,
        obs       : str,
        trigger   : Trigger,
        q2bin     : Qsq,
        selection : str,
        sample    : str):
        _ = name
        _ = wgt_cfg
        _ = obs
        _ = selection
        _ = sample

        self._trigger = trigger
        self._q2bin   = q2bin
    # --------------------------
    @property
    def rdf_uid(self) -> str:
        return 'mock_data'
    # --------------------------
    def _get_sigma(self) -> float:
        if self._trigger.is_muon:
            return 30

        if self._q2bin.is_rare:
            return 100

        return 20
    # --------------------------
    def get_data(self) -> zdat:
        log.warning('Using mock data')

        sigma   = self._get_sigma()
        array_1 = _RNG.normal(loc = 5280, scale = 1.0 * sigma, size = _DATA_SIZE)
        array_2 = _RNG.normal(loc = 5280, scale = 1.3 * sigma, size = _DATA_SIZE)
        array   = numpy.concatenate([array_1, array_2])

        obs   = zfit.Space('Mass', 4600, 6000)
        data  = zfit.data.Data.from_numpy(array = array, obs = obs)

        if isinstance(data, zfit.data.Data):
            return data

        raise ValueError('Invalid data')
# ---------------------------------------------------
class TestPRec:
    def __init__(
        self,
        name : str,
        obs  : str,
        trig : str,
        q2bin: str,
        cfg  : str):

        _ = name
        _ = obs
        _ = trig
        _ = q2bin
        _ = cfg
    # --------------------------
    def get_sum(self, name : str) -> zsum:
        log.warning('Using mock ccbar PDF')

        obs   = zfit.Space('Mass', 4600, 6000)
        lam   = zfit.Parameter(f"{name}_lambda", -0.002, -1.0, 1.0)
        mu    = zfit.Parameter(f"{name}_mu", 5280.0, 5000.0, 5500.0)
        sigma = zfit.Parameter(f"{name}_sigma", 20.0, 0.1, 100.0)
        low   = 4500.0
        high  = 6000.0

        exp_pdf     = zfit.pdf.Exponential(lambda_=lam, obs=obs, name=f"{name}_exp")
        gauss_pdf   = zfit.pdf.Gauss(mu=mu, sigma=sigma, obs=obs, name=f"{name}_gauss")
        uniform_pdf = zfit.pdf.Uniform(low=low, high=high, obs=obs, name=f"{name}_uniform")

        frac1 = zfit.Parameter(f"{name}_frac1", 0.3, 0.0, 1.0)
        frac2 = zfit.Parameter(f"{name}_frac2", 0.3, 0.0, 1.0)

        total_pdf= zfit.pdf.SumPDF(
            pdfs = [exp_pdf, gauss_pdf, uniform_pdf],
            fracs= [frac1, frac2],
            name = f"{name}_sum")

        return total_pdf
# ---------------------------------------------------
@pytest.fixture(autouse=True)
def initialize(monkeypatch):
    '''
    Runs before any test
    '''
    log.info('Disabling caching')

    monkeypatch.setattr(
        'fitter.sim_fitter.DataPreprocessor',
        TestDataPreprocessor)

    monkeypatch.setattr(
        'fitter.sim_fitter.PRec',
        TestPRec)

    LogStore.set_level('fitter:signal_constraints', 10)
    LogStore.set_level('fitter:data_preprocessor' , 10)
    LogStore.set_level('fitter:category_merger'   , 10)
    LogStore.set_level('fitter:sim_fitter'        , 10)
    LogStore.set_level('fitter:configs'           , 10)

    with RDFGetter.max_entries(value = 100_000):
        yield
# ----------------------
def _filter_category(name : str) -> bool:
    c1 = name.endswith('_b1')
    c2 = name.endswith('_b2')

    return c1 or c2
# ----------------------
def _float_fix_pars(pdf : ParsHolder) -> ParsHolder:
    '''
    Parameters
    -------------
    pdf: Holder of parameters

    Returns
    -------------
    PDF with parameters ending in _flt floating and everything else fixed
    '''
    par_flt = pdf.get_params(floating =  True)
    par_fix = pdf.get_params(floating = False)

    log.info('Fixing/Floating parameters:')
    for par in par_fix | par_flt:
        log.info(par.name)
        par.floating = par.name.endswith('_flt')

    return pdf
# ---------------------------------------------------
def test_nomc(tmp_path : Path):
    '''
    Test for components that have no MC associated
    '''
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor,
        range = (4500, 7000))

    data = gut.load_data(package='fitter_data', fpath='rare/rk/ee/comb.yaml')

    with ExitStack() as stack:
        stack.enter_context(Cache.cache_root(path = tmp_path))
        stack.enter_context(UnpackerModel.package(name = 'fitter_data'))

        cfg  = CombinatorialConf(**data)
        cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

        ftr = SimFitter(
            name     = Region.brem_x12,
            component= Component.comb,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.low)
        _ = ftr.get_model()
# ---------------------------------------------------
def test_nocat(tmp_path : Path):
    '''
    Test for components without categories, e.g. muon
    '''
    cfg_obs = ObservableConf(
        name  = Mass.b,
        range = (4800, 6000))
    data  = gut.load_data(package='fitter_data', fpath='rare/rk/mm/bpkpmm.yaml')
    cfg   = ParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=30_000):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rk_mm_os,
            q2bin    = Qsq.jpsi)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_param_clone(
    tmp_path : Path,
    trigger  : Trigger):
    '''
    Test fit to parametrized model in a single signal region
    '''
    q2bin   = Qsq.low
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor,
        range = (4500, 7000))

    if   trigger == Trigger.rk_ee_os:
        fpath = 'rare/rk/ee/bpkpee.yaml.j2'
    elif trigger == Trigger.rkst_ee_os:
        fpath = 'rare/rkst/ee/bdkstkpiee.yaml.j2'
    else:
        raise ValueError(f'Invalid trigger: {trigger}')

    data = gut.load_data(package='fitter_data', fpath=fpath)
    cfg  = ParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})
    cfg  = cfg.cfg_clone(prefix = 'BREM', regions = [Region.brem_xx1, Region.brem_xx2])
    cfg  = cfg.filter_category(func = _filter_category)

    d_sel : dict[Cuts, str] = {
        Cuts.cmb : 'mva_cmb > 0.9',
        Cuts.prc : 'mva_prc > 0.5'}
    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1),\
        sel.custom_selection(d_sel = d_sel):
        ftr = SimFitter(
            name     = Region.brem_x12,
            component= cfg.component,
            cfg      = cfg,
            trigger  = trigger,
            q2bin    = q2bin)
        pdf = ftr.get_model()

    assert pdf is not None

    print_pdf(pdf = pdf)
# ---------------------------------------------------
@pytest.mark.parametrize('region' , [Region.brem_xx1 ,    Region.brem_xx2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_param_region(
    tmp_path : Path,
    trigger  : Trigger,
    region   : Region):
    '''
    Test fit to parametrized model in a single signal region
    '''
    q2bin   = Qsq.low
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor,
        range = (4500, 7000))

    if   trigger == Trigger.rk_ee_os:
        fpath = 'rare/rk/ee/bpkpee.yaml.j2'
    elif trigger == Trigger.rkst_ee_os:
        fpath = 'rare/rkst/ee/bdkstkpiee.yaml.j2'
    else:
        raise ValueError(f'Invalid trigger: {trigger}')

    data = gut.load_data(package='fitter_data', fpath=fpath)
    cfg  = ParametricConf(**data)
    cfg  = cfg.cfg_copy(replacements = {'BREM' : region})
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})
    cfg  = cfg.filter_category(func = _filter_category)

    d_sel : dict[Cuts, str] = {
        Cuts.cmb : 'mva_cmb > 0.9',
        Cuts.prc : 'mva_prc > 0.5'}
    d_sel.update(region.selection)

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1),\
        sel.custom_selection(d_sel = d_sel):
        ftr = SimFitter(
            name     = region,
            component= cfg.component,
            cfg      = cfg,
            trigger  = trigger,
            q2bin    = q2bin)

        pdf = ftr.get_model()

    assert pdf is not None

    print_pdf(pdf = pdf)
# ---------------------------------------------------
@pytest.mark.parametrize('region' , [Region.brem_xx1 ,    Region.brem_xx2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_param_region_constrained(
    tmp_path : Path,
    trigger  : Trigger,
    region   : Region):
    '''
    Test fit to parametrized model in a single signal region and with constraints
    '''
    q2bin   = Qsq.central
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor,
        range = (4500, 7000))

    if   trigger == Trigger.rk_ee_os:
        fpath = 'rare/rk/ee/bpkpee.yaml.j2'
    elif trigger == Trigger.rkst_ee_os:
        fpath = 'rare/rkst/ee/bdkstkpiee.yaml.j2'
    else:
        raise ValueError(f'Invalid trigger: {trigger}')

    data = gut.load_data(package='fitter_data', fpath=fpath)
    cfg  = ParametricConf(**data)
    cfg  = cfg.cfg_copy(replacements = {'BREM' : region})
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})
    cfg  = cfg.filter_category(func = _filter_category)

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1):
        ftr = SimFitter(
            name     = region,
            component= cfg.component,
            cfg      = cfg,
            trigger  = trigger,
            q2bin    = q2bin)

        pdf = ftr.get_model()

    assert pdf is not None

    pdf = _float_fix_pars(pdf = pdf)
    calc= SignalConstraints(
        nll     = pdf,
        channel = Channel.ee,
        comp    = Component.bpkpee)

    constraints = calc.get_constraints()

    log.info('Found parameters:')
    for par in pdf.get_params():
        log.info(par.name)

    log.info('Printing constraints:')
    for cons in sorted(constraints):
        print(cons)
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bdkstkpiee, Component.bpkstkpiee, Component.bsphiee, Component.bpkpjpsiee])
def test_kde_rk(component : Component, tmp_path : Path):
    '''
    Test fitting with KDE
    '''
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor_smr,
        range = (4500, 7000))

    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}_np.yaml')
    cfg  = NonParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.central)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpipiee, Component.bdkstkpijpsiee, Component.bpk1kpipiee, Component.bpk2kpipiee])
@pytest.mark.parametrize('qsq', Qsq.for_physics())
def test_kde_rkst(
    component : Component,
    qsq       : Qsq,
    tmp_path  : Path):
    '''
    Test fitting with KDE
    '''
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor_smr,
        range = (4500, 7000))
    data = gut.load_data(package='fitter_data', fpath=f'rare/rkst/ee/{component}_np.yaml')
    cfg  = NonParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    cuts = {
        Cuts.brem : 'nbrem != 0',
        Cuts.cmb  : 'mva_cmb > 0.9',
        Cuts.prc  : 'mva_prc > 0.5'}

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1),\
         sel.custom_selection(d_sel = cuts):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rkst_ee_os,
            q2bin    = qsq)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkkk, Component.bpkpipi])
@pytest.mark.parametrize('q2bin'    , [Qsq.low, Qsq.central, Qsq.high])
def test_misid(
    component : Component,
    q2bin     : Qsq,
    tmp_path  : Path):
    '''
    Test fitting misID simulation
    '''
    cfg_obs = ObservableConf(
        name  = Mass.bp_bcor_smr,
        range = (5000, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}_np.yaml')

    with UnpackerModel.package('fitter_data'):
        cfg = MisIDConf(**data)
        cfg = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_nopid,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('mass', [Mass.bp_dtf_jpsi, Mass.bp_bcor_smr])
def test_ccbar_reso_rk(mass : Mass, tmp_path : Path):
    '''
    Tests retriveval of PDF associated to ccbar inclusive decays
    '''
    cfg_obs = ObservableConf(
        name  = mass,
        range = (4500, 6000))

    component = Component.ccbar
    data = gut.load_data(package='fitter_data', fpath=f'reso/rk/ee/{component}.yaml')
    cfg  = CCbarConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= component,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.jpsi)
        pdf = ftr.get_model()

    assert pdf is not None

    sut.print_pdf(pdf)
# ---------------------------------------------------
@pytest.mark.parametrize('mass', [Mass.bp_dtf_jpsi, Mass.bp_bcor_smr])
def test_ccbar_reso_rkst(mass : Mass, tmp_path : Path):
    '''
    Tests retriveval of PDF associated to ccbar inclusive decays
    '''
    cfg_obs = ObservableConf(
        name  = mass,
        range = (4500, 6000))

    component = Component.ccbar
    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/ee/{component}.yaml')
    cfg  = CCbarConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= component,
            cfg      = cfg,
            trigger  = Trigger.rkst_ee_os,
            q2bin    = Qsq.jpsi)
        pdf = ftr.get_model()

    assert pdf is not None

    sut.print_pdf(pdf)
# ---------------------------------------------------
def test_ccbar_rare(tmp_path : Path):
    '''
    Tests retriveval of PDF associated to ccbar inclusive decays
    for rare modes, i.e. without jpsi mass constraint
    '''
    component = Component.ccbar
    mass      = Mass.bp_bcor_smr
    q2bin     = Qsq.high
    cfg_obs   = ObservableConf(
        name  = mass,
        range = (4500, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}.yaml')
    cfg  = CCbarConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    d_sel = {
        Cuts.cmb : 'mva_cmb > 0.8',
        Cuts.prc : 'mva_prc > 0.8',
             }

    with Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel=d_sel):

        ftr = SimFitter(
            name     = 'main',
            component= component,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpjpsiee, Component.bppijpsiee])
def test_reso_rk_ee(
    component : Component,
    tmp_path  : Path):
    '''
    Test electron resonant with rk trigger
    '''
    cfg_obs   = ObservableConf(
        name  = Mass.bp_dtf_jpsi,
        range = (4500, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'reso/rk/ee/{component}.yaml')
    cfg  = ParametricConf(**data)
    cfg.add_category_suffix(suffix = 'b1')
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.jpsi)
        pdf = ftr.get_model()

    assert pdf is not None

    print_pdf(pdf = pdf)
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bdkstkpijpsimm, Component.bdkstkpipsi2mm])
def test_reso_rkst_mm(
    component : Component,
    tmp_path  : Path):
    '''
    Test resonant jpsi and psi2S in rkst muon channel
    '''
    q2bin = {
        Component.bdkstkpijpsimm : Qsq.jpsi,
        Component.bdkstkpipsi2mm : Qsq.psi2,
    }[component]

    mass = {
        Qsq.jpsi : Mass.bd_dtf_jpsi,
        Qsq.psi2 : Mass.bd_dtf_psi2
    }[q2bin]

    cfg_obs   = ObservableConf(
        name  = mass,
        range = (4800, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/mm/{component}.yaml')
    cfg  = ParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rkst_mm_os,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpjpsimm])
def test_reso_rk_mm(
    component : Component,
    tmp_path  : Path):
    '''
    Test resonant jpsi and psi2S in rkst muon channel
    '''
    q2bin = {
        Component.bpkpjpsimm : Qsq.jpsi,
        Component.bpkppsi2mm : Qsq.psi2,
    }[component]

    mass = {
        Qsq.jpsi : Mass.bp_dtf_jpsi,
        Qsq.psi2 : Mass.bp_dtf_psi2
    }[q2bin]

    cfg_obs   = ObservableConf(
        name  = mass,
        range = (4800, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'reso/rk/mm/{component}.yaml')
    cfg  = ParametricConf(**data)
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    cache = Cache.cache_root(path = tmp_path)
    with ExitStack() as stack:
        stack.enter_context(cache)

        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rk_mm_os,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bdkstkpijpsiee, Component.bdkstkpipsi2ee])
def test_reso_rkst_ee(
    component : Component,
    tmp_path  : Path):
    '''
    Test resonant jpsi and psi2S in rkst muon channel
    '''
    q2bin = {
        Component.bdkstkpijpsiee : Qsq.jpsi,
        Component.bdkstkpipsi2ee : Qsq.psi2,
    }[component]

    mass = {
        Qsq.jpsi : Mass.bd_dtf_jpsi,
        Qsq.psi2 : Mass.bd_dtf_psi2
    }[q2bin]

    cfg_obs   = ObservableConf(
        name  = mass,
        range = (4500, 6000))

    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/ee/{component}.yaml')
    cfg  = ParametricConf(**data)
    cfg.add_category_suffix(suffix = 'b1')
    cfg  = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            cfg      = cfg,
            trigger  = Trigger.rkst_ee_os,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------

