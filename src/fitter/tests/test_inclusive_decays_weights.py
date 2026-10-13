'''
Module with tests for Reader class in inclusive_decays_weights module
'''

import os
import pytest
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib                         import Path
from ROOT                            import RDF
from dmu                             import LogStore
from rx_data                         import RDFGetter
from rx_common                       import Trigger
from rx_common                       import Component
from fitter.inclusive_decays_weights import read_weight 

log=LogStore.add_logger('fitter:test_inclusive_decays_weights')

_SAMPLES = [
    (Component.bdjpsixee, Trigger.rk_ee_os  ),
    (Component.bpjpsixee, Trigger.rk_ee_os  ),
    (Component.bsjpsixee, Trigger.rk_ee_os  ),
    # -------------
    (Component.bdjpsixee, Trigger.rkst_ee_os),
    (Component.bpjpsixee, Trigger.rkst_ee_os),
    (Component.bsjpsixee, Trigger.rkst_ee_os),
    # -------------
    (Component.bdjpsixmm, Trigger.rk_mm_os  ),
    (Component.bpjpsixmm, Trigger.rk_mm_os  ),
    (Component.bsjpsixmm, Trigger.rk_mm_os  ),
    # -------------
    (Component.bdjpsixmm, Trigger.rkst_mm_os),
    (Component.bpjpsixmm, Trigger.rkst_mm_os),
    (Component.bsjpsixmm, Trigger.rkst_mm_os),
]
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:decay_reader', 10)
#-----------------------------------------------
def _rdf_to_idf(rdf : RDF.RNode) -> pnd.DataFrame:
    rdf   =rdf.Define('mass', 'B_const_mass_M')
    v_name=rdf.GetColumnNames()
    l_name=[ name.c_str() for name in v_name ]
    l_name=[ name for name in l_name if 'TRUEID' in name or 'MOTHER_ID' in name] + ['mass']

    d_id = rdf.AsNumpy(l_name)

    df = pnd.DataFrame(d_id)

    return df
#-----------------------------------------------
def _get_df(
    sample  : Component, 
    trigger : Trigger) -> pnd.DataFrame:
    gtr = RDFGetter(sample = sample, trigger = trigger)
    rdf = gtr.get_rdf(per_file=False)
    df  = _rdf_to_idf(rdf)

    return df
#-----------------------------------------------
def _plot_mass(
    df       : pnd.DataFrame, 
    sample   : str, 
    test     : str, 
    tmp_path : Path):
    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    ax1.hist(df.mass, bins=50, range=[4500, 6000], histtype='step', density=True, label='Unweighted', )
    ax1.hist(df.mass, bins=50, range=[4500, 6000], histtype='step', density=True, label='Weighted'  , weights=df.weight)

    nevs=df.weight.size
    area=df.weight.sum()

    title = f'{sample}; evs: {nevs}; sum: {area:.0f}'

    ax1.set_title(title)
    ax1.legend()

    ax2.hist(df.weight, bins=50, edgecolor='black')

    out_dir = tmp_path / test
    os.makedirs(out_dir, exist_ok=True)

    out_path = out_dir / f'{sample}.png'

    plt.savefig(out_path)
    plt.close()
#-----------------------------------------------
@pytest.mark.parametrize('sample, trigger', _SAMPLES)
def test_simple(
    sample   : Component, 
    trigger  : Trigger, 
    tmp_path : Path):
    '''
    Simplest test of addition of weights
    '''
    with RDFGetter.max_entries(100_000):
        df = _get_df(
            sample = sample, 
            trigger = trigger)

    df['weight'] = df.apply(read_weight, args=(trigger.project,), axis=1)

    _plot_mass(df, sample, f'{sample}_{trigger}', tmp_path = tmp_path)
#-----------------------------------------------
