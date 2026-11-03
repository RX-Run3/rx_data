'''
Module with functions needed to test EfficiencyCalculator class
'''
import pytest

from pathlib         import Path
from contextlib      import ExitStack
from dmu.workflow    import Cache
from dmu             import LogStore
from rx_common       import Cuts, Qsq, Trigger, Component
from rx_data         import RDFGetter
from rx_selection    import selection as sel
from rx_efficiencies import EfficiencyCalculator

_SAMPLES_RX    = [
    (Component.bpkpee    , Trigger.rk_ee_os),
    (Component.bpkpjpsiee, Trigger.rk_ee_os),
    (Component.bpkpmm    , Trigger.rk_mm_os),
    (Component.bpkpjpsimm, Trigger.rk_mm_os),
]

_SAMPLES_NOPID = [
    (Component.bpkpee    , Trigger.rk_ee_nopid),
    (Component.bpkpjpsiee, Trigger.rk_ee_nopid),
]

log = LogStore.add_logger('rx_efficiencies:test_efficiency_calculator')
#-------------------------------------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before tests
    '''
    LogStore.set_level('rx_efficiencies:efficiency_calculator', 10)
    LogStore.set_level('rx_data:rdf_getter'    , 10)
    LogStore.set_level('rx_data:spec_maker'    , 10)
    LogStore.set_level('rx_data:sample_patcher', 10)

    with RDFGetter.max_entries(value = 1000):
        yield
#-------------------------------------------------
@pytest.mark.parametrize('sample, trigger',       _SAMPLES_RX)
@pytest.mark.parametrize('q2bin' , [Qsq.low, Qsq.central, Qsq.high])
def test_rx_efficiency(
    q2bin   : Qsq,
    sample  : Component,
    trigger : Trigger,
    tmp_path: Path):
    '''
    Calculates efficiency over one sample at a time
    '''
    ctx_1 = Cache.cache_root(path = tmp_path)
    ctx_2 = sel.custom_selection(d_sel={Cuts.cmb : 'true'})

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        obj = EfficiencyCalculator(
            out_dir = tmp_path,
            q2bin   = q2bin,
            trigger = trigger,
            sample  = sample)

        eff, err = obj.get_efficiency()

    assert 0 <= eff < 1
    assert err > 0 or eff == 0
#-------------------------------------------------
@pytest.mark.parametrize('sample, trigger',    _SAMPLES_NOPID)
@pytest.mark.parametrize('q2bin' , [Qsq.low, Qsq.central, Qsq.high])
def test_nopid_efficiency(
    q2bin    : Qsq,
    sample   : Component,
    trigger  : Trigger,
    tmp_path : Path):
    '''
    Tests retrieval of total efficiency (acceptance x reco x selection)
    for RX project samples
    '''
    with Cache.cache_root(path = tmp_path),\
         sel.custom_selection(d_sel={Cuts.cmb : '(1)'}):
        obj      = EfficiencyCalculator(
            out_dir = tmp_path,
            q2bin   = q2bin,
            sample  = sample,
            trigger = trigger)
        eff, err = obj.get_efficiency()

    assert 0 <= eff < 1
    assert err > 0 or eff == 0
#-------------------------------------------------
