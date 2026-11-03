'''
Module holding functions needed to test SignalConstraints class
'''
import pytest

from dmu       import LogStore
from dmu.stats import CorrectionImplementation, Model, zfit
from dmu.stats import ModelFactory
from rx_common import Block, Brem, Channel, Component, Cuts
from zfit.loss import ExtendedUnbinnedNLL
from fitter    import SignalConstraints
from fitter    import Category
from fitter    import CategoryMerger

Loss = zfit.loss.ExtendedUnbinnedNLL
zobs = zfit.Space
zpdf = zfit.pdf.BasePDF
zpar = zfit.param.Parameter
log  = LogStore.add_logger('fitter:test_signal_constraints')

_RK_SHAPE = [
    'mu_bpkpee_brem_xx1_b1_scale_flt',
    'sg_bpkpee_brem_xx1_b1_reso_flt',
    'mu_bpkpee_brem_xx2_b1_scale_flt',
    'sg_bpkpee_brem_xx2_b1_reso_flt',
]

_FRACTIONS_BREM_1 = [
    'block_brem_xx1_b1_flt',
    'block_brem_xx1_b2_flt',
    'block_brem_xx1_b3_flt',
    'block_brem_xx1_b4_flt',
    'block_brem_xx1_b5_flt',
    'block_brem_xx1_b6_flt',
    'block_brem_xx1_b7_flt',
]

_FRACTIONS_BREM_2 = [
    'block_brem_xx2_b1_flt',
    'block_brem_xx2_b2_flt',
    'block_brem_xx2_b3_flt',
    'block_brem_xx2_b4_flt',
    'block_brem_xx2_b5_flt',
    'block_brem_xx2_b6_flt',
    'block_brem_xx2_b7_flt',
]

_FRACTIONS_BY_BREM = {
    Brem.one : _FRACTIONS_BREM_1,
    Brem.two : _FRACTIONS_BREM_2,
}

_RK_FRACTIONS = [
    'fr_bpkpee_block_brem_x12_b1_flt',
    'fr_bpkpee_block_brem_x12_b2_flt',
    'fr_bpkpee_block_brem_x12_b3_flt',
    'fr_bpkpee_block_brem_x12_b4_flt',
    'fr_bpkpee_block_brem_x12_b5_flt',
    'fr_bpkpee_block_brem_x12_b6_flt',
    'fr_bpkpee_block_brem_x12_b7_flt',
    'fr_bpkpee_brem_brem_xx1_b1_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b2_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b3_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b4_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b5_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b6_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b7_reso_flt',
    'fr_bpkpee_brem_brem_xx1_b8_reso_flt',
]

_RKST_FRACTIONS = [
    'fr_bdkstkpiee_block_brem_x12_b1_flt',
    'fr_bdkstkpiee_block_brem_x12_b2_flt',
    'fr_bdkstkpiee_block_brem_x12_b3_flt',
    'fr_bdkstkpiee_block_brem_x12_b4_flt',
    'fr_bdkstkpiee_block_brem_x12_b5_flt',
    'fr_bdkstkpiee_block_brem_x12_b6_flt',
    'fr_bdkstkpiee_block_brem_x12_b7_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b1_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b2_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b3_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b4_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b5_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b6_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b7_reso_flt',
    'fr_bdkstkpiee_brem_brem_xx1_b8_reso_flt',
]

_FRACTIONS = {
    Component.bpkpee    :   _RK_FRACTIONS,
    Component.bdkstkpiee: _RKST_FRACTIONS,
}

_BREM_CATS = [Brem.one, Brem.two]
# ----------------------
class ParsHolder:
    def __init__(self, pars : list[str]):
        self._pars = pars
    # -------------------------
    def _make_param(self, name : str) -> zpar:
        return zfit.Parameter(
            name = name,
            value= 0.5,
            lower= 0.0,
            upper= 1.0)
    # -------------------------
    def get_params(self, *args, **kwargs)-> set[zpar]:
        _    = kwargs
        _    = args

        pars = { self._make_param(name = name) for name in self._pars }

        return pars
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:signal_constraints', 10)
# ----------------------
def _fix_tails(pdf : zpdf) -> zpdf:
    '''
    Parameters
    -------------
    pdf: Zfit PDF

    Returns
    -------------
    Input PDF with tails fixed
    '''
    pars = pdf.get_params()
    for par in pars:
        if par.name.startswith('mu_'):
            continue

        if par.name.startswith('sg_'):
            continue

        par.floating = False

    return pdf
# ----------------------
def _get_signal(
    obs  : zobs,
    brem : Brem,
    block: Block):

    signal_name = f'signal_brem_{brem}_b{block}'
    scale       = CorrectionImplementation.scale
    reso        = CorrectionImplementation.reso

    with ModelFactory.correction(fixed = False):
        fct = ModelFactory(
            obs     = obs,
            l_pdf   = [Model.dscb],
            l_shared= [],
            l_float = [],
            d_rep   = {'mu' : scale, 'sg' : reso},
            preffix = signal_name)
        dscb = fct.get_pdf()
        dscb = _fix_tails(pdf = dscb)

    return dscb
# ----------------------
def _get_category(
    block: Block,
    brem : Brem,
    obs  : zobs) -> Category:
    '''
    Parameters
    -------------

    Returns
    -------------
    Category object
    '''

    pdf  = _get_signal(
        obs  = obs,
        brem = brem,
        block= block)

    cat  = Category(
        name      = f'{brem}_b{block}',
        pdf       = pdf,
        sumw      = 1000.,
        selection = {Cuts.mass : '(1)'},
        model     = [Model.gauss])

    return cat
# ----------------------
def test_full_model():
    '''
    Add brems and then blocks
    '''
    obs        = zfit.Space('dummy', limits=(4500, 6000))
    categories = [ _get_category(block = block, brem = brem, obs = obs) for block in Block.blocks() for brem in _BREM_CATS ]

    mgr = CategoryMerger(
        comp          = Component.bpkpee,
        categories    = categories,
        reparametrize = True)
    cat = mgr.get_category()
    nsg = zfit.Parameter('nsig', 1000, 0, 10_000)
    pdf = cat.pdf.create_extended(nsg)

    dat = pdf.create_sampler()
    nll = ExtendedUnbinnedNLL(model = pdf, data = dat)

    calc= SignalConstraints(
        nll     = nll,
        channel = Channel.ee,
        comp    = Component.bpkpee)
    constraints = calc.get_constraints()

    for cons in sorted(constraints):
        log.info(cons)

    ncons = len(constraints)
    log.info(f'Found {ncons} constraints')
# ----------------------
@pytest.mark.parametrize('component', [Component.bpkpee, Component.bdkstkpiee])
def test_fractions(component :  Component):
    '''
    Test that we can retrieve constraints
    for all fractions
    '''
    fractions = _FRACTIONS[component]

    nll = ParsHolder(pars = fractions)
    calc= SignalConstraints(
        nll     = nll,
        channel = Channel.ee,
        comp    = component)
    constraints = calc.get_constraints()

    for cons in sorted(constraints):
        log.info(cons)

    assert len(constraints) == len(fractions)
# ----------------------
@pytest.mark.parametrize('shapes', [_RK_SHAPE])
def test_rk_shape(shapes : list[str]):
    '''
    Test constraints to mu and sg
    '''
    nll   = ParsHolder(pars = shapes)
    calc  = SignalConstraints(
        nll     = nll,
        channel = Channel.ee,
        comp    = Component.bpkpee)
    constraints = calc.get_constraints()

    ncons = len(constraints)

    log.info(f'Found {ncons} constraints')

    assert ncons == len(shapes)
# ----------------------
@pytest.mark.parametrize('component', [Component.bpkpee, Component.bdkstkpiee])
@pytest.mark.parametrize('brem'     , [Brem.one, Brem.two])
def test_fractions_by_brem(component :  Component, brem : Brem):
    '''
    Test that we can retrieve constraints
    for all fractions
    '''
    values    = _FRACTIONS_BY_BREM[brem]
    fractions = [ f'fr_{component}_{value}' for value in values ]

    nll = ParsHolder(pars = fractions)
    calc= SignalConstraints(
        nll     = nll,
        channel = Channel.ee,
        comp    = component)
    constraints = calc.get_constraints()

    for cons in sorted(constraints):
        log.info(cons)

    assert len(constraints) == len(fractions)
