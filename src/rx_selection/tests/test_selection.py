'''
Script with functions needed to test functions in selection.py
'''
import pytest

from rx_common    import QsqDef
from pathlib      import Path
from dmu          import LogStore
from rx_common    import Component, Cuts, Qsq, Trigger
from rx_selection import selection as sel
from rx_data      import RDFGetter

log=LogStore.add_logger('rx_selection:test_selection')
# --------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_selection:selection'     , 10)
    LogStore.set_level('rx_selection:test_selection', 10)
# --------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os, Trigger.rkst_ee_os, Trigger.rkst_mm_os])
@pytest.mark.parametrize('q2bin'  , Qsq.for_physics())
@pytest.mark.parametrize('kind'   , QsqDef)
def test_override_qsq(
    trigger : Trigger,
    q2bin   : Qsq,
    kind    : QsqDef):
    '''
    Test update q2 cut
    '''
    q2bin     = Qsq(q2bin)
    component = Component.data_24
    d_default = sel.selection(
        trigger=trigger,
        q2bin  =q2bin,
        process=component)

    with sel.override_qsq(kind = kind):
        d_sel = sel.selection(
            trigger=trigger,
            q2bin  =q2bin,
            process=component)

    expected = kind.update_expression(expr = d_default[Cuts.q2])

    assert d_sel[Cuts.q2] == expected
# --------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_mm_os, Trigger.rkst_ee_os, Trigger.rkst_mm_os])
@pytest.mark.parametrize('q2bin'  , Qsq.for_physics())
def test_read_selection(
    trigger : Trigger,
    q2bin   : Qsq):
    '''
    Test reading the selection
    '''
    q2bin     = Qsq(q2bin)
    component = Component.data_24

    d_sel = sel.selection(
        trigger=trigger,
        q2bin  =q2bin,
        process=component)
    for cut_name, cut_value in d_sel.items():
        log.info(f'{cut_name:<20}{cut_value}')
# --------------------------
@pytest.mark.parametrize('sample', [Component.bpkpee, Component.data_24_md_c2])
@pytest.mark.parametrize('q2bin'  , Qsq.for_physics())
def test_custom_selection(sample : Component, q2bin : Qsq):
    '''
    This function tests the custom_selection
    context manager
    '''
    trigger = Trigger.rk_ee_os

    with sel.custom_selection(d_sel={Cuts.extra : 'val'}):
        d_cut = sel.selection(
            process=sample,
            q2bin  =q2bin,
            trigger=trigger)

    assert Cuts.extra in d_cut
    assert d_cut[Cuts.extra] == 'val'
# --------------------------
def test_multiple_custom_selection():
    '''
    Tests that we cannot call custom_selection manager in a nested way
    '''
    sample = Component.bpkpee
    q2bin  = Qsq.central
    trigger= Trigger.rk_ee_os

    with pytest.raises(sel.MultipleSelectionOverriding):
        with sel.custom_selection(d_sel={Cuts.extra : 'val'}):
            with sel.custom_selection(d_sel={Cuts.extra : 'vol'}):
                sel.selection(process=sample, q2bin=q2bin, trigger=trigger)
# --------------------------
def test_multiple_custom_selection_override():
    '''
    Tests calling custom_selection with overriding flag
    '''
    sample = Component.bpkpee
    q2bin  = Qsq.central
    trigger= Trigger.rk_ee_os
    cut    = Cuts.extra

    with sel.custom_selection(d_sel={Cuts.extra : 'val'}, force_override=True):
        d_cut_1 = sel.selection(
            process= sample,
            q2bin  = q2bin,
            trigger= trigger)
        assert d_cut_1[Cuts.extra] == 'val'
        with sel.custom_selection(d_sel={Cuts.extra : 'vol'}, force_override=True):
            d_cut_2 = sel.selection(process=sample, q2bin=q2bin, trigger=trigger)
            assert d_cut_2[cut] == 'vol'

        d_cut_1 = sel.selection(process=sample, q2bin=q2bin, trigger=trigger)
        assert d_cut_1[cut] == 'val'

    d_cut = sel.selection(process=sample, q2bin=q2bin, trigger=trigger)
    assert 'cut' not in d_cut
# --------------------------
def test_custom_selection_nested():
    '''
    Check that nesting of context managers does not break upstream (original) custom selection
    '''
    csel_000 = sel.Data.d_custom_selection
    cut_1    = Cuts.extra
    cut_2    = Cuts.mass
    cut_3    = Cuts.q2

    with sel.custom_selection(d_sel={cut_1 : 'val_1'}):
        csel_001 = sel.Data.d_custom_selection
        with sel.custom_selection(d_sel={cut_2 : 'val_2'}, force_override=True):
            csel_002 = sel.Data.d_custom_selection
            with sel.custom_selection(d_sel={cut_3 : 'val_3'}, force_override=True):
                csel_003 = sel.Data.d_custom_selection

            csel_012  = sel.Data.d_custom_selection
        csel_011  = sel.Data.d_custom_selection
    csel_010  = sel.Data.d_custom_selection

    assert csel_000 == csel_010
    assert csel_001 == csel_011
    assert csel_002 == csel_012
    assert csel_003 == {cut_3 : 'val_3'}
# --------------------------
def test_update_selection():
    '''
    Tests that manger can add cuts to existing selection
    '''
    cut_1    = Cuts.extra
    cut_2    = Cuts.mass

    isel_001 = {cut_1 : 'val_1'}
    with sel.update_selection(d_sel=isel_001):
        osel_001 = sel.Data.d_custom_selection

    assert    isel_001  ==    osel_001
    assert id(isel_001) != id(osel_001)

    csel_001 = {cut_1 : 'val_1'}
    isel_001 = {cut_2 : 'val_2'}
    with sel.custom_selection(d_sel=csel_001):
        with sel.update_selection(d_sel=isel_001):
            osel_001 = sel.Data.d_custom_selection

    csel_001.update(isel_001)

    assert    csel_001  == osel_001
    assert id(isel_001) != id(osel_001)

    isel_001 = {cut_1 : 'val_1'}
    isel_002 = {cut_2 : 'val_2'}
    with sel.update_selection(d_sel=isel_001):
        with sel.update_selection(d_sel=isel_002):
            osel_002 = sel.Data.d_custom_selection

    isel_001.update(isel_002)

    assert    isel_001  ==    osel_002
    assert id(isel_001) != id(osel_002)
# --------------------------
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rkst_ee_os])
def test_no_truth(trigger : Trigger):
    '''
    Test reading the selection
    '''
    sample  = Component.bdkstkpiee
    d_sel   = sel.selection(
        trigger   = trigger,
        q2bin     = Qsq.central,
        skip_truth= True,
        process   = sample)

    assert d_sel[Cuts.truth] == '(1)'
# --------------------------
@pytest.mark.skip(reason = 'Uses data, it is slow')
def test_apply_full_selection(tmp_path : Path):
    '''
    Tests application of selection
    '''
    q2bin  = Qsq.jpsi
    sample = Component.data_24
    trigger= Trigger.rk_ee_os

    with RDFGetter.max_entries(10_000):
        gtr = RDFGetter(
            sample =sample,
            trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    out_path = tmp_path / f'{q2bin}_{sample}_{trigger}'

    rdf =sel.apply_full_selection(
        rdf     =rdf,
        q2bin   =q2bin,
        process =sample,
        trigger =trigger,
        out_path=out_path)
# --------------------------
@pytest.mark.skip(reason = 'Uses data, it is slow')
def test_apply_selection(tmp_path : Path):
    '''
    Tests application of selection
    '''
    q2bin  = Qsq.jpsi
    sample = Component.data_24
    trigger= Trigger.rk_ee_os

    with RDFGetter.max_entries(10_000):
        gtr = RDFGetter(
            sample =sample,
            trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)

    out_path = tmp_path / f'{q2bin}_{sample}_{trigger}'

    cuts = sel.selection(
        q2bin   = q2bin,
        process = sample,
        trigger = trigger,
    )

    rdf =sel.apply_selection(
        rdf     =rdf,
        cuts    =cuts,
        uid     =gtr.get_uid(),
        out_path=out_path)
# --------------------------
