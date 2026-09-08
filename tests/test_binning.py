'''
Module with tests for Binning class
'''
import pytest

from typing      import Final
from hqm.binning import BinningConf, Bins
from dmu         import LogStore

log=LogStore.add_logger('hqm:test_binning')

_BINNING : Final[list[str]] = ['nbrem-1 B_PT-3', '']
# ------------------------------------
def test_load():
    '''
    Load binning
    '''
    obj = BinningConf.load()

    assert isinstance(obj, BinningConf)
# ------------------------------------
@pytest.mark.parametrize('binning', _BINNING)
def test_from_str(binning : str):
    '''
    Load binning
    '''
    obj = BinningConf.load()
    bin = obj.from_str(binning = binning)
    sel = bin.selection

    assert isinstance(bin, Bins)

    if binning == '':
        assert len(sel) == 0

    print(bin)
    for key, val in sel.items():
        log.info(f'{key:<20}{val}')
# ------------------------------------
