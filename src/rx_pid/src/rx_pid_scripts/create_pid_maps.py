'''
Script meant to be used to create PID maps
'''
# pylint: disable=line-too-long
import os
import argparse
from typing import cast, Any

from omegaconf                import DictConfig, OmegaConf
from pidcalib2.make_eff_hists import make_eff_hists

import dmu.generic.utilities as gut
from dmu.generic             import hashing
from dmu.logging.log_store   import LogStore

log=LogStore.add_logger('rx_pid:create_pid_maps')
# --------------------------------
class Data:
    '''
    Data class
    '''
    l_particle : list[str] = ['e', 'Pi', 'K', 'Mu', 'P']

    brem    : str
    particle: str
    sample  : str
    out_dir : str
    region  : str
    dry_run : bool

    max_files: int
    verbose  : bool
# --------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to calculate PID efficiencies using PIDCalib2')
    parser.add_argument('-b', '--brem', type=str, help='Version of binning file', choices=['nobrem', 'brem'], required=True)
    parser.add_argument('-p', '--particle', type=str, help='Particle name', choices=Data.l_particle    , required=True)
    parser.add_argument('-s', '--sample'  , type=str, help='Sample/block, e.g. b1, b2...'              , required=True)
    parser.add_argument('-o', '--out_dir' , type=str, help='Directory where pkl files will go'         , required=True)
    parser.add_argument('-r', '--region'  , type=str, help='Used to define selection', choices=['signal', 'control'], required=True)
    parser.add_argument('-d', '--dry-run' ,           help='Enable dry-run mode (default: False)'      , action='store_true')
    # These are by default None and will be used as in PIDCalib2's make_eff_hists
    parser.add_argument('-m', '--maxfiles', type=int, help='Limit number of files to this value')
    parser.add_argument('-v', '--verbose' , help='Will print debug messages', action='store_true')

    args          = parser.parse_args()
    Data.brem     = args.brem
    Data.region   = args.region
    Data.out_dir  = args.out_dir
    Data.particle = args.particle
    Data.sample   = args.sample
    Data.dry_run  = args.dry_run
    Data.verbose  = args.verbose
    Data.max_files= args.maxfiles
# --------------------------------
def _get_binning(conf : DictConfig) -> dict:
    '''
    Parameters
    ---------------
    conf : Configuration passed by user

    Returns
    ---------------
    Path to JSON file with binning
    '''
    data     = conf['binning']['nominal']
    data     = data[Data.sample]
    data     = OmegaConf.to_container(cfg=data, resolve=True)
    if not isinstance(data, dict):
        raise ValueError('Binning configuration not a dictionary')

    data     = cast(dict[str,str], data)
    data     = { _assign_particle_name(name=key) : val for key, val in data.items() }

    return { Data.particle : data }
# ----------------------
def _get_binning_vars(binning: dict) -> list[str]:
    '''
    Parameters
    -------------
    binning: Nested dictionary with binning information

    Returns
    -------------
    List of strings, symbolizing variable names used for axes in maps
    '''
    particle_binning = binning[Data.particle]
    l_var = list(particle_binning.keys())

    return l_var
# ----------------------
def _get_binning_path(binning : dict) -> str:
    '''
    Parameters
    ---------------
    binning: Nested dictionary with binning for current sample (block)

    Returns
    ---------------
    Path to JSON file with binning
    '''

    hash_val = hashing.hash_object(binning)

    os.makedirs('.binning', exist_ok=True)

    json_path = f'.binning/{hash_val}.json'
    log.debug(f'Using binning path: {json_path}')
    gut.dump_json(binning, json_path)

    return json_path
# ----------------------
def _assign_particle_name(name : str) -> str:
    '''
    Parameters
    -------------
    name: String containing PARTICLE substring

    Returns
    -------------
    Input string with substring replaced with proper name
    '''
    name = name.replace('PARTICLE', Data.particle)

    # Tree has pion branch with lowercase "p"
    # PIDCalib2 has them with uppercase
    name = name.replace('Pi_', 'pi_')

    return name
# --------------------------------
def _get_prior_cuts(conf : DictConfig) -> list[str]:
    '''
    Parameters
    ---------------
    conf : Dictionary with configuration

    Returns
    ---------------
    List of cuts needed to align calibration samples to analysis sample
    '''
    l_cut    = conf['selection']
    l_cut    = [ _assign_particle_name(name=cut) for cut in l_cut ]
    brem_cut = conf['subselection'][Data.brem]
    brem_cut = _assign_particle_name(name=brem_cut)
    l_cut.append(brem_cut)

    log.debug('Using cuts:')
    for cut in l_cut:
        log.debug(cut)

    return l_cut
# --------------------------------
def _get_pid_cuts(conf : DictConfig) -> str:
    '''
    Parameters
    ----------------
    conf: Dictionary with configuration, loaded from YAML file

    Returns
    ----------------
    Cut whose efficiency will be measured
    - Signal, control region cut
    - Hadron tagging cut
    - Brem or no brem cut
    '''
    l_cut   = conf['regions'   ][Data.region]
    if Data.region == 'control':
        tag_cut = conf['subregions']['hadron_tagging'][Data.particle]
        l_cut   = l_cut + [tag_cut]

    l_cut   = [ _assign_particle_name(name=cut) for cut in l_cut ]
    cut     = ' & '.join(l_cut)

    log.debug(f'Using PID cut: {cut}')

    return cut
# --------------------------------
def _get_polarity() -> str:
    if Data.sample in ['b1', 'b2', 'b3', 'b5', 'b8']:
        polarity = 'up'
    elif Data.sample in ['b4', 'b6', 'b7']:
        polarity = 'down'
    else:
        raise NotImplementedError(f'Invalid sample: {Data.sample}')

    log.debug(f'Using polarity: {polarity}')

    return polarity
# --------------------------------
def _get_config() -> dict[str,Any]:
    '''
    Returns
    --------------
    Returns configuration dictionary needed by PIDCalib2
    `make_eff_hists` method
    '''
    conf    = gut.load_conf(package='rx_pid_data', fpath='config/config.yaml')
    binning = _get_binning(conf=conf)

    cfg : dict              = {}
    cfg['sample']           = conf['samples'][Data.sample]
    cfg['pid_cuts']         = [ _get_pid_cuts(conf=conf) ] # PIDCalib2 expects a list of cuts, we use one cut, make list of one element...
    cfg['cuts']             = _get_prior_cuts(conf=conf)
    cfg['binning_file']     = _get_binning_path(binning=binning)
    cfg['bin_vars']         = _get_binning_vars(binning=binning)
    cfg['magnet']           = _get_polarity()
    cfg['particle']         = Data.particle
    cfg['output_dir']       = Data.out_dir
    cfg['max_files']        = Data.max_files
    cfg['verbose']          = Data.verbose
    cfg['local_dataframe']  = None
    cfg['file_list']        = None
    cfg['samples_file']     = None

    return cfg
# --------------------------------
def main():
    '''
    Start here
    '''
    _parse_args()
    if Data.verbose:
        LogStore.set_level('rx_pid:create_pid_maps', 10)

    cfg = _get_config()

    if Data.dry_run:
        return

    make_eff_hists(cfg)
# --------------------------------
if __name__ == '__main__':
    main()
