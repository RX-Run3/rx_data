'''
Module holding tests for yield classes
'''
from rx_plotter import GridPlotter
from rx_common  import Cuts, Cut, Trigger, WorkingPoint, Qsq
from dmu        import LogStore
from pathlib    import Path
from fitter     import YieldCalculator

log=LogStore.add_logger('fitter:test_yield')
# -------------------------------------------
def test_calculator(tmp_path : Path):
    '''
    Test yield calculator
    '''
    cmb = Cut(cut = Cuts.cmb, val = 0.99, var = 'mva_cmb')
    prc = Cut(cut = Cuts.prc, val = 0.60, var = 'mva_prc')
    wpt = WorkingPoint(root = [cmb, prc])

    cal = YieldCalculator(
        name    = 'full_scan',
        wp      = wpt,
        q2bin   = Qsq.low,
        trigger = Trigger.rk_ee_os)

    grid = cal.calculate()

    ptr = GridPlotter(grid = grid)
    ptr.plot(path = tmp_path / 'yields.png', randomize = True)
# -------------------------------------------
