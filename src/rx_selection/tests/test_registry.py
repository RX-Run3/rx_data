'''
Module with tests for Registry class
'''
import copy
import pytest

from rx_selection import Registry, selection as sel
from rx_common    import Component, Trigger, Qsq, Cuts

# ----------------------------------
def test_read_write():
    '''
    Test that can write and read from registry and we get the same
    values
    '''
    cuts_in = {Cuts.cmb : 'mva_cmb > 0.5'}
    entry   = Registry(
        component = Component.data_24,
        trigger   = Trigger.rk_ee_os,
        qsq       = Qsq.high)

    entry.set(cuts = cuts_in)
    cuts_ot = entry.get()

    assert cuts_in == cuts_ot
# ----------------------------------
def test_fail():
    '''
    Test that code raises if

    - Reading something that does not exist
    - Writting twice in the same location
    '''
    entry = Registry(
        component = Component.data_24,
        trigger   = Trigger.rk_ee_os,
        qsq       = Qsq.high)

    with pytest.raises(ValueError):
        entry.get()

    entry = Registry(
        component = Component.data_24,
        trigger   = Trigger.rk_ee_os,
        qsq       = Qsq.high)

    entry.set(cuts = {Cuts.cmb : 'mva_cmb > 0.5'})
    entry.set(cuts = {Cuts.cmb : 'mva_cmb > 0.5'})
# ----------------------------------
def test_diff():
    '''
    Test that registry can extract difference between
    registered selection and default one
    '''
    cmb_cut = 'mva_cmb > 0.5'
    proc    = Component.data_24
    trig    = Trigger.rk_ee_os
    qsq     = Qsq.high

    cuts = {Cuts.cmb : cmb_cut}
    with sel.custom_selection(d_sel = cuts):
        cuts_new    = sel.selection(
            q2bin   = qsq,
            trigger = trig,
            process = proc)

        entry = Registry(
            component = proc,
            trigger   = trig,
            qsq       = qsq)

        entry.set(cuts = cuts_new)

        assert Cuts.cmb in entry.diff
        assert entry.diff[Cuts.cmb] == cmb_cut
# ----------------------------------
