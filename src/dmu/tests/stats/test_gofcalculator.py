'''
Module with tests for GofCalculator class
'''
import math
import numpy
import pytest

from dmu        import LogStore
from dmu.stats  import zfit
from dmu.stats  import GofCalculator, GoodnessOfFit

log = LogStore.add_logger('dmu:stats:test_gofcalculator')
zdat= zfit.Data
#---------------------------------------------
class Data:
    '''
    Class used to share attributes
    '''
    minimizer = zfit.minimize.Minuit()
    obs       = zfit.Space('x', limits=(-10, 10))
#---------------------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    LogStore.set_level('dmu:stats:gofcalculator', 10)
#---------------------------------------------
def _get_model():
    mu  = zfit.Parameter('mu', 3, -1, 5)
    sg  = zfit.Parameter('sg', 2,  0, 5)
    pdf = zfit.pdf.Gauss(obs=Data.obs, mu=mu, sigma=sg)

    return pdf
# -------------------------------------------
def _get_data() -> zdat:
    numpy.random.seed(42)
    data_np = numpy.random.normal(0, 1, size=10000)
    data_zf = zfit.Data.from_numpy(obs=Data.obs, array=data_np)

    if not isinstance(data_zf, zdat):
        raise ValueError('Invalid data type')

    return data_zf
# -------------------------------------------
def _get_nll():
    pdf = _get_model()
    dat = _get_data()
    nll = zfit.loss.UnbinnedNLL(model=pdf, data=dat)

    return nll
# -------------------------------------------
def test_simple():
    '''
    Simplest test of GofCalculator
    '''
    nll = _get_nll()
    res = Data.minimizer.minimize(nll)
    print(res)

    gcl = GofCalculator(nll, ndof=10)
    gof = gcl.get_gof()

    assert math.isclose(gof.pval, 0.9649746, abs_tol=1e-5)
# -------------------------------------------
def test_gof_none():
    '''
    Test none class method in GoodnessOfFit
    '''
    gof = GoodnessOfFit.none()

    assert gof.calculated == False
# -------------------------------------------
