'''
Module with tests for PrecMaker class
'''
import pytest
import numpy
import numpy.typing as npt

from pathlib        import Path
from dmu.stats      import zfit
from hqm.config     import TransferFunctionMakerConf
from hqm.prec_maker import PrecMaker
from rx_common      import Project, Qsq
from dmu.generic    import Mode

type NpFltArr = npt.NDArray[numpy.float64]
type zpdf     = zfit.pdf.BasePDF
#--------------------------------------
class TransferFunctionTest:
    @property
    def pdf(self) -> zpdf:
        obs = zfit.Space('B_Mass', limits = (-1000, 1000))
        mu  = zfit.Parameter('mu',200,  0, 300)
        sg  = zfit.Parameter('sg',200, 10, 300)

        return zfit.pdf.Gauss(obs = obs, mu = mu, sigma = sg)
#--------------------------------------
def _get_array(self, out_dir, trig) -> NpFltArr:
    _ = self
    _ = out_dir
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

    _       = _use_fake_masses
    proj    = Project.rk
    binning = 'block-3 mva_cmb-3 mva_prc-2'

    cfg = TransferFunctionMakerConf.load(
        binning  = binning,
        project  = proj,
        source   = source,
        target   = target)

    obj = PrecMaker(
        cfg     = cfg,
        binning = binning,
        project = proj)
    obj.get_pdf(mode = Mode.write, name = 'test')
# ------------------------------------------------------------
