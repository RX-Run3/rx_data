'''
Module with tests for DataStore class
'''

import pytest
import numpy
import numpy.typing  as npt
import pandas        as pnd

from pathlib           import Path
from rx_common         import Component, Cuts, Mass, Qsq, Trigger
from hqm.binning       import Binning
from hqm.data_store    import DataStore
from hqm.plotter       import Plotter
from hqm.database_conf import DatabaseConf
from dmu               import LogStore

from .utilities        import get_data, SIZE

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
def _load_df(self) -> pnd.DataFrame:
    _    = self
    data = get_data()

    return pnd.DataFrame(data)
#--------------------------------------
@pytest.fixture(autouse = False)
def _patch_loader(monkeypatch):
    monkeypatch.setattr(
        DataStore,
        '_load_df',
        _load_df)
#--------------------------------------
@pytest.fixture(autouse = False)
def _block_selection():
    sel : dict[str,str] = {Cuts.block.value : 'block == 1'}
    with DataStore.selection(sel = sel, update = False):
        yield
#--------------------------------------
@pytest.mark.parametrize('comp', [Component.data_24, Component.bpkpjpsiee])
def test_data_retrieval(
    _patch_loader,
    comp     : Component,
    tmp_path : Path):
    '''
    Test initialized object with fake data
    '''
    _   = _patch_loader
    with DataStore.selection(sel = {Cuts.block : 'true'}, update = False):
        obj = DataStore(
            comp= comp,
            trig= Trigger.rk_ee_os,
            qsq = Qsq.jpsi)

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
    qsq  = Qsq.high

    df   = _load_df(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    with DataStore.selection(sel = {}, update = False):
        obj = DataStore(
            trig= trig,
            comp= comp,
            qsq = qsq)

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
    qsq  = Qsq.high

    df   = _load_df(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    sel = dict()
    sel[Cuts.q2]    = 'q2_dtf > 11e6'
    sel[Cuts.block] = 'block == 1'
    with DataStore.selection(sel = sel, update = False):
        obj = DataStore(
            trig= trig,
            comp= comp,
            qsq = qsq)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    obj.save_selection(path = selection_path)

    assert selection_path.exists()
    assert len(arr_raw) < SIZE
    assert len(arr_wgt) < SIZE
#--------------------------------------
def test_update_selection(
    monkeypatch,
    _block_selection,
    tmp_path : Path):
    '''
    Test with database data and selection from zero
    '''
    _ = _block_selection
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os
    qsq  = Qsq.high

    df   = _load_df(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    sel          = dict()
    sel[Cuts.q2] = 'q2_dtf > 11e6'

    with pytest.raises(ValueError):
        with DataStore.selection(sel = sel, update = False):
            obj = DataStore(
                trig= trig,
                comp= comp,
                qsq = qsq)

    with DataStore.selection(sel = sel, update = True):
        obj = DataStore(
            trig= trig,
            comp= comp,
            qsq = qsq)

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
    qsq  = Qsq.high

    df   = _load_df(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    binning         = Binning.load()
    bins            = binning.from_str('B_PT-3 ll_angle-2 nTracks-1')
    sel             = bins.selection
    sel[Cuts.q2]    = 'q2_dtf > 11e6'
    with DataStore.selection(sel = sel, update = False):
        obj = DataStore(
            trig= trig,
            comp= comp,
            qsq = qsq)

    arr_raw, arr_wgt = obj.get_array(mass = Mass.bp_bcor)
    selection_path   = tmp_path / 'selection.json'
    obj.save_selection(path = selection_path)

    assert selection_path.exists()
    assert len(arr_raw) < SIZE
    assert len(arr_wgt) < SIZE
#--------------------------------------

