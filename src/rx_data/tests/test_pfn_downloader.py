'''
File holding tests for PFNDownloader class
'''

from dmu import LogStore
import pytest

from functools import cached_property
from typing    import Final
from pathlib   import Path
from rx_data   import PFNDownloader
from rx_data   import PFNDownloaderConf

_PFNS : Final[set[str]] = {
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379104/0000/00379104_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379005/0000/00379005_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00378985/0000/00378985_00000001_1.tuple.root',
}
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:pfn_downloader', 10)
# ----------------------------------------
class PFNHolder:
    def __init__(self, empty : bool):
        self._empty = empty
    # ----------------------------------------
    @cached_property
    def pfns(self) -> set[str]:
        if self._empty:
            return set()

        return _PFNS
# ----------------------------------------
@pytest.mark.parametrize('empty'  , [True, False])
@pytest.mark.parametrize('dry_run', [True, False])
def test_simple(
    tmp_path : Path,
    dry_run  : bool,
    empty    : bool):
    '''
    Simplest test
    '''
    holder = PFNHolder(empty = empty)
    cfg    = PFNDownloaderConf(
        chunks    = 4,
        chunksize = 16_777_216,
        version   = 'v1',
        out_dir   = tmp_path,
        dry_run   = dry_run,
        nthread   = 3)

    dwr = PFNDownloader(
        cfg     = cfg,
        samples = holder)

    if not empty:
        dwr.run()
    else:
        with pytest.raises(ValueError):
            dwr.run()
# ----------------------------------------
@pytest.mark.parametrize('chunks', [1, 4, 8])
def test_benchmark(tmp_path : Path, benchmark, chunks : int):
    '''
    Benchmark downloads
    '''
    holder = PFNHolder(empty = False)
    cfg    = PFNDownloaderConf(
        chunks    = chunks,
        chunksize = 16_777_216,
        version   = 'v1',
        out_dir   = tmp_path,
        dry_run   = False,
        nthread   = 3)

    def _run():
        dwr = PFNDownloader(
            cfg     = cfg,
            samples = holder)
        dwr.run()

    benchmark.pedantic(_run, rounds=1, iterations=1)
