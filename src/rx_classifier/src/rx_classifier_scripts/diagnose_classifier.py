'''
Script with code used to make diagnostics plots for classifiers
'''
import os
import glob
import argparse
from importlib.resources   import files
from dataclasses           import dataclass

import yaml
import joblib
import mplhep
import matplotlib.pyplot as plt

from ROOT                  import RDataFrame
from rx_data.rdf_getter    import RDFGetter
from rx_selection          import selection as sel
from dmu.ml.cv_diagnostics import CVDiagnostics
from dmu.ml.cv_classifier  import CVClassifier
from dmu.logging.log_store import LogStore

log = LogStore.add_logger('rx_classifier:diagnose_classifier')
#---------------------------------
@dataclass
class Data:
    '''
    Class used to store shared information
    '''
    max_path    = 700
    sample      : str
    trigger     : str
    q2bin       : str
    conf        : str
    cfg         : dict
    max_entries : int
    l_model     : list
    log_level   : int

    mva_dir     : str
    data_dir    : str
#---------------------------------
def _get_args():
    '''
    Use argparser to put options in Data class
    '''
    parser = argparse.ArgumentParser(description='Script used to run diagnostic checks for classifier models')
    parser.add_argument('-s', '--sample'     , type=str, help='Sample name, meant to exist inside input_dir', required=True)
    parser.add_argument('-t', '--trigger'    , type=str, help='HLT trigger'                                 , required=True)
    parser.add_argument('-q', '--q2bin'      , type=str, help='q2 bin'                                      , required=True, choices=['low', 'central', 'jpsi', 'high'])
    parser.add_argument('-c', '--conf'       , type=str, help='Version of config file'                      , required=True)
    parser.add_argument('-l', '--log_level'  , type=int, help='Logging level', default=20, choices=[10, 20, 30])
    parser.add_argument('-m', '--max_entries', type=int, help='Limit datasets entries to this value', default=-1)
    args = parser.parse_args()

    Data.sample      = args.sample
    Data.trigger     = args.trigger
    Data.q2bin       = args.q2bin
    Data.conf        = args.conf
    Data.max_entries = args.max_entries
    Data.log_level   = args.log_level
# -------------------------------
def _initialize() -> None:
    _get_args()

    Data.data_dir = os.environ['DATADIR']
    Data.mva_dir  = os.environ['MVADIR']

    LogStore.set_level('rx_classifier:diagnose_classifier', Data.log_level)
    LogStore.set_level('dmu:ml:cv_diagnostics'            , Data.log_level)

    _load_config()
    plt.style.use(mplhep.style.LHCb2)

    out_dir = Data.cfg['diagnostics']['output']
    plt_dir = f'{out_dir}/{Data.q2bin}/{Data.sample}_{Data.trigger}'
    Data.cfg['diagnostics']['output'] = plt_dir
    Data.cfg['diagnostics']['correlations']['target']['overlay']['saving']['plt_dir'] = plt_dir
    Data.cfg['diagnostics']['correlations']['figure']['title'] = f'{Data.sample}; {Data.q2bin}'
# -------------------------------
def _load_config() -> None:
    conf_path = files('rx_classifier_data').joinpath(f'diagnostics/{Data.conf}.yaml')

    with open(conf_path, encoding='utf-8') as ofile:
        Data.cfg = yaml.safe_load(ofile)
# -------------------------------
def _path_to_name(path : str) -> str:
    name = os.path.basename(path)
    name = name.replace('.yaml', '')

    return name
# -------------------------------
def _apply_selection(rdf : RDataFrame) -> RDataFrame:
    if   'EE'   in Data.trigger:
        analysis = 'EE'
    elif 'MuMu' in Data.trigger:
        analysis = 'MM'
    else:
        raise ValueError(f'Cannot determine analysis from: {Data.trigger}')

    d_sel        = sel.selection(project='RK', analysis=analysis, q2bin=Data.q2bin, process=Data.sample)
    d_sel['bdt'] = '(1)'
    for name, cut in d_sel.items():
        rdf = rdf.Filter(cut, name)

    rep = rdf.Report()
    rep.Print()

    return rdf
# -------------------------------
def _get_rdf() -> RDataFrame:
    l_yaml   = Data.cfg['samples']
    l_sample = { _path_to_name(yaml_path) : f'{Data.data_dir}/{yaml_path}' for yaml_path in l_yaml }

    RDFGetter.samples = l_sample
    gtr = RDFGetter(sample=Data.sample, trigger=Data.trigger)
    rdf = gtr.get_rdf()
    rdf = _apply_selection(rdf)

    if Data.max_entries > 0:
        rdf = rdf.Filter(f'rdfentry_ < {Data.max_entries}')

    nentries = rdf.Count().GetValue()
    log.info(f'Using {nentries} entries for {Data.sample}/{Data.trigger}')

    return rdf
# -------------------------------
def _get_model() -> list[CVClassifier]:
    sub_dir = Data.cfg['sub_dir']
    if Data.q2bin == 'jpsi':
        q2bin = 'central'
    else:
        q2bin = Data.q2bin

    path_wc = f'{Data.mva_dir}/{sub_dir}/{q2bin}/*.pkl'
    l_path  = glob.glob(path_wc)

    if len(l_path) == 0:
        raise FileNotFoundError(f'No Files found in {path_wc}')

    l_model = [ joblib.load(path) for path in l_path ]

    return l_model
# -------------------------------
def main():
    '''
    Start here
    '''
    _initialize()

    l_model = _get_model()
    rdf     = _get_rdf()

    cvd = CVDiagnostics(models=l_model, rdf=rdf, cfg=Data.cfg['diagnostics'])
    cvd.run()
# -------------------------------
if __name__ == '__main__':
    main()
