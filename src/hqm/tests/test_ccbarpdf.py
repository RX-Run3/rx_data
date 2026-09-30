'''
Module holding tests for CCbarPDF
'''
import pytest
import matplotlib.pyplot as plt

from hqm           import ccbar_pdf
from pathlib       import Path
from rx_common     import Project
from hqm.ccbar_pdf import CCbarPDFMaker
from dmu.generic   import Mode
from dmu.stats     import FittedModel, Fitter, Model, ModelFactory
from dmu.stats     import ObsConf, ModelFactoryConf, SplinePDF, ZFitPlotter, ZFitPlotterConf, print_pdf, zfit
from dmu.stats     import utilities as sut

type zobs = zfit.Space
type zpdf = zfit.pdf.BasePDF
# ----------------------------
def _get_real_ccbar(obs : zobs) -> zpdf:
    binning = 'block-3 mva_cmb-3 mva_prc-3'
    project = Project.rk

    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    model= ccb.get_pdf(obs = obs, mode = Mode.read)
    pdf  = model.get_pdf(
        obs_name = 'mass',
        suffix   = 'suf')

    nev  = zfit.Parameter('nbkg', 1000, 0, 100_000)

    return pdf.create_extended(nev, name = 'ccbar')
# ----------------------------
def _get_fake_signal(obs : zobs) -> zpdf:
    mu = zfit.Parameter('mu'  , 5280, 5250, 5310)
    sg = zfit.Parameter('sg'  ,   80,   50,  100)
    nev= zfit.Parameter('nsig', 1000, 0, 100_000)

    pdf= zfit.pdf.Gauss(mu = mu, sigma = sg, obs = obs)

    return pdf.create_extended(nev, name = 'signal')
# ----------------------------
class TestRatio:
    larger_prec = False
    def get_value(self, name : str):
        _ = name
        if self.larger_prec:
            return 1.3, 0.03

        return 0.3, 0.03
# ----------------------------
class TestCCbarRatioCalculator:
    def __init__(self, cfg, binning, project):
        pass

    def get_ratio(self, mode : str):
        _ = mode
        return TestRatio()
# ----------------------------
class TestPdfBuilder:
    def __init__(
        self,
        name   ,
        comp   ,
        trigger,
        qsq    ,
        label  : str = ''):
        pass
    # ----------------------------
    def get_model(self, obs_ext : zobs, use_kde : str, mode : str):
        _ = use_kde
        _ = mode

        cfg_obs = ObsConf(name = 'B_Mass', lower = 4600, upper = 6500)
        cfg_mod = ModelFactoryConf.default(pdfs = [Model.gauss])
        values  = {
            'mu' : (5280, 5200, 5300),
            'sg' : (  50,   10,  300),
        }
        cfg_mod = cfg_mod.model_copy(update = values)

        fac = ModelFactory.from_conf(
            prefix = 'test',
            obs    = obs_ext,
            cfg    = cfg_mod)
        pdf = fac.get_pdf()
        data= pdf.create_sampler(n = 1000)

        ftr = Fitter(data = data, pdf = pdf)
        res = ftr.fit()

        return FittedModel(
            name       = 'test',
            obs_conf   = cfg_obs,
            model_conf = cfg_mod,
            fit_result = res)
# ----------------------------
class TestPrecMaker:
    def __init__(
        self,
        cfg,
        binning,
        project):
        pass
    # ----------------------------
    def get_pdf(self, mode : str, name : str):
        _   = mode
        _   = name

        obs = zfit.Space('B_Mass', limits=(4600, 6500))
        c   = zfit.Parameter('c',   -0.001,   -0.01,  0)

        pdf = zfit.pdf.Exponential(name = 'expo', lam  = c, obs = obs)
        pdf = SplinePDF.from_non_spline(pdf = pdf)

        return pdf
# ----------------------------
@pytest.mark.parametrize('larger_prec', [False, True])
def test_simple(
    monkeypatch,
    larger_prec : bool,
    tmp_path    : Path):
    '''
    Simplest test
    '''
    TestRatio.larger_prec = larger_prec

    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(ccbar_pdf, 'PdfBuilder'          , TestPdfBuilder)
    monkeypatch.setattr(ccbar_pdf, 'CCbarRatioCalculator', TestCCbarRatioCalculator)
    monkeypatch.setattr(ccbar_pdf, 'PrecMaker'           , TestPrecMaker)

    obs     = zfit.Space('B_Mass', limits = (4600, 6500))
    binning = 'block-3 mva_cmb-3'
    project = Project.rk

    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    model= ccb.get_pdf(obs = obs, mode = Mode.write)
    data = model.pdf.create_sampler(n = 10_000)

    cfg = ZFitPlotterConf.default()
    ptr = ZFitPlotter(model = model.pdf, data = data)
    ptr.run(cfg = cfg)
    plt.savefig(ccb.out_dir / 'fit.png')
    plt.close()

    print_pdf(model.pdf)
# ----------------------------
def test_suffix(monkeypatch, tmp_path : Path):
    '''
    Override suffix of PDF
    '''
    TestRatio.larger_prec = False 

    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(ccbar_pdf, 'PdfBuilder'          , TestPdfBuilder)
    monkeypatch.setattr(ccbar_pdf, 'CCbarRatioCalculator', TestCCbarRatioCalculator)
    monkeypatch.setattr(ccbar_pdf, 'PrecMaker'           , TestPrecMaker)

    obs     = zfit.Space('B_Mass', limits = (4600, 6500))
    binning = 'block-3 mva_cmb-3'
    project = Project.rk

    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    model= ccb.get_pdf(obs = obs, mode = Mode.write)
    pdf  = model.get_pdf(
        obs_name = 'mass',
        suffix   = 'suf')

    sut.print_pdf(pdf)
# ----------------------------
@pytest.mark.skip(reason = 'Needs external inputs')
def test_real_fit():
    '''
    Override suffix of PDF
    '''
    obs = zfit.Space('mass', limits = (4600, 6500))
    bkg = _get_real_ccbar(obs = obs)
    sig = _get_fake_signal(obs = obs)

    pdf = zfit.pdf.SumPDF([bkg, sig])
    dat = pdf.create_sampler()

    ftr = Fitter(data = dat, pdf = pdf)
    res = ftr.fit()
    print(res)

    cfg = ZFitPlotterConf.default()
    ptr = ZFitPlotter(data = dat, model = pdf)
    ptr.run(cfg = cfg)
    plt.savefig(tmp_path / 'plot.png')
    plt.close()
# ----------------------------
