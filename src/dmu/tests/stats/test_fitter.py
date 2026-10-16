'''
Module containing unit tests for Fitter class
'''

import tqdm
import numpy
import pytest
import matplotlib.pyplot   as plt

from pathlib     import Path
from functools   import cache

from dmu         import LogStore
from dmu.stats   import Constraint1D, Constraints
from dmu.stats   import Retries
from dmu.stats   import ConstraintType
from dmu.testing import get_model, get_nll
from dmu.stats   import FitConf, minimizers
from dmu.stats   import GofCalculator
from dmu.stats   import zfit
from dmu.stats   import Fitter
from dmu.stats   import ZFitPlotter
from dmu.stats   import ZFitPlotterConf
from dmu.generic import rxran
from ROOT        import RDF, gInterpreter # type: ignore

_NSAMPLE : int = 10_000

log = LogStore.add_logger('dmu:logging:test_fitter')

SamplerData = zfit.data.SamplerData
zdat        = zfit.data.Data
# ----------------------
@cache
def _get_data() -> numpy.ndarray:
    '''
    Returns
    -------------
    Array with dataset from gaussian plus exponential
    '''
    arr_sig = numpy.random.normal(5.0, 0.5, size=_NSAMPLE)
    arr_bkg = numpy.random.exponential(scale=10, size=_NSAMPLE)
    arr_tot = numpy.concatenate((arr_sig, arr_bkg))
    numpy.random.shuffle(arr_tot)

    return arr_tot
#-------------------------------------
class Data:
    '''
    Data class used to store share data
    '''
    data= _get_data()
    obs = zfit.Space('m', limits=(0, 10))
    zf  = zfit.data.Data.from_numpy(obs=obs, array=data)

    if not isinstance(zf, zfit.data.Data):
        raise ValueError('Invalid data format')

    l_arg_simple : list[ numpy.ndarray | zdat ] = [data, zf]
#-------------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:fitter', 10)

    with rxran.seed(value = 42):
        yield
#-------------------------------------
@cache
def _get_weighted_data():
    gInterpreter.ProcessLine('TRandom3 r(1);') # type: ignore

    d_val      = {}
    d_val['x'] = numpy.random.uniform(-1, 4, size=_NSAMPLE)
    d_val['y'] = numpy.random.uniform(-1, 4, size=_NSAMPLE)

    rdf = RDF.FromNumpy(d_val)
    rdf = rdf.Define('m', 'r.Gaus(x, 2 + y/4.)')

    return rdf
#-------------------------------------
@cache
def _get_pdf():
    mu  = zfit.Parameter('mu', 5.0,  0, 10)
    sg  = zfit.Parameter('sg', 0.3,  0,  5)
    sig = zfit.pdf.Gauss(obs=Data.obs, mu=mu, sigma=sg)
    nsg = zfit.Parameter('nsg', 100,  0, 10_000_000)
    sig = sig.create_extended(nsg)

    lb  = zfit.Parameter("lb", -0.1,  -0.9, 0)
    bkg = zfit.pdf.Exponential(obs=Data.obs, lam=lb)
    nbg = zfit.Parameter('nbk', 100,  0, 10_000_000)
    bkg = bkg.create_extended(nbg)

    pdf = zfit.pdf.SumPDF([sig, bkg])

    return pdf
#-------------------------------------
def _save_fit(
    test     : str, 
    kind     : str, 
    out_path : Path):
    plot_path = out_path / f'{test}_{kind}.png'

    log.info(f'Saving to: {plot_path}')
    plt.savefig(plot_path)
    plt.close()
#-------------------------------------
@pytest.mark.parametrize('dat', Data.l_arg_simple)
def test_simple(dat : numpy.ndarray | zdat):
    '''
    Simples fitting test
    '''
    pdf = _get_pdf()
    obj = Fitter(pdf, dat)
    res = obj.fit()

    assert res.valid
#-------------------------------------
def test_retry():
    '''
    Test fitting with multiple tries
    '''
    fcf = FitConf.default()
    rtr = Retries.default()
    cfg = fcf.model_copy(update = {'strategy' : rtr})

    pdf = _get_pdf()
    arr = _get_data()
    obj = Fitter(pdf, arr)
    res = obj.fit(cfg)

    assert res.valid
#-------------------------------------
def test_1d_constrain():
    '''
    Fits with constraints to parameters
    '''
    mu  = Constraint1D(
        kind = ConstraintType.gauss, 
        name = 'mu', 
        mu   = 5.0, 
        sg   = 1.0)

    sg  = Constraint1D(
        kind = ConstraintType.gauss,
        name = 'sg', 
        mu   = 1.0, 
        sg   = 0.1)

    fcf = FitConf.default()
    cfg = fcf.model_copy(update = {'constraints' : [mu, sg]})

    pdf = _get_pdf()
    arr = _get_data()
    obj = Fitter(pdf, arr)
    res = obj.fit(cfg)

    assert res.valid

    print(res)
#-------------------------------------
def test_nd_constrain():
    '''
    Fits with constraints to parameters
    '''
    mu  = Constraint1D(
        kind = ConstraintType.gauss, 
        name = 'mu', 
        mu   = 5.0, 
        sg   = 1.0)

    sg  = Constraint1D(
        kind = ConstraintType.gauss,
        name = 'sg', 
        mu   = 1.0, 
        sg   = 0.1)

    cons = Constraints(root = {'mu' : mu, 'sg' : sg}).merge(name = 'mu_sg_const')

    fcf = FitConf.default()
    cfg = fcf.model_copy(update = {'constraints' : [cons]})

    pdf = _get_pdf()
    arr = _get_data()
    obj = Fitter(pdf, arr)
    res = obj.fit(cfg)

    assert res.valid

    print(cons)
    print(res)
#-------------------------------------
def test_ranges(tmp_path : Path):
    '''
    Fit data in disjoint ranges
    '''
    pdf   = get_model('s+b')
    sam   = pdf.create_sampler(n=50_000)
    pdf   = get_model('s+b', lam = -0.0003)

    rng   = [(4500, 5100), (5300, 6000)]
    ftc   = FitConf.default()
    cfg   = ftc.model_copy(update = {'ranges' : rng})

    with GofCalculator.disabled(value=True):
        obj   = Fitter(pdf, sam)
        res   = obj.fit(cfg = cfg)

    print(res)
    assert res.valid

    cfg = ZFitPlotterConf(nbins = 50, stacked = True, ranges = rng)
    obj = ZFitPlotter(data=sam, model=pdf)
    obj.plot(cfg)

    _save_fit(test='ranges', kind='fit', out_path = tmp_path)
#-------------------------------------
# TODO: Need to improve this test
def test_wgt():
    '''
    Test fit to weighted dataset
    '''
    rdf = _get_weighted_data()
    arr = rdf.AsNumpy(['m'])['m']
    wgt = numpy.random.binomial(1, 0.5, size=arr.size)

    pdf = _get_pdf()
    dat = zfit.data.Data.from_numpy(array=arr, weights=wgt, obs=pdf.space)
    if not isinstance(dat, zfit.data.Data):
        raise ValueError('Invalid data format')

    obj = Fitter(pdf, dat)
    obj.fit()
#-------------------------------------
def test_minimizer() -> None:
    '''
    Simplest test of minimizer static method
    '''
    nll = get_nll(kind='s+b')
    with GofCalculator.disabled(value=True):
        minimizers.minimize(nll=nll)
# ----------------------
@pytest.mark.timeout(100)
def test_profiling_minimizer() -> None:
    '''
    Simplest test of minimizer static method
    '''
    ntoys = 30
    nll   = get_nll(kind='s+b')
    sam   = nll.data[0]
    if not isinstance(sam, SamplerData):
        raise ValueError('Data object is not a sampler')

    for _ in tqdm.trange(ntoys, ascii=' -'):
        sam.resample()
        minimizers.minimize(nll=nll)
# ----------------------
