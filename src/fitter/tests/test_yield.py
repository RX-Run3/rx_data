'''
Module holding tests for yield classes
'''

from fitter          import Yield
from rx_common       import Cuts, Cut, Trigger, WorkingPoint, Qsq
from rx_efficiencies import Efficiency
from dmu             import LogStore
from fitter          import YieldCalculator

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
def test_sum():
    '''
    Test sum of yields 
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld_1 = Yield(val = 300, err = 10, wp = wpt)
    yld_2 = Yield(val = 300, err = 10, wp = wpt)

    tot   = yld_1 + yld_2

    log.info(yld_1)
    log.info(yld_2)
    log.info(tot  )

    assert tot.val == yld_1.val + yld_2.val
# -------------------------------------------
def test_calculator():
    '''
    Test yield calculator
    '''
    cmb = Cut(cut = Cuts.cmb, val = 0.99, var = 'mva_cmb')
    prc = Cut(cut = Cuts.prc, val = 0.60, var = 'mva_prc')
    wpt = WorkingPoint(root = [cmb, prc])

    cal = YieldCalculator(
        name    = 'rare',
        wp      = wpt,
        q2bin   = Qsq.jpsi, # for tests, should be rare otherwise
        trigger = Trigger.rk_ee_os)

    grid = cal.calculate()
