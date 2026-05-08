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

_PFNS : Final[list[str]] = [
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379104/0000/00379104_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379005/0000/00379005_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00378985/0000/00378985_00000001_1.tuple.root',
]
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
    def pfns(self) -> list[str]:
        if self._empty:
            return []

        return _PFNS
# ----------------------------------------
@pytest.mark.parametrize('empty', [True, False])
def test_simple(
    tmp_path : Path,
    empty    : bool):
    '''
    Simplest test
    '''
    holder = PFNHolder(empty = empty)
    cfg    = PFNDownloaderConf(
        version = 'v1',
        out_dir = tmp_path,
        dry_run = False,
        nthread = 1)

    dwr    = PFNDownloader(
        cfg     = cfg,
        samples = holder)

    if not empty:
        dwr.run()
    else:
        with pytest.raises(ValueError):
            dwr.run()
