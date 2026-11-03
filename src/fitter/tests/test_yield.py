'''
Module holding tests for yield classes
'''
import numpy
import matplotlib.pyplot as plt

from dmu.generic     import LinkedNode
from rx_plotter      import GridPlotter
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

    yld = Yield(val = 300, err = 10, wp = WorkingPoint.empty())
    eff = Efficiency(gen = 1000, sel = 10, wp = wpt)

    yld_1 = yld * eff
    yld_2 = eff * yld

    assert yld_1 == yld_2

    assert yld_1.val == yld.val * eff.sel / eff.gen

    log.info(yld)
    log.info(eff)
    log.info(yld_1)
# -------------------------------------------
def test_ratio_eff():
    '''
    Test ration with efficiency
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
def test_ratio_yld():
    '''
    Test ration with efficiency
    '''
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld = Yield(val = 300, err = 10, wp = wpt)

    rat = yld       / yld
    ran = yld.gauss / yld.gauss

    assert numpy.isclose(rat.val , ran.mean)
    assert numpy.isclose(rat.err , ran.sdev)

    print(rat)
# -------------------------------------------
def test_sqrt():
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    val = Yield(val = 300, err = 10, wp = wpt)
    sqr = val.sqrt

    assert numpy.isclose(sqr.val * sqr.val, val.val)
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
        name    = 'full_scan',
        wp      = wpt,
        q2bin   = Qsq.low, # for tests, should be rare otherwise
        trigger = Trigger.rk_ee_os)

    grid = cal.calculate()

    _plot_values(grid = grid, out_dir = tmp_path)
# -------------------------------------------
def test_add_grids():
    yields : list[Yield] = []
    for val in [0.1, 0.2, 0.3, 0.4]:
        cut = Cut(cut = Cuts.cmb, val = val, var = 'mva_cmb')
        wpt = WorkingPoint(root = [cut])
        yld = Yield(val = 100 * val, err = 10, wp = wpt)
        yields.append(yld)

    grid_1 = YieldGrid(root = yields)
    grid_2 = YieldGrid(root = yields)
    grid_3 = grid_1 + grid_2

    assert grid_3.size == grid_1.size == grid_2.size

    for index in range(grid_3.size):
        assert grid_1.root[index] + grid_2.root[index] == grid_3.root[index]
# -------------------------------------------
def test_sqrt_grids():
    cut = Cut(cut = Cuts.cmb, val = 0.5, var = 'mva_cmb')
    wpt = WorkingPoint(root = [cut])

    yld_11 = Yield(val = 100, err = 10, wp = wpt)
    yld_12 = Yield(val = 200, err = 10, wp = wpt)
    yld_21 = Yield(val = 300, err = 10, wp = wpt)
    yld_22 = Yield(val = 400, err = 10, wp = wpt)

    grid   = YieldGrid(root = [yld_11, yld_12, yld_21, yld_22])
    sqrt   = grid.sqrt

    for val, sqr in zip(grid.root, sqrt.root, strict = True):
        assert numpy.isclose(val.val, sqr.val * sqr.val)
# -------------------------------------------
def test_ratio_grids():
    yields : list[Yield] = []
    for val in [0.1, 0.2, 0.3, 0.4]:
        cut = Cut(cut = Cuts.cmb, val = val, var = 'mva_cmb')
        wpt = WorkingPoint(root = [cut])
        yld = Yield(val = 100 * val, err = 10, wp = wpt)

        yields.append(yld)

    grid_num = YieldGrid(root = yields)
    grid_den = YieldGrid(root = yields)
    grid_rat = grid_num / grid_den

    for rat, num, den in zip(grid_rat.root, grid_num.root, grid_den.root, strict = True):
        cal = num.gauss / den.gauss

        assert numpy.isclose(rat.val , cal.mean)
        assert numpy.isclose(rat.err , cal.sdev)
# -------------------------------------------
def test_from_linked_node():
    '''
    Test building of Yield from LinkedNode
    '''
    loc   = 0.1, 0.2
    lnode = LinkedNode(
        val         = 1.3,
        err         = 0.2,
        coordinates = loc)

    cmb_cut = Cut(cut = Cuts.cmb, val = 1.1, var = 'mva_cmb')
    prc_cut = Cut(cut = Cuts.prc, val = 1.2, var = 'mva_prc')
    wp      = WorkingPoint(root = [cmb_cut, prc_cut])

    node    = Yield.from_linked_node(wp = wp, lnode = lnode)

    assert node.wp.location == loc
# -------------------------------------------
def test_patch_grids(tmp_path : Path):
    '''
    Test of grid patching, i.e. filling holes with
    average of sorrounding nodes
    '''
    yields : list[Yield] = []
    for cmb in [0.1, 0.2, 0.3, 0.4]:
        for prc in [0.1, 0.2, 0.3, 0.4]:
            if prc == 0.2 and cmb == 0.2: # noqa: PLR2004
                continue

            if prc == 0.4 and cmb == 0.4: # noqa: PLR2004
                continue

            if prc == 0.4 and cmb == 0.1: # noqa: PLR2004
                continue

            cmb_cut = Cut(cut = Cuts.cmb, val = cmb, var = 'mva_cmb')
            prc_cut = Cut(cut = Cuts.prc, val = prc, var = 'mva_prc')

            wpt = WorkingPoint(root = [cmb_cut, prc_cut])
            yld = Yield(val = 100 * cmb * prc, err = 10, wp = wpt)

            yields.append(yld)

    grid = YieldGrid(root = yields)

    for name, this_grid in {'original' : grid, 'patched' : grid.patched}.items():
        ptr = GridPlotter(grid = this_grid)
        ptr.plot(path = tmp_path / f'{name}.png', randomize = False)
# -------------------------------------------
