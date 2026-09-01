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
def test_from_non_spline(tmp_path : Path):
    '''
    Test building SplinePDF from non-spline
    '''
    xs  = np.linspace(1, 10, 400)
    obs = zfit.Space("x", limits=(1, 10))

    pdf        = zfit.pdf.Gauss(mu = 5.0, sigma = 1.0, obs = obs)
    spline_pdf = SplinePDF.from_non_spline(pdf = pdf)

    y1s =        pdf.pdf(xs)
    y2s = spline_pdf.pdf(xs)

    plt.scatter(xs, y1s, s = 6, label = 'Original')
    plt.scatter(xs, y2s, s = 1, label = 'Spline'  )
    plt.legend()
    plt.savefig(tmp_path / 'comparison.png')
    plt.close()

    assert np.isclose(y1s, y2s, atol = 1e-4).all()
    assert isinstance(spline_pdf, SplinePDF)
# ------------------------
