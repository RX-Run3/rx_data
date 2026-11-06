'''
File containing tests for FitResult class
'''

import numpy
import pytest

from pathlib     import Path
from typing      import Final
from dmu         import LogStore
from dmu.stats   import ErrorFailError
from dmu.stats   import FitResult, FitParameter
from dmu.stats   import zfit
from dmu.testing import get_nll
from dmu.generic import rxran

log=LogStore.add_logger('dmu:test_fit_result')

_FALL_BACK : Final[int] = 3 # placeholder for missing parameter value
# ----------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_stats:fit_result', 10)

    with rxran.seed(value = 42):
        yield
# -----------------------------
def test_from_zfit():
    '''
    Test conversion from zfit object
    '''
    nll       = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)
    _   = val.covariance

    cov = numpy.array(val.pars_covariance(pars = ['nbkg', 'nsig']), dtype=int)
    assert cov.tolist() == [[942, -420], [-420, 898]]

    cov = numpy.array(val.pars_covariance(pars = ['mu', 'sg']), dtype=int)
    assert cov.tolist() == [[86, 3], [3, 81]]
# -----------------------------
def test_dataframe():
    '''
    Test getting dataframe with parameter values
    '''
    nll       = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    res = FitResult.from_zfit(res = res)

    log.info('\n' + str(res.df))
# -----------------------------
def test_serialize(tmp_path : Path):
    '''
    Test conversion from zfit object
    '''
    nll       = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)

    fpath = tmp_path / 'data.json'
    val.to_json(path = fpath)

    obj = FitResult.from_json(path = fpath)

    assert obj == val
# -----------------------------
def test_getitem():
    '''
    Test conversion from zfit object
    '''
    nll = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)

    x, y = val['mu_gaus_test_1']

    print(val)
    print(x,y)
# -----------------------------
def test_getpar():
    '''
    Test conversion from zfit object
    '''
    nll = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)
    mu  = val.get_par(prefix = 'mu')
    sg  = val.get_par(prefix = 'sg')

    _, _ = mu.data
    _, _ = sg.data

    with pytest.raises(ValueError):
        val.get_par(prefix = 'missing_')
# -----------------------------
def test_get():
    '''
    Test conversion from zfit object
    '''
    nll = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    zres = minimizer.minimize(loss = nll)
    zres.hesse(name = 'minuit_hesse')

    res = FitResult.from_zfit(res = zres)

    x, y = res['mu_gaus_test_1']
    a, b = res.get('mu_gaus_test_1', _FALL_BACK)

    assert a == x
    assert b == y

    a, b = res.get('none', _FALL_BACK)

    assert a == _FALL_BACK
    assert b == _FALL_BACK
# -----------------------------
def test_extend():
    '''
    Test extending fit result
    '''
    nll = get_nll(kind = 's+b', suffix = '')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    ores = FitResult.from_zfit(res = res)

    p1  = FitParameter(name = 'f1', value = 1, error = 1)
    p2  = FitParameter(name = 'f2', value = 2, error = 2)

    eres = ores.extend(pars = [p1, p2])

    log.info(ores)
    log.info(eres)

    with pytest.raises(ValueError):
        mu = FitParameter(name = 'mu', value = 1, error = 1)
        ores.extend(pars = [mu])
# -----------------------------
def test_no_errors_ok():
    '''
    Test no_errors_ok
    '''
    nll = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    FitResult.from_zfit(res = res, no_errors_ok=True)

    with pytest.raises(ErrorFailError):
        FitResult.from_zfit(res = res)
# -----------------------------
def test_hash():
    '''
    Test conversion from zfit object
    '''
    nll = get_nll(kind = 's+b', suffix = '_gaus_test_1')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)
    hash(val)
# -----------------------------
@pytest.mark.parametrize('prefix', [None, 'yld', 's'])
def test_prefix(prefix : str | None):
    nll = get_nll(
        kind   = 's+b',
        prefix = prefix,
        suffix = 'test')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    val = FitResult.from_zfit(res = res)
    print(val)
# -----------------------------
def test_rename():
    '''
    Test renaming of parameters
    '''
    nll = get_nll(kind = 's+b', suffix = '_old_name')
    minimizer = zfit.minimize.Minuit()

    res = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse')

    old_res = FitResult.from_zfit(res = res)
    print(old_res)

    new_res = old_res.rename(
        original = 'old_name',
        new      = 'new_name')

    print(new_res)
# -----------------------------
