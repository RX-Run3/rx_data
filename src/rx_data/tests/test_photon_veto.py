'''
Module with tests for PhotonVeto class
'''

import numpy
import pytest
import mplhep
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib          import Path
from dmu              import LogStore
from rx_data          import PhotonVeto
from rx_data          import EcalCell
from ecal_calibration import calo_translator as ctran

log = LogStore.add_logger('rx_data:test_photon_veto')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:photon_veto', 10)
    plt.style.use(mplhep.style.LHCb2)
# --------------------------------
def _plot_region(
    df        : pnd.DataFrame, 
    name      : str, 
    title     : str,
    out_dir   : Path,
    color     : str  = 'blue', 
    skip_save : bool = False, 
    ax               = None):
    ax=df.plot.scatter(x='x', y='y', color=color, s=3.0, title=title, ax=ax)

    df_veto = df.query('veto == 1')
    ax=df_veto.plot.scatter(x='x', y='y', color='red', s=3.0, ax=ax)

    if name == 'inner':
        ax.set_xlim(-1_000, +1_000)
        ax.set_ylim(-1_000, +1_000)
    else:
        ax.set_xlim(-4_000, +4_000)
        ax.set_ylim(-3_500, +3_500)

    if not skip_save:
        out_path = out_dir / f'{name}.png'
        out_path.parent.mkdir(parents = True, exist_ok = True)

        plt.grid()
        plt.savefig(out_path)
        plt.close()

    return ax
# ----------------------
def _add_veto(
    row : pnd.Series,
    vet : PhotonVeto) -> int:
    '''
    Parameters
    --------------
    row: Series containing row, column, etc
    ver: PhotonVeto instance 

    Returns
    --------------
    1 if cell is meant to be vetoed, 0 otherwise
    '''
    cell = EcalCell(
        row  = row['r'],
        col  = row['c'],
        area = row['a'])
    val = vet.veto_cell(cell = cell)

    return int(val)
# ----------------------
@pytest.mark.parametrize('name'   , ['L1', 'L2'])
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_from_pandas(name : str, version : str):
    '''
    Simplest test
    '''
    size = 1000
    data                         = dict()
    data[f'{name}_BREMHYPOAREA'] = numpy.random.choice(a = [0, 1, 2], size = size)
    data[f'{name}_BREMHYPOROW' ] = numpy.random.randint(low = -60, high = 60, size = size)
    data[f'{name}_BREMHYPOCOL' ] = numpy.random.randint(low =  14, high = 49, size = size)

    df  = pnd.DataFrame(data)
    obj = PhotonVeto(version = version)
    for _, row in df.iterrows():
        obj.veto(
            row = row,
            lepton_name = name)

    if version == 'v0':
        assert obj.nvetoed == 0
    else:
        assert obj.nvetoed >  0

    log.info(f'Photons vetoed: {obj.nvetoed}/{obj.ntotal}')
# ----------------------
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_from_cell(version : str):
    '''
    Simplest test
    '''
    size= 1000
    obj = PhotonVeto(version = version)
    for _ in range(size):
        cell = EcalCell.random()
        obj.veto_cell(cell = cell)

    if version == 'v0':
        assert obj.nvetoed == 0
    else:
        assert obj.nvetoed >  0

    log.info(f'Photons vetoed: {obj.nvetoed}/{obj.ntotal}')
# ----------------------
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_plot_veto_inner(
    tmp_path : Path,
    version  : str):
    '''
    Plot veto in inner detector
    '''
    vet = PhotonVeto(version = version)
    df  = ctran.from_id_to_xy(det='Inner')
    df['veto'] = df.apply(_add_veto, args = (vet,), axis = 1)
    df_veto = df.query('veto == 1')

    title = f'Vetoed: {len(df_veto)}/{len(df)}'
    _plot_region(
        df      = df,
        name    = 'inner',
        title   = title,
        out_dir = tmp_path,
    )
# ----------------------
@pytest.mark.parametrize('version', ['v0', 'v1', 'v2'])
def test_plot_veto_full(
    tmp_path : Path,
    version  : str):
    '''
    Simplest test
    '''
    vet = PhotonVeto(version = version)
    df  = ctran.from_id_to_xy()
    df['veto'] = df.apply(_add_veto, args = (vet,), axis = 1)

    regions = [(2, 'blue'), (1, 'green'), (0, 'black')]
    ax  = None
    for area, color in regions:
        df_reg = df.query(f'a == {area}')
        ax = _plot_region(
            ax       = ax,
            df       = df_reg,
            name     = 'full',
            title    = 'Full ECAL',
            color    = color,
            out_dir  = tmp_path,
            skip_save= True)

    plt.grid()
    plt.savefig(tmp_path / 'all.png')
    plt.close()

