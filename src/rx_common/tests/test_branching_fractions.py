'''
Module with tests for Branching fractions
'''
from typing import Final

import pytest

from rx_common import BranchingFraction
from rx_common import Component
from dmu       import LogLevels, LogStore

log=LogStore.add_logger('rx_common:test_branching_fraction')

_COMPONENTS : Final[list[Component]] = [
    Component.bpkpee,
    Component.bpkpjpsiee,
    Component.bdkstkpiee,
    Component.bdkstkpijpsiee]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_common:branching_fraction', LogLevels.debug)
# ----------------------
@pytest.mark.parametrize('comp', _COMPONENTS)
def test_simple(comp : Component):
    BranchingFraction.from_decays(
        decays = comp.subdecays,
        latex  = comp.latex)
