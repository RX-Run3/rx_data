'''
Module holding tests for yield classes
'''
import matplotlib.pyplot as plt

from fitter          import YieldGrid
from rx_common       import Cuts, Cut, Trigger, WorkingPoint, Qsq
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
