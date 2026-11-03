'''
Script used to make diagnostic plots from filtered ntuples
'''

import copy
import argparse
import mplhep
import matplotlib.pyplot as plt

from ROOT         import RDF, RDataFrame
from dmu          import LogStore
#from dmu.plotting import Plotter1D
#from omegaconf    import OmegaConf
from dataclasses  import dataclass

import post_ap.utilities as ut

log=LogStore.add_logger('post_ap:plot_vars')
# -------------------------------------
@dataclass
class Data:
    '''
    Class meant to store shared data
    '''
    log_lvl : int
    cfg_nam : str
    cfg_dat : dict[str,dict[str,str]]
# -------------------------------------
def _get_args():
    parser = argparse.ArgumentParser(description='Used to plot yields of cut based vs MVA based lines vs luminosity')
    parser.add_argument('-c', '--cfg' , type =str, help='Name of config file specifying what to plot and how', required=True)
    parser.add_argument('-l', '--log' , type =int, help='Log level', default=20)
    args = parser.parse_args()

    Data.cfg_nam           = args.cfg
    Data.log_lvl           = args.log
# -------------------------------------
def _get_rdf(path_wc : str) -> RDF.RNode:
    '''
    Takes wildcard to ROOT files used as input
    Will return ROOT dataframe
    '''
    tree_name = Data.cfg_dat['input']['tree_name']

    log.debug(f'Loading: {path_wc}/{tree_name}')

    rdf    = RDataFrame(tree_name, path_wc)
    nev    = rdf.Count().GetValue()
    log.debug(f'Found {nev} entries in: {path_wc}')

    return rdf
# -------------------------------------
def _get_config(skip_bdt : bool) -> dict:
    '''
    Will pick skip_bdt flag and override plotting directory
    returns updated config
    '''

    cfg     = copy.deepcopy(Data.cfg_dat)
    plt_dir = cfg['saving']['plt_dir']

    if skip_bdt:
        cfg['saving']['plt_dir'] = f'{plt_dir}/no_bdt'
    else:
        cfg['saving']['plt_dir'] = f'{plt_dir}/with_bdt'

    return cfg
# -------------------------------------
def main():
    '''
    Script starts here
    '''
    _get_args()
    plt.style.use(mplhep.style.LHCb2)

    Data.cfg_dat = ut.load_config()
    LogStore.set_level('post_ap:plot_vars', Data.log_lvl)

    log.error('Code below was commented, needs updates in configuration, etc')

    #for skip_bdt in [True, False]:
    #    d_inp = Data.cfg_dat['input']['file_wc']
    #    d_rdf = { samp : _get_rdf(dset, skip_bdt) for samp, dset in d_inp.items()}

    #    data  = _get_config(skip_bdt)
    #    cfg   = OmegaConf.create(data)

    #    ptr   = Plotter1D(d_rdf, cfg)
    #    ptr.run()
# -------------------------------------
if __name__ == '__main__':
    main()
