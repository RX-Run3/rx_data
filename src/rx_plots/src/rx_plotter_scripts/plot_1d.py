'''
Script used to plot mass distributions
'''
# pylint: disable=logging-fstring-interpolation, no-name-in-module, line-too-long

import os
import glob
import argparse
from importlib.resources import files
from dataclasses         import dataclass

import yaml
import mplhep
import dmu.generic.utilities as gut
from ROOT                    import RDataFrame, EnableImplicitMT
from dmu.plotting.plotter_1d import Plotter1D
from dmu.logging.log_store   import LogStore
from dmu.generic             import version_management as vmn
from rx_data.rdf_getter      import RDFGetter
from rx_selection            import selection as sel

log=LogStore.add_logger('rx_selection:plot_1d')
# ---------------------------------
@dataclass
class Data:
    '''
    Class used to share attributes
    '''
    nthreads   = 13
    l_trigger  = ['Hlt2RD_BuToKpEE_MVA', 'Hlt2RD_BuToKpMuMu_MVA', 'Hlt2RD_BuToKpEE_SameSign_MVA']
    l_config   = ['bdt_q2_mass']
    d_reso     = {'jpsi' : 'B_const_mass_M', 'psi2' : 'B_const_mass_psi2S_M'}
    data_dir   = os.environ['DATADIR']

    mplhep.style.use('LHCb2')

    trigger : str
    q2_bin  : str
    level   : int
    trigger : str
    sample  : str
    config  : str
    version : str
    cfg_dir : str

    l_keep = []
# ---------------------------------
def _initialize() -> None:
    LogStore.set_level('dmu:plotting:Plotter'  , 10)
    LogStore.set_level('dmu:plotting:Plotter1D', 10)
    LogStore.set_level('rx_selection:plot_1d'  , 10)

    if Data.nthreads > 1:
        EnableImplicitMT(Data.nthreads)

    gut.TIMER_ON=True

    cfg_dir = files('rx_plotter_data').joinpath('')
    if Data.version is None:
        cfg_dir = vmn.get_last_version(dir_path=cfg_dir, version_only=False)
    else:
        cfg_dir = f'{cfg_dir}/{Data.version}'

    Data.cfg_dir = cfg_dir
    l_yaml  = glob.glob(f'{Data.data_dir}/samples/*.yaml')

    d_sample= { os.path.basename(path).replace('.yaml', '') : path for path in l_yaml }
    log.info('Using paths:')
    for name, path in d_sample.items():
        log.info(f'{name:<20}{path}')

    RDFGetter.samples = d_sample
# ---------------------------------
@gut.timeit
def _get_rdf() -> RDataFrame:
    gtr = RDFGetter(sample=Data.sample, trigger=Data.trigger)
    rdf = gtr.get_rdf()
    Data.l_keep.append(rdf)

    return rdf
# ---------------------------------
@gut.timeit
def _get_bdt_cutflow_rdf(rdf : RDataFrame) -> dict[str,RDataFrame]:
    cfg      = _get_cfg(kind='raw')
    d_wp     = cfg['wp'][Data.wp]
    l_cmb_wp = d_wp['cmb']
    l_prc_wp = d_wp['prc']

    d_rdf = {}
    for cmb in l_cmb_wp:
        rdf = rdf.Filter(f'mva_cmb > {cmb}')
        d_rdf [f'$MVA_{{cmb}}$ > {cmb}'] = rdf

    for prc in l_prc_wp:
        rdf = rdf.Filter(f'mva_prc > {prc}')
        d_rdf [f'$MVA_{{prc}}$ > {prc}'] = rdf

    return d_rdf
# ---------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to make plots of a dataset under a cutflow')
    parser.add_argument('-q', '--q2bin'  , type=str, help='q2 bin' , choices=['low', 'central', 'jpsi', 'psi2', 'high'], required=True)
    parser.add_argument('-t', '--trigger', type=str, help='HLT2 Trigger', choices=Data.l_trigger, required=True)
    parser.add_argument('-v', '--version', type=str, help='Version of inputs, will use latest if not set')
    parser.add_argument('-c', '--config' , type=str, help='Name of configuration file', choices=Data.l_config, required=True)
    parser.add_argument('-s', '--sample' , type=str, help='Name of sample, e.g. "Data*"', required=True)
    parser.add_argument('-k', '--kind'   , type=str, help='Type of cutflow', choices=['no_prc', 'prc'])
    parser.add_argument('-l', '--level'  , type=int, help='Logging message', choices=[10, 20, 30], default=20)
    args = parser.parse_args()

    Data.q2_bin = args.q2bin
    Data.config = args.config
    Data.trigger= args.trigger
    Data.version= args.version
    Data.sample = args.sample
    Data.level  = args.level
    Data.wp     = args.wp
# ---------------------------------
def _get_cfg(kind : str = 'raw') -> dict:
    cfg_path= f'{Data.cfg_dir}/{Data.config}.yaml'
    log.debug(f'Using config: {cfg_path}')
    with open(cfg_path, encoding='utf=8') as ifile:
        cfg = yaml.safe_load(ifile)

    if kind == 'raw':
        return cfg

    cfg = _override_cfg(cfg)

    if kind != 'last':
        return cfg

    d_plt        = cfg['plots']
    d_mas        = d_plt['B_M']
    if Data.trigger in ['Hlt2RD_BuToKpMuMu_MVA']:
        [_, maxx, nbins] = d_mas['binning']
        d_mas['binning'] = [5180, maxx, nbins]

    name         = d_mas['name']
    d_mas['name']= f'{name}_last'
    cfg['plots'] = {'B_M' : d_mas}

    return cfg
# ---------------------------------
def _get_cuts() -> dict:
    analysis = 'MM' if 'MuMu' in Data.trigger else 'EE'

    d_cut        = sel.selection(project='RK', analysis=analysis, q2bin=Data.q2_bin, process=Data.sample)
    d_cut['bdt'] = '(1)'

    log.info('Using cuts:')
    for name in d_cut:
        log.info(f'   {name}')

    return d_cut
# ---------------------------------
def _override_cfg(cfg : dict) -> dict:
    plt_dir                    = cfg['saving']['plt_dir']
    sample                     = Data.sample.replace('*', 'p')
    cfg['saving']['plt_dir']   = f'{plt_dir}/{Data.trigger}/{sample}/{Data.q2_bin}/{Data.wp}'
    cfg['selection']['cuts']   = _get_cuts()

    for var_name, d_plot in cfg['plots'].items():
        if 'title' not in d_plot:
            d_plot['title'] = ''

        title = d_plot['title']
        title = f'{Data.q2_bin} $q^2$ {title}'
        d_plot['title'] = title

        name           = d_plot['name']
        d_plot['name'] = name

        if var_name in ['B_M', 'ecalo_bias_B_M']:
            binning = cfg['mass_binning'][Data.q2_bin]
            cfg['plots'][var_name]['binning'] = binning

    return cfg
# ---------------------------------
@gut.timeit
def _plot(kind : str, d_rdf : dict[str,RDataFrame]) -> None:
    cfg= _get_cfg(kind)

    if kind == 'last':
        cfg['plots']['B_M']['yscale']  = 'linear'
        key, val = d_rdf.popitem()
        d_rdf    = {key : val}

        cfg['stats'] = {'nentries' : '\nEntries: {}'}

    ptr=Plotter1D(d_rdf=d_rdf, cfg=cfg)
    ptr.run()
# ---------------------------------
def main():
    '''
    Entry point
    '''
    _parse_args()
    _initialize()

    rdf   = _get_rdf()
    d_rdf = _get_bdt_cutflow_rdf(rdf)

    _plot(kind='cutflow', d_rdf = d_rdf)
    _plot(kind='last'   , d_rdf = d_rdf)
# ---------------------------------
if __name__ == '__main__':
    main()
