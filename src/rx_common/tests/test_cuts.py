'''
File with tests for Cuts enum
'''
import pytest

from rx_common import Cuts

@pytest.mark.parametrize('value', Cuts)
def test_types(value : Cuts):
    '''
    Test that values are strings
    '''
    isinstance(value, str)

def test_save():
    '''
    Test printing
    '''
    obj = {Cuts.mass : 'mass > 0', Cuts.pid_l : 'pid_e > 3'}

    print(obj)
