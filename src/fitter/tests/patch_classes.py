import numpy
import pytest

from types     import ModuleType
from typing    import Final
from rx_common import Trigger, Qsq
from dmu.stats import zfit
from dmu       import LogStore

type zdat = zfit.data.Data
type zsum = zfit.pdf.SumPDF
type zpdf = zfit.pdf.BasePDF

_RNG                    = numpy.random.default_rng(seed = 42)
_DATA_SIZE : Final[int] = 1000

log=LogStore.add_logger('fitter:patch_classes')
# ---------------------------------------------------
def _get_model(trigger : Trigger) -> zsum:
    log.warning('Using mock ccbar PDF')

    obs   = zfit.Space('Mass', 4600, 6000)
    lam   = zfit.Parameter(f"{trigger}_lambda", -0.002, -1.0, 1.0)
    mu    = zfit.Parameter(f"{trigger}_mu", 5280.0, 5000.0, 5500.0)
    sigma = zfit.Parameter(f"{trigger}_sigma", 20.0, 0.1, 100.0)
    low   = 4500.0
    high  = 6000.0

    exp_pdf     = zfit.pdf.Exponential(lambda_=lam, obs=obs, name=f"{trigger}_exp")
    gauss_pdf   = zfit.pdf.Gauss(mu=mu, sigma=sigma, obs=obs, name=f"{trigger}_gauss")
    uniform_pdf = zfit.pdf.Uniform(low=low, high=high, obs=obs, name=f"{trigger}_uniform")

    frac1 = zfit.Parameter(f"{trigger}_frac1", 0.3, 0.0, 1.0)
    frac2 = zfit.Parameter(f"{trigger}_frac2", 0.3, 0.0, 1.0)

    total_pdf= zfit.pdf.SumPDF(
        pdfs = [exp_pdf, gauss_pdf, uniform_pdf],
        fracs= [frac1, frac2],
        name = f"{trigger}_sum")

    return total_pdf
# ---------------------------------------------------
class TestDataModel:
    '''
    Class meant to replace DataModel in tests
    '''
    # ------------------------
    def __init__(
        self,
        cfg     : str,
        obs     : str,
        trigger : Trigger,
        q2bin   : str,
        name    : str):
        log.warning('Using testing DataModel')
        _ = cfg
        _ = obs
        _ = q2bin
        _ = name

        self._trigger = trigger
    # ------------------------
    def get_model(self) -> zpdf:
        return _get_model(trigger = self._trigger)
# ---------------------------------------------------
class TestDataPreprocessor:
    def __init__(
        self,
        name      : str,
        obs       : str,
        sample    : str,
        trigger   : Trigger,
        q2bin     : Qsq,
        wgt_cfg   : str | None,
        ph_sample : str | None = None,
        is_sig    : bool       = True,
        selection : str | None = None):
        _ = name
        _ = wgt_cfg
        _ = obs
        _ = selection
        _ = sample
        _ = ph_sample
        _ = is_sig

        log.warning('Using TestDataPreprocessor')

        self._trigger = trigger
        self._q2bin   = q2bin
    # --------------------------
    @property
    def rdf_uid(self) -> str:
        return 'mock_data'
    # --------------------------
    def _get_sigma(self) -> float:
        if self._trigger.is_muon:
            return 30

        if self._q2bin.is_rare:
            return 100

        return 20
    # --------------------------
    def get_data(self) -> zdat:
        log.warning('Using mock data')

        sigma   = self._get_sigma()
        array_1 = _RNG.normal(loc = 5280, scale = 1.0 * sigma, size = _DATA_SIZE)
        array_2 = _RNG.normal(loc = 5280, scale = 1.3 * sigma, size = _DATA_SIZE)
        array   = numpy.concatenate([array_1, array_2])

        obs   = zfit.Space('Mass', 4600, 6000)
        data  = zfit.data.Data.from_numpy(array = array, obs = obs)

        if isinstance(data, zfit.data.Data):
            return data

        raise ValueError('Invalid data')
# ---------------------------------------------------
class TestPRec:
    def __init__(
        self,
        trig : Trigger,
        name : str,
        obs  : str,
        q2bin: str,
        cfg  : str):

        log.warning('Using TestPRec')

        _ = name
        _ = obs
        _ = q2bin
        _ = cfg
        self._trig = trig
    # --------------------------
    def get_sum(self) -> zsum:
        return _get_model(trigger = self._trig)
# ---------------------------------------------------
@pytest.fixture
def _patch_data_model(
        request     : pytest.FixtureRequest,
        monkeypatch : pytest.MonkeyPatch):

    module : ModuleType = request.module
    target : str | None = getattr(module, '_DATA_MODEL_TARGET', None)

    if target is None:
        raise ValueError('Cannot set data model target')

    monkeypatch.setattr(target, TestDataModel)
# ---------------------------------------------------
@pytest.fixture
def _patch_data_preprocessor(
        request     : pytest.FixtureRequest,
        monkeypatch : pytest.MonkeyPatch):

    module : ModuleType = request.module
    target : str | None = getattr(module, '_DATA_PREPROCESSOR_TARGET', None)

    if target is None:
        raise ValueError('Cannot set data preprocessor target')

    monkeypatch.setattr(target, TestDataPreprocessor)
# -----------------------------------
@pytest.fixture
def _patch_prec(
        request     : pytest.FixtureRequest,
        monkeypatch : pytest.MonkeyPatch):

    module : ModuleType = request.module
    target : str | None = getattr(module, '_PREC_TARGET', None)

    if target is None:
        raise ValueError('Cannot set PRec target')

    monkeypatch.setattr(target, TestPRec)
# -----------------------------------
