'''
Module with tests for PrecMaker class
'''
import pytest
import numpy
import numpy.typing as npt

from pathlib        import Path
from contextlib     import ExitStack
from dmu.generic    import utilities as gut
from dmu.stats      import zfit
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from hqm.prec_maker import PrecMaker
from hqm.trfc       import TransferFunction
from rx_common      import Block, Cuts, Project, Qsq

type NpFltArr = npt.NDArray[numpy.float64]
type zpdf     = zfit.pdf.BasePDF
#--------------------------------------
class TransferFunctionTest:
    @property
    def pdf(self) -> zpdf:
        obs = zfit.Space('B_Mass', limits = (-100, 100))
        mu  = zfit.Parameter('mu', 0 , -20, 20)
        sg  = zfit.Parameter('sg', 15,  10, 20)

        return zfit.pdf.Gauss(obs = obs, mu = mu, sigma = sg)
#--------------------------------------
def _get_array(self, out_dir, sel, trig) -> NpFltArr:
    _ = self
    _ = out_dir 
    _ = sel 
    _ = trig 

    return numpy.random.uniform(3500, 4800, size = 10_000)
#--------------------------------------
def _get_trfc(self) -> TransferFunctionTest:
    _    = self
    return TransferFunctionTest()
#--------------------------------------
@pytest.fixture(autouse = True)
def _use_fake_masses(monkeypatch):
    monkeypatch.setattr(
        PrecMaker,
        '_PrecMaker__get_array',
        _get_array)

    monkeypatch.setattr(
        PrecMaker,
        '_PrecMaker__get_trfc',
        _get_trfc)
# ------------------------------------------------------------
@pytest.mark.parametrize('source', [Qsq.jpsi, Qsq.psi2])
@pytest.mark.parametrize('target', [Qsq.jpsi, Qsq.psi2, Qsq.high])
def test_resonant(
    _use_fake_masses,
    monkeypatch,
    tmp_path: Path,
    source  : Qsq, 
    target  : Qsq):
    '''
    Simplest test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    _     = _use_fake_masses
    proj  = Project.rk 
    blk   = 5
    block = Block(value = blk)

    cfg = TransferFunctionMakerConf.load(
        binning  = f'block-{blk}',
        project  = proj,
        source   = source,
        target   = target)

    ctx1 = DataStore.selection(sel = cfg.binning.selection, update = False)
    with ExitStack() as stack:
        stack.enter_context(ctx1)

        obj = PrecMaker(
            cfg     = cfg, 
            block   = block,
            project = proj)
        obj.get_pdf(update = True)
# ------------------------------------------------------------
