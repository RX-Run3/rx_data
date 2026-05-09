'''
File with tests for SampleOrganizer class
'''
import pytest

from ROOT        import RDataFrame
from ROOT.RDF    import RSnapshotOptions
from pathlib     import Path
from rx_common   import Trigger
from rx_data     import SampleOrganizer
from dmu         import LogStore
from dmu.generic import utilities as gut

log=LogStore.add_logger('rx_data:test_sample_organizer')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:sample_organizer', 10)
# ------------------------------------
class SampleHolder:
    '''
    Class meant to be used by SampleOrganizer in tests
    '''
    # ------------------------------------
    def __init__(
        self, 
        nfiles   : int,
        triggers : list[Trigger], 
        storage  : Path):
        '''
        Parameters
        ------------------
        triggers: List of triggers included in file
        storage : Path to directory where data will be
        '''
        self._nfiles   = nfiles
        self._triggers = triggers
        self._storage  = storage
        self._nentries = 100

        self._opt      = RSnapshotOptions()
        self._opt.fMode= 'update'
    # ------------------------------------
    def _make_file(self, file_name : str) -> Path:
        '''
        Parameters
        -------------
        file_name: End of file path
        '''
        file_path = self._storage / file_name
        for trigger in self._triggers:
            rdf = RDataFrame(self._nentries)
            rdf = rdf.Define('a', '1')

            rdf.Snapshot(
                options  = self._opt,
                treename = f'{trigger}/DecayTree', 
                filename = str(file_path))

        rdf = RDataFrame(self._nentries)
        rdf = rdf.Define('a', '1')

        rdf.Snapshot(
            options  = self._opt,
            treename = 'MCDT/MCDecayTree', 
            filename = str(file_path))

        return file_path
    # ------------------------------------
    @property
    def name(self) -> str:
        return 'sample_name'
    # ------------------------------------
    def local_paths(
        self, 
        directory : Path,
        must_exist: bool) -> list[Path]:

        _ = directory
        _ = must_exist 

        return [ self._make_file(file_name = f'test_{index:03}.root') for index in range(self._nfiles) ]
# ------------------------------------
@pytest.mark.parametrize('triggers', [[Trigger.rk_ee_os, Trigger.rkst_ee_os]])
def test_simple(
    tmp_path : Path, 
    triggers : list[Trigger]):
    '''
    Simplest test
    '''
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        sample = SampleHolder(
            nfiles   = 3,
            storage  = tmp_path,
            triggers = triggers)

        org = SampleOrganizer(
            cleanup = False,
            storage = tmp_path,
            dry_run = False)
        org.organize(sample = sample)
