'''
File with tests for Cuts enum
'''
import pytest

from rx_common import Cuts, Cut

from dmu import LogStore

log=LogStore.add_logger('rx_common:test_cuts')
# ----------------------
@pytest.mark.parametrize('value', Cuts)
def test_types(value : Cuts):
    '''
    Test that values are strings
    '''
    isinstance(value, str)
# ----------------------
def test_save():
    '''
    Test printing
    '''
    obj = {Cuts.mass : 'mass > 0', Cuts.pid_l : 'pid_e > 3'}

    print(obj)
# ----------------------
def test_clone_cut():
    '''
    Test cloning Cut instance
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    cln = cut.clone(value = 0.8)

    log.info(cut)
    log.info(cln)

    assert cln.val == 0.8
    assert cln     != cut
# ----------------------
