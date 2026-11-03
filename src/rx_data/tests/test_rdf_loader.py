'''
This module contains tests for the RDFLoader class
'''
import pytest

from dask.distributed import Client, LocalCluster
from rx_common        import Qsq, Component, Trigger
from rx_data          import RDFLoader
from rx_data          import SpecMaker
from rx_selection     import selection as sel
from dmu              import LogStore

log=LogStore.add_logger('rx_data:test_rdf_loader')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:rdf_loader', 10)
# ----------------------
def test_from_conf():
    '''
    Test loading dataframe from JSON config file
    '''
    sample = Component.data_24
    trigger= Trigger.rk_mm_os

    mkr    = SpecMaker(component=sample, trigger=trigger)
    path   = mkr.get_spec_path(per_file=False)

    rdf    = RDFLoader.from_conf(
        ntries = 3,
        wait   = 10,
        path   = path)

    rdf = sel.apply_full_selection(
        rdf     = rdf,
        q2bin   = Qsq.central,
        process = sample,
        trigger = trigger)

    assert rdf.Count().GetValue() > 0
# ----------------------
def test_dask():
    '''
    Load using dask client
    '''
    sample = Component.data_24
    trigger= Trigger.rk_mm_os

    mkr    = SpecMaker(component=sample, trigger=trigger)
    path   = mkr.get_spec_path(per_file=False)

    cluster = LocalCluster(
        n_workers         =2,
        threads_per_worker=1,
        processes         =True,
        memory_limit      ='6GiB')
    client  = Client(cluster)

    with RDFLoader.client(client = client):
        rdf = RDFLoader.from_conf(
            ntries = 3,
            wait   = 10,
            path   = path)

        rdf = sel.apply_full_selection(
            rdf     = rdf,
            q2bin   = Qsq.central,
            process = sample,
            trigger = trigger)

    assert rdf.Count().GetValue() > 0
