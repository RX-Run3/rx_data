'''
Module with tests for DataStore class
'''

import pytest
import numpy
import numpy.typing  as npt
import pandas        as pnd
import matplotlib.pyplot as plt

from contextlib        import ExitStack
from collections.abc   import Callable
from typing            import Any
from pathlib           import Path
from rx_common         import Channel, Component, Cuts, Mass, Trigger
from hqm.binning       import BinningConf
from hqm.data_store    import DataStore
from hqm.plotter       import Plotter
from hqm.utilities     import get_data, SIZE
from hqm.database_conf import DatabaseConf
from dmu               import LogStore

type NpFltArray = npt.NDArray[numpy.float64]

log=LogStore.add_logger('hqm:test_data_store')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_hqm:data_store', 10)
#--------------------------------------
def _load_df_ee(self : Any) -> pnd.DataFrame:
    _    = self
    data = get_data(channel = Channel.ee)

    return pnd.DataFrame(data)
#--------------------------------------
def _load_df_mm(self : Any) -> pnd.DataFrame:
    _    = self
    data = get_data(channel = Channel.mm)

    return pnd.DataFrame(data)
#--------------------------------------
@pytest.fixture(autouse = False)
def _patch_loader_ee(monkeypatch):
    monkeypatch.setattr(
        DataStore,
        '_load_df',
        _load_df_ee)
#--------------------------------------
@pytest.fixture(autouse = False)
def _patch_loader_mm(monkeypatch):
    monkeypatch.setattr(
        DataStore,
        '_load_df',
        _load_df_mm)
#--------------------------------------
@pytest.fixture(autouse = False)
def _block_selection():
    sel : dict[str,str] = {Cuts.block.value : 'block == 1'}
    with DataStore.selection(sel = sel, update = False):
        yield
#--------------------------------------
@pytest.mark.parametrize('comp', [Component.data_24, Component.bpkpjpsiee])
def test_data_retrieval(
    _patch_loader_ee : Callable,
    comp             : Component,
    tmp_path         : Path):
    '''
    Test initialized object with fake data
    '''
    _   = _patch_loader_ee
    with DataStore.selection(sel = {Cuts.block : 'true'}, update = False):
        obj = DataStore(comp= comp, trig= Trigger.rk_ee_os)

    arr_raw     , _   = obj.get_array(mass = Mass.bp_bcor)
    arr_dtf_jpsi, _   = obj.get_array(mass = Mass.bp_dtf_jpsi)
    arr_dtf_psi2, wgt = obj.get_array(mass = Mass.bp_dtf_psi2)

    ptr = Plotter(out_dir = tmp_path)
    ptr.plot_array(name = 'raw_mass'     , array = arr_raw)
    ptr.plot_array(name = 'dtf_mass_jpsi', array = arr_dtf_jpsi)
    ptr.plot_array(name = 'dtf_mass_psi2', array = arr_dtf_psi2)
    ptr.plot_array(name = 'weights'      , array = wgt)

    if not comp.is_mc:
        assert numpy.isclose(wgt, 1.0).all()

    assert len(arr_raw     ) == SIZE
    assert len(arr_dtf_jpsi) == SIZE
    assert len(arr_dtf_psi2) == SIZE
#--------------------------------------
def test_data_load(monkeypatch, tmp_path : Path):
    '''
    Test actually loading data from database
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os

    df   = _load_df_ee(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    with DataStore.selection(sel = {}, update = False):
        obj = DataStore(trig= trig, comp= comp)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)

    assert len(arr_raw) == SIZE
    assert len(arr_wgt) == SIZE
#--------------------------------------
def test_new_selection(monkeypatch, tmp_path : Path):
    '''
    Test with database data and selection from zero
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os

    df   = _load_df_ee(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    sel = dict()
    sel['q2']    = 'q2_dtf > 11e6'
    sel['block'] = 'block == 1'
    with DataStore.selection(sel = sel, update = False):
        obj = DataStore(trig= trig, comp= comp)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    obj.save_selection(path = selection_path)

    assert selection_path.exists()
    assert len(arr_raw) < SIZE
    assert len(arr_wgt) < SIZE
#--------------------------------------
def test_update_selection(
    monkeypatch,
    _block_selection : Callable,
    tmp_path : Path):
    '''
    Test with database data and selection from zero
    '''
    _ = _block_selection
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os

    df   = _load_df_ee(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    sel       = dict()
    sel['q2'] = 'q2_dtf > 11e6'

    with pytest.raises(ValueError):
        with DataStore.selection(sel = sel, update = False):
            obj = DataStore(trig= trig, comp= comp)

    with DataStore.selection(sel = sel, update = True):
        obj = DataStore(trig= trig, comp= comp)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    obj.save_selection(path = selection_path)

    assert selection_path.exists()
    assert len(arr_raw) < SIZE
    assert len(arr_wgt) < SIZE
#--------------------------------------
def test_binning_selection(monkeypatch, tmp_path : Path):
    '''
    Test with database data and selection from zero
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os

    df   = _load_df_ee(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    binning         = BinningConf.load()
    bins            = binning.from_str('B_PT-3 ll_angle-2 nTracks-1')
    sel             = bins.selection
    sel[Cuts.q2]    = 'q2_dtf > 11e6'
    with DataStore.selection(sel = sel, update = False):
        obj = DataStore(trig= trig, comp= comp)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    obj.save_selection(path = selection_path)

    for col in obj.columns:
        print(col)

    assert selection_path.exists()
    assert len(arr_raw) < SIZE
    assert len(arr_wgt) < SIZE
#--------------------------------------
def test_merge(monkeypatch, tmp_path : Path):
    '''
    Test with database data and selection from zero
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))
    min_entries = 100

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os

    df   = _load_df_ee(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    binning         = BinningConf.load()
    bins            = binning.from_str('block-1 ll_angle-2')
    sel             = bins.selection
    sel[Cuts.q2]    = 'q2_dtf > 10e6'
    with DataStore.selection(sel = sel, update = False):
        obj = DataStore(
            min_entries = min_entries,
            trig        = trig,
            comp        = comp)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    sel = obj.save_selection(path = selection_path)

    assert 'block' not in sel
    assert len(arr_raw) >= min_entries
#--------------------------------------
@pytest.mark.parametrize('comp', [Component.data_24, Component.bpkpjpsiee])
def test_smearing(
    _patch_loader_ee : Callable,
    comp             : Component,
    tmp_path         : Path):
    '''
    Test that smearing is/is not done
    '''
    _   = _patch_loader_ee
    ctx_1 = DataStore.selection(sel = {Cuts.block : 'true'}, update = True)
    with ExitStack() as stack:
        stack.enter_context(ctx_1)

        obj               = DataStore(comp= comp, trig= Trigger.rk_ee_os)
        arr_mass_smr, _   = obj.get_array(mass = Mass.bp_bcor)

    ctx_1 = DataStore.selection(sel = {Cuts.block : 'true'}, update = True)
    ctx_2 = DataStore.smear_masses(value = False)
    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)

        obj               = DataStore(comp= comp, trig= Trigger.rk_ee_os)
        arr_mass_raw, _   = obj.get_array(mass = Mass.bp_bcor)

    if not comp.is_mc:
        assert numpy.isclose(arr_mass_raw, arr_mass_smr).all()
    else:
        assert arr_mass_raw.std() < arr_mass_smr.std()

    plt.hist(arr_mass_raw, bins = 60, range = (5000, 6000), alpha    =    0.3, label = 'Raw')
    plt.hist(arr_mass_smr, bins = 60, range = (5000, 6000), histtype = 'step', label = 'Smeared')
    plt.title(comp.latex)
    plt.legend()
    plt.savefig(tmp_path / 'plot.png')
    plt.close()
#--------------------------------------
