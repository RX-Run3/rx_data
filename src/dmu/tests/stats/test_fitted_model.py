'''
Module with tests for FittedModel class
'''

from dmu.stats import ModelFactory
from dmu.stats import zfit, Model
from dmu.stats import Fitter
from dmu.stats import FittedModel

def test_simple():
    '''
    Simplest test
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
        cfg = mfc.conf, 
        pdf = pdf,
        res = res)

     
