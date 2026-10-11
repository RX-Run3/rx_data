'''
Module holding tests for EffScales class
'''
import pytest

from pathlib       import Path
from rx_common     import Component
from fitter        import EffScales
from rx_common     import Brem, Qsq
from rx_common     import Channel
from rx_common     import Project
from patch_classes import TestEfficiencyCalculator
from dmu.workflow  import Cache
from dmu           import LogStore
from dmu           import LogLevels

log=LogStore.add_logger('fitter:test_eff_scales')
# ----------------------
@pytest.fixture(autouse=True)
def initialize(
    request : pytest.FixtureRequest, 
    monkeypatch):
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:eff_scales', LogLevels.debug)

    if request.node.get_closest_marker('integration'):
        return

    monkeypatch.setattr(
        'fitter.eff_scales.EfficiencyCalculator',
        TestEfficiencyCalculator)
# ----------------------
def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    obj = EffScales(
        out_dir = tmp_path,
        sample  = Component.bdkstkpiee,
        channel = Channel.ee,
        source  = Project.rkst,
        target  = Project.rk,
        brem    = Brem.one,
        q2bin   = Qsq.central)

    val, err = obj.get_value()

    log.info(f'Value: {val:.3f}')
    log.info(f'Error: {err:.3f}')

    assert 0 < val < 1
    assert err < val
# ----------------------
@pytest.mark.integration
def test_real(tmp_path : Path):
    '''
    Run with real simulation, e.g full chain
    '''
    with Cache.cache_root(tmp_path):
        obj = EffScales(
            out_dir = tmp_path,
            sample  = Component.bdkstkpiee,
            channel = Channel.ee,
            source  = Project.rkst,
            target  = Project.rk,
            brem    = Brem.one,
            q2bin   = Qsq.central)

        val, err = obj.get_value()

        log.info(f'Value: {val:.3f}')
        log.info(f'Error: {err:.3f}')

        assert 0 < val < 1
        assert err < val
# ----------------------
