'''
Module with functions intended to test SystematicsCalculator
'''

import zfit
import pytest
import pandas as pnd

from typing        import Final, Literal
from pathlib       import Path
from zfit.loss     import ExtendedUnbinnedNLL

from dmu           import LogStore
from dmu.stats     import Constraints
from dmu.stats     import FitResult
from dmu.testing   import get_nll
from dmu.generic   import rxran
from dmu.generic   import utilities as gut

from fitter        import ToyConf
from systematics   import SystematicsCalculator

log = LogStore.add_logger('rx_stats:test_systematics_calculator')
type zlos = ExtendedUnbinnedNLL

_COLUMNS : Final[list[str]] = ['Parameter', 'Value', 'Error', 'Gen', 'Toy', 'GOF', 'Valid', 'Hash']
'''Columns needed in dataframe holding toys information'''
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
def _get_nll_sim(nentries : int, alt : Literal['ee','mm','none']) -> tuple[zlos, FitResult]:
    '''
    nentries: Size of dataset in NLL
    alt     : Channel for which model is alternative
    '''
    kind_mm = 's_alt+b' if alt == 'mm' else 's+b' 
    kind_ee = 's_alt+b' if alt == 'ee' else 's+b' 

    nll_ee = get_nll(
        nentries = nentries,
        kind     = kind_ee, 
        suffix   = 'ee')

    nll_mm = get_nll(
        nentries = nentries,
        kind     = kind_mm, 
        suffix   = 'mm')

    nll       = nll_mm + nll_ee
    minimizer = zfit.minimize.Minuit()
    obj       = minimizer.minimize(loss=nll)
    obj.hesse(name = 'minuit_hesse', method = 'minuit_hesse')

    res = FitResult.from_zfit(res = obj)

    return nll, res
# ----------------------
@pytest.mark.parametrize('ntoys', [10])
def test_bootstrap(
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

    nll  = get_nll(kind='skde+b', suffix = '')
    data = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    if ntoys is not None:
        data['ntoys'] = ntoys
    cfg  = ToyConf(**data)

    minimizer = zfit.minimize.Minuit()
    res       = minimizer.minimize(loss = nll)
    res.hesse(
        name   = 'minuit_hesse', 
        method = 'minuit_hesse')
    res  = FitResult.from_zfit(res = res)

    cns  = Constraints.none()
    scal = SystematicsCalculator(
        poi = 'nsig',
        nll = nll, 
        cns = cns,
        res = res, 
        cfg = cfg) 

    df_bts  = scal.bootstrap(
        nboot = 10,
        model = 'signal_kde',
        label = 'bootstrap')

    assert df_bts.columns.to_list() == _COLUMNS
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

    nll_nom = get_nll(kind='s+b', suffix = '')
    nll_alt = get_nll(kind='s_alt+b', suffix = '')

    cns_nom = Constraints.none()
    cns_alt = Constraints.none()

    minimizer = zfit.minimize.Minuit()

    res_nom   = minimizer.minimize(loss = nll_nom)
    res_nom.hesse(name = 'minuit_hesse', method = 'minuit_hesse')
    res_nom   = FitResult.from_zfit(res = res_nom)

    res_alt   = minimizer.minimize(loss = nll_alt)
    res_alt.hesse(name = 'minuit_hesse', method = 'minuit_hesse')
    res_alt   = FitResult.from_zfit(res = res_alt)

    data = gut.load_data(package='fitter_data', fpath='tests/toys/toy_maker.yaml')
    if ntoys is not None:
        data['ntoys'] = ntoys

    cfg  = ToyConf(**data)
    scal = SystematicsCalculator(
        poi = 'nsig',
        nll = nll_nom, 
        res = res_nom, 
        cns = cns_nom,
        cfg = cfg) 

    df_alt  = scal.switch_model(
        nll   = nll_alt, 
        res   = res_alt, 
        cns   = cns_alt,
        label = 'alt_signal')

    assert df_alt.columns.to_list() == _COLUMNS
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
    nll = get_nll(kind='s_alt+b', nentries = 10_000)
    cns = Constraints.none()

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
        nll = nll, 
        cns = cns,
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

    nll_nom   , res_nom    = _get_nll_sim(nentries = 6000, alt = 'none')
    nll_alt_ee, res_alt_ee = _get_nll_sim(nentries = 6000, alt = 'ee'  )
    nll_alt_mm, res_alt_mm = _get_nll_sim(nentries = 6000, alt = 'mm'  )

    data = gut.load_data(
        package='fitter_data', 
        fpath  ='tests/toys/toy_maker.yaml')
    data['ntoys'] = ntoys
    cfg = ToyConf(**data)

    cns  = Constraints.none()
    scal = SystematicsCalculator(
        poi = 'nsig_ee',
        nll = nll_nom, 
        cns = cns,
        res = res_nom, 
        cfg = cfg) 

    scal.make_toys()

    scal.switch_model(
        nll     = nll_alt_ee,
        cns     = cns,
        res     = res_alt_ee,
        label   = 'alt_sig_ee')

    scal.switch_model(
        nll     = nll_alt_mm,
        cns     = cns,
        res     = res_alt_mm,
        label   = 'alt_sig_mm')
# ----------------------
