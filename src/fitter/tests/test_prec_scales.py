'''
Module used to test PrecScales class
'''

import numpy
import pytest

from typing        import Any, Final
from pathlib       import Path
from rx_common     import Brem, Component, Qsq, Cuts
from rx_selection  import selection  as sel
from fitter        import PrecScales

from dmu           import LogStore
from dmu.workflow  import Cache

log=LogStore.add_logger('fitter:test_prec_scales')

NSCALES : Final[int] = 2
# -----------------------------------
@staticmethod
def _get_seq_wp(min_cmb : float, min_prc : float, step : float) -> list[str]:
    '''
    Will take starting point for both combinatorial and PRec WP, as well as step
    Will tighten one at a time and return list of cuts
    '''
    l_wp = []
    wp_cmb_str = '(1)'
    wp_prc_str = f'mva_prc > {min_prc:.3f}'
    for wp_cmb in numpy.arange(min_cmb, 1, step):
        wp_cmb_str = f'mva_cmb > {wp_cmb:.3f}'
        wp_str     = f'({wp_cmb_str}) && ({wp_prc_str})'
        l_wp.append(wp_str)

    for wp_prc in numpy.arange(min_prc, 1, step):
        wp_prc_str = f'mva_prc > {wp_prc:.3f}'
        wp_str     = f'({wp_cmb_str}) && ({wp_prc_str})'
        l_wp.append(wp_str)

    return l_wp
# -----------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This is called before any test
    '''
    LogStore.set_level('rx_fitter:prec_scales', 10)
    LogStore.set_level('rx_efficiencies:efficiency_calculator', 10)
# ----------------------
def _validate_scales(scales : Any) -> None:
    '''
    Validates prec scale and error
    '''
    assert len(scales) == NSCALES
    val, err = scales

    assert isinstance(val, float)
    assert isinstance(err, float)
#-------------------------------
@pytest.mark.parametrize('q2bin'    , [
    Qsq.low, 
    Qsq.central, 
    Qsq.high])
@pytest.mark.parametrize('component', [
    Component.bdkstkpiee, 
    Component.bpkstkpiee,
    Component.bsphiee])
@pytest.mark.parametrize('brem', [ Brem.one, Brem.two, Brem.brx12 ])
def test_all_datasets(
    q2bin    : Qsq, 
    brem     : Brem,
    component: Component, 
    tmp_path : Path):
    '''
    Tests retrieval of scales between signal and PRec yields
    '''
    signal   = Component.bpkpee
    with Cache.cache_root(path = tmp_path):
        obj    = PrecScales(
            output_directory= tmp_path,
            brem            = brem,
            comp            = component, 
            q2bin           = q2bin)

        scales = obj.get_scale(signal=signal)

    _validate_scales(scales = scales)
#-------------------------------
@pytest.mark.parametrize('q2bin'    , [
    Qsq.low, 
    Qsq.central, 
    Qsq.high])
@pytest.mark.parametrize('component', [
    Component.bdkstkpiee, 
    Component.bpkstkpiee,
    Component.bsphiee])
@pytest.mark.parametrize('mva_cut', _get_seq_wp(min_cmb=0.9, min_prc=0.9, step=0.1))
@pytest.mark.parametrize('brem', [ Brem.one, Brem.two, Brem.brx12 ])
def test_seq_scan_scales(
    mva_cut   : str, 
    q2bin     : Qsq, 
    brem      : Brem,
    component : Component,
    tmp_path  : Path) -> None:
    '''
    Tests retrieval of scales between signal and PRec yields, by cutting first on combinatorial and then on PRec
    '''
    signal = Component.bpkpee
    with sel.custom_selection(d_sel={Cuts.cmb : mva_cut}),\
         Cache.cache_root(path = tmp_path):
        obj    = PrecScales(
            output_directory= tmp_path,
            comp            = component, 
            brem            = brem,
            q2bin           = q2bin)
        scales = obj.get_scale(signal=signal)

    _validate_scales(scales = scales)
#-------------------------------
