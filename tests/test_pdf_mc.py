'''
Module with tests for PdfBuilder class
'''
import pytest

from contextlib     import ExitStack
from dmu.stats      import print_pdf, zfit
from dmu.stats      import FittedModel
from pathlib        import Path
from typing         import Final
from rx_common      import Component, Qsq, Trigger, Cuts
from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder

_SAMPLES_RK_EE : Final[list[tuple[Component,Trigger,Qsq,bool]]] = [
    (Component.bpkppsi2ee, Trigger.rk_ee_os, Qsq.jpsi, False),
    (Component.bpkpjpsiee, Trigger.rk_ee_os, Qsq.psi2, False),
    (Component.bpkppsi2ee, Trigger.rk_ee_os, Qsq.high, False),
    (Component.bpkpjpsiee, Trigger.rk_ee_os, Qsq.high, False),
    (Component.bpkppsi2ee, Trigger.rk_ee_os, Qsq.psi2, True ),
    (Component.bpkpjpsiee, Trigger.rk_ee_os, Qsq.jpsi, True ),
]

_SAMPLES_RKST_EE : Final[list[tuple[Component,Trigger,Qsq,bool]]] = [
    (Component.bdkstkpipsi2ee, Trigger.rkst_ee_os, Qsq.jpsi, False),
    (Component.bdkstkpijpsiee, Trigger.rkst_ee_os, Qsq.psi2, False),
    (Component.bdkstkpipsi2ee, Trigger.rkst_ee_os, Qsq.high, False),
    (Component.bdkstkpijpsiee, Trigger.rkst_ee_os, Qsq.high, False),
    (Component.bdkstkpipsi2ee, Trigger.rkst_ee_os, Qsq.psi2, True ),
    (Component.bdkstkpijpsiee, Trigger.rkst_ee_os, Qsq.jpsi, True ),
]

_SAMPLES_RK_MM : Final[list[tuple[Component,Trigger,Qsq]]] = [
    (Component.bpkpjpsimm, Trigger.rk_mm_os, Qsq.jpsi),
    (Component.bpkppsi2mm, Trigger.rk_mm_os, Qsq.psi2),
]

_SAMPLES_RKST_MM : Final[list[tuple[Component,Trigger,Qsq]]] = [
    (Component.bdkstkpijpsimm, Trigger.rkst_mm_os, Qsq.jpsi),
    (Component.bdkstkpipsi2mm, Trigger.rkst_mm_os, Qsq.psi2),
]
# --------------------
@pytest.mark.parametrize('comp,trig,qsq', _SAMPLES_RK_MM + _SAMPLES_RKST_MM)
@pytest.mark.parametrize('block', range(1,9))
def test_simple_mm(
    comp     : Component,
    trig     : Trigger,
    qsq      : Qsq,
    block    : int,
    tmp_path : Path):
    '''
    Simplest test
    '''
    sel             = {}
    sel[Cuts.q2   ] = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
    sel[Cuts.block] = f'block == {block}'

    obs  = zfit.Space('B_Mass', limits = (4500, 6000))

    ctx2 = DataStore.selection(sel = sel, update = True)
    with ExitStack() as stack:
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'block_{block:03d}',
            comp    = comp,
            trigger = trig,
            qsq     = qsq)

        mod = obj.get_model(obs = obs)

        print_pdf(pdf = mod.pdf)
# --------------------
@pytest.mark.parametrize('comp,trig,qsq,use_dtf', _SAMPLES_RK_EE + _SAMPLES_RKST_EE)
@pytest.mark.parametrize('block', range(1,9))
def test_simple_ee(
    comp     : Component,
    trig     : Trigger,
    qsq      : Qsq,
    use_dtf  : bool,
    block    : int,
    tmp_path : Path):
    '''
    Simplest test
    '''
    qsq_name        = 'q2_dtf' if use_dtf else 'q2'
    sel             = {}
    sel[Cuts.q2   ] = f'({qsq_name} > {qsq.lower_bound}) & ({qsq_name} < {qsq.upper_bound})'
    sel[Cuts.block] = f'block == {block}'

    ctx2 = DataStore.selection(sel = sel, update = True)
    obs  = zfit.Space('B_Mass', limits = (4500, 6000))
    with ExitStack() as stack:
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'block_{block:03d}',
            comp    = comp,
            trigger = trig,
            qsq     = qsq)

        mod = obj.get_model(obs = obs)
        path= obj.model_path

        assert path.exists()

    print_pdf(pdf = mod.pdf)
    fmo = FittedModel.from_json(path = path)
    print_pdf(pdf = fmo.pdf)
# --------------------
