'''
Module with tests for Ipatia class
'''
import numpy
import pytest
import matplotlib.pyplot as plt

from pathlib     import Path
from functools   import cache
from dmu         import LogStore
from dmu.generic import utilities as gut
from dmu.stats   import ZFitPlotter, ZFitPlotterConf, zfit
from dmu.stats   import Ipatia
from dmu.stats   import pdf_utilities as put

zfit.run.set_graph_mode(False)

log=LogStore.add_logger('dmu:test_ipatia')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    gut.TIMER_ON = True

    LogStore.set_level('dmu:pdf_utilities', 10)
# ----------------------------------------------------------
@cache
@gut.timeit
def __get_pdf():
    obs   = zfit.Space("x", limits=(-10, 10))
    mu    = zfit.Parameter("mu"   , 0.0)
    sigma = zfit.Parameter("sigma", 1.0)
    nl    = zfit.Parameter("nl"   , 2.0, 0.01, 50)
    al    = zfit.Parameter("al"   , 2.0, 0.01, 50)
    nr    = zfit.Parameter("nr"   , 2.0, 0.01, 50)
    ar    = zfit.Parameter("ar"   , 2.0, 0.01, 50)
    lam   = zfit.Parameter("lam"  , -1.0, -10, 10)
    beta  = zfit.Parameter("beta" , 0.0, -1, 1)
    zeta  = zfit.Parameter("zeta" , 1.0, 0.0001, 20)

    return Ipatia(
        obs  =obs,
        mu   =mu,
        sigma=sigma,
        nl   =nl,
        al   =al,
        nr   =nr,
        ar   =ar,
        lam  =lam,
        beta =beta,
        zeta =zeta)
# ----------------------------------------------------------
@pytest.mark.parametrize('nentries', [10_000])
def test_eval(nentries : int):
    model = __get_pdf()
    xvals = numpy.linspace(-10, 10, nentries)
    model.pdf(xvals)
# ----------------------------------------------------------
def test_plot(tmp_path : Path):
    model = __get_pdf()
    data  = model.create_sampler(n=10_000)
    cfg   = ZFitPlotterConf.default()
    cfg   = cfg.model_copy(update = {'skip_pulls' : True})

    zfp= ZFitPlotter(data = data, model = model)
    zfp.run(cfg = cfg)

    plt.savefig(tmp_path / 'plot.png')
# ----------------------------------------------------------
def test_gradient():
    model  = __get_pdf()
    assert put.has_gradient(pdf = model)
# ----------------------------------------------------------
