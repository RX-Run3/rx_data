'''
Module with tests for swap calculator class
'''
import mplhep
import pytest
import matplotlib.pyplot as plt

from ROOT      import RDF # type: ignore
from dmu       import LogStore
from dmu.stats import CandidateRebuilder

plt.style.use(mplhep.style.LHCb2) # type: ignore
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
def _get_rdf(ientries : int) -> RDF.RNode:
# ----------------------
def test_dzero_misid():
    '''
    Tests dzero decay contamination
    '''
    ientries = 10_000
    rdf      = _get_rdf(ientries = ientries)

    obj = CandidateRebuilder(
        rdf, 
        constraint   = (443 , {'L1', 'L2'}),
        tracks       = {'H1', 'H2', 'L1', 'L2'},
        replacements = {'H1' : 321, 'H2' : 2212})
    df  = obj.get_df(
        format      = 'pandas',
        prefix      = 'kkll',
        progress_bar= True)

    assert ientries == len(df)

    rng= 5000, 6000
    plt.hist(df['kkll_mass_old'], bins = 100, alpha = 0.7, range=rng, label = 'Old')
    plt.hist(df['kkll_mass_new'], bins = 100, alpha = 0.7, range=rng, label = 'New')
    plt.legend()
# ----------------------------------
