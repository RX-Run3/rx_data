'''
Module holding tests for CCbarPDF
'''
from hqm           import ccbar_pdf 
from contextlib    import contextmanager
from pathlib       import Path
from rx_common     import Project
from hqm.ccbar_pdf import CCbarPDFMaker
from dmu.stats     import FittedModel, Fitter, Model, ModelFactory, ModelFactoryConf, SplinePDF, zfit
from dmu.stats     import ObsConf

# ----------------------------
class TestRatio:
    def get_value(self, name):
        _ = name
        return 10, 1
# ----------------------------
class TestCCbarRatioCalculator:
    def __init__(self, cfg, binning, project):
        pass

    def get_ratio(self, update):
        _ = update
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
    def get_model(self, obs_ext, use_kde, update):
        _ = use_kde
        _ = update

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
    def get_pdf(self, update):
        _   = update

        obs = zfit.Space('B_Mass', limits=(4600, 6500))
        c   = zfit.Parameter('c',   -0.001,   -0.01,  0)

        pdf = zfit.pdf.Exponential(name = 'expo', lam  = c, obs = obs)
        pdf = SplinePDF.from_non_spline(pdf = pdf)

        return pdf
# ----------------------------
def test_simple(monkeypatch, tmp_path : Path):
    '''
    Simplest test
    '''
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

    pdf = ccb.get_pdf(obs = obs, update = False)
# ----------------------------
