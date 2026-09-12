'''
Module holding tests for CCbarPDF
'''

import hqm.pdf_mc     as pdf_mc
import hqm.ratc       as ratc 
import hqm.prec_maker as prec_maker
import hqm.data_store as data_store

from contextlib    import contextmanager
from pathlib       import Path
from rx_common     import Project
from hqm.ccbar_pdf import CCbarPDFMaker
from dmu.stats     import SplinePDF, zfit

# ----------------------------
class TestRatio:
    def get_value(self):
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

        mu = zfit.Parameter('mu', 5280, 5200, 5300)
        sg = zfit.Parameter('sg',   50,   10,  300)

        return zfit.pdf.Gauss(
            name = 'gauss', 
            obs  = obs_ext, 
            mu   = mu, 
            sigma= sg)
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

        pdf = zfit.pdf.Exponential(name = 'expo', lam  = c)
        pdf = SplinePDF.from_non_spline(pdf = pdf)

        return pdf.representation
# ----------------------------
def test_simple(monkeypatch, tmp_path : Path):
    '''
    Simplest test
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    monkeypatch.setattr(pdf_mc    , 'PdfBuilder'          , TestPdfBuilder)
    monkeypatch.setattr(ratc      , 'CCbarRatioCalculator', TestCCbarRatioCalculator)
    monkeypatch.setattr(prec_maker, 'PrecMaker'           , TestPrecMaker)

    obs     = zfit.Space('B_Mass', limits = (4600, 6500))
    binning = 'block-3 mva_cmb-3'
    project = Project.rk

    ccb = CCbarPDFMaker(
        binning = binning,
        project = project)

    pdf = ccb.get_pdf(obs = obs, update = False)
# ----------------------------
