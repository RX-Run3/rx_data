'''
Script used to test custom zfit minimizers
'''
import pytest

from dmu         import LogStore
from dmu.stats   import AnealingMinimizer
from dmu.stats   import ContextMinimizer
from dmu.stats   import zfit
from dmu.stats   import FitConf
from dmu.stats   import Retries
from dmu.testing import get_nll
from dmu.testing import SumLiteral

log = LogStore.add_logger('dmu:ml:test_minimizer')
#---------------------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    LogStore.set_level('dmu:ml:minimizers', 10)
# -------------------------------------------
@pytest.mark.parametrize('do_errors', [True, False])
def test_anealing(do_errors : bool):
    '''
    Test AnealingMinimizer with chi2
    '''
    strategy  = Retries(
        ntries = 5,
        pvalue = 0.05)

    cfg       = FitConf(
        strategy  = strategy,
        do_errors = do_errors)

    nll       = get_nll(kind = 's+b')
    minimizer = AnealingMinimizer(cfg = cfg)
    res       = minimizer.get_result(nll)

    print(res)
# -------------------------------------------
@pytest.mark.parametrize('kind', ['s+b'])
def test_context_minimizer(kind : SumLiteral):
    '''
    Test context minimizer
    '''
    nll       = get_nll(kind = kind)
    minimizer = zfit.minimize.Minuit()

    minimizer = ContextMinimizer(minimizer = minimizer)
    res       = minimizer.minimize(loss = nll)

    print(res)
# -------------------------------------------
def test_context_minimizer_sim():
    '''
    Test context minimizer with simultaneous fit
    '''
    nll_ee    = get_nll(kind = 's+b', suffix = 'gaus_ee_1')
    nll_mm    = get_nll(kind = 's+b', suffix = 'gaus_mm_1')
    nll       = nll_ee + nll_mm

    minimizer = zfit.minimize.Minuit()
    minimizer = ContextMinimizer(minimizer = minimizer)
    res       = minimizer.minimize(loss = nll)

    print(res)
# -------------------------------------------
