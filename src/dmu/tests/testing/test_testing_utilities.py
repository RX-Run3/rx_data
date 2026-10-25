'''
Module with unit tests for testing/utilities.py functions
'''
import pytest

from ROOT        import RDF
from dmu         import LogStore
from dmu.testing import utilities as ut

log = LogStore.add_logger('dmu:tests:test_utilities')
# ----------------------------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    LogStore.set_level('dmu:testing:utilities', 10)
# ----------------------------------------------
def _check_rdf(rdf : RDF.RNode) -> None:
    log.info('')
    rdf.Display(nRows=20).Print()
# ----------------------------------------------
def test_get_rdf():
    '''
    Test for toy dataframe getter
    '''
    rdf = ut.get_rdf(kind='sig', nentries=10)
    _check_rdf(rdf)

    rdf = ut.get_rdf(kind='bkg', nentries=10)
    _check_rdf(rdf)
# ----------------------------------------------
def test_get_rdf_with_nans():
    '''
    Test for toy dataframe getter
    '''
    rdf = ut.get_rdf(kind='sig', nentries=10, columns_with_nans=['y', 'z'])
    _check_rdf(rdf)

    rdf = ut.get_rdf(kind='bkg', nentries=10, columns_with_nans=['y', 'w'])
    _check_rdf(rdf)
# ----------------------------------------------
def test_build_friend_structure():
    '''
    Tests function that builds files needed to test friend tree dependent code
    '''
    log.info('Testing build_friend_structure')
    ut.build_friend_structure('friends.yaml', nentries=100)
# ----------------------------------------------
def test_get_models():
    '''
    Tests the get_models function
    '''
    rdf_sig = ut.get_rdf(kind='sig')
    rdf_bkg = ut.get_rdf(kind='bkg')

    l_model, _ = ut.get_models(
        rdf_sig,
        rdf_bkg)

    assert len(l_model) == 3
# ----------------------------------------------

