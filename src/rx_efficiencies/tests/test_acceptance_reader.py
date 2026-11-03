'''
Modules used to test AcceptanceReader class
'''

import pytest

from typing           import Final
from dmu              import LogStore
from rx_common        import Project, Component
from rx_efficiencies  import AcceptanceReader
from rx_efficiencies  import is_acceptance_defined

_COMPONENTS : Final[list[Component]] = [
    Component.bpkpmm,
    Component.bpkpee,
    Component.bpkpjpsimm,
    Component.bpkpjpsiee,
    # ----
    Component.bdkstkpimm,
    Component.bdkstkpiee,
    Component.bdkstkpijpsimm,
    Component.bdkstkpijpsiee,
    # ----
    Component.bsphiee,
    Component.bpk1kpipiee,
    Component.bpk2kpipiee,
    Component.bpkstkpiee,
]

log=LogStore.add_logger('rx_efficiencies:test_acceptance_reader')
#------------------------------------
@pytest.mark.parametrize('component', _COMPONENTS)
@pytest.mark.parametrize('year'     , ['2018', '2024'])
@pytest.mark.parametrize('project'  , [Project.rk, Project.rkst])
def test_simple(year : str, component : Component, project : Project):
    '''
    Test reading acceptances from JSON files for multiple processes and years
    '''
    if not is_acceptance_defined(sample = component, project = project):
        return

    obj=AcceptanceReader(
        year   =year,
        project=project,
        sample =component.sample)
    acc=obj.read()

    log.info(f'{year:<20}{component:<20}{acc:10.3f}')

    assert 0.1 < acc < 0.2
#------------------------------------
