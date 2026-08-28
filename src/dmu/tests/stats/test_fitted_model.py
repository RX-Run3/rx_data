'''
Module with tests for FittedModel class
'''

from pathlib import Path

from dmu.stats import ModelFactory
from dmu.stats import zfit, Model
from dmu.stats import Fitter
from dmu.stats import FittedModel

# -----------------------------
def _get_fit_model() -> FittedModel:
    obs = zfit.Space('mass', limits=(5000, 6000))
    mfc = ModelFactory(
        obs     = obs,
        l_pdf   = [Model.gauss],
        l_shared= [],
        l_float = [],
        preffix = 'test')

    pdf  = mfc.get_pdf()
    data = pdf.create_sampler(n = 1000)

    ftr  = Fitter(pdf = pdf, data = data)
    res  = ftr.fit()

    fmo     = FittedModel.from_fit(
        cfg = mfc.cfg, 
        pdf = pdf,
        res = res)

    return fmo
# -----------------------------
def test_from_fit():
    '''
    Test creating object from fit outputs
    '''
    obs = zfit.Space('mass', limits=(5000, 6000))
    mfc = ModelFactory(
        obs     = obs,
        l_pdf   = [Model.gauss],
        l_shared= [],
        l_float = [],
        preffix = 'test')

    pdf  = mfc.get_pdf()
    data = pdf.create_sampler(n = 1000)

    ftr  = Fitter(pdf = pdf, data = data)
    res  = ftr.fit()

    fmo     = FittedModel.from_fit(
        cfg = mfc.cfg, 
        pdf = pdf,
        res = res)
# -----------------------------
def test_serialize(tmp_path : Path):
    '''
    Test creating object from fit outputs
    '''
    path = tmp_path / 'model.json'
    fmo  = _get_fit_model()
    fmo.to_json(path = path)

    FittedModel.from_json(path = path)
# -----------------------------
