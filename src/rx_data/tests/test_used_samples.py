'''
Module with tests for UsedSamples
'''
import pytest

from rx_common import Project
from rx_data   import UsedSamples
from dmu       import LogStore

log = LogStore.add_logger('rx_data:test_used_samples')
# -------------------------------------
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
def test_simple(project : Project):
    '''
    Simplest test
    '''
    obj = UsedSamples.from_project(project = project)

    assert len(obj.identifiers) > 0

    for elm in obj.identifiers:
        log.info(elm)
# -------------------------------------

