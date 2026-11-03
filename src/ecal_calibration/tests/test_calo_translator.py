'''
Module with functions meant to test the row,col <-> x,y translation
'''
import pytest
import pandas             as pnd
import matplotlib.pyplot  as plt

from pathlib               import Path
from matplotlib            import patches
from dmu.logging.log_store import LogStore
from ecal_calibration      import calo_translator as ctran

log=LogStore.add_logger('ecal_calibration:test_calo_translator')

subdetectors = [
            'Inner',
            'Middle',
            'Outer']
# --------------------------------
def _plot_boundaries(ax):
    x1 = -2_000
    y1 = -1_200

    x2 =  2_000
    y2 =  1_200

    height= y2 - y1
    width = x2 - x1

    rectangle = patches.Rectangle((min(x1, x2), min(y1, y2)), width, height, edgecolor='red', facecolor='none', linewidth=2)
    ax.add_patch(rectangle)

    x1 = -1_000
    y1 =   -680

    x2 =  1_000
    y2 =   +680

    height= y2 - y1
    width = x2 - x1

    rectangle = patches.Rectangle((min(x1, x2), min(y1, y2)), width, height, edgecolor='red', facecolor='none', linewidth=2)
    ax.add_patch(rectangle)
# --------------------------------
def _plot_translation(
    df      : pnd.DataFrame,
    out_dir : Path,
    row     : int,
    col     : int,
    det     : str,
    name    : str):
    if len(df) != 1:
        print(df)
        raise ValueError(f'Dataframe does not have one and only one element for: {row}/{col}/{name}')

    ax = df.plot.scatter(x='x', y='y', color='blue', title=f'Det={det}; Row={row}; Col={col}')
    ax.set_xlim(-6_000, +6_000)
    ax.set_ylim(-4_000, +4_000)

    _plot_boundaries(ax)

    fname = f'{det}_{row:03}_{col:03}.png'
    out_path = out_dir / name / fname
    out_path.parent.mkdir(parents = True, exist_ok=True)

    plt.savefig(out_path)
    plt.close()
# --------------------------------
def _plot_region(
    df        : pnd.DataFrame,
    det       : str,
    name      : str,
    out_dir   : Path,
    color     : str  = 'blue',
    skip_save : bool = False,
    ax               = None):
    ax=df.plot.scatter(x='x', y='y', color=color, s=0.1, title=det, ax=ax)
    ax.set_xlim(-4_000, +4_000)
    ax.set_ylim(-3_500, +3_500)

    if not skip_save:
        out_path = out_dir / name / f'{det}.png'
        out_path.parent.mkdir(parents = True, exist_ok = True)

        plt.grid()
        plt.savefig(out_path)
        plt.close()

    return ax
# --------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This function will execute before the tests
    '''
    LogStore.set_level('rx_data:calo_translator', 10)
# --------------------------------
def test_load():
    '''
    Tests loading data to dataframe
    '''
    log.info('')
    df = ctran.get_data()
    log.info('\n' + str(df))
    log.info(df.dtypes)
# --------------------------------
def test_read_xy():
    '''
    Tests reading XY coordinates, given row and column
    '''
    row = 10
    col = 10

    df     = ctran.get_data()
    in_row = df.r == row
    in_col = df.c == col

    df     = df[in_row & in_col]

    print(df)
# --------------------------------
def test_plot_row_col(tmp_path : Path):
    '''
    Plots row and column histograms
    '''
    df     = ctran.get_data()
    df.c.hist(bins=64, histtype='step', linestyle='-', label='column')
    df.r.hist(bins=64, histtype='step', linestyle=':', label='row')
    plt.legend()
    plt.savefig(tmp_path / 'row_col.png')
    plt.close()
# --------------------------------
def test_plot_xyz(tmp_path : Path):
    '''
    Tests plotting X and Y coodinates
    '''
    df     = ctran.get_data()
    df.x.hist(bins=50, histtype='step', label='x')
    df.y.hist(bins=50, histtype='step', label='y')
    df.z.hist(bins=50, histtype='step', label='z')
    plt.legend()
    plt.savefig(tmp_path / 'xyz.png')
    plt.close()
# --------------------------------
@pytest.mark.parametrize('det', subdetectors)
def test_scan_dets(det : str, tmp_path : Path):
    '''
    Tests translation from row and column to x and y
    '''
    df = ctran.from_id_to_xy(det=det)

    _plot_region(
        df      = df,
        det     = det,
        out_dir = tmp_path,
        name    ='detector_scan')
# --------------------------------
def test_overlay_detectors(tmp_path : Path):
    '''
    Tests translation from row and column to x and y
    '''
    ax = None
    for det, color in [('Inner', 'red'), ('Middle', 'green'), ('Outer', 'blue')]:
        df = ctran.from_id_to_xy(det=det)
        ax = _plot_region(
            df,
            det,
            out_dir   = tmp_path,
            name      = 'detector_scan',
            color     = color,
            skip_save = True,
            ax        = ax)

    plt.grid()
    plt.savefig(tmp_path / 'overlay_detectors.png')
    plt.close()
# --------------------------------
def test_fully_defined():
    '''
    Tests translation from row and column to x and y
    '''
    x1, y1 = ctran.from_id_to_xy(row=14, col=35, det ='Inner')
    x2, y2 = ctran.from_id_to_xy(row=14, col=35, area=      2)

    assert x1 == x2
    assert y1 == y2
# --------------------------------
