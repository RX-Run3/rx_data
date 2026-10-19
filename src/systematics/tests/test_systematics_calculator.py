'''
Module with functions intended to test SystematicsCalculator
'''

import zfit
import pytest
import pandas as pnd

from typing        import Final
from pathlib       import Path
from zfit.loss     import ExtendedUnbinnedNLL

from dmu           import LogStore
from dmu.stats     import FitResult
from dmu.testing   import get_nll, get_model
from dmu.generic   import rxran
from dmu.generic   import utilities as gut

from fitter        import ChannelHolder, ToyConf
from systematics   import SystematicsCalculator

log = LogStore.add_logger('rx_stats:test_systematics_calculator')
type zlos = ExtendedUnbinnedNLL
# ----------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_stats:systematics', 10)
    LogStore.set_level('rx_stats:toy_maker'  , 10)
    with rxran.seed(value = 42):
        yield
# ----------------------
@pytest.mark.parametrize('ntoys', [10])
def test_model_switch(
    monkeypatch,
    tmp_path : Path,
    ntoys    : int | None) -> None:
    '''
    Parameters
    -------------
    tmp_path : Where output plots will go
    ntoys    : Number of toys to override what is in config
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    log.info('')

    nll   = get_nll(kind='s+b', suffix = '')
    assert isinstance(nll, ExtendedUnbinnedNLL)

    data = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    if ntoys is not None:
        data['ntoys'] = ntoys

    minimizer = zfit.minimize.Minuit()
    res       = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse', method = 'minuit_hesse')

    res       = FitResult.from_zfit(res = res)
    model_alt = get_model(kind = 's_alt+b')

    cfg  = ToyConf(**data)
    scal = SystematicsCalculator(
        poi = 'nsig',
        obj = nll, 
        res = res, 
        cfg = cfg) 

    df_alt  = scal.switch_model(
        model = model_alt, 
        label = 'alt_signal')

    df_nom  = scal.switch_model(
        model = None, 
        label = 'nom_signal')

    assert df_alt is not None
    assert df_nom is not None
# ----------------------
@pytest.mark.parametrize('ntoys', [10])
def test_parameter_fixing(
    monkeypatch,
    tmp_path : Path,
    ntoys    : int | None) -> None:
    '''
    Test fixing nuisance parameters

    Parameters
    -------------
    tmp_path : Where output plots will go
    ntoys    : Number of toys to override what is in config
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    log.info('')
    nll   = get_nll(kind='s_alt+b', nentries = 10_000)
    assert isinstance(nll, ExtendedUnbinnedNLL)

    data      = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    if ntoys is not None:
        data['rseed'] = 123
        data['ntoys'] = ntoys

    cfg       = ToyConf(**data)
    minimizer = zfit.minimize.Minuit()
    res       = minimizer.minimize(loss = nll)
    res.hesse(name = 'minuit_hesse', method = 'minuit_hesse')
    res       = FitResult.from_zfit(res = res)

    POI : Final[str] = 'nsig_gaus_test_1'
    scal = SystematicsCalculator(
        poi = POI,
        obj = nll, 
        res = res, 
        cfg = cfg) 

    npars = len(scal.parameters)
    nrows = cfg.ntoys * npars
    index = 1
    for par in scal.parameters.values():
        if par.name == scal.poi:
            continue

        df = scal.fix_parameter(
            name  = par.name,
            label = f'fix_{par.name}')

        size = len(df)
        df_nsig = df.query(f'Parameter == \"{POI}\"')

        assert len(df_nsig['Gen'].unique()) == 1
        assert size == nrows - index * cfg.ntoys 
        assert isinstance(df, pnd.DataFrame)
        assert len(df) > 0

        index += 1
# ----------------------
@pytest.mark.parametrize('ntoys', [1])
def test_sim_model_switch(
    monkeypatch,
    tmp_path : Path,
    ntoys    : int | None) -> None:
    '''
    Switch models in simultaneous fit

    Parameters
    -------------
    tmp_path : Where output plots will go
    ntoys    : Number of toys to override what is in config
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    log.info('')
    nll_mm = get_nll(
        nentries = 6000,
        kind     ='s+b', 
        suffix   = 'mm')

    nll_ee = get_nll(
        nentries = 2000,
        kind     ='s+b', 
        suffix   = 'ee')

    minimizer = zfit.minimize.Minuit()
    obj       = minimizer.minimize(loss=nll_mm + nll_ee)
    obj.hesse(name = 'minuit_hesse')
    res = FitResult.from_zfit(res = obj)

    data = gut.load_data(
        package='fitter_data', 
        fpath  ='tests/toys/toy_maker.yaml')
    data['ntoys'] = ntoys
    cfg = ToyConf(**data)
    obj = ChannelHolder(ee = nll_ee, mm = nll_mm)

    scal = SystematicsCalculator(
        poi = 'nsig_ee',
        obj = obj, 
        res = res, 
        cfg = cfg) 

    scal.switch_model(
        model = None, 
        label = 'nominal')

    alt_model_ee = get_model(kind = 's_alt+b', suffix = 'ee')
    scal.switch_model(
        model   = alt_model_ee, 
        channel = 'ee',
        label   = 'alt_sig_ee')

    alt_model_mm = get_model(kind = 's_alt+b', suffix = 'mm')
    scal.switch_model(
        model   = alt_model_mm, 
        channel = 'mm',
        label   = 'alt_sig_mm')
# ----------------------
@pytest.mark.parametrize('ntoys', [10])
def test_sim_parameter_fixing(
    monkeypatch,
    tmp_path : Path,
    ntoys    : int | None) -> None:
    '''
    Test fixing one parameter after another with 
    simultaneous fits

    Parameters
    -------------
    tmp_path : Where output plots will go
    ntoys    : Number of toys to override what is in config
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    log.info('')
    nll_mm    = get_nll(kind='s+b', suffix = 'mm')
    nll_ee    = get_nll(kind='s+b', suffix = 'ee')

    data          = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    data['rseed'] = 123
    if ntoys is not None:
        data['ntoys'] = ntoys

    cfg       = ToyConf(**data)
    minimizer = zfit.minimize.Minuit()
    obj       = minimizer.minimize(loss = nll_mm + nll_ee)
    obj.hesse(name = 'minuit_hesse')
    res = FitResult.from_zfit(res = obj)

    POI : Final[str] = 'nsig_ee'
    scal = SystematicsCalculator(
        poi = POI,
        obj = ChannelHolder(ee = nll_ee, mm = nll_mm), 
        res = res, 
        cfg = cfg) 

    npars = len(scal.parameters)
    nrows = cfg.ntoys * npars
    index = 1
    for par in scal.parameters.values():
        if par.name == scal.poi:
            continue

        df = scal.fix_parameter(
            name  = par.name,
            label = f'fix_{par.name}')

        size = len(df)
        df_nsig = df.query(f'Parameter == \"{POI}\"')

        assert len(df_nsig['Gen'].unique()) == 1
        assert size == nrows - index * cfg.ntoys 
        assert isinstance(df, pnd.DataFrame)
        assert len(df) > 0

        index += 1
# ----------------------
