'''
Module with tests for zutils.plot plot class
'''
import numpy
import pytest
import matplotlib.pyplot as plt

from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import zfit
from dmu.stats    import ZFitPlotter
from dmu.stats    import ZFitPlotterConf
from zfit.data    import Data         as zdat

log = LogStore.add_logger('dmu:test_fit_plotter')
#--------------------------------
class Data:
    '''
    Class storing shared variables
    '''
    l_arg_xerror = [
            (True , 'xerr_on' ),
            (False, 'xerr_off'),
            (0.5  , 'xerr_0p5'),
            ]
#--------------------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before all tests in this module
    '''
    LogStore.set_level('dmu:zfit_plotter', 10)
    numpy.random.seed(42)
#--------------------------------
def test_simple(tmp_path : Path):
    '''
    Simplest test of plotting class
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 1000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    d_leg = {'gauss': 'New Gauss'}
    cfg   = ZFitPlotterConf(d_leg = d_leg)

    obj   = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.plot(cfg)
    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_high_binning(tmp_path : Path):
    '''
    Test with large datasets and many bins
    '''
    arr = numpy.random.normal(0, 1, size=100_000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100_000, 0, 1000_000)
    pdf = pdf.create_extended(nev,)

    d_leg = {'gauss_ext': 'New Gauss'}
    cfg   = ZFitPlotterConf(d_leg = d_leg)

    obj   = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.plot(cfg)
    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_run(tmp_path : Path):
    '''
    Simplest test of plotting class
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 1000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    d_leg = {'gauss': 'New Gauss'}
    cfg = ZFitPlotterConf(
        stacked   = True,
        nbins     = 50,
        d_leg     = d_leg,
        plot_range= (-10, 10),
        ext_text  = 'Extra text here')

    obj = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.run(cfg = cfg)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_title(tmp_path : Path):
    '''
    Testing adding title in plot
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 1000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.plot(cfg)
    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_legend(tmp_path : Path):
    '''
    Tests overriding of PDF name in legend
    '''
    obs = zfit.Space('m', limits=(0, 10))

    mu  = zfit.Parameter("mu", 5.0,  0, 10)
    sg  = zfit.Parameter("sg", 0.5,  0,  5)
    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg)
    nsg = zfit.Parameter('nsg', 1000, 0, 10000)
    esig= sig.create_extended(nsg, name='gauss')

    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    nbk = zfit.Parameter('nbk', 1000, 0, 10000)
    ebkg= bkg.create_extended(nbk, name='expo')

    pdf = zfit.pdf.SumPDF([ebkg, esig])
    sam = pdf.create_sampler()

    d_leg = {'gauss': 'New Gauss'}
    cfg   = ZFitPlotterConf(d_leg = d_leg)
    obj   = ZFitPlotter(data=sam, model=pdf)
    obj.plot(cfg)

    # add a line to pull hist
    obj.axs[1].plot([0, 10], [0, 0], linestyle='--', color='black')

    obj.set_yscale('linear')
    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_size(tmp_path : Path):
    '''
    Tests use of figsize argument
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 1000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    cfg = ZFitPlotterConf(figsize = (30, 10))
    obj = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.plot(cfg)

    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_leg_loc(tmp_path : Path):
    '''
    Test usage of leg_loc argument, to place legend
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 1000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    cfg = ZFitPlotterConf(leg_loc = 'upper left')
    obj = ZFitPlotter(data=arr, model=pdf, result=None)
    obj.plot(cfg)

    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_weights(tmp_path : Path):
    '''
    Tests plotting of weighted zfit data
    '''
    obs = zfit.Space('m', limits=(0, 10))
    mu  = zfit.Parameter("mu",    5,  4.0, 6)
    sg1 = zfit.Parameter("sg1", 1.0,  0.5, 2)
    sg2 = zfit.Parameter("sg2", 2.0,  0.5, 2)

    mu.floating = False
    sg1.floating= False
    sg2.floating= False

    pdf_a = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg1, name='gauss_1')
    pdf_b = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg2, name='gauss_2')

    nev_1 = zfit.Parameter('nev_1', 200, 1, 100000)
    nev_2 = zfit.Parameter('nev_2', 300, 1, 100000)

    pdf_1 = pdf_a.create_extended(nev_1, name='G1')
    pdf_2 = pdf_b.create_extended(nev_2, name='G2')
    pdf   = zfit.pdf.SumPDF([pdf_1, pdf_2], name='Model')

    arr   = numpy.random.normal(loc=5, scale=1, size=1000)
    wgt   = numpy.random.binomial(1, 0.5, size=arr.size)
    dat   = zfit.Data.from_numpy(obs=obs, array=arr, weights=wgt)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=dat, model=pdf, result=res)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')
#--------------------------------
def test_low_stat(tmp_path : Path):
    '''
    Testing fit plots with low statistics data
    '''
    arr = numpy.random.normal(0, 1, size=10)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.4, -5, 5)
    sg  = zfit.Parameter("sg", 1.3,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100, 0, 10000)
    pdf = pdf.create_extended(nev,)

    dat = zfit.Data.from_numpy(obs=obs, array=arr)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    #Fake GOF for ploting purposes
    setattr(res, 'gof', (11, 10, 0.5)) # noqa: B010

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=arr, model=pdf, result=res)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_skip_pulls(tmp_path : Path):
    '''
    Test usage of skip_pulls=True arg
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.4, -5, 5)
    sg  = zfit.Parameter("sg", 1.3,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100, 0, 10000)
    pdf = pdf.create_extended(nev,)

    dat = zfit.Data.from_numpy(obs=obs, array=arr)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    setattr(res, 'gof', (11, 10, 0.5)) # noqa: B010

    cfg = ZFitPlotterConf(skip_pulls = True)
    obj = ZFitPlotter(data=arr, model=pdf, result=res)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')
#--------------------------------
def test_nodata(tmp_path : Path):
    '''
    Tests usage of no_data=True arg, to remove data from plot
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.4, -5, 5)
    sg  = zfit.Parameter("sg", 1.3,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100, 0, 10000)
    pdf = pdf.create_extended(nev,)

    dat = zfit.Data.from_numpy(obs=obs, array=arr)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    cfg = ZFitPlotterConf(no_data = True)
    obj = ZFitPlotter(data=arr, model=pdf, result=res)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')
#--------------------------------
def test_empty_region(tmp_path : Path):
    '''
    Tests fit with empty regions, no data
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.4, -5, 5)
    sg  = zfit.Parameter("sg", 1.3,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100, 0, 10000)
    pdf = pdf.create_extended(nev,)

    dat = zfit.Data.from_numpy(obs=obs, array=arr)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    wgt = numpy.ones_like(arr, dtype = float)

    cfg = ZFitPlotterConf(plot_range = (0, 10))
    obj = ZFitPlotter(data=arr, model=pdf, result=res, weights=wgt)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit.png')
#--------------------------------
def test_axs(tmp_path : Path):
    '''
    Tests overlaying axes, i.e. overlaying plots
    '''
    arr = numpy.random.normal(0, 1, size=1000)

    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 1.0,  0, 5)
    sg1 = zfit.Parameter("sg1", 1.7,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg , name='gauss_1')
    pdf1= zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg1, name='gauss_2')

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=arr, model=pdf)
    obj.plot(cfg)

    cfg_1 = ZFitPlotterConf(axs = obj.axs)
    obj_1 = ZFitPlotter(data=arr, model=pdf1)
    obj_1.plot(cfg_1)

    obj.axs[1].set_ylim(-5, 5)
    obj.axs[1].plot(linestyle='--', color='black')

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')
#--------------------------------
def test_stacked(tmp_path : Path):
    '''
    Testing stacked PDF plots
    '''
    obs = zfit.Space('m', limits=(0, 10))
    mu  = zfit.Parameter("mu", 5.0,  0, 10)
    sg  = zfit.Parameter("sg", 1.3,  0,  5)

    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nsg = zfit.Parameter('nsg', 1000, 0, 10000)
    esig= sig.create_extended(nsg)

    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    nbk = zfit.Parameter('nbk', 1000, 0, 10000)
    ebkg= bkg.create_extended(nbk)

    pdf = zfit.pdf.SumPDF([ebkg, esig])

    sam = pdf.create_sampler()
    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=sam)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    print(res)

    cfg = ZFitPlotterConf(staked = True)
    obj = ZFitPlotter(data=sam, model=pdf, result=res)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')
#--------------------------------
def test_composed(tmp_path : Path):
    '''
    Testing plot of SumPDF (?)
    '''
    obs = zfit.Space('m', limits=(0, 10))

    mu  = zfit.Parameter("mu", 5.0,  0, 10)
    sg  = zfit.Parameter("sg", 0.5,  0,  5)
    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nsg = zfit.Parameter('nsg', 1000, 0, 10000)
    esig= sig.create_extended(nsg)

    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    nbk = zfit.Parameter('nbk', 1000, 0, 10000)
    ebkg= bkg.create_extended(nbk)

    pdf = zfit.pdf.SumPDF([ebkg, esig])
    sam = pdf.create_sampler()

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=sam, model=pdf)
    obj.plot(cfg)

    # add a line to pull hist
    obj.axs[1].plot([0, 10], [0, 0], linestyle='--', color='black')
    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    obj.axs[0].set_ylim(bottom = 0.1)
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_composed_nonextended(tmp_path : Path):
    '''
    Testing plot of sum of PDFs with fractions, non-extended
    '''
    obs = zfit.Space('m', limits=(-10, 10))
    mu1 = zfit.Parameter("mu1", 0.4, -5, 5)
    sg1 = zfit.Parameter("sg1", 1.3,  0, 5)
    mu2 = zfit.Parameter("mu2", 0.4, -5, 5)
    sg2 = zfit.Parameter("sg2", 1.3,  0, 5)

    pd1 = zfit.pdf.Gauss(obs=obs, mu=mu1, sigma=sg1, name='gauss1')
    fr1 = zfit.Parameter('fr1', 0.5, 0, 1)

    pd2 = zfit.pdf.Gauss(obs=obs, mu=mu2, sigma=sg2, name='gauss2')
    fr2 = zfit.Parameter('fr2', 0.5, 0, 1)

    pdf = zfit.pdf.SumPDF([pd1, pd2], fracs=[fr1, fr2])

    dat = pdf.create_sampler(n=1000)

    cfg = ZFitPlotterConf()
    obj = ZFitPlotter(data=dat, model=pdf)
    obj.plot(cfg)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_composed_blind(tmp_path : Path):
    '''
    Test of blindind of a component
    '''
    obs = zfit.Space('m', limits=(0, 10))
    mu  = zfit.Parameter("mu", 5.0,  0, 10)
    sg  = zfit.Parameter("sg", 1.3,  0,  5)

    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nsg = zfit.Parameter('nsg', 1000, 0, 10000)
    esig= sig.create_extended(nsg, name = 'signal')

    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    nbk = zfit.Parameter('nbk', 1000, 0, 10000)
    ebkg= bkg.create_extended(nbk)

    pdf = zfit.pdf.SumPDF([esig, ebkg])

    sam = pdf.create_sampler()
    dat = sam.numpy().flatten()
    dat = zfit.Data.from_numpy(obs=obs, array=dat)
    assert isinstance(dat, zdat)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    print(res)

    cfg = ZFitPlotterConf(blind = ('signal', 4, 5))
    obj = ZFitPlotter(data=dat, model=pdf, result=res)
    obj.plot(cfg)

    # add a line to pull hist
    obj.axs[1].plot([0, 10], [0, 0], linestyle='--', color='black')
    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_composed_ranges(tmp_path : Path):
    '''
    Testing plot in ranges of composed PDF
    '''
    obs = zfit.Space('m', limits=(0, 10))

    mu  = zfit.Parameter('mu', 5.0,  0, 10)
    sg  = zfit.Parameter('sg', 1.0,  0,  5)
    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    sg.floating=False
    mu.floating=False
    lm.floating=False

    nsg = zfit.Parameter('nsg',  5000, 0, 100000)
    nbk = zfit.Parameter('nbk', 10000, 0, 100000)

    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    ebkg= bkg.create_extended(nbk)

    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    esig= sig.create_extended(nsg)

    pdf = zfit.pdf.SumPDF([ebkg, esig])
    sam = pdf.create_sampler()

    nsg.set_value(100)
    nbk.set_value(1000)

    nll_1 = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=sam, fit_range=(0, 4))
    nll_2 = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=sam, fit_range=(6,10))
    nll   = nll_1 + nll_2
    mnm   = zfit.minimize.Minuit()
    res   = mnm.minimize(nll)

    print(res)

    cfg = ZFitPlotterConf(ranges = [(0, 4), (6, 10)])
    obj = ZFitPlotter(data=sam, model=pdf, result=res)
    obj.plot(cfg)
    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_plot_pars(tmp_path : Path):
    '''
    Testing plotting of parameters alongside fit
    '''
    obs = zfit.Space('m', limits=(-10, 10))
    mu  = zfit.Parameter("mu", 0.4, -5, 5)
    sg  = zfit.Parameter("sg", 1.3,  0, 5)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 100, 0, 10000)
    pdf = pdf.create_extended(nev)
    dat = pdf.create_sampler(n=10000)

    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    plt_path= tmp_path / 'fit_all.png'
    cfg_2 = ZFitPlotterConf(add_pars = 'all')
    obj_1 = ZFitPlotter(model=pdf, data=dat, result=res)
    obj_1.plot(cfg_2)
    log.info(f'Saving to: {plt_path}')
    plt.savefig(f'{plt_path}')

    plt_path= tmp_path / 'fit_some.png'
    cfg_2 = ZFitPlotterConf(add_pars = ['mu', 'sg'])
    obj_2 = ZFitPlotter(model=pdf, data=dat, result=res)
    obj_2.plot(cfg_2)
    log.info(f'Saving to: {plt_path}')
    plt.savefig(f'{plt_path}')

    plt.close('all')
#--------------------------------
def test_blind(tmp_path : Path):
    '''
    Testing blind argument
    '''
    obs = zfit.Space('m', limits=(-5, +5))
    mu  = zfit.Parameter("mu", 0.0, -5, 5)
    sg  = zfit.Parameter("sg", 0.5,  0, 5)
    lm  = zfit.Parameter("lm",-0.1, -5, 0)

    pdf = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nev = zfit.Parameter('nev', 5000, 0, 10000)
    pdf = pdf.create_extended(nev,)

    bkg= zfit.pdf.Exponential(obs=obs, lam=lm, name='expo')
    nbk = zfit.Parameter('nbk', 5000, 0, 10000)
    bkg = bkg.create_extended(nbk,)

    pdf = zfit.pdf.SumPDF([bkg, pdf])

    dat = pdf.create_sampler()
    nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)
    mnm = zfit.minimize.Minuit()
    res = mnm.minimize(nll)

    #Fake GOF for ploting purposes
    setattr(res, 'gof', (11, 10, 0.5)) # noqa: B010

    cfg = ZFitPlotterConf(blind = ['gauss_ext', -2, +2])
    obj = ZFitPlotter(data=dat, model=pdf, result=res)
    obj.plot(cfg)

    obj.axs[1].plot([-5, 5], [0, 0], linestyle='--', color='black')
    plt.savefig(tmp_path / 'fit_lin.png', bbox_inches='tight')

    obj.set_yscale('log')
    plt.savefig(tmp_path / 'fit_log.png', bbox_inches='tight')
#--------------------------------
def test_show_components(tmp_path : Path):
    '''
    Tests plot_components argument, which shows subcomponents of PDF
    '''
    obs   = zfit.Space('m', limits=(-10, 10))
    mu    = zfit.Parameter("mu", 0.0, -5, 5)
    sg    = zfit.Parameter("sg", 1.0,  0, 5)

    sig   = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg)
    nsg   = zfit.Parameter('nsg', 1000, 0, 10000)
    sig   = sig.create_extended(nsg, name='gauss')
    #-----------------------------------------
    lm_1  = zfit.Parameter("lm_1", -0.1, -5.0, 0)
    lm_2  = zfit.Parameter("lm_2", -0.1, -5.0, 0)
    fr_1  = zfit.Parameter("fr_1",  0.5,  0.0, 1)
    fr_2  = zfit.Parameter("fr_2",  0.5,  0.0, 1)

    bkg_1 = zfit.pdf.Exponential(lam=lm_1, obs=obs, name='ex_1')
    bkg_2 = zfit.pdf.Exponential(lam=lm_2, obs=obs, name='ex_2')

    bkg   = zfit.pdf.SumPDF([bkg_1, bkg_2], fracs=[fr_1, fr_2])
    nbk   = zfit.Parameter('nbk', 1000, 0, 10000)
    bkg   = bkg.create_extended(nbk, name='bkg')
    #-----------------------------------------
    pdf   = zfit.pdf.SumPDF([bkg, sig])
    #-----------------------------------------
    cfg = ZFitPlotterConf(plot_components=['bkg'])
    obj = ZFitPlotter(data=pdf.create_sampler(), model=pdf, result=None)
    obj.plot(cfg)
    obj.axs[1].set_ylim(-5, 5)

    plt.savefig(tmp_path / 'fit.png', bbox_inches='tight')
#--------------------------------
def test_plot_range(tmp_path : Path):
    '''
    Plot in reduced range
    '''
    obs = zfit.Space('m', limits=(0, 10))

    mu  = zfit.Parameter("mu", 5.0,  0, 10)
    sg  = zfit.Parameter("sg", 0.5,  0,  5)
    sig = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg, name='gauss')
    nsg = zfit.Parameter('nsg', 10_000, 0, 100_000)
    esig= sig.create_extended(nsg)

    lm  = zfit.Parameter('lm', -0.1, -1, 0)
    bkg = zfit.pdf.Exponential(obs=obs, lam=lm)
    nbk = zfit.Parameter('nbk', 10_000, 0, 100_000)
    ebkg= bkg.create_extended(nbk)

    pdf = zfit.pdf.SumPDF([ebkg, esig], obs = obs)
    sam = pdf.create_sampler()

    cfg = ZFitPlotterConf(
        stacked    = False,
        plot_range = (3, 8),
        nbins      = 40)
    obj = ZFitPlotter(data=sam, model=pdf)
    obj.plot(cfg)
    plt.savefig(tmp_path / 'fit_ovr.png')

    cfg = ZFitPlotterConf(
        stacked    = True,
        plot_range = (3, 8),
        nbins      = 40)
    obj = ZFitPlotter(data=sam, model=pdf)
    obj.plot(cfg)
    plt.savefig(tmp_path / 'fit_stk.png')
#--------------------------------
