'''
Module holding tests for WorkingPoint class
'''
import pytest

from rx_common import WorkingPoint
from rx_common import Cut
from rx_common import Cuts

# ------------------------------------------------
def test_initialize():
    '''
    Test bulding object
    '''
    cut = Cut(cut = Cuts.cmb, var = 'mva_cmb', val = 0.5)

    WorkingPoint(root = [cut])
    with pytest.raises(ValueError):
        WorkingPoint(root = [cut, cut])
# ------------------------------------------------
def test_extend():
    '''
    Test joining working points
    '''
    cmb= Cut(cut = Cuts.cmb, var = 'mva_cmb', val = 0.5)
    prc= Cut(cut = Cuts.prc, var = 'mva_prc', val = 0.5)

    wp1 = WorkingPoint(root = [cmb])
    wp2 = WorkingPoint(root = [prc])

    wp3 = wp1.extend(wp2)

    assert [cmb, prc] == wp3.root
# ------------------------------------------------
