'''
Module testing the MassCalculator class
'''
import os
import pytest
import numpy
import pandas            as pnd
import matplotlib.pyplot as plt

from pathlib   import Path
from ROOT      import RDF
from dmu       import LogStore
from rx_common import Component, Trigger
from rx_data   import RDFGetter
from rx_data   import MassCalculator

log=LogStore.add_logger('rx_data:test_mass_calculator')
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:test_mass_calculator', 10)
    LogStore.set_level('rx_data:mass_calculator'     , 10)
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    user     = os.environ['USER']
    plot_dir = Path(f'/tmp/{user}/tests/rx_data/mass_calculator')
# ----------------------
def _check_entries(rdf_in : RDF.RNode, rdf_ot : RDF.RNode) -> None:
    '''
    Parameters
    -------------
    rdf_in/ot: Input/Output dataframe
    '''
    log.debug('Checking number of entries')

    nent_in = rdf_in.Count().GetValue()
    nent_ot = rdf_ot.Count().GetValue()

    assert nent_in == nent_ot
# ----------------------
def _closure_check(df : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------
    df : Dataframe with arrays with masses
    '''
    log.debug('Run closure check')

    arr_mass_def = df['B_M'         ].dropna().to_numpy()
    arr_mass_cal = df['B_Mass_check'].dropna().to_numpy()

    assert numpy.allclose(arr_mass_def, arr_mass_cal, rtol=0.001)
# ----------------------
def _validate_rdf(
    test   : str,
    name   : str,
    rdf_in : RDF.RNode,
    rdf_ot : RDF.RNode) -> None:
    '''
    Parameters
    -------------
    test  : Test name, for naming output directory
    name  : Name of output in test, used for naming output plots
    rdf_in: Original dataframe
    rdf_ot: DataFrame with EVENTNUMBER, RUNNUMBER and masses
    '''
    _check_entries(rdf_in=rdf_in, rdf_ot=rdf_ot)

    data = rdf_ot.AsNumpy()
    df   = pnd.DataFrame(data)

    _closure_check(df=df)

    assert set(df.columns) == {'EVENTNUMBER', 'RUNNUMBER', 'B_Mass_hdkk', 'B_Mass_hdpipi', 'B_M', 'B_Mass_check'}

    plt.hist(df['B_Mass_hdkk'  ], range=(4500, 7000), bins=50, histtype='step', ls='-', label=r'$H_s K^+K^+$')
    plt.hist(df['B_Mass_hdpipi'], range=(4500, 7000), bins=50, histtype='step', ls='-', label=r'$H_s \pi^+\pi^-$')
    plt.hist(df['B_Mass_check' ], range=(4500, 7000), bins=50, histtype='step', ls='-', label='Check'   , color='red')
    plt.hist(df['B_M']          , range=(4500, 7000), bins=50, histtype='step', ls=':', label='Original', color='black')

    plt.legend()
    plt.axvline(x=5280, label='PDG', linestyle=':', c='black', lw=2)

    out_dir = Data.plot_dir/test
    out_dir.mkdir(parents=True, exist_ok=True)

    plt.title(f'Sample={name}')
    plt.savefig(out_dir/f'{name}.png')
    plt.close()
# ----------------------
@pytest.mark.parametrize('sample', [
    Component.bpkpee,
    Component.bpkpipi,
    Component.bpkkk])
def test_hadronic_mc(sample : Component):
    '''
    Will run test where
    Kee -> KKK   in B_Mass_kkk
    Kee -> Kpipi in B_Mass_kpipi

    for simulated samples
    '''
    with RDFGetter.max_entries(value=10_000):
        gtr = RDFGetter(
            sample  = sample,
            trigger = Trigger.rk_ee_nopid)
        rdf_in = gtr.get_rdf(per_file=False)

    cal    = MassCalculator(rdf=rdf_in, with_validation=True)
    rdf_ot = cal.get_rdf()

    _validate_rdf(rdf_in=rdf_in, rdf_ot=rdf_ot, test='hadronic_mc', name=sample)
# ----------------------
@pytest.mark.parametrize('sample' , [Component.data_24_md_c2])
@pytest.mark.parametrize('trigger', [Trigger.rk_ee_os, Trigger.rk_ee_misid])
def test_hadronic_data(sample : Component, trigger : Trigger):
    '''
    Will run test where
    Kee -> KKK   in B_Mass_kkk
    Kee -> Kpipi in B_Mass_kpipi

    for data samples
    '''
    with RDFGetter.max_entries(value=10_000):
        gtr = RDFGetter(
            sample  = sample,
            trigger = trigger)
        rdf_in = gtr.get_rdf(per_file=False)

    cal    = MassCalculator(rdf=rdf_in, with_validation=True)
    rdf_ot = cal.get_rdf()

    _validate_rdf(rdf_in=rdf_in, rdf_ot=rdf_ot, test='hadronic_data', name=f'{sample}_{trigger}')
