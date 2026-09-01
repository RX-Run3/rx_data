'''
Module with tests for SplinePDF
'''

import numpy             as np
import matplotlib.pyplot as plt

from pathlib     import Path
from dmu.stats   import ZFitPlotterConf, ZFitPlotter 
from dmu.stats   import SplinePDF, zfit

# ------------------------
def test_simple(tmp_path : Path):
    '''
    Test making PDF and plot it
    '''
    n_points = 400
    x_grid   = np.linspace(0, 10, n_points)
    y_grid   = (x_grid - 2)**2 * (x_grid - 5)**2 * (x_grid - 8)**2 + 1
    
    obs = zfit.Space("x", limits=(1, 10))
    pdf = SplinePDF(obs = obs, xs = x_grid, ys = y_grid)
    data= pdf.create_sampler(n = 1000)
    
    cfg = ZFitPlotterConf.default()
    
    ptr = ZFitPlotter(data = data, model = pdf)
    ptr.run(cfg = cfg)
    plt.savefig(tmp_path / 'fit.png')
    plt.close()
# ------------------------
def test_serialize(tmp_path : Path):
    '''
    Test dumping and loading to JSON
    '''
    n_points = 400
    x_grid   = np.linspace(0, 10, n_points)
    y_grid   = (x_grid - 2)**2 * (x_grid - 5)**2 * (x_grid - 8)**2 + 1
    
    obs  = zfit.Space("x", limits=(1, 10))
    pdf  = SplinePDF(obs = obs, xs = x_grid, ys = y_grid)
    path = tmp_path / 'spline.json'

    pdf.to_json(path = path)
    SplinePDF.from_json(path = path)
# ------------------------
