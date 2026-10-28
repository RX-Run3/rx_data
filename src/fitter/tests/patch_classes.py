import numpy

from typing        import Any
from contextlib    import contextmanager
from typing        import Final
from rx_common     import Trigger, Qsq, Project, Mass, Component
from dmu           import LogStore
from dmu.stats     import Constraint1D, Constraints
from dmu.stats     import zfit, ModelFactory, Model
from dmu.stats     import ConstraintType
from dmu.stats     import ConstraintND
from pydantic      import BaseModel

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
# ----------------------
def get_test_prec_constraints(
        brem  : Any,
        pars  : list[str],
        signal: Any,
        cfg   : Any) -> list[Constraint1D]:

    _ = brem
    _ = signal
    _ = cfg

    def _get_cons(par: str):
        return Constraint1D(
            name = par,
            kind = ConstraintType.gauss,
            mu   = 0,
            sg   = 1)

    return [ _get_cons(par) for par in pars ]
# ----------------------
class TestCCbarConfTF(BaseModel, frozen = True):
    from_sim_fit : int = False
    def get_pdf(
        self,
        obs_name: str,
        project : Project,
        pdfs    : dict[Component, zpdf]) -> zpdf:
        _     = project
        _     = pdfs

        name  = 'name'
        obs   = zfit.Space(obs_name, 4600, 6000)
        mu    = zfit.Parameter(f"{name}_mu", 5280.0, 5000.0, 5500.0)
        sigma = zfit.Parameter(f"{name}_sigma", 20.0, 0.1, 100.0)
        pdf   = zfit.pdf.Gauss(mu=mu, sigma=sigma, obs=obs, name=name)

        return pdf
# ---------------------------------------------------
class TestSimFitter:
    _mass = 'Mass'
    # ----------------------
    def __init__(
        self,
        name      : str,
        component : Component,
        trigger   : Trigger,
        q2bin     : str,
        cfg       : str):

        self._name      = name
        self._component = component
        self._trigger   = trigger

        _ = q2bin
        _ = cfg
    # ----------------------
    @property
    def pdfs(self) -> list[Model]:
        if self._component == Component.comb:
            return [Model.exp]

        return [Model.gauss]
    # ----------------------
    @property
    def values(self) -> dict[str, tuple[float,float,float]]:
        signals         = {Component.bpkpee, Component.bpkpmm, Component.bdkstkpimm, Component.bpkpipi, Component.bpkkk}
        signal_shape    = {'mu' : (5280., 5200., 5350.), 'sg' : (50., 5., 100.)}

        resonant        = {Component.bpkpjpsiee, Component.bpkpjpsimm, Component.bdkstkpijpsiee, Component.bdkstkpijpsimm}
        resonant_shape  = {'mu' : (5280., 5200., 5350.), 'sg' : (30., 5., 100.)}

        cabibbo         = {Component.bppijpsimm, Component.bppijpsiee}
        cabibbo_shape   = {'mu' : (5320., 5200., 5350.), 'sg' : (80., 5., 100.)}

        part_reco       = {Component.bsphiee, Component.bpkxkpipiee}
        part_reco_shape = {'mu' : (5000., 4800., 5200.), 'sg' : (200., 100., 300.)}

        leak_down       = {Component.bpkpjpsiee, Component.bdkstkpijpsiee}
        leak_down_shape = {'mu' : (4800., 4500., 5000.), 'sg' : (400., 200., 600.)}

        if self._component == Component.comb:
            return {'c' : (-0.001, -0.01, 0.00)}

        if self._component in signals:
            return signal_shape

        if self._component in cabibbo:
            return cabibbo_shape

        if self._component in resonant:
            return resonant_shape

        if self._component == Component.bdkstkpiee and self._trigger == Trigger.rk_ee_os:
            return part_reco_shape 

        if self._component == Component.bdkstkpiee and self._trigger == Trigger.rkst_ee_os:
            return signal_shape

        if self._component in part_reco:
            return part_reco_shape

        if self._component in leak_down:
            return leak_down_shape


        raise ValueError(f'No values for {self._component}/{self._trigger}')
    # ----------------------
    @classmethod
    @contextmanager
    def mass(cls, value : Mass):
        old_value  = cls._mass
        cls._mass = value
        try:
            yield
        finally:
            cls._mass = old_value
    # ----------------------
    def get_model(self) -> zpdf | None:
        log.warning('Using mock SimFitter PDF')
        skipped = {
            Component.ccbar, 
            Component.bdkstkpijpsimm_kpimm_pikmm,
            Component.bdkstkpijpsiee_kpiee_pikee,
            Component.bskstjpsiee,
            Component.bskstjpsimm,
            Component.bsphijpsiee,
            Component.bsphijpsimm,
            Component.lbpkjpsimm,
            Component.lbpkjpsiee,
            Component.bpkppsi2ee, 
            Component.bpkstkpiee,
            Component.bdkstkpipsi2ee}

        if self._component in skipped:
            return None

        name  = f'{self._component}_{self._name}'
        obs   = zfit.Space(self._mass, 4600, 6000)
        mfc   = ModelFactory(
            obs     = obs,
            preffix = name,
            l_float = [],
            l_shared= [],
            values  = self.values,
            l_pdf   = self.pdfs)

        log.debug(f'Component: {self._component}')

        return mfc.get_pdf()
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
            return 15

        if self._q2bin.is_rare:
            return 70

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
    def get_sum(self, name : str) -> zsum:
        _ = name
        return _get_model(trigger = self._trig)
# ---------------------------------------------------
class TestEfficiencyCalculator:
    '''
    Testing class meant to monkeypatch EfficiencyCalculator
    '''
    # --------------------
    def __init__(
        self,
        out_dir : Any,
        q2bin   : Any,
        sample  : Component,
        trigger : Trigger):
        _ = out_dir
        _ = q2bin
        _ = sample
        trig = trigger

        self._is_signal = trig.rare_signal == sample

        log.warning('Using TestEfficiencyCalculator')
    # --------------------
    def get_efficiency(self) -> tuple[float,float]:
        if self._is_signal:
            return 0.8, 0.1

        return 0.1, 0.01
# ---------------------------------------------------
class TestCmbConstraints:
    '''
    Class meant to monkey patch CmbConstraints
    '''
    def __init__(
        self,
        brem    : Any,
        signal  : Any,
        cfg_fit : Any) -> None:
        _ = brem
        _ = signal 
        _ = cfg_fit 
        log.warning('Using patch version of CmbConstraints')
    # ---------------------
    def get_constraint(self) -> ConstraintND:
        return ConstraintND(
            name       = 'test',
            kind       = ConstraintType.gauss,
            parameters = ['a', 'b'],
            values     = [1, 2],
            cov        = [[1,0], [0,1]])
# ---------------------------------------------------
class TestMisIDConstraints:
    '''
    Test used to monkeypatch MisIDConstraints
    '''
    # ------------------------
    def __init__(cfg : Any, q2bin : Any):
        _ = cfg
        _ = q2bin
    # ------------------------
    def get_constraints(self) -> Constraints[Constraint1D]:
        ca = Constraint1D(
            name = 'ca',
            kind = ConstraintType.gauss,
            mu   = 100,
            sg   = 10)

        cb = Constraint1D(
            name = 'cb',
            kind = ConstraintType.gauss,
            mu   = 100,
            sg   = 10)

        data = {'ca' : ca, 'cb' : cb}

        return Constraints[Constraint1D](root = data)
# ---------------------------------------------------
