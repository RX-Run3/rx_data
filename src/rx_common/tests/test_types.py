'''
Script with functions meant to test Enums
'''
import pytest

from functools import reduce
from operator  import add

from dmu       import LogStore
from rx_common import Correction
from rx_common import Component
from rx_common import Brem
from rx_common import Channel
from rx_common import Trigger
from rx_common import Project

log=LogStore.add_logger('rx_common::test_types')
# -------------------------------------------
@pytest.mark.parametrize('corr', Correction)
def test_correction(corr : Correction):
    '''
    Tests Correction type
    '''
    assert isinstance(corr.latex, str)
    assert corr.kind in {'reso', 'scale', 'weight'}
# -------------------------------------------
def test_brem():
    '''
    Test for Enum representing brem
    '''
    assert str(Brem.zero) == 'brem_xx0'
    assert str(Brem.one)  == 'brem_xx1'
    assert str(Brem.two)  == 'brem_xx2'

    assert Brem.zero + Brem.one == Brem.br01x
    assert Brem.zero + Brem.two == Brem.br0x2
    assert Brem.one  + Brem.two == Brem.brx12

    assert Brem.zero + Brem.one + Brem.two == Brem.br012

    brems : list[Brem]

    with pytest.raises(TypeError):
        brems = []
        total = reduce(add, brems)

    brems = [Brem.one]
    total = reduce(add, brems)
    assert total == Brem.one

    brems = [Brem.one, Brem.two]
    total = reduce(add, brems)
    assert total == Brem.brx12

    brems = [Brem.zero, Brem.one, Brem.two]
    total = reduce(add, brems)
    assert total == Brem.br012
# -------------------------------------------
@pytest.mark.parametrize('sample', Component)
def test_channel(sample : Component):
    '''
    Tests channel property of samples
    '''
    if   sample.name.endswith('ee'):
        expected = Channel.ee
    elif sample.name.endswith('mm'):
        expected = Channel.mm
    else:
        expected = None

    if expected is not None:
        assert sample.channel == expected
        return
# -------------------------------------------
@pytest.mark.parametrize('trigger', Trigger)
def test_trigger(trigger : Trigger):
    '''
    Test trigger enum
    '''

    if   trigger.name.endswith('nopid') and trigger.name.startswith('rk_'):
        expected = Project.rk_no_pid
    elif trigger.name.endswith('nopid') and trigger.name.startswith('rkst_'):
        expected = Project.rkst_no_pid
    elif trigger.name.startswith('rk_'):
        expected = Project.rk
    elif trigger.name.startswith('rkst_'):
        expected = Project.rkst
    else:
        expected = None

    if expected is not None:
        assert trigger.project == expected
# -------------------------------------------

