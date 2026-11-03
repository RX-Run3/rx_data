'''
Script holding functions needed to test SampleWeighter class
'''
import os

import pickle
import numpy
import pytest
import pandas            as pnd

from functools       import cache, lru_cache
from boost_histogram import Histogram
from dmu             import LogStore
from dmu.generic     import utilities      as gut
from rx_misid        import SampleWeighter
from rx_misid.types import MisIDSampleWeights

log=LogStore.add_logger('rx_misid:test_weighter')
# -------------------------------------------------------
class Data:
    '''
    Data class
    '''
    user     = os.environ['USER']
    nentries = 5_000

    l_block = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8]
# -------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    numpy.random.seed(42)
    LogStore.set_level('rx_misid:sample_weighter', 10)
# -------------------------------------------------------
@lru_cache(maxsize=100)
def _get_dataframe(
    sample           : str,
    block            : int,
    good_phase_space : bool = True) -> pnd.DataFrame:

    df = pnd.DataFrame(index=range(Data.nentries))

    if 'DATA' in sample:
        particles = ['kaon', 'pion']
    elif sample == 'Bu_KplKplKmn_eq_sqDalitz_DPC':
        particles = ['kaon']
    elif sample == 'Bu_piplpimnKpl_eq_sqDalitz_DPC':
        particles = ['pion']
    else:
        raise ValueError(f'Invalid sample: {sample}')

    df['block' ]      = block
    df['hadron']      = numpy.random.choice(particles   , size=Data.nentries)
    df['weight']      = numpy.random.choice([1, 10]     , size=Data.nentries)
    df['L1_HASBREM' ] = numpy.random.choice(a = [0, 1], p = [0.5, 0.5], size = Data.nentries)
    df['L2_HASBREM' ] = numpy.random.choice(a = [0, 1], p = [0.5, 0.5], size = Data.nentries)
    df['L1_ProbNNe'] = numpy.random.random(size=Data.nentries)
    df['L2_ProbNNe'] = numpy.random.random(size=Data.nentries)
    df['L1_PIDe'   ] = numpy.random.uniform(-10, 10, size=Data.nentries)
    df['L2_PIDe'   ] = numpy.random.uniform(-10, 10, size=Data.nentries)

    for lep in ['L1', 'L2']:
        df[f'{lep}_TRACK_PT' ] = 10 ** numpy.random.uniform(2, 5, Data.nentries)
        df[f'{lep}_TRACK_ETA'] = numpy.random.uniform(2.0,     5.5, Data.nentries)

    if not good_phase_space:
        return df

    df = df[ df['L1_TRACK_PT'] < (30_000 - 5_000 * df['L1_TRACK_ETA']) ]
    df = df[ df['L2_TRACK_PT'] < (30_000 - 5_000 * df['L2_TRACK_ETA']) ]

    df = df[ df['L1_TRACK_PT'] > ( 8_000 - 2_000 * df['L1_TRACK_ETA']) ]
    df = df[ df['L2_TRACK_PT'] > ( 8_000 - 2_000 * df['L2_TRACK_ETA']) ]

    return df
# ----------------------
def _check_weights(df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    df: Pandas dataframe to be checked
    '''

    assert 'pid_weights' in df.columns
    assert 'pid_eff_l1'  in df.columns
    assert 'pid_eff_l2'  in df.columns

    arr_wgt_tot = df['pid_weights'].to_numpy().astype(float)
    arr_wgt_l1  = df['pid_eff_l1' ].to_numpy().astype(float)
    arr_wgt_l2  = df['pid_eff_l2' ].to_numpy().astype(float)

    assert numpy.isclose(arr_wgt_tot, arr_wgt_l1 * arr_wgt_l2, rtol=1e-5).all()
# ----------------------
def _check_blocks(
    df            : pnd.DataFrame,
    arr_block_inp : numpy.ndarray) -> None:
    '''
    Parameters
    -------------
    df           : DataFrame to check
    arr_block_inp: Array of blocks in the input data
    '''
    arr_block_out = df['block'].to_numpy()

    # Check that no shuffling of entries happened, using
    # array of block numbers
    assert numpy.array_equal(arr_block_inp, arr_block_out)
# ----------------------
def _closure_check(
    df     : pnd.DataFrame,
    sample : str,
    block  : int,
    is_sig : bool) -> None:
    '''
    Parameters
    -------------
    df    : Dataframe with weighted data
    sample: MC sample
    is_sig: If true, will read the signal region maps
    '''
    for has_brem in [0, 1]:
        pidc = _get_pidc_map(has_brem=has_brem, block=block, sample=sample, is_sig=is_sig)
        if pidc is None:
            continue

        hist = _build_map(df=df, has_brem=has_brem, block=block)

        _check_maps(hist_calc=hist, hist_pidc=pidc)
# ----------------------
def _get_pidc_map(
    has_brem : int,
    block    : int,
    sample   : str,
    is_sig   : bool) -> numpy.ndarray|None:
    '''
    Parameters
    -------------
    has_brem: If 1 will build map from tracks with brem only
    sample  : MC sample
    is_sig  : If true, will read the signal region maps

    Returns
    -------------
    Calibration map from PIDCalib as numpy array
    '''
    if   sample == 'Bu_KplKplKmn_eq_sqDalitz_DPC':
        particle = 'K'
        cut      = '(PROBNN_E>0.2)&(DLLe>3.0)' if is_sig else '((PROBNN_E<0.2)|(DLLe<3.0))&(DLLe>-1.0)&(K_PROBNN_K>0.1)'
    elif sample == 'Bu_piplpimnKpl_eq_sqDalitz_DPC':
        particle = 'Pi'
        cut      = '(PROBNN_E>0.2)&(DLLe>3.0)' if is_sig else '((PROBNN_E<0.2)|(DLLe<3.0))&(DLLe>-1.0)&(pi_PROBNN_K<0.1)'
    else:
        return

    particle_cut = particle.lower() if particle == 'Pi' else particle
    polarity     = 'down' if block in [6, 7] else 'up'

    brem_name = {1 : 'brem', 0 : 'nobrem'}[has_brem]
    ana_dir   = os.environ['ANADIR']
    map_name  = f'effhists-2024_WithUT_block{block}_v2-{polarity}-{particle}-{cut}-log10({particle_cut}_PT).{particle_cut}_ETA.pkl'
    fpath     = f'{ana_dir}/Calibration/mis_id/v14/{brem_name}/{map_name}'
    with open(fpath, 'rb') as ifile:
        mapping = pickle.load(ifile)

    arr = mapping.values()
    arr = numpy.where(numpy.isnan(arr), 0, arr)
    arr = numpy.where(arr          > 1, 1, arr)

    return arr
# ----------------------
def _check_maps(
    hist_calc : numpy.ndarray,
    hist_pidc : numpy.ndarray) -> None:
    '''
    Parameters
    -------------
    hist_calc: Efficiency map calculated from weighted data
    hist_pidc: Efficiency map from PIDCalib
    '''
    hist_diff = hist_pidc - hist_calc
    hist_diff = numpy.where(hist_diff < 1e-7, 0, hist_diff)

    assert numpy.isclose(0, hist_diff, rtol=1e-6).all()
# ----------------------
def _build_map(df : pnd.DataFrame, has_brem : int, block : int) -> numpy.ndarray:
    '''
    Parameters
    -------------
    df      : DataFrame with weights
    has_brem: If 1 will build map from tracks with brem only
    block   : Block from which map comes

    Returns
    -------------
    Efficiency map
    '''
    df           = df[ df['block'     ] == block    ]
    df_1         = df[ df['L1_HASBREM'] == has_brem ]
    df_2         = df[ df['L2_HASBREM'] == has_brem ]

    arr_pid_eff1 = df_1['pid_eff_l1'  ].to_numpy()
    arr_pid_eff2 = df_2['pid_eff_l2'  ].to_numpy()
    arr_pt_l1    = df_1['L1_TRACK_PT' ].to_numpy()
    arr_pt_l2    = df_2['L2_TRACK_PT' ].to_numpy()
    arr_et_l1    = df_1['L1_TRACK_ETA'].to_numpy()
    arr_et_l2    = df_2['L2_TRACK_ETA'].to_numpy()

    arr_eff      = numpy.concatenate((arr_pid_eff1, arr_pid_eff2)).astype(float)
    arr_et       = numpy.concatenate((arr_et_l1   , arr_et_l2   ))
    arr_pt       = numpy.concatenate((arr_pt_l1   , arr_pt_l2   ))
    arr_pt       = numpy.log10(arr_pt)

    l_xedge, l_yedge = _get_binning()
    arr_xedge = numpy.array(l_xedge)
    arr_yedge = numpy.array(l_yedge)

    eff_wgt, _, _ = numpy.histogram2d(arr_pt, arr_et, bins=[arr_xedge, arr_yedge], weights=arr_eff)
    eff_raw, _, _ = numpy.histogram2d(arr_pt, arr_et, bins=[arr_xedge, arr_yedge], weights=None   )

    return numpy.where(eff_raw > 0, eff_wgt / eff_raw, 0)
# ----------------------
@cache
def _get_binning() -> tuple[list[float], list[float]]:
    '''
    Returns
    -------------
    Tuple with two lists of floats, representing boundaries used to make
    calibration maps
    '''
    data    = gut.load_conf(package='rx_pid_data', fpath='config/binning.yaml')
    l_xedge = data['bin']['log10(PARTICLE_TRACK_PT)']
    l_yedge = data['bin']['PARTICLE_TRACK_ETA']

    return l_xedge, l_yedge
# ----------------------------
@pytest.mark.parametrize('block' , [1, 2, 3, 5, 6, 7, 8])
@pytest.mark.parametrize('is_sig', [True, False])
@pytest.mark.parametrize('sample', [
    'Bu_KplKplKmn_eq_sqDalitz_DPC',
    'Bu_piplpimnKpl_eq_sqDalitz_DPC'])
def test_simple(
    is_sig : bool,
    sample : str,
    block  : int):
    '''
    Parameters
    -------------
    is_sig: If true, it will weight sample to put it in the signal region
            Otherwise it will go to control region
    sample: MC and data samples need to be weighted in different ways
    block : Number from 1 to 8
    '''
    data= gut.load_data(package='rx_misid_data', fpath='weights.yaml')
    cfg = MisIDSampleWeights(**data)

    df  = _get_dataframe(good_phase_space=False, sample=sample, block=block)
    arr_block_inp = df['block'].to_numpy().astype(float)

    wgt = SampleWeighter(
        df    = df,
        cfg   = cfg,
        sample= sample,
        is_sig= is_sig)
    df  = wgt.get_weighted_data()

    _check_blocks(df=df, arr_block_inp=arr_block_inp)
    _check_weights(df=df)
    _closure_check(df=df, is_sig=is_sig, sample=sample, block=block)
# ----------------------------
def test_get_maps():
    '''
    Test of get_maps method
    '''
    data  = gut.load_data(package='rx_misid_data', fpath='weights.yaml')
    cfg   = MisIDSampleWeights(**data)

    d_map = SampleWeighter.get_maps(cfg=cfg, kind='brem')

    assert len(d_map) == 32
    for hist in d_map.values():
        assert isinstance(hist, Histogram)
