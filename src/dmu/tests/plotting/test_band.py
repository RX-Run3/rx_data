'''
Module with functions to test BandPlotter class
'''

import numpy
import pandas as pnd

from pathlib      import Path
from dmu.plotting import Style
from dmu.plotting import BandPlotter
from dmu.plotting import BandPlotterConf

# ------------------------------
def _get_df(
    parameter : str) -> pnd.DataFrame:
    size = 1
    data = {
        'Value' : numpy.random.normal(loc = 10, scale = 1.0, size = size),
        'Error' : numpy.random.normal(loc =  1, scale = 0.1, size = size),
    }

    df = pnd.DataFrame(data)
    df['Parameter'] = parameter

    return df
# ------------------------------
def _get_all_df():
    l_df : list[pnd.DataFrame] = []
    for category in ['c1', 'c2', 'c3', 'c4']:
        for kind in ['w', 'x', 'y', 'z']:
            for parameter in ['a', 'b', 'c']:
                df            = _get_df(
                    parameter = parameter)

                df['Kind'] = kind
                df['Category'] = category

                l_df.append(df)

    df = pnd.concat(l_df)

    return df
# ------------------------------
def test_simple(tmp_path : Path):
    df     = _get_all_df()
    astyle = Style(
        ylabel    = 'Value',
        yrange    = (5., 15.),
        xrotation = 45,
        alpha     = 0.3,
    )

    styles = {
        'a' : astyle,
        'b' : astyle,
        'c' : astyle,
    }

    groups = {
        'g1' : ['c1', 'c2'],
        'g2' : ['c3', 'c4'],
    }

    labels = {
        'c1' : 'Cat 1',
        'c2' : 'Cat 2',
        'c3' : 'Cat 3',
        'c4' : 'Cat 4',
    }

    cfg = BandPlotterConf(
        size    = (15, 10),
        out_dir = tmp_path,
        xname   = 'Kind',
        styles  = styles,
        labels  = labels,
        groups  = groups,
    )

    ptr = BandPlotter(
        cfg = cfg,
        df  = df)
    ptr.plot()
# ------------------------------
