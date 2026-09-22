'''
Module with tests for CCbarConfTF
'''
from rx_common    import Cuts
from rx_common    import Block
from rx_common    import Component
from rx_common    import Project
from rx_common    import Qsq
from rx_common    import Trigger
from rx_selection import Registry, selection as sel
from fitter       import CCbarConfTF
from dmu.testing  import stats as tst
from dmu.stats    import zfit, utilities as sut
from typing       import Final

_COMPONENT : Final[Component] = Component.data_24
_TRIGGER   : Final[Trigger  ] = Trigger.rk_ee_os 
_QSQ       : Final[Qsq      ] = Qsq.high

type zsum = zfit.pdf.SumPDF
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
    cuts[Cuts.cmb] = 'mva_cmb > 0.5'
    cuts[Cuts.prc] = 'mva_prc > 0.5'

    entry = Registry(
        qsq       = _QSQ,
        trigger   = _TRIGGER,
        component = _COMPONENT)
    entry.set(cuts = cuts)

    pdf = _get_pdf()
    cfg = CCbarConfTF(kind = 'CCbarPDFTF')
    pdf = cfg.get_pdf(
        pdfs    = {Component.bpkpee : pdf },
        project = Project.rk)

    sut.print_pdf(pdf)
# ---------------------------------
