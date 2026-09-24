'''
Module with tests for CCbarConfTF
'''
import pytest

from rx_common    import Cuts
from rx_common    import Block
from rx_common    import Component
from rx_common    import Project
from rx_common    import Qsq
from rx_common    import Trigger
from rx_selection import Registry, selection as sel
from fitter       import CCbarConfTF
from dmu          import LogStore
from dmu.testing  import stats as tst
from dmu.stats    import zfit, utilities as sut
from typing       import Final

_COMPONENT : Final[Component] = Component.data_24
_TRIGGER   : Final[Trigger  ] = Trigger.rk_ee_os 
_QSQ       : Final[Qsq      ] = Qsq.high

type zsum = zfit.pdf.SumPDF

log=LogStore.add_logger('fitter:test_ccbartf')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:model_factory', 30)
# ---------------------------------
def _get_pdf() -> zsum:
    obs  = zfit.Space('B_Mass', limits=(4500, 7000))
    pdfs = []
    fracs= []
    for block in Block.blocks():
        pdf = tst.get_model(
            obs    = obs,
            prefix = str(block),
            kind   = 'signal')
        pdfs.append(pdf)

        frac = zfit.Parameter(f'block_b{block}', 0.16, 0.0, 1.0)
        fracs.append(frac)

    return zfit.pdf.SumPDF(
        pdfs  = pdfs,
        fracs = fracs[:-1])
# ---------------------------------
def test_simple():
    '''
    Simplest test
    '''
    cuts           = sel.selection(q2bin = _QSQ, process = _COMPONENT, trigger = _TRIGGER)
    cuts[Cuts.cmb] = '(mva_cmb >= 0.6) && (mva_cmb < 1.0)'
    cuts[Cuts.prc] = '(mva_prc >= 0.5) && (mva_prc < 1.0)'

    entry = Registry(
        qsq       = _QSQ,
        trigger   = _TRIGGER,
        component = _COMPONENT)
    entry.set(cuts = cuts)

    pdf_sig = _get_pdf()
    cfg     = CCbarConfTF(kind = 'CCbarPDFTF')
    pdf_ccb = cfg.get_pdf(
        pdfs    = {Component.bpkpee : pdf_sig },
        project = Project.rk)

    sut.print_pdf(pdf_ccb)
# ---------------------------------
