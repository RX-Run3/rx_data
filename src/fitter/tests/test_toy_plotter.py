'''
Module with functions meant to test the ToyPlotter class
'''
import math
import mplhep
import matplotlib.pyplot as plt

import logging
import pytest
import numpy
import pandas as pnd

from pathlib     import Path
from functools   import lru_cache
from dmu.generic import utilities as gut
from dmu         import LogStore
from fitter      import ToyPlotter, MissingVariableConfiguration

log=LogStore.add_logger('fitter:test_toy_plotter')
plt.style.use(mplhep.style.LHCb2)
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:plotting:Plotter1D', 10)
# ----------------------
@lru_cache(maxsize=3)
def _get_df(ntoys : int, l_var : tuple[str]) -> pnd.DataFrame:
    '''
    Returns 
    ------------------
    dataframe with fake fit parameter information
    '''
    numpy.random.seed(42)
    l_df_var : list[pnd.DataFrame] = []
    for var in l_var:
        df_var              = pnd.DataFrame(columns=['Parameter', 'Value', 'Error', 'Gen', 'Toy', 'GOF', 'Valid'])
        df_var['Parameter'] = ntoys * [var]
        if var != 'b':
            df_var['Gen'      ] = numpy.zeros(ntoys)
            df_var['Value'    ] = numpy.random.normal(loc=0.0, scale=1.0, size=ntoys)
            df_var['Error'    ] = numpy.random.normal(loc=1.0, scale=0.1, size=ntoys)
        else:
            df_var['Gen'      ] = numpy.array(ntoys * [1000])
            df_var['Value'    ] = numpy.random.normal(loc=1000, scale=30, size=ntoys)
            df_var['Error'    ] = numpy.random.normal(loc=  30, scale= 1, size=ntoys)
        df_var['Toy'      ] = numpy.arange(ntoys) 

        l_df_var.append(df_var)

    df = pnd.concat(l_df_var)
    df = df.reset_index(drop=True)

    npar = len(l_var)
    for itoy in range(ntoys):
        gof = numpy.random.uniform(low=0, high=1, size=1)
        cnv = numpy.random.choice(a=[True, False], p=[0.95, 0.05], size=1)

        df.loc[df.Toy == itoy,   'GOF'] = npar * [gof] # type: ignore
        df.loc[df.Toy == itoy, 'Valid'] = npar * [cnv] # type: ignore

    df['GOF']   = df['GOF'  ].astype(float)
    df['Valid'] = df['Valid'].astype(bool )

    for numeric in ['Value', 'Error', 'Gen', 'Toy', 'GOF']:
        log.info(f'Checking: {numeric}')
        assert numpy.isfinite(df[numeric]).all()

    df['Hash'] = df['Toy']

    return df
# ----------------------
def test_simple(tmp_path : Path) -> None:
    '''
    This is the simplest test of ToyPlotter
    '''
    log.info('')
    df = _get_df(ntoys=1000, l_var=('a', 'b'))
    cfg= gut.load_conf(package='fitter_data', fpath='tests/toys/toy_plotter.yaml')
    cfg.saving.plt_dir = tmp_path/cfg.saving.plt_dir

    ptr = ToyPlotter(df=df, cfg=cfg)
    cfg = ptr.plot()

    assert math.isclose(cfg.median_a_unc, 153.3263369554583, rel_tol=1e-5)
    assert math.isclose(cfg.median_b_unc, 2.998985959009677, rel_tol=1e-5)
    assert math.isclose(cfg.mean_Valid  , 0.948            , rel_tol=1e-5)

    assert math.isclose(cfg.a_pul.mu, 0.02316429312808755, rel_tol=1e-5) # pyrefly: ignore
    assert math.isclose(cfg.a_pul.sg, 0.982856552637077  , rel_tol=1e-5) # pyrefly: ignore
# ----------------------
def test_missing_variable(caplog, tmp_path : Path) -> None:
    '''
    Test that plotter class:

    - Raises re ValueError when variable is missing
    - Shows list of variables found instead
    '''
    log.info('')
    df = _get_df(ntoys=1000, l_var=('c', 'b'))
    cfg= gut.load_conf(package='fitter_data', fpath='tests/toys/toy_plotter.yaml')
    cfg.saving.plt_dir = tmp_path/cfg.saving.plt_dir

    logger = LogStore.get_logger(name='fitter:toy_plotter')
    if logger is None:
        raise ValueError('Invalid logger name')
    logger.addHandler(caplog.handler) # pyrefly: ignore

    caplog.set_level(logging.INFO)
    with pytest.raises(MissingVariableConfiguration):
        ptr= ToyPlotter(df=df, cfg=cfg)
        ptr.plot()

    l_message= [ record.getMessage() for record in caplog.records ] 

    assert l_message[-3:] == ['Parameters found:', 'b', 'c']
# ----------------------
