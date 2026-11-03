'''
Module with tests for swap calculator class
'''
import mplhep
import pytest
import matplotlib.pyplot as plt

from dmu       import LogStore
from rx_data   import CandidateRebuilder
from rx_common import Component, Trigger

from rx_data.rdf_getter import RDFGetter

plt.style.use(mplhep.style.LHCb2)
log = LogStore.add_logger('rx_data:test_mass_rebuilder')
# ----------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This runs before any test
    '''
    LogStore.set_level('rx_data:mass_rebuilder'     , 10)
    LogStore.set_level('rx_data:test_mass_rebuilder', 10)
# ----------------------
def test_dzero_misid():
    '''
    Tests dzero decay contamination
    '''
    ientries = 10_000
    gtr = RDFGetter(
        trigger= Trigger.rkst_ee_os,
        sample = Component.data_24)
    rdf = gtr.get_rdf(per_file = False)

    rdf = rdf.Range(100_000, 100_000 + ientries)

    obj = CandidateRebuilder(
        rdf,
        constraint   = (443 , {'L1', 'L2'}),
        tracks       = {'H1', 'H2', 'L1', 'L2'},
        replacements = {'H2' : 2212})
    df  = obj.get_df(
        kind        = 'pandas',
        prefix      = 'kkll',
        progress_bar= True)

    assert ientries == len(df)

    rng= 5000, 6000
    plt.hist(df['kkll_mass_old'], bins = 100, alpha = 0.7, range=rng, label = 'Old')
    plt.hist(df['kkll_mass_new'], bins = 100, alpha = 0.7, range=rng, label = 'New')
    plt.legend()
# ----------------------------------
