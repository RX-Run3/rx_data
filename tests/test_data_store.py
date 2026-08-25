'''
Module with tests for DataStore class
'''

import pytest
import numpy
import numpy.typing  as npt
import pandas        as pnd

from pathlib           import Path
from rx_common         import Component, Mass, Qsq, Trigger
from hqm.data_store    import DataStore
from hqm.plotter       import Plotter
from hqm.database_conf import DatabaseConf

from .utilities        import get_data, SIZE

NpFltArray = npt.NDArray[numpy.float64]
#--------------------------------------
def _load_df(self) -> pnd.DataFrame:
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
def test_data_retrieval(_patch_loader, tmp_path : Path):
    '''
    Test retrieving data
    '''
    obj = DataStore(
        trig= Trigger.rk_mm_os,
        comp= Component.data_24,
        qsq = Qsq.jpsi)

    arr_raw      = obj.get_array(mass = Mass.bp_bcor)
    arr_dtf_jpsi = obj.get_array(mass = Mass.bp_dtf_jpsi)
    arr_dtf_psi2 = obj.get_array(mass = Mass.bp_dtf_psi2)

    with Plotter.plot(path = tmp_path):
        ptr = Plotter()
        ptr.plot_array(name = 'raw_mass'     , array = arr_raw)
        ptr.plot_array(name = 'dtf_mass_jpsi', array = arr_dtf_jpsi)
        ptr.plot_array(name = 'dtf_mass_psi2', array = arr_dtf_psi2)

    assert len(arr_raw     ) == SIZE
    assert len(arr_dtf_jpsi) == SIZE
    assert len(arr_dtf_psi2) == SIZE
#--------------------------------------
def test_data_load(monkeypatch, tmp_path : Path):
    monkeypatch.setenv('ANADIR', str(tmp_path))

    comp = Component.bpkpjpsiee
    trig = Trigger.rk_ee_os
    qsq  = Qsq.high

    df   = _load_df(self = None)
    cfg  = DatabaseConf.load()
    path = cfg.get_path(comp = comp, trig = trig)
    df.to_parquet(path = path)

    print(df)

    obj = DataStore(
        trig= trig,
        comp= comp,
        qsq = qsq)

    arr_raw = obj.get_array(mass = Mass.bp_bcor)
    assert len(arr_raw) == SIZE
#--------------------------------------
