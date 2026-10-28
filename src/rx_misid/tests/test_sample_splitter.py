'''
Module with functions meant to test SampleSplitter class
'''
import os

import numpy
import pytest
import mplhep
import matplotlib.pyplot as plt
import pandas            as pnd

from pathlib        import Path
from ROOT           import RDF

from dmu            import LogStore
from dmu.workflow   import Cache
from dmu.generic    import utilities   as gut

from rx_selection   import selection   as sel
from rx_common      import Component, Trigger
from rx_data        import RDFGetter
from rx_misid       import SampleSplitter
from rx_misid.types import MisIDSampleSplitting

log=LogStore.add_logger('rx_misid:test_data_splitter')
# -------------------------------------------------------
class Data:
    '''
    Data class
    '''
    plt.style.use(mplhep.style.LHCb2)
    user    = os.environ['USER']
# -------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_misid:test_splitter', 10)
    LogStore.set_level('rx_misid:splitter'     , 10)
    LogStore.set_level('rx_data:rdf_getter'    , 30)
    LogStore.set_level('rx_data:path_splitter' , 30)
# -------------------------------------------------------
def _get_rdf(sample : Component, trigger : Trigger):
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)
    uid = gtr.get_uid()
    with sel.custom_selection(d_sel = {'pid_l' : '(1)'}):
        rdf = sel.apply_full_selection(
            rdf    = rdf,
            uid    = uid,
            q2bin  = 'central',
            process= sample,
            trigger= trigger)

    return rdf
# -------------------------------------------------------
def _plot_simulation_pide(
    df       : pnd.DataFrame, 
    tmp_path : Path,
    sample   : str) -> None:
    '''
    Parameters
    ---------------
    df    : Pandas dataframe with tagged candidates
    sample: E.g. Bu_Kee_eq_btosllball05_DPC...
    '''
    for hadron, df_hadr in df.groupby('hadron'):
        ax = None
        ax = df_hadr.plot.scatter(x='L1_PIDe', y='L1_ProbNNe', color='blue', s=1, label='$e_{SS}$', ax=ax)
        ax = df_hadr.plot.scatter(x='L2_PIDe', y='L2_ProbNNe', color='red' , s=1, label='$e_{OS}$', ax=ax)

        plot_path = tmp_path / f'{sample}_{hadron}.png'

        ax.set_xlabel(r'$\Delta LL (e)$')
        ax.set_ylabel('ProbNN(e)')

        bname = '$B^+$'
        plt.title(f'{hadron}; {bname}')
        plt.savefig(plot_path)
        plt.close()
# -------------------------------------------------------
def _check_mc_stats(rdf : RDF.RNode, df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    rdf : ROOT dataframe used as input when doing MC tests
    df  : Pandas dataframe in the output
    '''
    ninput = rdf.Count().GetValue()
    noutput= len(df)

    assert ninput == noutput

    arr_block_rdf = rdf.AsNumpy(['block'])['block']
    arr_block_pnd = df['block'].to_numpy()

    # Use sequence of blocks to check that
    # There is no shufflign of entries for MC
    assert numpy.array_equal(arr_block_rdf, arr_block_pnd)
# ----------------------
def _check_columns(df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    df: Pandas dataframe produced by SampleSplitter
    '''
    s_expected = {
        'B_Mass',
        'B_Mass_smr',
        'block',
        'L1_HASBREM',
        'L2_HASBREM',
        'L1_PIDe',
        'L2_PIDe',
        'L1_ProbNNe',
        'L2_ProbNNe',
        'L1_TRACK_PT',
        'L1_TRACK_ETA',
        'L2_TRACK_PT',
        'L2_TRACK_ETA',
        'weight',
        'hadron'}

    assert set(df.columns) == s_expected
# -------------------------------------------------------
@pytest.mark.parametrize('sample', [
    'Bu_piplpimnKpl_eq_sqDalitz_DPC',
    'Bu_KplKplKmn_eq_sqDalitz_DPC'])
def test_simulation(sample : str, tmp_path : Path):
    '''
    Tests getting split dataset
    '''
    log.info('')

    rdf   = _get_rdf(
        sample = Component(sample),
        trigger= Trigger.rk_ee_nopid)

    data = gut.load_data(package='rx_misid_data', fpath='splitting.yaml')
    cfg  = MisIDSampleSplitting(**data)

    with Cache.cache_root(path = tmp_path):
        spl = SampleSplitter(rdf = rdf, cfg = cfg)
        df  = spl.get_sample()

    log.info('Dataframe found, checking')
    _plot_simulation_pide(df=df, sample=sample, tmp_path = tmp_path)
    _check_mc_stats(rdf=rdf, df=df)
    _check_columns(df=df)
# -------------------------------------------------------
