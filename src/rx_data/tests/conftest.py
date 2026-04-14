'''
This module is needed to control how pytest will run tests
'''
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import mplhep
import pytest
import pandas            as pnd
import matplotlib.pyplot as plt
from dmu.logging.log_store import LogStore
from _pytest.config        import Config
from rx_data.rdf_getter    import RDFGetter
from rx_data               import collector as col

# ------------------------------
class Data:
    '''
    Data class
    '''
    user    = os.environ['USER']
    out_dir = f'/tmp/{user}/tests/rx_data'
# ------------------------------
def pytest_configure(config : Config):
    '''
    This will run before any test by pytest
    '''
    _config = config

    LogStore.set_level('rx_data:mass_calculator'          , 10)
    LogStore.set_level('rx_data:mva_calculator'           , 10)
    LogStore.set_level('rx_data:test_mva_calculator'      , 10)
    LogStore.set_level('rx_data:rdf_getter12'             , 10)
    LogStore.set_level('rx_data:rdf_getter'               , 10)
    LogStore.set_level('rx_selection:selection'           , 30)
    LogStore.set_level('dmu:ml:cv_predict'                , 30)
# -----------------------------------------------
@pytest.fixture
def only_main():
    """
    Turns off all the friend trees
    """
    with RDFGetter.only_friends(s_friend=set()):
        yield
# -----------------------------------------------
@pytest.fixture(scope='session')
def out_dir() -> str:
    '''
    This is a fixture meant to be passed as an argument
    to the tests to make the path to the output directory
    available to them
    '''
    user = os.environ['USER']
    path = f'/tmp/{user}/tests/rx_data'
    os.makedirs(path, exist_ok=True)

    return path
# ------------------------------
def pytest_sessionfinish(session, exitstatus):
    '''
    Used to post-process outputs of tests
    '''
    plt.style.use(mplhep.style.LHCb2)

    if 'selection' not in col.Collector.data:
        return

    df = col.Collector.data['selection']
    _plot_selection(df = df)
# ------------------------------
def _plot_selection(df : pnd.DataFrame):
    plot_dir = f'{Data.out_dir}/selection'
    os.makedirs(plot_dir, exist_ok=True)

    for sample, df_sam in df.groupby('sample'):
        df_sam = df_sam.drop(columns='sample')
        for q2bin, df_qsq in df_sam.groupby('q2bin'):
            df_qsq = df_qsq.drop(columns='q2bin')

            _compare_smearing(df=df_qsq, plot_name=f'{sample}_{q2bin}', plot_dir=plot_dir)
# ------------------------------
def _compare_smearing(df : pnd.DataFrame, plot_name : str, plot_dir : str) -> None:
    ax = None
    for smeared, df_smr in df.groupby('smeared'):
        df_smr= _add_eff(df=df_smr)
        label = 'Smeared' if smeared else 'Unsmeared'
        ax    = df_smr.plot(x='cut', y='Eff', label=label, ax=ax)

    plot_path = f'{plot_dir}/{plot_name}.png'

    plt.title(plot_name)
    plt.yscale('log')
    plt.savefig(plot_path)
    plt.close()
# ------------------------------
def _add_eff(df : pnd.DataFrame) -> pnd.DataFrame:
    df['Eff'] = df['Passed'] / df['All']
    df['Cum'] = df['Eff'].cumprod()

    return df
# ------------------------------
