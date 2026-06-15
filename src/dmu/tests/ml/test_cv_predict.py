'''
Contains unit tests for CVPredict class
'''

import pytest

import numpy

import dmu.testing.utilities as ut

from pathlib               import Path
from dmu.logging.log_store import LogStore
from dmu.ml.cv_predict     import CVPredict

log = LogStore.add_logger('dmu:ml:tests:cv_predict')
#--------------------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:ml:cv_predict', 10)
    LogStore.set_level('dmu:ml:utilities' , 10)
    LogStore.set_level('dmu:testing:utilities', 10)
    LogStore.set_level('dmu:ml:train_mva' , 20)
#--------------------------------------------------------------------
def _check_probabilities(arr_prb : numpy.ndarray, has_negative : bool) -> None:
    n_above = int(numpy.sum(arr_prb > 1))
    n_below = int(numpy.sum(arr_prb < 0))

    if n_above != 0:
        log.error(f'Found {n_above} elements above 1')

    if n_below != 0 and not has_negative:
        log.error(f'Found {n_below} elements below 0')

    assert n_above == 0

    if has_negative:
        assert n_below >  0
    else:
        assert n_below == 0
#--------------------------------------------------------------------
def test_unused_fold(tmp_path):
    '''
    Tests prediction of dataset where fold's model cannot be used for any
    candidate because all candidates were used in training of model
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')
    l_model, _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)
    rdf        = rdf_sig.Filter('rdfentry_ < 3')

    cvp= CVPredict(models=l_model, rdf=rdf)
    cvp.predict()
#--------------------------------------------------------------------
def test_all_nans(tmp_path):
    '''
    Tests prediction of dataset where all entries contain a NaN
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')
    l_model, _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    with LogStore.level('dmu:testing:utilities', 10):
        rdf = ut.get_rdf(kind='sig', columns_with_nans=['z'], nan_fraction=1.0)

    cvp= CVPredict(models=l_model, rdf=rdf)
    cvp.predict()
#--------------------------------------------------------------------
def test_with_friend_trees(tmp_path):
    '''
    Tests training when a dataframe build with friend trees is used
    '''
    with LogStore.level('dmu:tests:rdf_with_friend', 10):
        rdf_sig    = ut.get_rdf(kind='sig', with_friend=True)
        rdf_bkg    = ut.get_rdf(kind='bkg', with_friend=True)

    with LogStore.level('dmu:ml:train_mva', 10):
        l_model, _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path, name='train_mva_with_friends')

    rdf     = ut.get_rdf(kind='sig', with_friend=True)
    cvp     = CVPredict(models=l_model, rdf=rdf)
    cvp.predict()
#--------------------------------------------------------------------
def test_non_overlap(tmp_path):
    '''
    Tests prediction when input dataset is different from training one
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')
    l_model, _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    rdf     = ut.get_rdf(kind='sig')
    cvp     = CVPredict(models=l_model, rdf=rdf)
    cvp.predict()
#--------------------------------------------------------------------
def test_overlap(tmp_path):
    '''
    Tests prediction when input dataset is same as training one
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')
    l_model, _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    cvp     = CVPredict(models=l_model, rdf=rdf_sig)
    cvp.predict()
#--------------------------------------------------------------------
def test_patch(tmp_path):
    '''
    Prediction with training and application datasets where all NaNs are cleaned
    '''
    rdf_sig     = ut.get_rdf(kind='sig', columns_with_nans=['y'])
    rdf_bkg     = ut.get_rdf(kind='bkg', repeated=True)
    l_model , _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    log.info('Predicting')

    rdf     = ut.get_rdf(kind='sig', columns_with_nans=['y'])
    cvp     = CVPredict(models=l_model, rdf=rdf)
    arr_prb = cvp.predict()

    _check_probabilities(arr_prb, has_negative=False)
#--------------------------------------------------------------------
def test_partial_patch(tmp_path):
    '''
    Test with input and prediction datasets partially cleaned
    '''
    log.info('\nTraining')

    rdf_sig    = ut.get_rdf(kind='sig', columns_with_nans=['x', 'y'])
    rdf_bkg    = ut.get_rdf(kind='bkg', repeated=True)
    l_model , _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    log.info('Predicting')

    rdf     = ut.get_rdf(kind='sig', columns_with_nans=['x', 'y'])
    cvp     = CVPredict(models=l_model, rdf=rdf)
    arr_prb = cvp.predict()

    _check_probabilities(arr_prb, has_negative=True)
#--------------------------------------------------------------------
def test_sample_def(tmp_path : Path):
    '''
    Tests prediction when a features is the result of a definition
    that is different for different samples
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')
    l_model, _ = ut.get_models(
            rdf_sig,
            rdf_bkg,
            name    = 'train_mva_def',
            out_dir = f'{tmp_path}/sample_def')

    rdf     = ut.get_rdf(kind='sig')
    cvp     = CVPredict(
            models = l_model,
            rdf    =rdf)
    cvp.predict()
#--------------------------------------------------------------------
def test_skip_mva_prediction(tmp_path):
    '''
    Tests skipping the reading of scores for candidates
    with the skip_mva_prediction branch set to 1
    '''
    rdf_sig    = ut.get_rdf(kind='sig')
    rdf_bkg    = ut.get_rdf(kind='bkg')

    skip_col   = 'skip_mva_prediction'
    l_model , _ = ut.get_models(rdf_sig, rdf_bkg, out_dir=tmp_path)

    rdf     = ut.get_rdf(kind='sig')
    rdf     = rdf.Define(skip_col, 'rdfentry_ % 2')

    cvp     = CVPredict(models=l_model, rdf=rdf)
    arr_prb = cvp.predict()

    arr_skipped = arr_prb[1::2]
    arr_res     = arr_skipped + 1.0
    arr_dif     = numpy.abs(arr_res)
    arr_fail    = arr_skipped[arr_dif > 1e-5]

    assert len(arr_fail) == 0
#--------------------------------------------------------------------
