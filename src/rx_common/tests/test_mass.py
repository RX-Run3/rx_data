'''
Module holding tests for the Mass enum
'''

import pytest
from dmu.stats import zfit
from rx_common import Mass

@pytest.mark.parametrize('mass', Mass)
def test_simple(mass : Mass):
    '''
    Simplest test of mass Enum
    '''
    assert isinstance(mass.latex, str)

    lower, upper = mass.limits
    assert lower < upper

    isinstance(mass.obs, zfit.Space)
