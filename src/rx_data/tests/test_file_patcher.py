'''
Module meant to test FilePatcher class
'''
import pytest

from ROOT    import RDataFrame, RDF
from pathlib import Path
from rx_data import FilePatcher
from dmu     import LogStore

log=LogStore.add_logger('rx_data:test_file_patcher')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:file_patcher', 10)
# -----------------------------------------
def _make_input(path : Path, add_block : bool = False) -> None:
    '''
    Makes dummy data
    '''
    rdf_rec = RDataFrame(100)
    rdf_rec = rdf_rec.Define('a', '1')

    rdf_gen = RDataFrame(100)
    rdf_gen = rdf_gen.Define('b', '1')
    if add_block:
        rdf_gen = rdf_gen.Define('block', '2')

    opts = RDF.RSnapshotOptions()
    opts.fMode = 'update'

    rdf_rec.Snapshot(
        treename = 'DecayTree', 
        filename = str(path))

    rdf_gen.Snapshot(
        treename = 'MCDecayTree',
        filename = str(path), 
        options  = opts)
# -----------------------------------------
def test_mc_add_block(tmp_path : Path):
    '''
    Test on MC files that miss block
    '''
    ptc = FilePatcher(dry_run = False)

    for hash in ptc.hashes:
        path = tmp_path / f'mc_file_{hash}.root'
        _make_input(path = path)

        assert ptc.run(path = path) == 1
# -----------------------------------------
def test_data_add_block(tmp_path : Path):
    '''
    Test on data files 
    '''
    ptc = FilePatcher(dry_run = False)

    path = tmp_path / 'data_file_xxx.root'
    _make_input(path = path)

    assert ptc.run(path = path) == -3
# -----------------------------------------
def test_mc_already_present(tmp_path : Path):
    '''
    Test on MC files that have block branch 
    '''
    ptc  = FilePatcher(dry_run = False)
    hash = list(ptc.hashes)[0]
    path = tmp_path / f'mc_file_{hash}.root'
    _make_input(path = path, add_block = True)

    assert ptc.run(path = path) == 0
# -----------------------------------------
def test_dry_run(tmp_path : Path):
    '''
    Test dry run 
    '''
    ptc  = FilePatcher(dry_run = True)

    for hash in ptc.hashes:
        path = tmp_path / f'mc_file_{hash}.root'
        _make_input(path = path)

        assert ptc.run(path = path) == 2
