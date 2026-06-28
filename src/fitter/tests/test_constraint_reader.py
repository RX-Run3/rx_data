'''
Module with functions needed to test ConstraintReader class
'''
import pytest

from contextlib     import ExitStack
from typing         import Final, cast
from pathlib        import Path
from dmu.workflow   import Cache
from dmu            import LogStore
from dmu.stats      import ModelFactory, print_constraints
from dmu.stats      import zfit
from dmu.stats      import ParameterLibrary as PL
from dmu.generic    import UnpackerModel, utilities           as gut
from rx_common      import Brem, Qsq, Component, Region, Cuts
from rx_selection   import selection           as sel
from fitter         import RXFitConfig
from zfit.loss      import ExtendedUnbinnedNLL
from zfit.param     import Parameter           as zpar
from zfit           import Space               as zobs
from zfit.pdf       import BasePDF             as zpdf 
from fitter         import ConstraintReader
from fitter         import CombinatorialConf, FitModelConf
from fitter         import MVAWp

log=LogStore.add_logger('fitter:test_constraint_reader')

_PRC_COMPONENTS : Final[list[Component]] = [
    Component.bsphiee,
    Component.bpkstkpiee,
    Component.bdkstkpiee
]

_CONSTRAINTS : Final[list[str]] = [
    'sig_par', 
    'rare_prec_rk', 
    'rare_misid',
    'combinatorial', 
    'brem_frac']
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:prec_scales'       , 10)
    LogStore.set_level('fitter:constraint_reader' , 10)
    LogStore.set_level('fitter:signal_constraints', 10)
    LogStore.set_level('fitter:scale_reader'      , 10)
    LogStore.set_level('fitter:cmb_constraints'   , 10)

    with UnpackerModel.package(name = 'fitter_data'):
        yield
# ----------------------
def _get_signal(
    obs   : zobs,
    brem  : int, 
    block : int) -> zpdf:
    mu_name = f'mu_bpkpee_brem_xx{brem}_b{block}_scale_flt'
    sg_name = f'sg_bpkpee_brem_xx{brem}_b{block}_reso_flt'

    mu   = zfit.Parameter(mu_name, 5200, 4500, 6000)
    sg   = zfit.Parameter(sg_name,  150,   10, 200)
    pdf  = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg)
    nev  = zfit.param.Parameter(f'nsig_{brem}_{block}', 1000, 0, 1000_000)

    sig  = pdf.create_extended(nev)

    return sig
# ----------------------
class Parameters:
    '''
    Class used to instantiate objects holding parameters and observables
    They are needed in tests
    '''
    # ----------------------
    def __init__(self, kind : str, obs : zobs) -> None:
        '''
        Parameters
        -------------
        kind: Defines what parameters will be returning depending on test
        obs : Observable
        '''
        self._obs   = obs
        self._s_par = self._get_pars(kind=kind)
    # ----------------------
    @property
    def space(self) -> zobs:
        '''
        Returns
        -------------
        Observable
        '''
        return self._obs
    # ----------------------
    def _get_pars(self, kind : str) -> set[zpar]:
        '''
        Parameters
        -------------
        kind: Type of parameters

        Returns
        -------------
        Set of zfit parameters
        '''
        if   kind == 'dummy':
            return set()
        # -----------------------------
        elif kind == f'reso_misid_rkst_{Brem.zero}':
            l_par_name = [ f's_{comp}_{Brem.zero}'  for comp in _RESO_MISID_RKST_MM_COMPONENTS ]
        # -----------------------------
        elif kind == f'reso_misid_rkst_{Brem.brx12}':
            l_par_name = [ f's_{comp}_{Brem.brx12}' for comp in _RESO_MISID_RKST_EE_COMPONENTS ]
        elif kind == f'reso_misid_rkst_{Brem.one}':
            l_par_name = [ f's_{comp}_{Brem.one}'   for comp in _RESO_MISID_RKST_EE_COMPONENTS ]
        elif kind == f'reso_misid_rkst_{Brem.two}':
            l_par_name = [ f's_{comp}_{Brem.two}'   for comp in _RESO_MISID_RKST_EE_COMPONENTS ]
        # -----------------------------
        elif kind == f'reso_misid_rk_{Brem.zero}':
            l_par_name = [ f's_{comp}_{Brem.zero}'  for comp in _RESO_MISID_RK_MM_COMPONENTS ]
        # -----------------------------
        elif kind == f'reso_misid_rk_{Brem.brx12}':
            l_par_name = [ f's_{comp}_{Brem.brx12}' for comp in _RESO_MISID_RK_EE_COMPONENTS ]
        elif kind == f'reso_misid_rk_{Brem.one}':
            l_par_name = [ f's_{comp}_{Brem.one}'   for comp in _RESO_MISID_RK_EE_COMPONENTS ]
        elif kind == f'reso_misid_rk_{Brem.two}':
            l_par_name = [ f's_{comp}_{Brem.two}'   for comp in _RESO_MISID_RK_EE_COMPONENTS ]
        # -----------------------------
        elif kind == f'rare_prec_rk_{Brem.brx12}':
            l_par_name = [ f's_{comp}_{Brem.brx12}' for comp in _PRC_COMPONENTS ]
        elif kind == f'rare_prec_rk_{Brem.one}':
            l_par_name = [ f's_{comp}_{Brem.one}'   for comp in _PRC_COMPONENTS ]
        elif kind == f'rare_prec_rk_{Brem.two}':
            l_par_name = [ f's_{comp}_{Brem.two}'   for comp in _PRC_COMPONENTS ]
        # -----------------------------
        elif kind == 'rare_prec_rkst':
            l_par_name = []
        elif kind == 'rare_misid':
            l_par_name = [
                'yld_bpkpipi',
                'yld_bpkkk']
        elif kind == 'brem_frac':
            l_par_name = [
                'fr_brem_xx1_b1_reso_flt',
                'fr_brem_xx1_b2_reso_flt',
                'fr_brem_xx1_b3_reso_flt',
                'fr_brem_xx1_b4_reso_flt',
                'fr_brem_xx1_b5_reso_flt',
                'fr_brem_xx1_b6_reso_flt',
                'fr_brem_xx1_b7_reso_flt',
                'fr_brem_xx1_b8_reso_flt']
        elif kind == 'sig_par':
            l_par_name = [
                'mu_bpkpee_brem_xx1_b1_scale_flt',
                'sg_bpkpee_brem_xx1_b1_reso_flt',
                'mu_bpkpee_brem_xx2_b1_scale_flt',
                'sg_bpkpee_brem_xx2_b1_reso_flt',
                'al_dscb_Signal_xx2_1_reso_flt',
                'ar_dscb_Signal_xx2_1_reso_flt',
                'nl_dscb_Signal_xx1_1_reso_flt',
                'nr_dscb_Signal_xx2_1_reso_flt']
        elif kind == 'combinatorial':
            l_par_name = [
                'mu_hypexp_comb_main_1',
                'ap_hypexp_comb_main_1',
                'bt_hypexp_comb_main_1',
                'ncmb',
                'nsig']
        else:
            raise ValueError(f'Invalid kind of parameters: {kind}')

        return { zfit.Parameter(name, 0, 0, 1) for name in l_par_name }
    # ----------------------
    def __str__(self):
        names = [ par.name for par in self._s_par ]
        msg   = '\n'.join(names)

        return f'\n{msg}'
    # ----------------------
    def get_params(self, floating : bool, is_yield : bool = False) -> set[zpar]:
        '''
        Parameters
        -------------
        floating: Bool, meant to be True

        Returns
        -------------
        Set of zfit parameters
        '''
        _ = is_yield
        _ = floating

        return self._s_par 
# ----------------------
def _get_nll(
    obs  : zobs, 
    reg  : Region,
    q2bin: Qsq,
    cfg  : RXFitConfig) -> ExtendedUnbinnedNLL:
    '''
    Parameters
    -------------
    reg  : Region
    obs  : Observable
    cfg  : Configuration for fit
    q2bin: E.g. central

    Returns
    -------------
    Likelihood with:

    - PDF used to fit combinatorial
    - Parameters needed for misID
    '''
    cfg_cmb = cfg.mod_cfg.components[Component.comb]
    if not isinstance(cfg_cmb, CombinatorialConf):
        ctype = type(cfg_cmb)
        raise ValueError(f'Expected combinatorial config, found: {ctype}')

    sig_11 = _get_signal(obs = obs, brem = 1, block = 1)
    sig_21 = _get_signal(obs = obs, brem = 2, block = 1)
    sig_12 = _get_signal(obs = obs, brem = 1, block = 2)
    sig_22 = _get_signal(obs = obs, brem = 2, block = 2)

    pdf_names = cfg_cmb.models[q2bin].pdfs
    fct  = ModelFactory(
        preffix = reg,
        obs     = obs,
        l_pdf   = pdf_names,
        l_shared= [],
        l_float = [])
    expo = fct.get_pdf()

    nexpo = zfit.param.Parameter('nbkg', 1000, 0, 1000_000)

    bkg   = expo.create_extended(nexpo, name = f'{Component.comb}_{reg}')
    pdf   = zfit.pdf.SumPDF(pdfs = [bkg, sig_11, sig_21, sig_22, sig_12])
    dat   = pdf.create_sampler()

    return zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
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
    if q2bin.is_rare:
        data = gut.load_data(package='fitter_data', fpath = 'rare/rk/ee/data.yaml')
    else:
        data = gut.load_data(package='fitter_data', fpath = 'reso/rk/ee/data.yaml')

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
# --------------------------------------------------------------
@pytest.mark.skip(reason = 'Includes misID, too slow')
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
@pytest.mark.parametrize('kind' , _CONSTRAINTS)
def test_all_but_cmb(
    tmp_path : Path, 
    kind     : str, 
    q2bin    : Qsq,
    slow_mode: bool):
    '''
    Tests all the constraints but the combinatorial shape

    Parameters
    -------------
    kind : Type of parameters
    q2bin: q2 bin
    '''
    brem = Brem.brx12

    obs = zfit.Space('dummy', limits=(4500, 6000))
    nll = Parameters(kind = kind, obs = obs) 
    nll = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params

    cfg = _get_fit_config(q2bin = q2bin)
    del cfg.mod_cfg.components[Component.comb]

    if not slow_mode:
        log.info('Skipping misid constraints')
        del cfg.mod_cfg.components[Component.bpkkk  ]
        del cfg.mod_cfg.components[Component.bpkpipi]
    else:
        log.info('Running full test')

    with Cache.cache_root(path = tmp_path):
        obj        = ConstraintReader(
            brem   = brem,
            signal = Component.bpkpee,
            nll    = nll, 
            cfg    = cfg)
        constraints= obj.get_constraints()

    print_constraints(constraints = constraints)

    # TODO: Needs to be updated when other parameter constraints be implemented
    if kind != 'rare_prec_rk':
        return

    assert len(constraints) > 0 
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_only_cmb(
    tmp_path : Path, 
    q2bin    : Qsq):
    '''
    Tests all the constraints but the combinatorial shape

    Parameters
    -------------
    q2bin: q2 bin
    '''
    brem   = Brem.brx12
    signal = Component.bpkpee

    obs  = zfit.Space('B_Mass_smr', limits=(4500, 7000))
    cfg  = _get_fit_config(q2bin = q2bin)
    nll  = _get_nll(
        obs   = obs, 
        reg   = brem.region,
        cfg   = cfg, 
        q2bin = q2bin) 

    with ExitStack() as stack:
        stack.enter_context(Cache.cache_root(path = tmp_path))
        stack.enter_context(sel.custom_selection(d_sel = cfg.overriding_selection))
        stack.enter_context(PL.parameter_schema(cfg = cfg.mod_cfg.yields))

        obj         = ConstraintReader(
            brem    = brem,
            signal  = signal,
            nll     = nll, 
            cfg     = cfg)

        constraints = obj.get_constraints(
            skip_misid  = True,
            skip_signal = True,
            skip_prec   = True,
        )

    print_constraints(constraints = constraints)

    assert len(constraints) > 0 
# --------------------------------------------------------------
@pytest.mark.skip(reason = 'Includes misID, too slow')
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_rare_misid(
    tmp_path : Path, 
    q2bin    : Qsq):
    '''
    Tests all the constraints but the combinatorial shape

    Parameters
    -------------
    q2bin: q2 bin
    '''
    brem = Brem.brx12
    obs  = zfit.Space('dummy', limits=(4500, 6000))
    nll  = Parameters(kind = 'rare_misid', obs = obs) 
    nll  = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params

    cfg = _get_fit_config(q2bin = q2bin)
    del cfg.mod_cfg.components[Component.comb]

    with Cache.cache_root(path = tmp_path):
        obj         = ConstraintReader(
            brem    = brem,
            signal  = Component.bpkpee,
            nll     = nll, cfg=cfg)
        constraints = obj.get_constraints(
            skip_comb   = True,
            skip_signal = True,
            skip_prec   = True,
    )


    print_constraints(constraints = constraints)
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
@pytest.mark.parametrize('brem' , [Brem.one, Brem.two, Brem.brx12])
def test_only_prec(
    brem     : Brem,
    tmp_path : Path, 
    q2bin    : Qsq):
    '''
    Tests all the constraints but the combinatorial shape

    Parameters
    -------------
    q2bin: q2 bin
    '''
    obs  = zfit.Space('dummy', limits=(4500, 6000))
    nll  = Parameters(kind = f'rare_prec_rk_{brem}', obs = obs) 
    nll  = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params
    cfg  = _get_fit_config(q2bin = q2bin)

    for component in _PRC_COMPONENTS:
        cfg.mod_cfg.components.pop(component, None)

    with Cache.cache_root(path = tmp_path):
        obj         = ConstraintReader(
            brem    = brem,
            signal  = Component.bpkpee,
            nll     = nll, 
            cfg     = cfg)

        constraints = obj.get_constraints(
            skip_comb   = True,
            skip_signal = True,
            skip_misid  = True,
    )

    log.error('-------------------------------')
    print_constraints(constraints = constraints)
    log.error('-------------------------------')

    assert len(constraints) == len(_PRC_COMPONENTS)
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_save(
    tmp_path : Path, 
    q2bin    : Qsq):
    '''

    Parameters
    -------------
    q2bin: q2 bin
    '''
    brem = Brem.brx12
    obs  = zfit.Space('B_Mass_smr', limits=(4500, 7000))
    cfg  = _get_fit_config(q2bin = q2bin)
    nll  = _get_nll(obs=obs, cfg=cfg, q2bin = q2bin, reg = brem.region) 

    with Cache.cache_root(path = tmp_path):
        obj         = ConstraintReader(
            brem    = brem,
            signal  = Component.bpkpee,
            nll     = nll,
            cfg     = cfg)
        constraints = obj.get_constraints(
            skip_misid = True,
            save_to    = tmp_path / 'constraints.yaml')

    print_constraints(constraints = constraints)

    assert len(constraints) > 0 
# --------------------------------------------------------------
