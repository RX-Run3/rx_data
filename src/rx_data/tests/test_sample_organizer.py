'''
File with tests for SampleOrganizer class
'''
import os
import pytest

from functools   import cached_property
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
        self.is_mc     = True
        self._name     = name
        self._nfiles   = nfiles
        self._triggers = triggers
        self._storage  = storage
        self._nentries = 100

        self._opt      = RSnapshotOptions()
    # ------------------------------------
    def _make_file(self, file_name : str) -> Path:
        '''
        Parameters
        -------------
        file_name: End of file path
        '''
        file_path = self._storage / file_name
        if file_path.exists():
            return file_path

        for trigger in self._triggers:
            rdf = RDataFrame(self._nentries)
            rdf = rdf.Define('a', 'gRandom->Gaus()')

            rdf.Snapshot(
                options  = self._opt,
                treename = f'{trigger}/DecayTree', 
                filename = str(file_path))
            self._opt.fMode = 'update'

        rdf = RDataFrame(self._nentries)
        rdf = rdf.Define('a', 'gRandom->Gaus()')

        extra_tree = 'MCDT/MCDecayTree' if self.is_mc else 'lumiTree'

        rdf.Snapshot(
            options  = self._opt,
            treename = extra_tree, 
            filename = str(file_path))

        return file_path
    # ------------------------------------
    @property
    def name(self) -> str:
        return self._name 
    # ------------------------------------
    def local_paths(
        self, 
        must_exist: bool) -> list[Path]:

        _ = must_exist 

        return [ self._make_file(file_name = f'test_{index:03}.root') for index in range(self._nfiles) ]
    # ------------------------------
    @cached_property
    def target_paths(self) -> dict[Trigger, Path]:
        '''
        Returns
        --------------
        Dictionary mapping trigger to path to ROOT file
        '''
        ana_dir  = Path(os.environ['ANADIR'])
        paths : dict[Trigger,Path] = {}
        for trigger in self._triggers:
            target_path    = ana_dir / f'Data/{trigger.project}/main'
            paths[trigger] = target_path / f'latest/{self.name}_{trigger}.root'

        if len(paths) == 0:
            raise ValueError('No target paths found')

        return paths 
    # ------------------------------
    @property
    def is_organized(self) -> bool:
        '''
        Parameters
        -------------
        triggers: List of triggers associated to ROOT files belonging to this sample

        Returns
        -------------
        True if all of the files exist
        '''
        merged = True
        for path in self.target_paths.values():
            if path.exists():
                log.info(f'Found: {path}')
                continue

            log.info(f'Could not find: {path}')
            merged = False

        return merged
# ------------------------------------
@pytest.mark.parametrize('dry_run', [True, False])
@pytest.mark.parametrize('is_mc'  , [True, False])
def test_simple(
    dry_run  : bool,
    is_mc    : bool,
    tmp_path : Path):
    '''
    Simplest test
    '''
    triggers = list(Trigger)
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}):
        sample = TestSample(
            name     = 'test_sample',
            nfiles   = 3,
            storage  = tmp_path,
            triggers = triggers)

        sample.is_mc = is_mc

        org = SampleOrganizer(
            cleanup = False,
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
            dry_run = False)

        assert     org.organize(sample = sample)
        assert not org.organize(sample = sample)
