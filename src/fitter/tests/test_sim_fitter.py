'''
This module is meant to test the SimFitter class
'''
import pytest

from pathlib       import Path
from dmu           import LogStore
from dmu.stats     import ParsHolder, print_pdf, zfit
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import utilities as sut
from dmu.workflow  import Cache

from rx_common     import Component, Cuts, Mass, Qsq, Region
from rx_common     import Trigger
from rx_data       import RDFGetter
from rx_selection  import selection as sel
from fitter        import CombinatorialConf
from fitter        import SimFitter
from fitter        import ParametricConf
from fitter        import CCbarConf
from fitter        import NonParametricConf
from fitter        import MisIDConf
from fitter        import SignalConstraints

log=LogStore.add_logger('fitter:test_sim_fitter')
# ---------------------------------------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    Runs before any test
    '''
    log.info('Disabling caching')

    LogStore.set_level('fitter:signal_constraints', 10)
    LogStore.set_level('fitter:category_merger'   , 10)
    LogStore.set_level('fitter:sim_fitter'        , 10)

    with RDFGetter.max_entries(value = 100_000):
        yield
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
    obs = zfit.Space(obs = 'B_Mass_smr', limits=(4500, 7000), label = 'nomc')

    data = gut.load_data(package='fitter_data', fpath='rare/rk/ee/comb.yaml')
    cfg  = CombinatorialConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= Component.comb,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.low)
        _ = ftr.get_model()
# ---------------------------------------------------
def test_nocat(tmp_path : Path):
    '''
    Test for components without categories, e.g. muon
    '''
    obs   = zfit.Space('B_Mass_smr', limits=(5000, 5800))
    data  = gut.load_data(package='fitter_data', fpath='rare/rk/mm/bpkpmm.yaml')
    cfg   = ParametricConf(**data)

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value=30_000):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rk_mm_os,
            q2bin    = Qsq.jpsi)
        ftr.get_model()
# ---------------------------------------------------
def test_with_cat(tmp_path : Path):
    '''
    Test for components with brem categories
    '''
    region = Region.brem_xx1
    obs    = zfit.Space(
        obs   = Mass.bp_bcor.latex, 
        label = Mass.bp_bcor,
        limits=(4600, 6900))
    data = gut.load_data(package='fitter_data', fpath='rare/rk/ee/bpkpee.yaml.j2')
    cfg  = ParametricConf(**data)
    cfg  = cfg.cfg_copy(replacements = {'BREM' : region})

    def _filter(name : str) -> bool:
        c1 = name.endswith('_b1')
        c2 = name.endswith('_b2')

        return c1 or c2

    cfg  = cfg.filter_category(func = _filter)
    d_sel= {
        Cuts.brem: region.selection,
        Cuts.cmb : 'mva_cmb > 0.9', 
        Cuts.prc : 'mva_prc > 0.5'}

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1),\
        sel.custom_selection(d_sel = d_sel):
        ftr = SimFitter(
            name     = region,
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.high)

        pdf = ftr.get_model()

    assert pdf is not None

    print_pdf(pdf = pdf)
# ---------------------------------------------------
def test_with_cat_constrained(tmp_path : Path):
    '''
    Test for signal and add constraints
    '''
    obs  = zfit.Space(
        obs   = Mass.bp_bcor_smr.latex, 
        label = Mass.bp_bcor_smr,
        limits=(4500, 7000))
    data = gut.load_data(package='fitter_data', fpath='rare/rk/ee/bpkpee.yaml.j2')
    cfg  = ParametricConf(**data)

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.central)

        pdf = ftr.get_model()

    assert pdf is not None

    pdf = _float_fix_pars(pdf = pdf)
    calc= SignalConstraints(nll = pdf, comp = Component.bpkpee)
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
    mass = Mass.bp_bcor_smr

    obs = zfit.Space(
        obs   = mass.latex,
        label = mass,
        limits= mass.limits)
    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}_np.yaml')
    cfg  = NonParametricConf(**data)

    with Cache.cache_root(path = tmp_path),\
         RDFGetter.max_entries(value = -1):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rk_ee_os,
            q2bin    = Qsq.central)
        ftr.get_model()
# ---------------------------------------------------
@pytest.mark.parametrize('component', [Component.bpkpipiee, Component.bdkstkpijpsiee])
def test_kde_rkst(component : Component, tmp_path : Path):
    '''
    Test fitting with KDE
    '''
    mass   = Mass.bp_bcor_smr
    limits = 4600, 6900

    obs       = zfit.Space(
        obs   = mass.latex,
        label = mass,
        limits= limits)
    data = gut.load_data(package='fitter_data', fpath=f'rare/rkst/ee/{component}_np.yaml')
    cfg  = NonParametricConf(**data)

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
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rkst_ee_os,
            q2bin    = Qsq.central)
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

    mass = Mass.bp_bcor
    obs  = zfit.Space(
        obs   = mass.latex,
        label = mass, 
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}_np.yaml')

    with UnpackerModel.package('fitter_data'):
        cfg  = MisIDConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
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
    component = Component.ccbar 
    obs       = zfit.Space(
        obs   = mass.latex, 
        label = mass,
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'reso/rk/ee/{component}.yaml')
    cfg  = CCbarConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= component,
            obs      = obs,
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
    component = Component.ccbar 
    obs       = zfit.Space(
        obs   = mass.latex, 
        label = mass,
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/ee/{component}.yaml')
    cfg  = CCbarConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= component,
            obs      = obs,
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
    obs       = zfit.Space(
        obs   = mass.latex,
        label = mass,
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'rare/rk/ee/{component}.yaml')
    cfg  = CCbarConf(**data)

    d_sel = {
        Cuts.cmb : 'mva_cmb > 0.8',
        Cuts.prc : 'mva_prc > 0.8',
             }

    with Cache.cache_root(path = tmp_path),\
        sel.custom_selection(d_sel=d_sel):

        ftr = SimFitter(
            name     = 'main',
            component= component,
            obs      = obs,
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
    obs  = zfit.Space(
        obs   = Mass.bp_dtf_jpsi.latex,
        label = Mass.bp_dtf_jpsi,
        limits= Mass.bp_dtf_jpsi.limits)

    data = gut.load_data(package='fitter_data', fpath=f'reso/rk/ee/{component}.yaml')
    cfg  = ParametricConf(**data)
    cfg.add_category_suffix(suffix = 'b1')

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
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

    obs = zfit.Space(
        obs   = mass.latex, 
        label = mass,
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/mm/{component}.yaml')
    cfg  = ParametricConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rkst_mm_os,
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

    obs = zfit.Space(
        obs   = mass.latex, 
        label = mass,
        limits= mass.limits)

    data = gut.load_data(package='fitter_data', fpath=f'reso/rkst/ee/{component}.yaml')
    cfg  = ParametricConf(**data)

    with Cache.cache_root(path = tmp_path):
        ftr = SimFitter(
            name     = 'main',
            component= cfg.component,
            obs      = obs,
            cfg      = cfg,
            trigger  = Trigger.rkst_ee_os,
            q2bin    = q2bin)
        ftr.get_model()
# ---------------------------------------------------

