'''
Module containing unit tests for CVClassifier
'''

import os

import yaml
import numpy
import pytest
import joblib
import pandas  as pnd

from ROOT                  import RDataFrame
from dmu.logging.log_store import LogStore
from dmu.ml.cv_classifier  import CVClassifier as cls
from dmu.ml.cv_classifier  import CVSameData

import dmu.testing.utilities as ut

log = LogStore.add_logger('dmu.test.ml.test_cv_classifier')
# -------------------------------------------------
class Data:
    '''
    Class used to share attributes
    '''

    out_dir = '/tmp/tests/dmu/ml/cv_classifier'
# -------------------------------------------------
def _add_vars(rdf : RDataFrame, d_def : dict[str,str]) -> RDataFrame:
    for name, expr in d_def.items():
        rdf = rdf.Define(name, expr)

    return rdf
# -------------------------------------------------
def _get_train_input():
    '''
    Will return pandas dataframe with features and list of labels
    made from toy data
    '''
    rdf_sig = ut.get_rdf(kind='sig')
    rdf_bkg = ut.get_rdf(kind='bkg')

    cfg     = ut.get_config('ml/tests/train_mva.yaml')
    d_def   = cfg['dataset']['define']
    rdf_sig = _add_vars(rdf_sig, d_def)
    rdf_bkg = _add_vars(rdf_bkg, d_def)

    l_feat_name = cfg['training']['features']
    d_sig = rdf_sig.AsNumpy(l_feat_name)
    d_bkg = rdf_bkg.AsNumpy(l_feat_name)

    df_sig = pnd.DataFrame(d_sig)
    df_bkg = pnd.DataFrame(d_bkg)

    df_ft  = pnd.concat([df_bkg, df_sig], axis=0)

    nbkg    = len(df_bkg)
    nsig    = len(df_sig)

    l_lab   = [0] * nbkg + [1] * nsig
    arr_lab = numpy.array(l_lab)

    return df_ft, arr_lab
# -------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('dmu:ml:CVClassifier', 10)
# -------------------------------------------------
def test_save_load():
    '''
    Used to save and load class
    '''
    cfg   = ut.get_config('ml/tests/train_mva.yaml')

    model      = cls(cfg=cfg)
    model_path = f'{Data.out_dir}/save/model.pkl'
    model_dir  = os.path.dirname(model_path)
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, model_path)

    model = joblib.load(model_path)

    print(model)
# -------------------------------------------------
def test_fit():
    '''
    Test model fitting
    '''

    cfg   = ut.get_config('ml/tests/train_mva.yaml')

    df_ft, l_lab = _get_train_input()

    model= cls(cfg=cfg)
    model.fit(df_ft, l_lab)

    model_path = f'{Data.out_dir}/fit/model.pkl'
    model_dir  = os.path.dirname(model_path)
    os.makedirs(model_dir, exist_ok=True)

    joblib.dump(model, model_path)

    print(model)
# -------------------------------------------------
def test_predict():
    '''
    Will test probability prediction
    '''
    cfg   = ut.get_config('ml/tests/train_mva.yaml')

    df_ft, l_lab = _get_train_input()

    model= cls(cfg=cfg)
    model.fit(df_ft, l_lab)

    try:
        _ = model.predict_proba(df_ft)
    except CVSameData:
        pass
# -------------------------------------------------
def test_properties():
    '''
    Will test if properties (hashes/feature names, etc) can be retrieved
    '''

    cfg   = ut.get_config('ml/tests/train_mva.yaml')

    df_ft, l_lab = _get_train_input()

    model= cls(cfg=cfg)
    model.fit(df_ft, l_lab)

    l_feat = model.features
    s_hash = model.hashes
    d_cfg  = model.cfg
    nhash  = len(s_hash)

    assert cfg == d_cfg

    log.info(f'Found features: {l_feat}')
    log.info(f'Found hashes: {nhash}')
# -------------------------------------------------
def test_save_config():
    '''
    Test saving of config
    '''

    cfg_inp = ut.get_config('ml/tests/train_mva.yaml')
    df_ft, l_lab = _get_train_input()

    model= cls(cfg=cfg_inp)
    model.fit(df_ft, l_lab)

    config_path = f'{Data.out_dir}/save/config.yaml'
    model.save_cfg(path=config_path)

    with open(config_path, encoding='utf-8') as ifile:
        cfg_out = yaml.safe_load(ifile)

    assert cfg_inp == cfg_out
# -------------------------------------------------
