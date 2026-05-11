'''
File with tests for SampleOrganizer class
'''
import os
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
class TestSample:
    '''
    Class meant to be used by SampleOrganizer in tests
    '''
    # ------------------------------------
    def __init__(
        self, 
        name     : str,
        nfiles   : int,
        triggers : list[Trigger], 
        storage  : Path):
        '''
        Parameters
        ------------------
        name    : Sample name
        triggers: List of triggers included in file
        nfiles  : Number of files in sample
        storage : Path to directory where data will be
        '''
        self._name     = name
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
        return self._name 
    # ------------------------------------
    def local_paths(
        self, 
        directory : Path,
        must_exist: bool) -> list[Path]:

        _ = directory
        _ = must_exist 

        return [ self._make_file(file_name = f'test_{index:03}.root') for index in range(self._nfiles) ]
    # ------------------------------
    def target_path(self, trigger : Trigger) -> Path:
        '''
        Parameters
        --------------
        trigger: HLT2 trigger

        Returns
        --------------
        Path to merged file associated to this sample and trigger
        i.e. after merging and splitting stage
        '''
        ana_dir     = Path(os.environ['ANADIR'])
        target_path = ana_dir / f'Data/{trigger.project}/main'
        target_path = target_path / f'latest/{self.name}.root'

        return target_path
    # ------------------------------
    def is_merged(self, triggers : list[Trigger]) -> bool:
        '''
        Parameters
        -------------
        triggers: List of triggers associated to ROOT files belonging to this sample

        Returns
        -------------
        True if all of the files exist
        '''
        paths = [ self.target_path(trigger = trigger) for trigger in triggers ]

        return all(path.exists() for path in paths)
# ------------------------------------
@pytest.mark.parametrize('triggers', [[Trigger.rk_ee_os, Trigger.rkst_ee_os]])
@pytest.mark.parametrize('dry_run' , [True, False])
def test_simple(
    dry_run  : bool,
    tmp_path : Path, 
    triggers : list[Trigger]):
    '''
    Simplest test
    '''
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        sample = TestSample(
            name     = 'test_sample',
            nfiles   = 3,
            storage  = tmp_path,
            triggers = triggers)

        org = SampleOrganizer(
            cleanup = False,
            storage = tmp_path,
            dry_run = dry_run)
        org.organize(sample = sample)
# ------------------------------------
@pytest.mark.parametrize('triggers', [[Trigger.rk_ee_os, Trigger.rkst_ee_os]])
def test_versions(
    tmp_path : Path, 
    triggers : list[Trigger]):
    '''
    Test that new version does not override old one
    '''
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        for index in range(3):
            sample = TestSample(
                name     = f'sample_{index:03}',
                nfiles   = 3,
                storage  = tmp_path,
                triggers = triggers)

            org = SampleOrganizer(
                cleanup = False,
                storage = tmp_path,
                dry_run = False)
            org.organize(sample = sample)
# ------------------------------------
@pytest.mark.parametrize('triggers', [[Trigger.rk_ee_os, Trigger.rkst_ee_os]])
def test_skip_done(
    tmp_path : Path, 
    triggers : list[Trigger]):
    '''
    Test that if sample was organized, it won't be organized again
    i.e. caching behavior
    '''
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
         sample      = TestSample(
            name     = 'test_sample',
            nfiles   = 3,
            storage  = tmp_path,
            triggers = triggers)

         org = SampleOrganizer(
             cleanup = False,
             storage = tmp_path,
             dry_run = False)

         assert     org.organize(sample = sample)
         assert not org.organize(sample = sample)
