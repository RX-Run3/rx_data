'''
This module has functions to test the NtuplePartitioner class
'''
import pytest
from rx_common import Project
from rx_data   import NtuplePartitioner

_FRIENDS=[
    'main',
    'mva',
    'hop',
    'mass',
    'brem_track_2',
    'swp_jpsi_misid',
    'swp_cascade']

_TOTAL=3

@pytest.mark.parametrize('friend', _FRIENDS)
@pytest.mark.parametrize('index' , range(_TOTAL))
def test_all_friends(friend : str, index : int):
    '''
    Test that can access all paths
    '''
    prt   = NtuplePartitioner(kind = friend, project = Project.rk)
    paths = prt.get_paths(index=index, total=_TOTAL)

    assert isinstance(paths, list)
    assert paths

    for path in paths:
        assert path.exists()
