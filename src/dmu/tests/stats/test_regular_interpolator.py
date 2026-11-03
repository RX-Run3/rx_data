'''
Module with tests for RegularIterpolator class
'''
import pytest
import numpy             as np
import matplotlib.pyplot as plt
import tensorflow        as tf

from pathlib   import Path
from dmu.stats import RegularInterpolator
from dmu       import LogStore

# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:regular_interpolator', 10)
# ---------------------------------------
def test_numpy(tmp_path : Path):
    '''
    Interpolate with numpy arrays
    '''
    x_grid = np.linspace(-5, 5, 100)
    y_grid = np.exp(-x_grid**2 / 9)
    itp    = RegularInterpolator(xs = x_grid, ys = y_grid)

    xs  = np.linspace(-5, 5, 1000)
    ys  = itp.interpolate(xs = xs)

    plt.scatter(xs    , ys      , s = 1)
    plt.scatter(x_grid, y_grid  , s = 2)
    plt.savefig(tmp_path / 'interpolation.png')
    plt.close()
# ---------------------------------------
def test_tensor(tmp_path : Path):
    '''
    Interpolate with tensors
    '''
    x_grid = np.linspace(-5, 5, 100)
    y_grid = np.exp(-x_grid**2 / 9)
    itp    = RegularInterpolator(xs = x_grid, ys = y_grid)

    xs  = np.linspace(-5, 5, 1000)
    xs  = tf.constant(xs, dtype=tf.float32)
    ys  = itp.interpolate(xs = xs)

    xs  = xs.numpy()
    ys  = ys.numpy()

    plt.scatter(xs    , ys      , s = 1)
    plt.scatter(x_grid, y_grid  , s = 2)
    plt.savefig(tmp_path / 'interpolation.png')
    plt.close()
# ---------------------------------------
