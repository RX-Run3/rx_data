'''
Script used to test Q2SmearCorrector class
'''

import numpy
import pytest
import pandas            as pnd
import matplotlib.pyplot as plt

from functools             import lru_cache
from typing                import Final
from ROOT                  import RDF # type: ignore
from pathlib               import Path
from dmu.logging.log_store import LogStore
from rx_common             import Channel
from rx_q2                 import Q2SmearCorrector

log  = LogStore.add_logger('rx_q2:test_q2smear_corrector')

_CHANNELS : Final[list[Channel]] = [Channel.ee, Channel.mm]
_NENTRIES : Final[int] = 10_000
# -------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('fitter:scale_reader'         , 10)
    LogStore.set_level('rx_q2:q2smear_corrector'     , 10)
    LogStore.set_level('rx_q2:test_q2smear_corrector', 10)
# -------------------------------------------
def _plot_masses(
    rdf      : RDF.RNode,
    is_data  : bool,
    particle : str,
    dir_path : Path) -> None:
    log.info('Plotting')

    data     = rdf.AsNumpy()
    arr_reco = data[f'{particle}_Mass'    ]
    arr_smr  = data[f'{particle}_Mass_smr']

    rng = {'B' : (5000, 6000), 'Jpsi' : (2000, 3500)}[particle]

    if is_data:
        assert numpy.isclose(arr_reco, arr_smr).all()

    plt.hist(arr_reco, range=rng, bins=60, alpha=0.3      , label = 'Raw'    )
    plt.hist(arr_smr , range=rng, bins=60, histtype='step', label = 'Smeared')

    dir_path.mkdir(exist_ok=True, parents=True)
    plt.legend()
    plt.savefig(dir_path / f'{particle}.png')
    plt.close()
# -------------------------------------------
def _plot_df_masses(
    df       : pnd.DataFrame,
    is_data  : bool,
    particle : str,
    dir_path : Path) -> None:
    log.info('Plotting')

    arr_reco = df[f'{particle}_Mass'    ].to_numpy()
    arr_smr  = df[f'{particle}_Mass_smr'].to_numpy()

    rng = {'B' : (5000, 6000), 'Jpsi' : (2000, 3500)}[particle]

    if is_data:
        assert numpy.isclose(arr_reco, arr_smr).all()

    plt.hist(arr_reco, range=rng, bins=60, alpha=0.3      , label = 'Raw'    )
    plt.hist(arr_smr , range=rng, bins=60, histtype='step', label = 'Smeared')

    dir_path.mkdir(exist_ok=True, parents=True)
    plt.legend()
    plt.savefig(dir_path / f'{particle}.png')
    plt.close()
# -------------------------------------------
@lru_cache(maxsize = 3)
def _get_df(
    uniform : bool,
    is_data : bool,
    channel : str) -> pnd.DataFrame:

    df = pnd.DataFrame()
    df['EVENTNUMBER'] = 1
    df['RUNNUMBER'  ] = 2

    rng = numpy.random.default_rng(seed = 42)

    if   channel == 'ee':
        df['nbrem'] = rng.choice([1, 2], _NENTRIES)
    elif channel == 'mm':
        df['nbrem'] = rng.choice([0]   , _NENTRIES)
    else:
        raise ValueError(f'Invalid channel: {channel}')

    df['block']    = rng.choice(range(1, 7) , _NENTRIES)

    df = _add_mass(df=df, rng = rng, particle='B'   , uniform=uniform)
    df = _add_mass(df=df, rng = rng, particle='Jpsi', uniform=uniform)

    if not is_data:
        df['B_TRUEID'   ] = 521
        df['Jpsi_TRUEID'] = 451
        df['B_TRUEM'    ] = 5280
        df['Jpsi_TRUEM' ] = 3096.9

    return df
# ----------------------
def _add_mass(
    df       : pnd.DataFrame,
    rng      : numpy.random.Generator,
    uniform  : bool,
    particle : str) -> pnd.DataFrame:
    '''
    Parameters
    -------------
    particle: Name of particle to add to dataframe, e.g Jpsi

    Returns
    -------------
    DataFrame with column added
    '''
    name = f'{particle}_Mass'

    if       uniform and particle == 'Jpsi':
        df[name] = rng.uniform(1800, 3700, _NENTRIES)
    elif not uniform and particle == 'Jpsi':
        df[name] = rng.normal(loc=3097, scale=100, size=_NENTRIES)
    elif     uniform and particle == 'B':
        df[name] = rng.uniform(5000, 6000, _NENTRIES)
    elif not uniform and particle == 'B':
        df[name] = rng.normal(loc=5280, scale=100, size=_NENTRIES)
    else:
        raise ValueError(f'Invalid particle: {particle}')

    return df
# ----------------------
def _check_columns(rdf : RDF.RNode) -> None:
    '''
    Parameters
    -------------
    rdf: Dataframe
    '''
    s_col  = { name.c_str() for name in rdf.GetColumnNames() }

    fail = False
    for col in ['EVENTNUMBER', 'RUNNUMBER', 'Jpsi_Mass_smr', 'B_Mass_smr', 'q2_smr']:
        if col in s_col:
            continue

        fail = True
        log.error(f'Missing column: {col}')

    assert not fail
# ----------------------
def _check_rdf(rdf : RDF.RNode) -> None:
    '''
    Parameters
    -------------
    rdf: DataFrame after correction
    '''

    _check_columns(rdf=rdf)

    data   = rdf.AsNumpy()
    arr_q2 = data['q2_smr']
    arr_jp = data['Jpsi_Mass_smr']

    assert numpy.isclose(arr_q2, arr_jp ** 2, atol=1).all()
# -------------------------------------------
@pytest.mark.parametrize('is_uniform', [False])
@pytest.mark.parametrize('channel'   , [Channel.ee])
@pytest.mark.parametrize('is_data'   , [False])
def test_get_rdf(
    is_uniform : bool,
    channel    : Channel,
    is_data    : bool,
    tmp_path   : Path):
    '''
    Run using ROOT data frame input
    '''
    df  = _get_df(
        uniform = is_uniform,
        channel = channel,
        is_data = is_data)
    rdf = RDF.FromPandas(df)

    obj = Q2SmearCorrector(channel=channel, add_original=True)
    rdf = obj.get_rdf(rdf=rdf)

    _check_rdf(rdf=rdf)

    sample = 'data' if is_data else 'simulation'

    _plot_masses(rdf=rdf, is_data = is_data, particle='B'   , dir_path=tmp_path / sample)
    _plot_masses(rdf=rdf, is_data = is_data, particle='Jpsi', dir_path=tmp_path / sample)
# -------------------------------------------
@pytest.mark.parametrize('is_uniform', [False])
@pytest.mark.parametrize('channel'   , [Channel.ee])
@pytest.mark.parametrize('is_data'   , [False])
def test_get_df(
    is_uniform : bool,
    channel    : Channel,
    is_data    : bool,
    tmp_path   : Path):
    '''
    Run using pandas data frame input
    '''
    df  = _get_df(
        uniform = is_uniform,
        channel = channel,
        is_data = is_data)

    obj = Q2SmearCorrector(channel=channel, add_original=True)
    df  = obj.get_df(df=df)

    sample = 'data' if is_data else 'simulation'

    _plot_df_masses(
        df      = df,
        is_data = is_data,
        particle='B',
        dir_path=tmp_path / sample)

    _plot_df_masses(
        df      = df,
        is_data = is_data,
        particle='Jpsi',
        dir_path=tmp_path / sample)
# -------------------------------------------
