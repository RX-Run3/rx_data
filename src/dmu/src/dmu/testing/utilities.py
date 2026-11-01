'''
Module containing utility functions needed by unit tests
'''
import os
import math
import glob
from typing              import Union
from dataclasses         import dataclass
from importlib.resources import files

from ROOT import RDF, TFile, RDataFrame

import uproot
import joblib
import pandas as pnd
import numpy
import yaml

from pathlib               import Path
from dmu.ml.train_mva      import TrainMva
from dmu.ml.cv_classifier  import CVClassifier
from dmu.logging.log_store import LogStore
from .rdf_with_friend      import rdf_with_friend

log = LogStore.add_logger('dmu:testing:utilities')
# -------------------------------
@dataclass
class Data:
    '''
    Class storing shared data
    '''
    out_dir : Path = Path('/tmp/tests/dmu/ml/cv_predict')

    d_col   = {
            'main' : ['index', 'a0', 'b0'],
            'frn1' : ['index', 'a1', 'b1'],
            'frn2' : ['index', 'a2', 'b2'],
            'frn3' : ['index', 'a3', 'b3'],
            'frn4' : ['index', 'a4', 'b4'],
            }
# -------------------------------
def _double_data(df_1 : pnd.DataFrame) -> pnd.DataFrame:
    df_2   = df_1.copy()
    df     = pnd.concat([df_1, df_2], axis=0)

    return df
# -------------------------------
def _add_nans(
    df      : pnd.DataFrame, 
    fraction: float,
    columns : list[str]) -> pnd.DataFrame:
    '''
    Parameters
    -----------------
    df      : Dataframe with data to train/test in tests
    fraction: Fraction of entries that will be randomly assigned NaNs
    columns : List of columns where NaNs will be injected

    Returns
    -----------------
    Dataframe with NaNs added
    '''
    ntot= len(df)
    nnan= math.ceil(ntot * fraction)

    for col in columns:
        arr_val = df[col].to_numpy(copy=True)
        arr_ind = numpy.random.choice(ntot, nnan, replace=False)
        arr_val[arr_ind] = numpy.nan

        df[col] = arr_val

    log.debug(f'Replacing randomly with {nnan} NaNs')

    return df
# -------------------------------
def get_rdf(
    kind              : str | None      = None,
    repeated          : bool            = False,
    nentries          : int             = 3_000,
    use_preffix       : bool            = False,
    with_friend       : bool            = False,
    nan_fraction      : float           = 0.2,
    columns_with_nans : list[str]|None  = None):
    '''
    Return ROOT dataframe with toy data

    kind              : sig, bkg or bkg_alt
    repeated          : Will add repeated rows
    nentries          : Number of rows
    dotted            : Will use columns with dots in name
    nan_fraction      : When columns_with_nans is used, this is the fraction of rows with NaNs, default 0.2
    columns_with_nans : List of column names in [w, y, z]
    '''
    # Needed for a specific test
    xnm = 'preffix.x.suffix' if use_preffix else 'x'

    d_data = {}
    if   kind == 'sig':
        d_data[xnm] = numpy.random.normal(0.0, 1.0, size=nentries)
        d_data['w'] = numpy.random.normal(0.0, 1.0, size=nentries)
        d_data['y'] = numpy.random.normal(0.0, 1.0, size=nentries)
        d_data['z'] = numpy.random.normal(0.0, 1.0, size=nentries)
    elif kind == 'bkg':
        d_data[xnm] = numpy.random.normal(1.0, 1.0, size=nentries)
        d_data['w'] = numpy.random.normal(1.0, 1.0, size=nentries)
        d_data['y'] = numpy.random.normal(1.0, 1.0, size=nentries)
        d_data['z'] = numpy.random.normal(1.0, 1.0, size=nentries)
    elif kind == 'bkg_alt':
        d_data[xnm] = numpy.random.normal(1.3, 1.3, size=nentries)
        d_data['w'] = numpy.random.normal(1.3, 1.3, size=nentries)
        d_data['y'] = numpy.random.normal(1.3, 1.3, size=nentries)
        d_data['z'] = numpy.random.normal(1.3, 1.3, size=nentries)
    else:
        log.error(f'Invalid kind: {kind}')
        raise ValueError

    df = pnd.DataFrame(d_data)

    if repeated:
        df = _double_data(df)

    if columns_with_nans is not None:
        df = _add_nans(df, columns=columns_with_nans, fraction=nan_fraction)

    if with_friend:
        rdf = rdf_with_friend(df=df, branch='y')
    else:
        log.debug('Not using friend trees to build dataframe')
        rdf = RDF.FromPandas(df)

    return rdf
# -------------------------------
def get_config(name : Union[str,None] = None):
    '''
    Takes path to the YAML config file, after `dmu_data`
    Returns dictionary with config
    '''
    if name is None:
        raise ValueError('Name not pased')

    cfg_path = files('dmu_data').joinpath(name)
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf-8') as ifile:
        d_cfg = yaml.safe_load(ifile)

    return d_cfg
# -------------------------------
def _get_rdf(nentries : int) -> RDataFrame:
    rdf = RDataFrame(nentries)
    rdf = rdf.Define('x', '0')
    rdf = rdf.Define('y', '1')
    rdf = rdf.Define('z', '2')

    return rdf
# -------------------------------
def get_file_with_trees(path : str) -> TFile:
    '''
    Picks full path to toy ROOT file, in the form of /a/b/c/file.root
    returns handle to it
    '''
    dir_name    = os.path.dirname(path)
    os.makedirs(dir_name, exist_ok=True)

    snap        = RDF.RSnapshotOptions()
    snap.fMode  = 'recreate'

    l_tree_name = ['odir/idir/a', 'dir/b', 'c']
    l_nevt      = [    100, 200, 300]

    l_rdf = [ _get_rdf(nevt) for nevt in l_nevt ]
    for rdf, tree_name in zip(l_rdf, l_tree_name, strict = True):
        rdf.Snapshot(tree_name, path, ['x', 'y', 'z'], snap)
        snap.fMode  = 'update'

    return TFile(path)
# -------------------------------
def get_models(
    rdf_sig : RDF.RNode,
    rdf_bkg : RDF.RNode,
    name    : str               = 'train_mva',
    out_dir : str | Path | None = None) -> tuple[list[CVClassifier], float]:
    '''
    Will train and return models together with the AUC in a tuple

    rdf_xxx : Signal or background dataframe used for training
    name    : Name of config file, e.g. train_mva
    out_dir : Directory where the training output will go, optional.
    '''
    out_dir = Data.out_dir if out_dir is None else out_dir

    cfg                     = get_config(f'ml/tests/{name}.yaml')
    cfg['saving']['output'] = out_dir

    obj = TrainMva(sig=rdf_sig, bkg=rdf_bkg, cfg=cfg)
    auc = obj.run()

    pkl_wc     = f'{out_dir}/model*.pkl'
    l_pkl_path = glob.glob(pkl_wc)
    l_model    = [ joblib.load(pkl_path) for pkl_path in l_pkl_path ]

    return l_model, auc
# -------------------------------
def _make_file(
    fpath    : str,
    tree     : str,
    nentries : int) -> None:

    fdir       = os.path.dirname(fpath)
    sample     = os.path.basename(fdir)
    l_col_name = Data.d_col[sample]

    data : dict[str,numpy.ndarray] = {}
    for col_name in l_col_name:
        if col_name == 'index':
            data[col_name] = numpy.arange(nentries)
            continue

        data[col_name] = numpy.random.normal(loc = 0, scale = 1, size = nentries)

    with uproot.recreate(fpath) as ofile:
        log.debug(f'Saving to: {fpath}:{tree}')
        ofile[tree] = data
# -------------------------------
def build_friend_structure(file_name : str, nentries : int) -> None:
    '''
    Will load YAML file with file structure needed to
    test code that relies on friend trees, e.g. DDFGetter

    Parameters:
    -------------------
    file_name (str): Name of YAML file with wanted structure, e.g. friends.yaml
    nentries (int) : Number of entries in file
    '''
    cfg_path = files('dmu_data').joinpath(f'rfile/{file_name}')
    cfg_path = str(cfg_path)
    with open(cfg_path, encoding='utf=8') as ifile:
        data = yaml.safe_load(ifile)

    if 'tree' not in data:
        raise ValueError('tree entry missing in: {cfg_path}')

    tree_name : str = data['tree']

    if 'samples' not in data:
        raise ValueError('Samples section missing in: {cfg_path}')

    if 'files' not in data:
        raise ValueError('Files section missing in: {cfg_path}')

    for fdir in data['samples']:
        for fname in data['files']:
            path = f'{fdir}/{fname}'
            _make_file(fpath=path, tree=tree_name, nentries=nentries)
# ----------------------------------------------
