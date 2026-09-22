'''
Module with tests for Binning class
'''
import pytest

from typing      import Final
from rx_common   import Block
from hqm.binning import BinningConf, BinConf
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

    assert isinstance(bin, BinConf)

    if binning == '':
        assert len(sel) == 0

    print(bin)
    for key, val in sel.items():
        log.info(f'{key:<20}{val}')
# ------------------------------------
def test_block_found():
    '''
    Test that we can extract block from cut
    '''
    iblock  = 3
    binning = f'block-{iblock}'

    obj = BinningConf.load()
    bin = obj.from_str(binning = binning)

    assert bin.block == Block(value = iblock)
# ------------------------------------
def test_block_missing():
    '''
    Load binning
    Test that we cannot extract block from cut missing block
    '''
    iblock  = 3
    binning = 'mva_cmb-3 mva_prc-2'

    obj = BinningConf.load()
    bin = obj.from_str(binning = binning)

    with pytest.raises(ValueError):
        assert bin.block == Block(value = iblock)
# ------------------------------------
def test_from_sel():
    '''
    Retrieve bin index given selection
    '''
    binning_in = 'mva_cmb-1 mva_prc-1'

    cfg     = BinningConf.load()
    bin_cfg = cfg.from_str(binning_in)
    sel     = bin_cfg.selection

    binning_out = cfg.binning_from_sel(sel = sel)

    assert binning_in == binning_out
# ------------------------------------
