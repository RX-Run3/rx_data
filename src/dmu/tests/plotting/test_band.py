'''
Module with functions to test BandPlotter class
'''

import numpy
import pandas as pnd

from dmu.plotting import BandPlotter
from dmu.plotting import BandPlotterConf

# ------------------------------
def _get_df() -> pnd.DataFrame:
    size = 10_000
    data = {
        'Value' : numpy.random.normal(loc = 10, scale = 1.0, size = size),
        'Error' : numpy.random.normal(loc =  1, scale = 0.1, size = size),
    }

    df = pnd.DataFrame(data)
    df['Parameter'] = 'a'

    return df
# ------------------------------
def test_simple():
    df = _get_df()
    cfg = BandPlotterConf()

    ptr = BandPlotter(
        cfg = cfg,
        df  = df)
    ptr.plot()
