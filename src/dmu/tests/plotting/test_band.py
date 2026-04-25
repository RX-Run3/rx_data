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
    kind      : str, 
    parameter : str) -> pnd.DataFrame:
    size = 1
    data = {
        'Value' : numpy.random.normal(loc = 10, scale = 1.0, size = size),
        'Error' : numpy.random.normal(loc =  1, scale = 0.1, size = size),
    }

    df = pnd.DataFrame(data)
    df['Parameter'] = parameter
    df['kind'     ] = kind 

    return df
# ------------------------------
def test_simple(tmp_path : Path):
    l_df : list[pnd.DataFrame] = []
    for kind in ['w', 'x', 'y', 'z']:
        for parameter in ['a', 'b', 'c']:
            df = _get_df(
                kind      = kind, 
                parameter = parameter)
            l_df.append(df)
    df = pnd.concat(l_df)

    astyle = Style(
        ylabel    = 'Value',
        yrange    = (5., 15.),
        xrotation = 45,
        alpha     = 0.3,
        color     = 'blue',
    )

    bstyle = astyle.model_copy(update = {'color' :   'red'})
    cstyle = astyle.model_copy(update = {'color' : 'green'})

    styles = {
        'a' : astyle,
        'b' : bstyle,
        'c' : cstyle,
    }

    cfg = BandPlotterConf(
        out_dir = tmp_path,
        xname   = 'kind',
        styles  = styles,
        labels  = {'a' : r'$\alpha$', 'b' : r'$\beta$', 'c' : r'$\gamma$'},
        groups  = {'ab' : ['a', 'b'], 'c' : ['c']},
    )

    ptr = BandPlotter(
        cfg = cfg,
        df  = df)
    ptr.plot()
