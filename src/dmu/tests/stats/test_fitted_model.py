'''
Module with tests for FittedModel class
'''
import pytest

from typing    import Final
from pathlib   import Path
from dmu.stats import ModelFactory
from dmu.stats import zfit, Model
from dmu.stats import Fitter
from dmu.stats import FittedModel
from dmu.stats import utilities as sut

_MODELS : Final[list[list[Model]]] = [
    [Model.gauss],
    [Model.cbr, Model.cbl],
]

zfit.settings.set_seed(42)
# -----------------------------
def _get_fit_model(models : list[Model]) -> FittedModel:
    obs = zfit.Space('mass', limits=(5000, 6000))
    mfc = ModelFactory(
        obs     = obs,
        l_pdf   = models,
        l_shared= [],
        l_float = [],
        preffix = 'test')

    pdf  = mfc.get_pdf()
    data = pdf.create_sampler(n = 1000)

    ftr  = Fitter(pdf = pdf, data = data)
    res  = ftr.fit()

    fmo     = FittedModel.from_fit(
        name= 'test',
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
        l_float = ['mu'],
        preffix = 'test')

    pdf  = mfc.get_pdf()
    data = pdf.create_sampler(n = 1000)

    ftr  = Fitter(pdf = pdf, data = data)
    res  = ftr.fit()

    fmo     = FittedModel.from_fit(
        name= 'test',
        cfg = mfc.cfg, 
        pdf = pdf,
        res = res)

    sut.print_pdf(fmo.pdf)

    [mu] = [ par for par in fmo.pdf.get_params(floating = None) if par.name.startswith('mu') ]
    [sg] = [ par for par in fmo.pdf.get_params(floating = None) if par.name.startswith('sg') ]

    assert     mu.floating
    assert not sg.floating

    assert isinstance(fmo, FittedModel)
# -----------------------------
@pytest.mark.parametrize('models', _MODELS)
def test_serialize(tmp_path : Path, models : list[Model]):
    '''
    Test creating object from fit outputs
    '''
    path = tmp_path / 'model.json'
    fmo  = _get_fit_model(models = models)
    fmo.to_json(path = path)

    FittedModel.from_json(path = path)
# -----------------------------
@pytest.mark.parametrize('models', _MODELS)
def test_renamed(models : list[Model]):
    '''
    Test that PDF from model can be named
    '''
    pdf_name = 'pdf_name'
    fmo      = _get_fit_model(models = models)
    pdf      = fmo.get_pdf(name = pdf_name)

    assert pdf.name == pdf_name

    sut.print_pdf(pdf = pdf)
# -----------------------------
