'''
Script used to plot mass distributions
'''

import os
import argparse
import mplhep

from dmu.generic   import utilities as gut
from dmu.plotting  import Plotter2D
from dmu           import LogStore
from pathlib       import Path
from typing        import Final
from omegaconf     import DictConfig
from rx_selection  import selection as sel
from rx_data       import RDFGetter
from rx_common     import Component, Qsq, Trigger, info

log=LogStore.add_logger('rx_plots:plot_2d')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ---------------------------------
class Data:
    '''
    Class used to share attributes
    '''
    mplhep.style.use('LHCb2')

    nthreads: int = 1
    loglvl  : int = 20
    config  : str = ''
    q2bin   : Qsq
    sample  : Component
    trigger : Trigger
# ---------------------------------
def _set_logs() -> None:
    LogStore.set_level('rx_plots:plot_2d'      , Data.loglvl)
    LogStore.set_level('rx_selection:selection', Data.loglvl)
    LogStore.set_level('rx_data:rdf_getter'    , Data.loglvl)
    LogStore.set_level('dmu:plotting:Plotter2D', Data.loglvl)
    LogStore.set_level('dmu:plotting:Plotter'  , Data.loglvl)
# ---------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to make 2D plots')
    parser.add_argument('-q', '--q2bin'   , type=Qsq      , help='q2 bin, optional' , choices=list(Qsq), required=True)
    parser.add_argument('-c', '--config'  , type=str      , help='Settings, i.e. mass_q2', required=True)
    parser.add_argument('-s', '--sample'  , type=Component, help='Name of sample, can use wildcards', required=True)
    parser.add_argument('-t', '--trigger' , type=Trigger  , help='Name of trigger', required=True)
    parser.add_argument('-l', '--loglvl'  , type=int      , help='Log level', choices=[10, 20, 30], default=20)
    parser.add_argument('-n', '--nthreads', type=int      , help='Number of threads', default=Data.nthreads)
    args = parser.parse_args()

    project = info.project_from_trigger(trigger=args.trigger, lower_case=True)

    Data.sample   = args.sample
    Data.trigger  = args.trigger
    Data.loglvl   = args.loglvl
    Data.q2bin    = args.q2bin
    Data.config   = f'{args.config}_{project}'
    Data.nthreads = args.nthreads
# ---------------------------------
def _override_output(cfg : DictConfig) -> DictConfig:
    '''
    Parameters
    ---------------
    cfg: Dictionary with plotting configuration

    Returns
    ---------------
    This method returns configuration with:

    - Plotting directory overriden
    - Name of output file overriden
    '''
    plt_dir = cfg.saving.plt_dir
    cfg.saving.plt_dir = f'{_ANADIR}/{plt_dir}/{Data.sample}/{Data.trigger.value}'

    for l_setting in cfg.plots_2d:
        name         = l_setting[3]
        l_setting[3] = f'{name}_{Data.q2bin}'

    return cfg
# ----------------------
def _initialize_settings(cfg : DictConfig) -> None:
    '''
    Parameters
    -------------
    cfg: Configuration dictionary passed when this file is treated as a module
    '''

    Data.sample   = Component(cfg.sample)
    Data.trigger  = Trigger(cfg.trigger)
    Data.q2bin    = Qsq(cfg.q2bin)
    Data.config   = f'{cfg.config}_{Data.trigger.project}'
    Data.loglvl   = 20
    Data.nthreads = 1
# ---------------------------------
def main(cfg : DictConfig|None = None):
    '''
    Script starts here
    '''
    if cfg is None:
        _parse_args()
    else:
        _initialize_settings(cfg=cfg)

    _set_logs()

    cfg_plt = gut.load_conf(package='rx_plotter_data', fpath=f'2d/{Data.config}.yaml')
    cfg_plt = _override_output(cfg=cfg_plt)
    d_cut   = cfg_plt.get('selection', {})
    d_def   = cfg_plt.get('definitions', {})

    with RDFGetter.custom_columns(columns = d_def),\
        sel.custom_selection(d_sel=d_cut):

        cfg_plt.pop('definitions', None)
        cfg_plt.pop('selection', None)

        gtr = RDFGetter(sample=Data.sample, trigger=Data.trigger)
        rdf = gtr.get_rdf(per_file=False)

        rdf = sel.apply_full_selection(
            process  = Data.sample,
            trigger  = Data.trigger,
            q2bin    = Data.q2bin,
            out_path = Path(cfg_plt.saving.plt_dir),
            rdf      = rdf)

        ptr=Plotter2D(rdf=rdf, cfg=cfg_plt)
        ptr.run()
# ---------------------------------
if __name__ == '__main__':
    main()
