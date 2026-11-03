'''
Module meant to test Process class
'''

import pytest
from rx_common import set_nproc, get_nproc

# -----------------------------------------------
@pytest.mark.parametrize('nproc', [2, 5, 10])
def test_simple(nproc : int):
    '''
    Simplest test
    '''
    with set_nproc(value = nproc):
        assert get_nproc() == nproc
# -----------------------------------------------
@pytest.mark.parametrize('nproc', [2])
def test_fail(nproc : int):
    '''
    Simplest test
    '''
    with set_nproc(value = nproc):
        with pytest.raises(ValueError):
            with set_nproc(value = nproc):
                pass

    with pytest.raises(ValueError):
        get_nproc()
# -----------------------------------------------
