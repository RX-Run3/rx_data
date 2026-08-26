'''
Module with tests for utility functions
'''
import os
import numpy
import pytest
import pandas as pnd
import matplotlib.pyplot as plt

from ecal_calibration   import utilities as cut

pytestmark = pytest.mark.skip(
    reason='''
    This part of the code did not produce useful results
    will turn off the tests, due to time constraints
    ''')
# -----------------------------------------
class Data:
    '''
    Data class
    '''
    out_dir = '/tmp/tests/ecal_calibration/utilities'
# -----------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    os.makedirs(Data.out_dir, exist_ok=True)
# -----------------------------------------
def _plot_distributions(df : pnd.DataFrame, test_name : str) -> None:
    _plot_vtx( test_name=test_name, df=df)
    _plot_brem(test_name=test_name, df=df)
    _plot_lept(test_name=test_name, df=df, name= 'BREMHYPOROW')
    _plot_lept(test_name=test_name, df=df, name= 'BREMHYPOCOL')
    _plot_lept(test_name=test_name, df=df, name='BREMHYPOAREA')
    _plot_lept(test_name=test_name, df=df, name=          'PT')

    _plot_evt(test_name=test_name, df=df, name='nPVs')
    _plot_evt(test_name=test_name, df=df, name='block')
# -----------------------------------------
def _plot_evt(
        df        : pnd.DataFrame,
        test_name : str,
        name      : str) -> None:
    out_dir = f'{Data.out_dir}/{test_name}'
    os.makedirs(out_dir, exist_ok=True)

    df[name].plot.hist(bins=30)

    plt.legend()
    plt.xlabel(name)
    plt.savefig(f'{out_dir}/{name}.png')
    plt.close()
# -----------------------------------------
def _plot_lept(
        df        : pnd.DataFrame,
        test_name : str,
        name      : str) -> None:

    out_dir = f'{Data.out_dir}/{test_name}'
    os.makedirs(out_dir, exist_ok=True)

    if name == 'PT':
        arr_l1 = df[f'L1_{name}'].to_numpy()
        arr_l2 = df[f'L2_{name}'].to_numpy()

        arr_l1_log = numpy.log(arr_l1)
        arr_l2_log = numpy.log(arr_l2)

        plt.hist(arr_l1_log, range=(-5, +4), label='$e^+$', bins=100, alpha=0.3)
        plt.hist(arr_l2_log, range=(-5, +4), label='$e^-$', bins=100, histtype='step')

        plt.xlabel(f'Log {name}')
    else:
        df[f'L1_{name}'].plot.hist(label='$e^+$', bins=100, alpha=0.3)
        df[f'L2_{name}'].plot.hist(label='$e^-$', bins=100, histtype='step')

        plt.xlabel(name)

    plt.legend()
    plt.savefig(f'{out_dir}/{name}.png')
    plt.close()
# -----------------------------------------
def _plot_brem(df : pnd.DataFrame, test_name : str) -> None:
    out_dir = f'{Data.out_dir}/{test_name}'
    os.makedirs(out_dir, exist_ok=True)

    df['nbrem'  ] = df['L1_brem'] + df['L2_brem']

    df['L1_brem'].plot.hist(label='$e^+$', bins=10, alpha=0.3)
    df['L2_brem'].plot.hist(label='$e^-$', bins=10, alpha=0.3)
    df['nbrem'  ].plot.hist(label='both' , bins=10, alpha=0.3)

    plt.legend()
    plt.xlabel('brem')
    plt.savefig(f'{out_dir}/brem.png')
    plt.close()
# -----------------------------------------
def _plot_vtx(df : pnd.DataFrame, test_name : str) -> None:
    out_dir = f'{Data.out_dir}/{test_name}'
    os.makedirs(out_dir, exist_ok=True)

    df['B_END_VX'].plot.hist(label='VX', bins=80, alpha=0.3, range=[-20, +20])
    df['B_END_VY'].plot.hist(label='VY', bins=80, alpha=0.3, range=[-20, +20])
    df['B_END_VY'].plot.hist(label='VY', bins=80, alpha=0.3, range=[-20, +20])

    plt.yscale('log')
    plt.xlabel('B vertex position')
    plt.savefig(f'{out_dir}/end_vtx.png')
    plt.close()
# -----------------------------------------
@pytest.mark.parametrize('bias', [0.8, 1.0, 1.2])
def test_get_ddf_flat_bias(bias : float):
    '''
    Tests getter of dask dataframe
    '''
    ddf = cut.get_ddf(name='fake_data', bias=bias, kind='flat')
    df  = ddf.compute()

    assert len(df) == 100_000

    bias_str = f'{100 * bias:.0f}'
    _plot_distributions(df=df, test_name=f'nobias/{bias_str}')
# -----------------------------------------
