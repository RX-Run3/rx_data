'''
Script in charge of comparing different classifiers' performances
'''
import os
import glob
import argparse
import joblib
import mplhep
import matplotlib.pyplot as plt

from importlib.resources   import files
from ROOT                  import RDF
from dmu                   import LogStore
from dmu.ml                import CVPerformance
from dmu.ml                import CVClassifier
from dmu.generic           import utilities as gut
from rx_common             import Cuts
from rx_data               import RDFGetter
from rx_selection          import selection as sel
from rx_classifier         import utilities as cut

log=LogStore.add_logger('rx_classifier:compare_classifier')
plt.style.use(mplhep.style.LHCb2)
# -------------------------------
class Data:
    '''
    Data class
    '''
    cfg     : dict
    nev     : int
    lvl     : int
    nam     : str
    out_dir : str

    cvp = CVPerformance()
# -------------------------------
def _initialize():
    LogStore.set_level('rx_data:rdf_getter'             , 30)
    LogStore.set_level('rx_selection:selection'         , 30)
    LogStore.set_level('rx_selection:compare_classifier', Data.lvl)
    LogStore.set_level('dmu:ml:cv_predict'              , Data.lvl)

    ana_dir      = os.environ['ANADIR']
    Data.out_dir = f'{ana_dir}/mva/comparison'

    os.makedirs(Data.out_dir, exist_ok=True)
# -------------------------------
def _load_config(name : str) -> dict:
    fpath = files('rx_classifier_data').joinpath(f'performance/{name}.yaml')
    fpath = str(fpath)
    data  = gut.load_json(fpath)

    return data
# -------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to compare performance of classifiers')
    parser.add_argument('-c', '--config', type=str, help='Name of config file', required=True)
    parser.add_argument('-n', '--nevent', type=int, help='Number of entries to limit run')
    parser.add_argument('-l', '--loglvl', type=int, help='Logging level', default=20)
    args = parser.parse_args()

    Data.cfg = _load_config(name=args.config)
    Data.nam = args.config
    Data.nev = args.nevent
    Data.lvl = args.loglvl
# -------------------------------
def _get_models(path : str) -> list[CVClassifier]:
    path_wc = f'{path}/model_*.pkl'
    l_path  = glob.glob(path_wc)
    l_model = [ joblib.load(path) for path in l_path ]

    if len(l_model) == 0:
        raise ValueError(f'No models found in: {path_wc}')

    return l_model
# -------------------------------
def _override_selection(cfg : dict, d_sel : dict[Cuts,str]) -> dict[Cuts,str]:
    if 'selection' not in cfg:
        return d_sel

    d_cut=cfg['selection']
    d_sel.update(d_cut)

    return d_sel
# -------------------------------
def _apply_selection(rdf : RDF.RNode, cfg : dict) -> RDF.RNode:
    name  = cfg['name']
    q2bin = cfg['q2bin']
    trig  = cfg['trigger']

    d_sel : dict[Cuts,str] = sel.selection(
            q2bin  =q2bin,
            trigger=trig,
            process=name)

    d_sel = _override_selection(cfg=cfg, d_sel=d_sel)
    log.info('Applying selection')
    for name, expr in d_sel.items():
        log.debug(f'{name:<15}{expr}')
        rdf = rdf.Filter(expr, name)

    return rdf
# -------------------------------
def _get_rdf(cfg : dict) -> RDF.RNode:
    name = cfg['name']
    trig = cfg['trigger']

    d_vers = {}
    if 'mva' in Data.cfg:
        vers = Data.cfg['mva']
        log.warning(f'Overriding MVA version with {vers}')
        d_vers['mva'] = vers

    with RDFGetter.custom_friends(versions=d_vers):
        gtr  = RDFGetter(sample=name, trigger=trig)
        rdf  = gtr.get_rdf(per_file = False)

    if 'MuMu' in trig:
        rdf = cut.add_muon_columns(rdf=rdf)

    rdf  = _apply_selection(rdf, cfg)
    if Data.nev == -1:
        return rdf

    rdf = rdf.Filter(f'rdfentry_ < {Data.nev}')

    return rdf
# -------------------------------
def _plot_roc(kind : str, cfg : dict) -> None:
    rdf_sig = _get_rdf(cfg['samples']['signal'    ])
    rdf_bkg = _get_rdf(cfg['samples']['background'])
    color   = cfg['color']
    models  = _get_models(cfg['model'])
    auc     = Data.cvp.plot_roc(
        sig  = rdf_sig,
        bkg  = rdf_bkg,
        model= models,
        name = kind,
        color= color)

    log.info(f'For {kind} found AUC: {auc:.3f}')
# -------------------------------
def _plot(out_path : str) -> None:
    cfg = Data.cfg['plotting']
    minx= cfg.get('minx' , 0)
    miny= cfg.get('miny' , 0)
    titl= cfg.get('title','')

    plt.xlim(minx, None)
    plt.ylim(miny, None)

    plt.xlabel('Signal Efficiency')
    plt.ylabel('Background Rejection')
    plt.title(titl)
    plt.legend()
    plt.grid()
    log.info(f'Saving to: {out_path}')
    plt.savefig(out_path)
    plt.close()
# -------------------------------
def main():
    '''
    Start here
    '''
    _parse_args()
    _initialize()

    log.info('Plotting:')
    for kind, cfg in Data.cfg['cases'].items():
        log.info(f'{"":<4}{kind:<20}')
        _plot_roc(kind=kind, cfg=cfg)

    out_path = f'{Data.out_dir}/{Data.nam}.png'

    _plot(out_path=out_path)
# -------------------------------
if __name__ == '__main__':
    main()
