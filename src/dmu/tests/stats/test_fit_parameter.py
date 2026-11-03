'''
Module with tests for FitParameter class
'''
import pytest

from dmu.stats import FitParameter

def test_prod():
    '''
    Tests product of fit parameter objects
    '''
    par_1 = FitParameter(name='p1', value=10, error=2)
    par_2 = FitParameter(name='p2', value=20, error=1)
    par_3 = par_1 * par_2

    assert par_3.value == par_1.value * par_2.value
    assert par_3.name  == f'{par_1.name}_prod_{par_2.name}'

    expected_error = par_3.value * (
        (par_1.error / par_1.value) ** 2 + (par_2.error / par_2.value) ** 2
    ) ** 0.5
    assert par_3.error == pytest.approx(expected_error)
