'''
File holding tests for PFNDownloader class
'''

from functools import cached_property
from typing  import Final

import pytest
from rx_data import PFNDownloader

_PFNS : Final[list[str]] = [
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379104/0000/00379104_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00379005/0000/00379005_00000001_1.tuple.root',
    'root://x509up_u1000@eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00378985/0000/00378985_00000001_1.tuple.root',
]

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
def test_simple(empty : bool):
    holder = PFNHolder(empty = empty)
    dwr    = PFNDownloader(samples = holder)

    if not empty:
        dwr.run()
    else:
        with pytest.raises(ValueError):
            dwr.run()
