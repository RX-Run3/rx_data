'''
Module holding tests for yield classes
'''

from fitter          import Yield
from rx_common       import Cuts, Cut
from rx_efficiencies import Efficiency, WorkingPoint
from dmu             import LogStore

log=LogStore.add_logger('fitter:test_yield')
# -------------------------------------------
def test_simple():
    '''
    Basic initialization test
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    Yield(val = 300, err = 10, wp = wpt)
# -------------------------------------------
def test_product():
    '''
    Test multiplication with efficiency
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld = Yield(val = 300, err = 10, wp = wpt)
    eff = Efficiency(gen = 1000, sel = 10, wp = wpt)

    yld_1 = yld * eff
    yld_2 = eff * yld

    assert yld_1 == yld_2

    assert yld_1.val == yld.val * eff.sel / eff.gen 

    log.info(yld)
    log.info(eff)
    log.info(yld_1)
# -------------------------------------------
def test_ratio():
    '''
    Test multiplication with efficiency
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld = Yield(val = 300, err = 10, wp = wpt)
    eff = Efficiency(gen = 1000, sel = 10, wp = wpt)

    yld_1 = yld / eff

    assert yld_1.val == yld.val / eff.val

    log.info(yld)
    log.info(eff)
    log.info(yld_1)
# -------------------------------------------
