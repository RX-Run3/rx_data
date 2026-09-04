'''
Module with tests for NonParametricModel class
'''
import numpy
import matplotlib.pyplot as plt

from pathlib   import Path
from dmu.stats import zfit
from dmu.stats import NonParametricModel
from dmu.stats import ZFitPlotter, ZFitPlotterConf

def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    obs   = zfit.Space('mass', limits = (4500, 6000))
    array = numpy.random.normal(loc = 5000, scale = 300, size = 1000)
    data  = zfit.Data.from_numpy(obs = obs, array = array)
    if not isinstance(data, zfit.Data):
        raise ValueError('Invalid data type')

    model = NonParametricModel.from_data(data = data)

    cfg = ZFitPlotterConf.default()
    ptr = ZFitPlotter(data = data, model = model.pdf)
    ptr.run(cfg = cfg)
    plt.savefig(tmp_path / 'fit.png')
    plt.close()
