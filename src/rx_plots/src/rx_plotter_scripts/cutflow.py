'''
Script used to plot cutflows
'''
import os
import argparse
import mplhep

from copy          import deepcopy
from ROOT          import RDF, EnableImplicitMT
from dmu           import LogStore
from dmu.generic   import utilities as gut
from dmu.plotting  import Plotter1D
from dmu.generic   import naming
from omegaconf     import DictConfig
from rx_data       import RDFGetter
from rx_selection  import selection
from rx_common     import Component, Cuts, Qsq, Trigger

log=LogStore.add_logger('rx_selection:cutflow')
_ANADIR = os.environ['ANADIR']
# ---------------------------------
class Data:
    '''
    Class used to share attributes
    '''
    d_reso     = {'jpsi' : 'B_const_mass_M', 'psi2' : 'B_const_mass_psi2S_M'}

    mplhep.style.use('LHCb2')

    chanel    : str
    ncores    : int
    component : Component 
    trigger   : Trigger 
    q2_bin    : Qsq 
    config    : str
    plt_dir   : str
    cfg       : DictConfig 
    d_def     : dict[str,str] = {}

    l_ee_trees = ['brem_track_2', 'ecalo_bias']
    l_keep     = []
    l_col      = []
# ---------------------------------
def _apply_definitions(rdf : RDF.RNode) -> RDF.RNode:
    if 'definitions' not in Data.cfg:
        return rdf
    
    for name, expr in Data.cfg.definitions.items():
        good_name = naming.clean_special_characters(name=name)
        rdf       = rdf.Define(good_name, expr)

    return rdf
# ---------------------------------
def _apply_selection(rdf : RDF.RNode) -> tuple[RDF.RNode, dict[Cuts,str]]:
    d_sel = selection.selection(
        trigger=Data.trigger, 
        q2bin  =Data.q2_bin, 
        process=Data.component)

    if 'selection' in Data.cfg:
        log.debug('Overriding selection')
        d_sel.update(Data.cfg.selection)

    log.info(40 * '-')
    log.info('Applying selection')
    log.info(40 * '-')
    for cut_name, cut_expr in d_sel.items():
        log.info(f'{cut_name:<20}{cut_expr}')
        good_name = naming.clean_special_characters(name=cut_name)
        rdf       = rdf.Filter(cut_expr, good_name)

    nentries = rdf.Count().GetValue()
    if nentries == 0:
        raise ValueError('No entries found after selection')

    return rdf, d_sel
# ---------------------------------
@gut.timeit
def _get_rdf() -> tuple[RDF.RNode, dict[Cuts,str]]:
    gtr      = RDFGetter(sample=Data.component, trigger=Data.trigger)
    rdf      = gtr.get_rdf(per_file=False)
    rdf      = _apply_definitions(rdf=rdf)
    rdf, sel = _apply_selection(rdf=rdf)

    return rdf, sel
# ---------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to cutflow plots')
    parser.add_argument('-q', '--q2bin'  , type=Qsq      , help='q2 bin'         , required=True)
    parser.add_argument('-s', '--sample' , type=Component, help='Sample'         , required=True)
    parser.add_argument('-t', '--trigger', type=Trigger  , help='Trigger'        , required=True)
    parser.add_argument('-c', '--config' , type=str      , help='Configuration'  , required=True)
    parser.add_argument('-n', '--ncores' , type=int      , help='Number of cores', default =   1)
    args = parser.parse_args()

    Data.q2_bin   = args.q2bin
    Data.component= args.sample
    Data.trigger  = args.trigger
    Data.ncores   = args.ncores
    Data.config   = f'{args.config}_{Data.trigger.project}'
# ---------------------------------
def _get_cfg() -> DictConfig:
    cfg           = gut.load_conf(package='rx_plotter_data', fpath=f'cutflow/{Data.config}.yaml')
    plt_dir       = cfg.saving.plt_dir
    cfg['saving'] = {'plt_dir' : _get_out_dir(plt_dir) }

    if 'definitions' in cfg:
        Data.d_def = cfg['definitions']
        del cfg['definitions']

    cfg = _add_title(cfg)

    return cfg
# ---------------------------------
def _add_title(cfg : DictConfig) -> DictConfig:
    title = f'{Data.component.latex}; {Data.trigger}; {Data.q2_bin}'
    for cfg_var in cfg.plots.values():
        cfg_var.title = title

    return cfg
# ---------------------------------
def _get_out_dir(plt_dir : str) -> str:
    out_dir = f'{_ANADIR}/plots/{plt_dir}/{Data.component}_{Data.trigger.value}_{Data.q2_bin}'

    return out_dir
# ---------------------------------
def _get_inp() -> dict[str, tuple[RDF.RNode, dict[Cuts,str]]]:
    rdf, sel = _get_rdf()

    if 'cutflow' not in Data.cfg:
        return {'None' : (rdf, sel)}

    d_cut = Data.cfg['cutflow'][Data.q2_bin]
    d_rdf : dict[str, tuple[RDF.RNode,dict[Cuts,str]]]= {}
    log.info('Applying cutflow')
    for name, cut in d_cut.items():
        log.info(f'{"":<4}{name:<15}{cut}')
        good_name      = naming.clean_special_characters(name=name)
        sel[name]      = cut
        sel_copy       = deepcopy(sel)

        rdf            = rdf.Filter(cut, good_name)
        d_rdf[name]    = (rdf, sel_copy)

    return d_rdf
# ---------------------------------
def _fix_ranges(cfg : DictConfig) -> DictConfig:
    '''
    Takes configuration and makes sure mass ranges make sense
    '''
    if 'MuMu' not in Data.trigger:
        return cfg

    for key, cfg_plt in cfg.plots.items():
        if key.startswith('B_M'):
            cfg_plt.binning = [5150, 5400, 50]

        if key.startswith('Jpsi_M'):
            cfg_plt.binning = [3000, 3200, 50]

    return cfg
# ---------------------------------
def _plot(d_rdf : dict[str,tuple[RDF.RNode, dict[Cuts,str]]]) -> None:
    cfg  = _get_cfg()
    cfg  = _fix_ranges(cfg=cfg)
    rdfs = { key : rdf for key, (rdf,   _) in d_rdf.items() }
    sels = { key : sel for key, (_  , sel) in d_rdf.items() }

    gut.dump_json(
        exists_ok= True,
        data     = sels, 
        path     = f'{cfg.saving.plt_dir}/selection.json')

    ptr=Plotter1D(d_rdf=rdfs, cfg=cfg)
    ptr.run()
# ---------------------------------
def _set_config(args : dict[str,str]) -> None:
    '''
    Parameters
    -------------
    settings: Dictionary with settings needed when used as a module
    '''
    config = args['config']

    Data.q2_bin   = Qsq(args['q2bin'])
    Data.component= Component(args['sample'])
    Data.trigger  = Trigger(args['trigger'])
    Data.config   = f'{config}_{Data.trigger.project}'
    Data.ncores   = 1
# ---------------------------------
def main(args : dict[str,str] | None = None):
    '''
    Script starts here
    '''
    if args is None:
        _parse_args()
    else:
        _set_config(args=args)

    if Data.ncores > 1:
        log.info(f'Using {Data.ncores} cores')
        EnableImplicitMT(Data.ncores)

    Data.cfg = _get_cfg()
    with RDFGetter.max_entries(value=-1),\
         RDFGetter.custom_columns(columns=Data.d_def):

        d_rdf = _get_inp()
        _plot(d_rdf = d_rdf)
# ---------------------------------
if __name__ == '__main__':
    main()
