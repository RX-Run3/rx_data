'''
Module with tests for PdfBuilder class
'''
import numpy
import numpy.typing as npt
import pytest

from typing         import Any
from contextlib     import ExitStack
from dmu.stats      import print_pdf, zfit
from dmu.stats      import FittedModel
from pathlib        import Path
from typing         import Final
from rx_common      import Component, Qsq, Trigger
from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder
from dmu.generic    import Mode

_SAMPLES_RK_EE : Final[list[tuple[Component,Trigger,Qsq,bool]]] = [
    (Component.bpkppsi2ee, Trigger.rk_ee_os, Qsq.jpsi, False),
]

_SAMPLES_RKST_EE : Final[list[tuple[Component,Trigger,Qsq,bool]]] = [
    (Component.bdkstkpipsi2ee, Trigger.rkst_ee_os, Qsq.jpsi, False),
]

_SAMPLES_RK_MM : Final[list[tuple[Component,Trigger,Qsq]]] = [
    (Component.bpkpjpsimm, Trigger.rk_mm_os, Qsq.jpsi),
]

_SAMPLES_RKST_MM : Final[list[tuple[Component,Trigger,Qsq]]] = [
    (Component.bdkstkpijpsimm, Trigger.rkst_mm_os, Qsq.jpsi),
]

_SIZE : Final[int] = 10_000

type NpFltArray = npt.NDArray[numpy.float64]
type zobs       = zfit.Space
type zdat       = zfit.data.Data

_RNG = numpy.random.default_rng(seed = 42)
# --------------------
def _get_arrays_ee(self : Any, mass : Any) -> tuple[NpFltArray, NpFltArray]:
    _ = self
    _ = mass

    masses  = _RNG.normal(5280, 200, _SIZE)
    weights = numpy.ones_like(masses)

    return masses, weights
# --------------------
def _get_arrays_mm(self : Any, mass : Any) -> tuple[NpFltArray, NpFltArray]:
    _ = self
    _ = mass

    masses  = _RNG.normal(5280, 8, 1_000)
    weights = numpy.ones_like(masses)

    return masses, weights
# --------------------
@pytest.mark.parametrize('comp,trig,qsq', _SAMPLES_RK_MM + _SAMPLES_RKST_MM)
@pytest.mark.parametrize('block', range(1,2))
def test_simple_mm(
    monkeypatch,
    tmp_path : Path,
    comp     : Component,
    trig     : Trigger,
    qsq      : Qsq,
    block    : int):
    '''
    Simplest test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(
        PdfBuilder,
        '_PdfBuilder__get_arrays',
        _get_arrays_mm)

    sel          = {}
    sel['q2   '] = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
    sel['block'] = f'block == {block}'

    obs  = zfit.Space('B_Mass', limits = (4500, 6000))

    ctx2 = DataStore.selection(sel = sel, update = True)
    with ExitStack() as stack:
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'block_{block:03d}',
            comp    = comp,
            trigger = trig,
            qsq     = qsq)

        mod = obj.get_model(obs_ext = obs, mode = Mode.write)

        print_pdf(pdf = mod.pdf)
# --------------------
@pytest.mark.parametrize('comp,trig,qsq,use_dtf', _SAMPLES_RK_EE + _SAMPLES_RKST_EE)
@pytest.mark.parametrize('block', range(1,2))
def test_simple_ee(
    monkeypatch,
    tmp_path : Path,
    comp     : Component,
    trig     : Trigger,
    qsq      : Qsq,
    use_dtf  : bool,
    block    : int):
    '''
    Simplest test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(
        PdfBuilder,
        '_PdfBuilder__get_arrays',
        _get_arrays_ee)

    qsq_name     = 'q2_dtf' if use_dtf else 'q2'
    sel          = {}
    sel['q2'   ] = f'({qsq_name} > {qsq.lower_bound}) & ({qsq_name} < {qsq.upper_bound})'
    sel['block'] = f'block == {block}'

    ctx2 = DataStore.selection(sel = sel, update = True)
    obs  = zfit.Space('B_Mass', limits = (4500, 6000))
    with ExitStack() as stack:
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'block_{block:03d}',
            comp    = comp,
            trigger = trig,
            qsq     = qsq)

        mod = obj.get_model(obs_ext = obs, mode = Mode.write)
        path= obj.model_path

        assert path.exists()

    print_pdf(pdf = mod.pdf)
    fmo = FittedModel.from_json(path = path)
    print_pdf(pdf = fmo.pdf)
# --------------------
def test_use_kde(tmp_path : Path, monkeypatch):
    '''
    Test fitting with KDE
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(
        PdfBuilder,
        '_PdfBuilder__get_arrays',
        _get_arrays_ee)

    comp     = Component.bpkppsi2ee
    trig     = Trigger.rk_ee_os
    qsq      = Qsq.psi2
    block    = 1
    pdf_name = 'pdf_name'

    sel          = {}
    sel['q2'   ] = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
    sel['block'] = f'block == {block}'

    ctx2 = DataStore.selection(sel = sel, update = True)
    obs  = zfit.Space('B_Mass', limits = (4500, 6000))
    with ExitStack() as stack:
        stack.enter_context(ctx2)

        obj = PdfBuilder(
            name    = f'block_{block:03d}',
            comp    = comp,
            trigger = trig,
            qsq     = qsq)

        model = obj.get_model(
            obs_ext= obs,
            use_kde= True,
            mode   = Mode.write)

    pdf = model.get_pdf(name = pdf_name)

    print_pdf(pdf = pdf)

    assert pdf.name == pdf_name
# --------------------
