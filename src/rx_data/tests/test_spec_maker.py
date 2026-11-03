'''
Module with tests for SpecMaker class
'''
import pytest

from typing    import Final
from dmu       import LogStore
from rx_common import Component, Project, Trigger
from rx_data   import SpecMaker

_LATEST_MVA_TREE : Final[str] = 'v9'

_NOPIDSAMPLES=[
    Component.bpkkk,
    Component.bpkpipi,
]

# These samples need minimal patching/emulation, etc
_GOODSAMPLES=[
    (Component.bpkpjpsiee, Trigger.rk_ee_os),
    (Component.bpkpjpsimm, Trigger.rk_mm_os),
    (Component.bdkstkpiee, Trigger.rkst_ee_os),
    (Component.bdkstkpimm, Trigger.rkst_mm_os),
]

_PATCHING_SAMPLES = [
    (Component.bpjpsixmm, Trigger.rk_mm_os),
    (Component.bsjpsixmm, Trigger.rk_mm_os),
]

_INCLUSIVE_SAMPLES = [
    (Component.bpjpsixee, Trigger.rk_ee_os),
    (Component.bdjpsixee, Trigger.rk_ee_os),
    (Component.bsjpsixee, Trigger.rk_ee_os),
    # ----------
    (Component.bpjpsixmm, Trigger.rk_mm_os),
    (Component.bdjpsixmm, Trigger.rk_mm_os),
    (Component.bsjpsixmm, Trigger.rk_mm_os),
]

log=LogStore.add_logger('rx_data:test_spec_maker')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:spec_maker'     , 10)
    LogStore.set_level('rx_data:sample_emulator', 10)
    LogStore.set_level('rx_data:sample_patcher' , 10)
# ------------------------------------------------------
@pytest.mark.parametrize('component, trigger', _PATCHING_SAMPLES)
def test_patching(
    component : Component,
    trigger   : Trigger) -> None:
    '''
    Return path to specification of combined sample
    '''
    mkr  = SpecMaker(
        component = component,
        trigger   = trigger)
    path = mkr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _INCLUSIVE_SAMPLES)
def test_inclusive(sample : Component, trigger : Trigger) -> None:
    '''
    Test ccbar samples
    '''
    mkr  = SpecMaker(component=sample, trigger=trigger)
    path = mkr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _PATCHING_SAMPLES)
def test_skip_patching(sample : Component, trigger : Trigger) -> None:
    '''
    Disable patching
    '''
    with SpecMaker.skip_patching(val = True):
        mkr  = SpecMaker(component=sample, trigger=trigger)
        path = mkr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _GOODSAMPLES)
def test_combined(sample : Component, trigger : Trigger) -> None:
    '''
    Return path to specification of combined sample
    '''
    mkr  = SpecMaker(component=sample, trigger=trigger)
    path = mkr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------------
@pytest.mark.parametrize('sample, trigger', _GOODSAMPLES)
def test_per_file(sample : Component, trigger : Trigger) -> None:
    '''
    Return path to specification of combined sample
    '''
    mkr  = SpecMaker(component=sample, trigger=trigger)
    paths= mkr.get_spec_path(per_file=True)

    for root_path, config_path in paths.items():
        assert root_path.exists()
        assert config_path.exists()
# ------------------------------------------------
@pytest.mark.parametrize('friend' , ['mva', 'brem_track_2'])
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_exclude_friends(friend : str, sample : Component, trigger : Trigger):
    '''
    Tests excluding friend trees through a context manager
    '''
    with SpecMaker.exclude_friends(names=[friend]):
        gtr = SpecMaker(component=sample, trigger=trigger)
        path= gtr.get_spec_path(per_file=False)

    assert path.exists()

    assert friend not in gtr.spec.friends
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_custom_friend(sample : Component, trigger : Trigger):
    '''
    Tests getting data with a custom version for a given tree, either friend or main
    '''
    with SpecMaker.custom_friends(versions={'mva' : _LATEST_MVA_TREE}):
        gtr = SpecMaker(component=sample, trigger=trigger)
        path= gtr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_only_friends(sample : Component, trigger : Trigger):
    '''
    Tests getting data with a custom version for a given tree, either friend or main
    '''
    s_friend = {'mva', 'hop'}
    with SpecMaker.only_friends(s_friend=s_friend):
        gtr = SpecMaker(component=sample, trigger=trigger)
        path= gtr.get_spec_path(per_file=False)

    assert path.exists()
# ------------------------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rk_bad_ecal])
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os])
def test_project(sample : Component, trigger : Trigger, project : Project):
    '''
    Tests getting data with a custom version for a given tree, either friend or main
    '''
    if project == Project.rk_bad_ecal and trigger.is_muon:
        return

    with SpecMaker.project(project=project):
        gtr = SpecMaker(component=sample, trigger=trigger)
        path= gtr.get_spec_path(per_file=False)

    assert path.exists()
# ----------------------
@pytest.mark.parametrize('sample', _NOPIDSAMPLES)
def test_nopid_mc(sample : Component):
    '''
    Test specification building for noPID samples
    '''
    gtr = SpecMaker(component=sample, trigger=Trigger.rk_ee_nopid)
    path= gtr.get_spec_path(per_file=False)

    assert path.exists()

    log.info(f'Specification saved to: {path}')
# ----------------------
@pytest.mark.parametrize('sample', [Component.data_24])
def test_nopid_data(sample : Component):
    '''
    Test specification building for noPID samples
    '''
    gtr = SpecMaker(component=sample, trigger=Trigger.rk_ee_nopid)
    path= gtr.get_spec_path(per_file=False)

    assert path.exists()

    log.info(f'Specification saved to: {path}')
# ----------------------
