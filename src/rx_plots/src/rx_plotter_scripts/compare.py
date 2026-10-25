'''
Script used to compare different variables in the same dataframe
'''
import os
import mplhep
import argparse

from typing       import Final
from rx_common    import Component, Cuts, Qsq, Trigger
from dataclasses  import dataclass
from pathlib      import Path
from omegaconf    import DictConfig
from ROOT         import RDF, EnableImplicitMT
from dmu          import LogLevels, LogStore
from dmu.generic  import utilities as gut
from dmu.plotting import Plotter1D
from rx_data      import RDFGetter
from rx_selection import selection as sel

log=LogStore.add_logger('rx_plots:compare')

_BLOCKS : Final[list[int]] = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8]
# ---------------------------------
class EmptyInput(Exception):
    '''
    Meant to be used when input dataframe is empty
    but it's not meant to be empty
    '''
    def __init__(self, message: str, code: int|None = None):
        super().__init__(message)
        self.code = code
# ---------------------------------
@dataclass
class Config:
    '''
    Class used to store configuration
    '''
    q2_bin  : Qsq 
    sample  : Component 
    trigger : Trigger 
    config  : str
    brem    : int
    block   : int
    mva     : int 
    emulate : int
    ncores  : int

    d_reso  = {Qsq.jpsi : 'B_const_mass_M', Qsq.psi2 : 'B_const_mass_psi2S_M'}
    ana_dir = Path(os.environ['ANADIR'])
    l_col   = []
# ---------------------------------
def _get_plot_cfg(cfg : Config) -> DictConfig: 
    '''
    Returns
    -------------
    OmegaConf dictionary with configuration
    '''
    cfg_plt = gut.load_conf(package='rx_plotter_data', fpath=f'compare/{cfg.config}.yaml')
    plt_dir = cfg_plt.saving.plt_dir
    cfg_plt.saving.plt_dir = _get_out_dir(plt_dir=plt_dir, cfg=cfg)

    for d_setting in cfg_plt.plots.values():
        brem  = 'all' if cfg.brem == -1 else str(cfg.brem)
        block = 'all' if cfg.block== -1 else str(cfg.block)

        d_setting['title'] = f'Brem {brem}; Block {block}; {cfg.sample.latex}'

    # If user does not request emulation
    # Drop these plots
    run12_key = 'Corrected and L0(nPVs)'
    if cfg.emulate == 0 and cfg.config == 'resolution':
        log.info('Not emulating Run1/2 conditions')
        del cfg_plt.comparison[run12_key]
    else:
        log.info('Emulating Run1/2 conditions')

    return cfg_plt
# ---------------------------------
def _apply_definitions(
    rdf    : RDF.RNode,
    cfg_plt: DictConfig) -> RDF.RNode:

    if 'definitions' not in cfg_plt:
        return rdf

    for name, expr in cfg_plt.definitions.items():
        rdf = rdf.Define(name, expr)

    # Not needed anymore
    # Would interfere with rest of code
    del cfg_plt['definitions']

    return rdf
# ---------------------------------
def _check_entries(rdf : RDF.RNode) -> None:
    nentries = rdf.Count().GetValue()

    if nentries > 0:
        return

    rep = rdf.Report()
    rep.Print()

    raise EmptyInput('Found zero entries in dataframe')
# ---------------------------------
def _update_with_brem(
    cfg   : Config,
    d_sel : dict[Cuts,str]) -> dict[Cuts,str]:
    '''
    Parameters
    ---------------
    cfg  : Configuration needed to build inputs
    d_sel: Selection

    Returns
    ---------------
    Updated selection dictionary
    '''
    if cfg.brem == -1:
        log.info('Not filtering by brem')
        return d_sel

    if cfg.brem == 12: # noqa
        d_sel[Cuts.brem] = 'nbrem == 1 || nbrem == 2'
    else:
        d_sel[Cuts.brem] = f'nbrem == {cfg.brem}'

    return d_sel
# ---------------------------------
def _update_with_block(
    d_sel : dict[Cuts,str],
    cfg   : Config) -> dict[Cuts,str]:
    '''
    Parameters
    ---------------
    cfg  : Configuration needed to build inputs
    d_sel: Selection

    Returns
    ---------------
    Updated block cuts 
    '''
    if cfg.block == -1:
        log.info('Not filtering by block')
        return d_sel

    d_sel[Cuts.block] = f'block == {cfg.block}'

    return d_sel
# ---------------------------------
@gut.timeit
def _get_rdf(
    cfg     : Config, 
    cfg_plt : DictConfig) -> RDF.RNode:
    '''
    Parameters
    ----------------
    cfg    : Config used to build input
    cfg_plt: Config with plotting information

    Returns
    ----------------
    ROOT dataframe
    '''
    gtr   = RDFGetter(sample=cfg.sample, trigger=cfg.trigger)
    rdf   = gtr.get_rdf(per_file=False)
    rdf   = _apply_definitions(rdf=rdf, cfg_plt=cfg_plt)
    d_sel = _get_selection(cfg=cfg, cfg_plt=cfg_plt)

    for cut_name, cut_value in d_sel.items():
        log.info(f'{cut_name:<20}{cut_value}')
        rdf = rdf.Filter(cut_value, cut_name)

    return rdf
# ----------------------
def _get_selection(
    cfg     : Config,
    cfg_plt : DictConfig) -> dict[Cuts,str]:
    '''
    Parameters
    -------------
    cfg    : Configuration used to build inputs 
    cfg_plt: Plotting configuration

    Returns
    -------------
    Dictionary with selection
    '''
    d_sel = sel.selection(trigger=cfg.trigger, q2bin=cfg.q2_bin, process=cfg.sample)

    if cfg.mva == 0:
        log.info('Removing MVA requirement')
        d_sel[Cuts.cmb] = '(1)'
        d_sel[Cuts.prc] = '(1)'

    if 'selection' in cfg_plt:
        d_cut = cfg_plt.selection
        # Mass cut on DTF mass is only needed in data
        # to remove part reco
        if not cfg.sample.startswith('DATA_'):
            d_cut['mass'] = '(1)'

        d_sel.update(d_cut)
        del cfg_plt.selection

    d_sel = _update_with_brem( d_sel = d_sel, cfg = cfg)
    d_sel = _update_with_block(d_sel = d_sel, cfg = cfg)

    return d_sel
# ---------------------------------
def _cfg_from_args() -> Config:
    '''
    Returns
    ------------------
    Configuration instance built from arguments passed by user
    '''
    parser = argparse.ArgumentParser(description='Script used to make comparison plots between distributions in the same dataframe')
    parser.add_argument('-s', '--sample' , type=Component, help='Sample' , required=True)
    parser.add_argument('-t', '--trigger', type=Trigger  , help='Trigger', required=True)
    parser.add_argument('-q', '--q2bin'  , type=Qsq      , help='q2 bin' , choices=list(Qsq), required=True)
    parser.add_argument('-c', '--config' , type=str      , help='Configuration', required=True)
    parser.add_argument('-b', '--brem'   , type=int      , help='Brem category, 12 = 1 or 2, -1 = all' , choices=[-1, 0, 1, 2, 12], required=True)
    parser.add_argument('-B', '--block'  , type=int      , help='Block to which data belongs, -1 will put all the data together', choices=_BLOCKS, required=True)
    parser.add_argument('-l', '--log_lvl', type=int      , help='Logging level', choices=list(LogLevels), default=LogLevels.info)
    parser.add_argument('-n', '--ncores' , type=int      , help='Number of cores if using multithreading', default=1)
    parser.add_argument('-m', '--mva'    , type=int      , help='If 1, will use mva, otherwise will drop it', choices=[0, 1])
    parser.add_argument('-e', '--emulate', type=int      , help='If 1, will emulate Run1/2 conditions'      , choices=[0, 1])
    args = parser.parse_args()

    LogStore.set_level('rx_plots:compare'      , args.log_lvl)
    LogStore.set_level('dmu:plotting:Plotter'  , args.log_lvl)
    LogStore.set_level('dmu:plotting:Plotter1D', args.log_lvl)

    cfg = Config(
        q2_bin = args.q2bin,
        sample = args.sample,
        trigger= args.trigger,
        config = args.config,
        brem   = args.brem,
        block  = args.block,
        mva    = args.mva,
        ncores = args.ncores,
        emulate= args.emulate)

    return cfg
# ---------------------------------
def _get_out_dir(
    plt_dir : Path, 
    cfg     : Config) -> Path:
    '''
    Parameters
    ---------------
    plt_dir : Directory where plots will go
    cfg     : Configuration with metadata

    Returns
    ---------------
    Directory where plots will go
    '''

    brem  = 'all' if cfg.brem == -1 else str(cfg.brem)
    block = 'all' if cfg.block== -1 else str(cfg.block)

    out_dir = cfg.ana_dir / plt_dir / f'{cfg.sample}/{cfg.trigger.value}/{cfg.q2_bin}/{brem}_{block}'
    out_dir = out_dir / 'drop_mva' if cfg.mva == 0 else out_dir / 'with_mva'

    return out_dir
# ---------------------------------
def _rdf_from_def(
    rdf   : RDF.RNode, 
    d_def : DictConfig) -> RDF.RNode:
    '''
    Parameters
    ------------------
    rdf  : ROOT dataframe with data to plot
    d_def: Dictionary with variable needed to be plotted and their definitions

    Returns
    ------------------
    ROOT dataframe with data
    '''
    log.debug('Defining extra columns')
    for name, expr in d_def.vars.items():
        log.verbose(f'Defining: {name}={expr}')
        rdf = rdf.Define(name, expr)

    if 'cuts' not in d_def:
        log.debug('No cuts specified')
        return rdf

    log.debug('Applying cuts')
    for cut_name, cut_expr in d_def.cuts.items():
        log.verbose(f'Applying cut: {cut_expr}')
        rdf = rdf.Filter(cut_expr, cut_name)

    if log.getEffectiveLevel() < LogLevels.info:
        rep = rdf.Report()
        rep.Print()

    _check_entries(rdf=rdf)

    return rdf
# ---------------------------------
def _get_inp(cfg : Config, cfg_plt : DictConfig) -> dict[str,RDF.RNode]:
    '''
    Parameters
    -------------------
    cfg    : Configuration needed to builld input data
    cfg_plt: Configuration needed for plotting

    Returns
    -------------------
    Dictionary where keys are identifiers and values are dataframes with data to plot
    '''
    rdf_in = _get_rdf(cfg=cfg, cfg_plt=cfg_plt)
    d_cmp  = cfg_plt.comparison

    d_rdf  = {}
    for kind, d_def in d_cmp.items():
        rdf = _rdf_from_def(rdf=rdf_in, d_def=d_def)
        d_rdf[kind] = rdf

    log.info('Returning dataframe')

    return d_rdf
# ---------------------------------
def _omega_conf_to_config(settings : DictConfig) -> Config:
    '''
    Transforms DictConfig object from LAW workflow into
    data class
    '''
    return Config(
        q2_bin = Qsq(settings.q2_bin),
        sample = Component(settings.sample),
        trigger= Trigger(settings.trigger),
        config = settings.config,
        brem   = settings.brem,
        block  = settings.block,
        mva    = settings.mva,
        emulate= settings.emulate,
        ncores = 1) # Use one core per run with workflows
# ---------------------------------
def main(settings : DictConfig|None = None) -> list[Path]:
    '''
    Parameters
    ------------------
    settings: Dictionary with configuration needed to build dataframes

    Returns
    ------------------
    List of paths to plots made
    '''
    if settings is None:
        cfg = _cfg_from_args()
    else:
        cfg = _omega_conf_to_config(settings = settings)

    if cfg.ncores > 1:
        log.info(f'Using {cfg.ncores} cores')
        EnableImplicitMT(cfg.ncores)

    cfg_plt = _get_plot_cfg(cfg=cfg)
    mplhep.style.use('LHCb2')

    l_path = []
    d_rdf  = _get_inp(cfg=cfg, cfg_plt=cfg_plt)
    for rdf in d_rdf.values():
        rep = rdf.Report()
        rep.Print()

    log.info('Plotting')
    ptr    = Plotter1D(d_rdf=d_rdf, cfg=cfg_plt)
    path   = ptr.run()

    l_path.append(path)

    return l_path
# ---------------------------------
if __name__ == '__main__':
    main()
