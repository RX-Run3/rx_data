'''
Module with tests for Binning class
'''
from hqm.binning import Binning, Bins
from dmu         import LogStore

log=LogStore.add_logger('hqm:test_binning')
# ------------------------------------
def test_load():
    '''
    Load binning
    '''
    obj = Binning.load()

    assert isinstance(obj, Binning)
# ------------------------------------
def test_from_str():
    '''
    Load binning
    '''
    obj = Binning.load()
    bin = obj.from_str(binning = 'nbrem-1 B_PT-3')
    sel = bin.selection

    assert isinstance(bin, Bins)

    print(bin)
    for key, val in sel.items():
        log.info(f'{key:<20}{val}')
# ------------------------------------
