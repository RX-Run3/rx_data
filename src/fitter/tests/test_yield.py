'''
Module holding tests for yield classes
'''
import matplotlib.pyplot as plt

from fitter          import Yield, YieldGrid
from rx_common       import Cuts, Cut, Trigger, WorkingPoint, Qsq
from rx_efficiencies import Efficiency
from dmu             import LogStore
from pathlib         import Path
from fitter          import YieldCalculator

log=LogStore.add_logger('fitter:test_yield')
# -----------------------------------
def _plot_values(
    grid    : YieldGrid,
    out_dir : Path) -> None:
    '''
    Plot dataframe as an interpolated mesh
    '''
    df      = grid.df
    pivoted = df.pivot(
            index  ='prc',
            columns='cmb',
            values ='yld')

    v1 : float = pivoted.columns.min() # type: ignore
    v2 : float = pivoted.columns.max() # type: ignore
    v3 : float = pivoted.index.min()
    v4 : float = pivoted.index.max()

    plt.imshow(
        pivoted.values,
        origin='lower',
        extent=(v1, v2, v3, v4),
        cmap='viridis',
        interpolation='bilinear',
    )

    plt.title('Yields vs WP')
    plt.colorbar(label='z')
    plt.xlabel('MVA${}_{comb}$')
    plt.ylabel('MVA${}_{prec}$')
    plt.tight_layout()

    out_path = out_dir / 'yields.png'
    plt.savefig(out_path)
    plt.close()
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
def test_calculator(tmp_path : Path):
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

    _plot_values(grid = grid, out_dir = tmp_path)
# -------------------------------------------
def test_add_grids():
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld_11 = Yield(val = 100, err = 10, wp = wpt)
    yld_12 = Yield(val = 200, err = 10, wp = wpt)
    yld_21 = Yield(val = 300, err = 10, wp = wpt)
    yld_22 = Yield(val = 400, err = 10, wp = wpt)

    grid_1 = YieldGrid(root = [yld_11, yld_12])
    grid_2 = YieldGrid(root = [yld_21, yld_22])

    grid_3 = grid_1 + grid_2

    assert grid_3.size == grid_1.size == grid_2.size

    for index in range(grid_3.size):
        assert grid_1.root[index] + grid_2.root[index] == grid_3.root[index]
# -------------------------------------------
