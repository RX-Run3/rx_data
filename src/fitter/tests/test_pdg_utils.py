'''
This module contains tests for the functions in pdg_utils.py
'''
import math

from fitter import pdg_utils as pu

# ---------------------------------------------
def test_simle() -> None:
    '''
    Simplest test
    '''

    v1 = pu.get_bf('B+ --> J/psi(1S) K+')
    v2 = pu.get_bf('B0 --> J/psi(1S) K*(892)0')
    v3 = pu.get_bf('B_s()0 --> J/psi(1S) phi')

    assert math.isclose(v1, 1.02e-3, rel_tol=1e-3)
    assert math.isclose(v2, 1.27e-3, rel_tol=1e-3)
    assert math.isclose(v3, 1.01e-3, rel_tol=1e-3)
