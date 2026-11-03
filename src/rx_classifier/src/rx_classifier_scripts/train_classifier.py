'''
Script in charge of training classifier
'''

import os
import glob
import random
import shutil
import argparse

from importlib.resources import files

import matplotlib.pyplot as plt
import mplhep
import yaml
import ROOT

from omegaconf             import DictConfig
from ROOT                  import RDataFrame, RDF, kWarning
from rx_selection          import selection as sel
from rx_data.rdf_getter    import RDFGetter

import dmu.generic.utilities as gut
from dmu.logging.log_store import LogStore
from dmu.ml.train_mva      import TrainMva
from dmu.rdataframe        import utilities as rut

ROOT.gErrorIgnoreLevel = kWarning
log = LogStore.add_logger('rx_classifier:train_classifier')
#---------------------------------
class Data:
    '''
    Class meant to hold data to be shared
    '''
    root_regex  = r'\d{3}_\d{3}.root'
    ana_dir     = os.environ['ANADIR']
    cfg_dict    : dict
    cfg_name    : str
    version     : str
    project     : str
    q2bin       : str
    opt_ntrial  : int
    workers     : int
    max_entries : int
    log_level   : int
    plot_only   : bool
    load_trained: bool

    ran_val     = random.randint(10**9, 10**10 - 1)
    user        = os.environ['USER']
    cache_dir   = f'/tmp/{user}/rx_classifier/{ran_val}/cache/train_classifier/samples'
#---------------------------------
def _override_path(path : str) -> str:
    if 'VERSION' not in path:
        raise ValueError(f'VERSION expected in: {path}')

    replacement = f'{Data.version}/{Data.q2bin}'

    path = path.replace('VERSION', replacement)
    path = f'{Data.ana_dir}/{path}'

    log.info(f'Using output path: {path}')

    return path
#---------------------------------
def _reformat_config(cfg : dict) -> dict:
    path = cfg['saving']['output']
    cfg['saving']['output']     = _override_path(path)
    cfg['training']['features'] = cfg['features'][Data.q2bin]

    if 'diagnostics' in cfg:
        out_dir = cfg['diagnostics']['output']
        cfg['diagnostics']['output'] = _override_path(out_dir)

    d_corr = cfg['diagnostics']['correlations']['target']
    if 'overlay' in d_corr:
        d_save  = d_corr['overlay']['saving']
        plt_dir = d_save['plt_dir']
        d_save['plt_dir'] = _override_path(plt_dir)

    return cfg
#---------------------------------
def _reformat_hyperparameters(cfg : dict) -> dict:
    d_common_hyper = cfg.get('hyper', {})
    d_q2hyper      = cfg['training']['hyper'][Data.q2bin]

    d_common_hyper.update(d_q2hyper)

    cfg['training']['hyper'] = d_common_hyper

    return cfg
#---------------------------------
def _load_config():
    '''
    Will load YAML file config
    '''

    cfg_path = files('rx_classifier_data').joinpath(f'classification/{Data.project}/{Data.version}/{Data.cfg_name}.yaml')
    cfg_path = str(cfg_path)
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f'Could not find: {cfg_path}')

    with open(cfg_path, encoding='utf-8') as ifile:
        cfg_dict = yaml.safe_load(ifile)
        cfg_dict = _reformat_config(cfg_dict)
        cfg_dict = _reformat_hyperparameters(cfg_dict)

    Data.cfg_dict = cfg_dict
#---------------------------------
def _parse_args():
    '''
    Use argparser to put options in Data class
    '''
    parser = argparse.ArgumentParser(description='Used to train classifier based on config file')
    parser.add_argument('-v', '--version'    , type=str, help='Version of config files', required=True)
    parser.add_argument('-c', '--cfg_name'   , type=str, help='Kind of config file'    , required=True)
    parser.add_argument('-P', '--project'    , type=str, help='Project, e.g rk'        , required=True, choices=['rk', 'rkst'])
    parser.add_argument('-q', '--q2bin'      , type=str, help='q2bin'                  , required=True, choices=['low', 'central', 'jpsi', 'psi2S', 'high'])
    parser.add_argument('-l', '--log_level'  , type=int, help='Logging level', default=20, choices=[10, 20, 30])
    parser.add_argument('-n', '--opt_ntrial' , type=int, help='Number of tries for hyperparameter optimization', default=0)
    parser.add_argument('-w', '--workers'    , type=int, help='Number of processes, if using parallel processing', default=1)
    parser.add_argument('-m', '--max_entries', type=int, help='Limit datasets entries to this value', default=-1)
    parser.add_argument('-p', '--plot_only'   , action='store_true', help='If used, will only do plots of feature distributions, not training')
    parser.add_argument('-L', '--load_trained', action='store_true', help='Nothing changes, but instead of training models, will load trained models, which should exist')
    args = parser.parse_args()

    Data.version     = args.version
    Data.project     = args.project
    Data.cfg_name    = args.cfg_name
    Data.workers     = args.workers
    Data.opt_ntrial  = args.opt_ntrial
    Data.q2bin       = args.q2bin
    Data.max_entries = args.max_entries
    Data.log_level   = args.log_level
    Data.plot_only   = args.plot_only
    Data.load_trained= args.load_trained
# ----------------------
def _initialize_args(cfg : DictConfig) -> None:
    '''
    Parameters
    -------------
    cfg: Configuration used when module is imported
    '''
    Data.cfg_name    = cfg.kind
    Data.q2bin       = cfg.q2bin
    Data.project     = cfg.project
    Data.version     = cfg.version

    Data.workers     = 5
    Data.opt_ntrial  = 0
    Data.max_entries = -1
    Data.log_level   = 20
    Data.plot_only   = False
    Data.load_trained= False
#---------------------------------
def _merge_dataframes(
    d_rdf : dict[str, RDF.RNode],
    kind  : str) -> RDF.RNode:
    '''
    Takes list of dataframes, one for a different sample, after selection

    d_rdf: Dictionary mapping sample names to ROOT dataframes to merge
    kind : Type of sample, e.g. sig, bkg
    '''

    for sample, rdf, in d_rdf.items():
        fpath = f'{Data.cache_dir}/{kind}_{sample}.root'
        nevt  = rdf.Count().GetValue()
        if nevt == 0:
            log.warning(f'Dataset {sample} empty, not saving it')
            continue

        if os.path.isfile(fpath):
            shutil.rmtree(fpath)

        log.info(f'Saving temporary file to: {fpath}')
        rdf.Snapshot('tree', fpath)

    rdf = RDataFrame('tree', f'{Data.cache_dir}/{kind}_*.root')

    return rdf
#---------------------------------
def _get_rdf(kind : str) -> RDF.RNode:
    '''
    Will load and return ROOT dataframe

    Parameters
    ---------------------
    kind (str): kind of dataset to find in config input section
    '''
    log.info(f'Getting dataframe for {kind}')

    sample : str = Data.cfg_dict['dataset']['samples'][kind]['sample']
    trigger: str = Data.cfg_dict['dataset']['samples'][kind]['trigger']

    if   isinstance(sample, str):
        rdf   = _get_sample_rdf(sample=sample, trigger=trigger, kind=kind)
        d_rdf = {'all' : rdf}
    elif isinstance(sample, list):
        log.info(f'Found composed sample: {sample}')
        d_rdf = { sname : _get_sample_rdf(sample=sname, trigger=trigger, kind=kind) for sname in sample }
    else:
        raise ValueError(f'Unexpected value of sample: {sample}')

    rdf   = _merge_dataframes(d_rdf=d_rdf, kind=kind)

    return rdf
#---------------------------------
def _get_sample_rdf(sample : str, trigger : str, kind : str) -> RDF.RNode:
    gtr = RDFGetter(sample=sample, trigger=trigger)
    rdf = gtr.get_rdf(per_file=False)

    rdf = _apply_selection(rdf, sample, kind)

    _save_cutflow(rdf=rdf, kind=kind, sample=sample)

    return rdf
#---------------------------------
def _save_cutflow(
    rdf   : RDF.RNode,
    sample: str,
    kind  : str) -> None:
    '''
    Parameters
    ----------------
    rdf   : Dataframe needed to get the cutflow from
    sample: Sample associated to dataframe
    kind  : E.g. bkg, sig
    '''
    log.info(f'Saving cutflow for: {kind}')

    out_dir = Data.cfg_dict['saving']['output']
    out_dir = f'{out_dir}/input'
    os.makedirs(out_dir, exist_ok=True)

    rep = rdf.Report()
    rep.Print()

    df  = rut.rdf_report_to_df(rep)

    df.to_json(f'{out_dir}/cutflow_{kind}_{sample}.json', indent=2)
#---------------------------------
def _save_selection(
    cuts  : dict[str,str],
    sample: str,
    kind  : str) -> None:
    '''
    Parameters
    -----------------
    cuts  : Selection used to create training sample
    sample: Sample name, e.g. Bu_Kee_eq_btosllball05_DPC
    kind  : E.g. sig, bkg
    '''
    log.info(f'Saving selection for: {kind}')

    out_dir = Data.cfg_dict['saving']['output']
    out_dir = f'{out_dir}/input'
    os.makedirs(out_dir, exist_ok=True)

    gut.dump_json(
        data      = cuts,
        exists_ok = True,
        path      = f'{out_dir}/selection_{kind}_{sample}.yaml')
#---------------------------------
def _get_overriding_selection(kind : str) -> dict[str,str]:
    '''
    Kind here is bkg or sig
    '''
    cfg_sel = Data.cfg_dict['dataset']['selection']

    d_cut   = cfg_sel[kind]
    if 'override' not in cfg_sel:
        return d_cut

    if Data.q2bin not in cfg_sel['override']:
        return d_cut

    d_cut_ext = cfg_sel['override'][Data.q2bin]
    d_cut.update(d_cut_ext)

    return d_cut
#---------------------------------
def _apply_selection(
    rdf    : RDF.RNode,
    sample : str,
    kind   : str) -> RDF.RNode:
    '''
    Will:
      - Take ROOT dataframe and kind (bkg or sig)
      - Load selection from config
      - Return dataframe after selection
    '''

    log.info(f'Applying selection to: {sample} ({kind})')
    trigger = Data.cfg_dict['dataset']['samples'][kind]['trigger']

    d_sel = sel.selection(trigger=trigger, q2bin=Data.q2bin, process=sample)
    d_cut = _get_overriding_selection(kind=kind)
    d_sel.update(d_cut)

    _save_selection(cuts=d_sel, kind=kind, sample=sample)

    for cut_name, cut_expr in d_sel.items():
        log.debug(f'{cut_name:<30}{cut_expr}')
        rdf = rdf.Filter(cut_expr, cut_name)

    log.info(f'Cutflow for: {kind}')

    return rdf
#---------------------------------
def _initialize():
    _load_config()
    plt.style.use(mplhep.style.LHCb2)

    os.makedirs(Data.cache_dir, exist_ok=True)

    LogStore.set_level('rx_classifier:train_classifier', Data.log_level)
    LogStore.set_level('dmu:ml:train_mva'              , Data.log_level)
    LogStore.set_level('dmu:plotting:Plotter1D'        , Data.log_level)
# ----------------------
def _check_existing_model() -> None:
    '''
    If the output directory contains models, raise exception
    In order not to override already trained models
    '''
    if Data.plot_only:
        return

    out_dir = Data.cfg_dict['saving']['output']

    l_model = glob.glob(f'{out_dir}/model_*.pkl')
    if not l_model:
        return

    for model in l_model:
        log.info(model)

    raise ValueError('Already found models')
#---------------------------------
def main(cfg : DictConfig|None = None):
    '''
    Parameters
    --------------
    cfg: Dictionary with configuration, used when this module is imported
    '''
    if cfg is None:
        _parse_args()
    else:
        _initialize_args(cfg=cfg)

    _initialize()

    _check_existing_model()

    with RDFGetter.max_entries(value = Data.max_entries):
        rdf_sig = _get_rdf(kind='sig')
        rdf_bkg = _get_rdf(kind='bkg')

        trn = TrainMva(sig=rdf_sig, bkg=rdf_bkg, cfg=Data.cfg_dict)
        with trn.use(nworkers=Data.workers):
            trn.run(
            skip_fit    =Data.plot_only,
            opt_ntrial  =Data.opt_ntrial,
            load_trained=Data.load_trained)
#---------------------------------
if __name__ == '__main__':
    main()
