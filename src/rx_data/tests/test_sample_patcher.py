'''
Module with tests for SamplePatcher class
'''

import pytest

from dmu        import LogStore
from rx_common  import Component
from rx_common  import Trigger
from rx_data    import SamplePatcher
from rx_data    import SpecMaker

_UNPATCHED_SAMPLES = [
    (Component.data_24_md_c2, Trigger.rk_ee_os  ),
    (Component.data_24_md_c2, Trigger.rk_mm_os  ),
    (Component.data_24_md_c2, Trigger.rkst_ee_os),
    (Component.data_24_md_c2, Trigger.rkst_mm_os),
]
_PATCHED_SAMPLES = [
    (Component.bsjpsixmm , Trigger.rk_mm_os),
    (Component.bpjpsixmm , Trigger.rk_mm_os),
    (Component.bpkpmm    , Trigger.rk_mm_os),
    (Component.bpkpjpsiee, Trigger.rk_ee_os),
    (Component.bpkpee    , Trigger.rk_ee_nopid),
]

log=LogStore.add_logger('rx_data:test_sample_patching')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:sample_patcher', 10)
    LogStore.set_level('rx_data:spec_maker'    , 10)
    LogStore.set_level('rx_data:path_splitter' , 30)
    LogStore.set_level('rx_data:rdf_getter'    , 30)
# ----------------------
@pytest.mark.parametrize('component, trigger', _UNPATCHED_SAMPLES)
def test_unpatched(component : Component, trigger : Trigger) -> None:
    '''
    Tests that patching does not affect samples that are not
    meant to be patched
    '''
    with SpecMaker.skip_patching(val = True):
        spk  = SpecMaker(component=component, trigger=trigger)
        spec_old = spk.spec

    ptr  = SamplePatcher(sample = component, spec = spec_old)
    spec_new = ptr.get_patched_specification()

    assert spec_old == spec_new
    assert len(spec_new.ranges.root) == 0
# ----------------------
@pytest.mark.parametrize('component, trigger', _PATCHED_SAMPLES)
def test_patched(component : Component, trigger : Trigger) -> None:
    '''
    Tests that patching
    '''
    with SpecMaker.skip_patching(val = True):
        spk = SpecMaker(component=component, trigger=trigger)
        spec_old = spk.spec

    ptr = SamplePatcher(sample = component, spec = spec_old)
    spec_new = ptr.get_patched_specification()

    assert spec_old != spec_new
    assert len(spec_new.ranges.root) != 0
# ----------------------
