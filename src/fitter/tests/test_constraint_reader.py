'''
Module with functions needed to test ConstraintReader class
'''
import tempfile
import pytest

from pytest         import MonkeyPatch
from typing         import Final, cast
from pathlib        import Path
from dmu.workflow   import Cache
from dmu            import LogStore
from dmu.stats      import zfit
from dmu.generic    import UnpackerModel, utilities           as gut
from rx_common      import Brem, Channel, Project, Qsq, Component
from fitter         import RXFitConfig
from zfit.loss      import ExtendedUnbinnedNLL
from zfit.param     import Parameter           as zpar
from zfit           import Space               as zobs
from fitter         import ConstraintReader
from fitter         import FitModelConf
from rx_common      import MVAWp
from patch_classes  import TestCmbConstraints, get_test_prec_constraints
from patch_classes  import TestMisIDConstraints

log=LogStore.add_logger('fitter:test_constraint_reader')

# TODO: Improve these tests
_PRC_COMPONENTS : Final[list[Component]] = [
    Component.bsphiee,
    Component.bpkstkpiee,
    Component.bdkstkpiee
]

_RESO_MISID_RKST_EE_COMPONENTS : Final[list[Component]] = [
    Component.bskstjpsiee,
    Component.lbpkjpsiee,
    Component.bsphijpsiee,
    Component.bdkstkpijpsiee_kpiee_pikee,
]

_RESO_MISID_RKST_MM_COMPONENTS : Final[list[Component]] = [
    Component.bskstjpsimm,
    Component.lbpkjpsimm,
    Component.bsphijpsimm,
    Component.bdkstkpijpsiee_kpiee_pikee,
]

_RESO_MISID_RK_EE_COMPONENTS : Final[list[Component]] = [
    Component.bppijpsiee,
]

_RESO_MISID_RK_MM_COMPONENTS : Final[list[Component]] = [
    Component.bppijpsimm,
]

_RESO_MISID_RK_CONSTRAINTS : Final[list[str]] = [
    f'reso_misid_rk_{Brem.zero}',
    f'reso_misid_rk_{Brem.one}',
    f'reso_misid_rk_{Brem.two}',
    f'reso_misid_rk_{Brem.brx12}',
]

_RESO_MISID_RKST_CONSTRAINTS : Final[list[str]] = [
    f'reso_misid_rkst_{Brem.zero}',
    f'reso_misid_rkst_{Brem.one}',
    f'reso_misid_rkst_{Brem.two}',
    f'reso_misid_rkst_{Brem.brx12}',
]

_RESO_MISID_CONSTRAINTS = _RESO_MISID_RK_CONSTRAINTS + _RESO_MISID_RKST_CONSTRAINTS

_CONSTRAINTS : Final[list[str]] = [
    'sig_par',
    'reso_misid_rk',
    'reso_misid_rkst',
    'rare_prec_rk',
    'rare_misid',
    'combinatorial',
    'brem_frac']
# ----------------------
@pytest.fixture(autouse=True)
def initialize(monkeypatch : MonkeyPatch):
    '''
    This will run before any test
    '''
    with tempfile.TemporaryDirectory(delete = False) as tmp_dir:
        monkeypatch.setenv('ANADIR', tmp_dir)

    LogStore.set_level('fitter:prec_scales'       , 10)
    LogStore.set_level('fitter:constraint_reader' , 10)
    LogStore.set_level('fitter:signal_constraints', 10)
    LogStore.set_level('fitter:scale_reader'      , 10)
    LogStore.set_level('fitter:cmb_constraints'   , 10)

    with UnpackerModel.package(name = 'fitter_data'):
        yield
# ----------------------
class Parameters:
    '''
    Class used to instantiate objects holding parameters and observables
    They are needed in tests
    '''
    # ----------------------
    def __init__(self, comp : Component, obs : zobs) -> None:
        '''
        Parameters
        -------------
        kind: Defines what parameters will be returning depending on test
        obs : Observable
        '''
        self._obs   = obs
        self._s_par = self._get_pars(comp = comp)
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
    def _get_pars(self, comp : Component) -> set[zpar]:
        '''
        Parameters
        -------------
        kind: Type of parameters

        Returns
        -------------
        Set of zfit parameters
        '''
        if   comp in {Component.bppijpsiee, Component.bppijpsimm}:
            l_par_name = f's_{comp}_{Brem.two}'
        elif comp in {Component.bdkstkpiee}:
            l_par_name = [ f's_{comp}_{Brem.two}' for comp in _PRC_COMPONENTS ]
        elif comp == Component.bpkpipi:
            l_par_name = ['yld_bpkpipi']
        elif comp == Component.bpkkk:
            l_par_name = ['yld_bpkkk']
        elif comp == Component.bpkpee:
            l_par_name = [
                f'mu_{comp}_brem_xx1_b1_rk_ee_scale_flt',
                f'sg_{comp}_brem_xx1_b1_rk_ee_reso_flt',
                f'mu_{comp}_brem_xx2_b1_rk_ee_scale_flt',
                f'sg_{comp}_brem_xx2_b1_rk_ee_reso_flt',
                # ------
                # Brem fraction
                # ------
                f'fr_{comp}_brem_brem_xx1_b1_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b2_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b3_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b4_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b5_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b6_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b7_reso_flt',
                f'fr_{comp}_brem_brem_xx1_b8_reso_flt',
                # ------
                # Block fraction
                # ------
                f'fr_{comp}_block_brem_x12_b1_flt',
                f'fr_{comp}_block_brem_x12_b2_flt',
                f'fr_{comp}_block_brem_x12_b3_flt',
                f'fr_{comp}_block_brem_x12_b4_flt',
                f'fr_{comp}_block_brem_x12_b5_flt',
                f'fr_{comp}_block_brem_x12_b6_flt',
                f'fr_{comp}_block_brem_x12_b7_flt',
                f'fr_{comp}_block_brem_x12_b8_flt']
        elif comp == Component.comb:
            l_par_name = [
                'mu_hypexp_comb_brem_x12_rk_ee_1',
                'ap_hypexp_comb_brem_x12_rk_ee_1',
                'bt_hypexp_comb_brem_x12_rk_ee_1']
        else:
            raise ValueError(f'Invalid kind of parameters: {comp}')

        return { zfit.Parameter(name, 0, 0, 1) for name in l_par_name }
    # ----------------------
    def __str__(self):
        names = [ par.name for par in self._s_par ]
        msg   = '\n'.join(names)

        return f'\n{msg}'
    # ----------------------
    def get_params(self, floating : bool = True, is_yield : bool = False) -> set[zpar]:
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
def _get_fit_config(
    out_dir : Path,
    project : Project,
    channel : Channel,
    q2bin   : Qsq) -> RXFitConfig:
    '''
    Parameters
    -------------
    q2bin: E.g. central

    Returns
    -------------
    Object storing fit configuration
    '''
    if q2bin.is_rare:
        data = gut.load_data(package='fitter_data', fpath = f'rare/{project}/{channel}/data.yaml')
    else:
        data = gut.load_data(package='fitter_data', fpath = f'reso/{project}/{channel}/data.yaml')

    mod_cfg = FitModelConf(**data)

    cfg = RXFitConfig(
        name    = 'test',
        group   = 'test',
        mod_cfg = mod_cfg,
        mva_cmb = MVAWp(0.9),
        mva_prc = MVAWp(0.8),
        q2bin   = q2bin,
        log_lvl = 10,
    )

    return cfg.model_copy(update = {'output_directory' : out_dir})
# --------------------------------------------------------------
def _get_component_config(
    comp  : Component,
    path  : Path, 
    q2bin : Qsq) -> RXFitConfig:
    '''
    Provides fit configuration for fit with specific component
    parameters constrained
    '''
    cfg = _get_fit_config(
        out_dir = path,
        project = Project.rk,
        channel = Channel.ee,
        q2bin   = q2bin)

    components = cfg.mod_cfg.components[q2bin]
    dropped    = [ component for component in components if component != comp ]
    for component in dropped: 
        del components[component]

    return cfg
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_rare_hadronic_misid(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path,
    q2bin       : Qsq):
    '''
    Test constraints for rare hadronic misID

    Parameters
    -------------
    q2bin: q2 bin
    '''
    monkeypatch.setattr(
        'fitter.constraint_reader.MisIDConstraints',
        TestMisIDConstraints)

    brem = Brem.brx12
    obs  = zfit.Space('dummy', limits=(4500, 6000))
    nll  = Parameters(comp = Component.bpkpipi, obs = obs)
    nll  = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params

    cfg = _get_fit_config(
        out_dir = tmp_path,
        q2bin   = q2bin,
        project = Project.rk,
        channel = Channel.ee)

    obj         = ConstraintReader(
        brem    = brem,
        signal  = Component.bpkpee,
        nll     = nll, cfg=cfg)
    constraints = obj.get_constraints(
        skip_comb   = True,
        skip_signal = True,
        skip_prec   = True)

    print(constraints)
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
@pytest.mark.parametrize('brem' , [Brem.one, Brem.two, Brem.brx12])
def test_background_fraction(
    monkeypatch: MonkeyPatch,
    brem       : Brem,
    tmp_path   : Path,
    q2bin      : Qsq):
    '''
    Tests scales for background fraction in rare mode

    Parameters
    -------------
    q2bin: q2 bin
    '''
    monkeypatch.setattr(
        'fitter.constraint_reader.get_prec_constraints', 
        get_test_prec_constraints)

    obs  = zfit.Space('dummy', limits=(4500, 6000))
    nll  = Parameters(comp = Component.bdkstkpiee, obs = obs)
    nll  = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params
    cfg  = _get_fit_config(
        out_dir = tmp_path,
        project = Project.rk,
        channel = Channel.ee,
        q2bin   = q2bin)

    obj         = ConstraintReader(
        brem    = brem,
        signal  = Component.bpkpee,
        nll     = nll,
        cfg     = cfg)

    constraints = obj.get_constraints(
        skip_comb   = True,
        skip_signal = True,
        skip_misid  = True)

    log.info('-------------------------------')
    print(constraints)
    log.info('-------------------------------')

    assert len(constraints.root) == len(_PRC_COMPONENTS)
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
@pytest.mark.parametrize('comp' , [Component.bpkpee])
def test_signal(
    tmp_path : Path,
    comp     : Component,
    q2bin    : Qsq):
    '''
    Check signal shape constraints
    '''
    brem = Brem.brx12

    obs  = zfit.Space('dummy', limits=(4500, 6000))
    nll  = Parameters(comp = comp, obs = obs)
    nll  = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params
    cfg  = _get_component_config(
        comp = comp,
        path = tmp_path, 
        q2bin= q2bin)

    with Cache.cache_root(path = tmp_path):
        obj        = ConstraintReader(
            brem   = brem,
            signal = comp,
            nll    = nll,
            cfg    = cfg)
        constraints= obj.get_constraints()

    print(constraints)

    pars = nll.get_params()
    assert len(constraints.root) == len(pars) 
# --------------------------------------------------------------
@pytest.mark.parametrize('q2bin', [Qsq.low, Qsq.central, Qsq.high])
def test_combinatorial(
    monkeypatch : MonkeyPatch,
    tmp_path    : Path,
    q2bin       : Qsq):
    '''
    Tests all the constraints but the combinatorial shape

    Parameters
    -------------
    q2bin: q2 bin
    '''
    monkeypatch.setattr('fitter.constraint_reader.CmbConstraints', TestCmbConstraints)

    brem   = Brem.brx12
    signal = Component.bpkpee

    obs = zfit.Space('B_Mass_smr', limits=(4500, 7000))
    cfg = _get_fit_config(
        out_dir = tmp_path,
        q2bin   = q2bin,
        project = Project.rk,
        channel = Channel.ee)

    nll = Parameters(comp = Component.comb, obs = obs)
    nll = cast(ExtendedUnbinnedNLL, nll) # Tests will only need get_params

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

    print(constraints)

    assert len(constraints.root) > 0
# --------------------------------------------------------------
