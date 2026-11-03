'''
Script used to plot overlays of a given variable, in a given dataframe,
under diferent selections. E.g. the mass distribution for different blocks
'''
import os
import argparse
import mplhep

from typing        import Final
from dataclasses   import dataclass
from omegaconf     import DictConfig
from dmu.generic   import utilities as gut
from ROOT          import RDF, EnableImplicitMT
from dmu.plotting  import Plotter1D
from dmu           import LogLevels, LogStore
from rx_data       import RDFGetter
from rx_selection  import selection as sel
from rx_common     import Component, Qsq, Trigger

log=LogStore.add_logger('rx_selection:cutflow')

_ANADIR       : Final[str] = os.environ['ANADIR']
_MIN_ELEMENTS : Final[int] = 2
mplhep.style.use('LHCb2')
# ---------------------------------
@dataclass
class Data:
    '''
    Class used to share attributes
    '''
    nthreads   = 1
    d_reso     = {'jpsi' : 'B_const_mass_M', 'psi2' : 'B_const_mass_psi2S_M'}
    l_kind     = [
        'ecal_xy',
        'brem',
        'block_no_tail',
        'npv',
        'resolution',
        'for_hlt',
        'q2_cut',
        'tail_cut',
        'no_dtf_mass_shape']

    chanel  : str
    config  : str
    sample  : Component
    trigger : Trigger
    q2_bin  : Qsq
    cfg_dir : str
    brem    : int | None
    logl    : int

    l_col  = []
# ---------------------------------
def _apply_definitions(rdf : RDF.RNode, cfg : DictConfig) -> RDF.RNode:
    if 'definitions' not in cfg:
        return rdf

    for name, expr in cfg.definitions.items():
        rdf = rdf.Define(name, expr)

    return rdf
# ---------------------------------
def _filter_by_brem(rdf : RDF.RNode) -> RDF.RNode:
    if Data.brem is None:
        return rdf

    brem_cut = f'nbrem == {Data.brem}' if Data.brem in [0, 1] else f'nbrem >= {Data.brem}'
    rdf = rdf.Filter(brem_cut, 'nbrem')

    return rdf
# ---------------------------------
@gut.timeit
def _get_rdf() -> RDF.RNode:
    cfg = _get_cfg()
    gtr = RDFGetter(sample=Data.sample, trigger=Data.trigger)
    rdf = gtr.get_rdf(per_file=False)
    rdf = _apply_definitions(rdf, cfg)

    d_sel = sel.selection(trigger=Data.trigger, q2bin=Data.q2_bin, process=Data.sample)

    if 'selection' in cfg:
        d_cut = cfg['selection']
        d_sel.update(d_cut)

    for cut_name, cut_value in d_sel.items():
        log.info(f'{cut_name:<20}{cut_value}')
        rdf = rdf.Filter(cut_value, cut_name)

    rdf = _filter_by_brem(rdf)

    if log.getEffectiveLevel() == LogLevels.info:
        rep = rdf.Report()
        rep.Print()

    return rdf
# ---------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to make generic plots')
    parser.add_argument('-q', '--q2bin'  , type=Qsq      , help='q2 bin'       , choices=list(Qsq), required=True)
    parser.add_argument('-s', '--sample' , type=Component, help='Sample'       , required=True)
    parser.add_argument('-t', '--trigger', type=Trigger  , help='Trigger'      , required=True)
    parser.add_argument('-c', '--config' , type=str      , help='Configuration', required=True)
    parser.add_argument('-b', '--brem'   , type=int      , help='Brem category', choices=[-1, 0, 1, 2], required=True)
    parser.add_argument('-l', '--logl'   , type=int      , help='Log level'    , choices=[10, 20, 30], default=20)
    args = parser.parse_args()

    Data.q2_bin = args.q2bin
    Data.sample = args.sample
    Data.trigger= args.trigger
    Data.config = f'{args.config}_{Data.trigger.project}'
    Data.brem   = args.brem
    Data.logl   = args.logl
# ---------------------------------
def _get_cfg() -> DictConfig:
    cfg = gut.load_conf(package='rx_plotter_data', fpath=f'overlay/{Data.config}.yaml')
    ini_dir = cfg.saving.plt_dir
    end_dir = _get_out_dir()

    cfg.saving.plt_dir = f'{_ANADIR}/plots/{ini_dir}/{end_dir}'
    log.info(f'Saving to: {cfg.saving.plt_dir}')

    return cfg
# ---------------------------------
def _get_out_dir() -> str:
    '''
    Returns
    --------------
    String defining termination of the path defined in the config
    '''
    if Data.brem == -1:
        brem_name = 'all'
    else:
        brem_name = f'{Data.brem:03}'

    out_dir = f'{Data.sample}/{Data.trigger.value}/{Data.q2_bin}/{brem_name}'

    return out_dir
# ---------------------------------
def _get_dataframes() -> dict[str,RDF.RNode]:
    cfg   = _get_cfg()
    rdf_in= _get_rdf()

    d_rdf = {}

    if len(cfg.cutflow) < _MIN_ELEMENTS:
        raise ValueError('At least two elements needed in cutflow')

    log.info('Applying overlay')
    for name, cut in cfg.cutflow.items():
        log.info(f'   {name:<20}{cut}')
        rdf = rdf_in.Filter(cut, name)
        d_rdf[name] = rdf

    return d_rdf
# ---------------------------------
def _plot(d_rdf : dict[str,RDF.RNode]) -> None:
    cfg= _get_cfg()
    cfg= _fix_ranges(cfg=cfg)

    if 'definitions' in cfg:
        del cfg['definitions']

    ptr=Plotter1D(d_rdf=d_rdf, cfg=cfg)
    ptr.run()
# ---------------------------------
def _fix_ranges(cfg : DictConfig) -> DictConfig:
    '''
    Takes configuration and makes sure mass ranges make sense
    '''
    if 'MuMu' not in Data.trigger:
        return cfg

    for key, cfg_plt in cfg.plots.items():
        if key.startswith('B_M'):
            cfg_plt.binning = [5150, 5400, 100]

        if key.startswith('Jpsi_M'):
            cfg_plt.binning = [3000, 3200, 100]

    return cfg
# ----------------------
def _initialize_pars(cfg : DictConfig) -> None:
    '''
    Parameters
    -------------
    cfg: User defined config, needed to initialize attributes of Data
    '''
    Data.q2_bin = Qsq(cfg.q2bin)
    Data.sample = Component(cfg.sample)
    Data.trigger= Trigger(cfg.trigger)
    Data.config = f'{cfg.config}_{Data.trigger.project}'
    Data.brem   = cfg.brem
    Data.logl   = LogLevels.info
# ---------------------------------
def main(cfg : DictConfig|None = None):
    '''
    Script starts here
    '''
    if cfg is None:
        _parse_args()
    else:
        _initialize_pars(cfg=cfg)

    if Data.nthreads > 1:
        EnableImplicitMT(Data.nthreads)

    LogStore.set_level('rx_selection:cutflow', Data.logl)

    d_rdf = _get_dataframes()
    _plot(d_rdf = d_rdf)
# ---------------------------------
if __name__ == '__main__':
    main()
