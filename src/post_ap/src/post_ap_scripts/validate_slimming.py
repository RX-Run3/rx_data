'''
Script used to validate slimmed ntuples

Usage:

validate_slimming -P rk -v v1 -p /path/to/directory/with/ntuples

In the case above, the slimmed ntuples will have been made with a config
`v1.yaml` associated to project `rk`. The script will check that:

- The number of LFNs to the processed according to:

  - APD, taken from the `v1.yaml` config file through `PFNReader`

  is the same as

  - The ones that were processed according to the metadata of the ntuples.
'''

import textwrap
import argparse
import tqdm
import json
from ROOT                  import TFile
from pathlib               import Path
from dataclasses           import dataclass

from dmu.generic           import hashing
from dmu.generic           import utilities as gut
from dmu.logging.log_store import LogStore
from omegaconf             import DictConfig, OmegaConf
from post_ap.pfn_reader    import PFNReader

log=LogStore.add_logger('post_ap:validate_slimming')
# ----------------------
@dataclass(frozen=True)
class Conf:
    '''
    Data class meant to contain configuration
    '''
    project    : str
    version    : str
    path       : Path
# ----------------------
def _get_conf() -> Conf:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''
    if not isinstance(__doc__, str):
        raise ValueError('Missing documentation for module')

    parser = argparse.ArgumentParser(
        prog           = 'validate_slimming',
        formatter_class= argparse.RawDescriptionHelpFormatter,
        description    = textwrap.dedent(__doc__).strip())

    parser.add_argument('-P', '--project' , type=str , help='Project, needed to find config', choices=['rk', 'rkst'])
    parser.add_argument('-v', '--version' , type=str , help='Version of LFNs'                       , required=True)
    parser.add_argument('-p', '--path'    , type=Path, help='Path to directory with slimmed ntuples', required=True)

    args = parser.parse_args()

    return Conf(
        project    = args.project,
        version    = args.version,
        path       = args.path)
# ----------------------
def _get_paths(cfg : Conf) -> set[Path]:
    '''
    Parameters
    -------------
    cfg: Configuration object

    Returns
    -------------
    List of paths to ROOT files resulting from slimming
    '''
    gen    = cfg.path.glob(pattern='*.root')
    s_path = set(gen)
    npath  = len(s_path)

    if npath == 0:
        raise ValueError(f'No files found in: {cfg.path}')

    log.info(f'Found {npath} files in {cfg.path}')

    return s_path
# ----------------------
def _get_pfns_from_apd(cfg : Conf) -> set[str]:
    '''
    Parameters
    -------------
    cfg: Object storing configuration

    Returns
    -------------
    Set of PFNs needed to be slimmed
    '''
    cfg_slim   = gut.load_conf(package='post_ap_data', fpath=f'post_ap/{cfg.project}/{cfg.version}.yaml')
    production = _production_from_config(cfg=cfg_slim)
    samples    = cfg_slim.productions[production].samples

    l_pfn : list[str] = []
    reader = PFNReader(cfg=cfg_slim)
    for sample in samples:
        log.debug(f'Picking PFNs for: {sample}')
        d_tmp = reader.get_pfns(production=production, nickname=sample)
        for value in d_tmp.values():
            l_pfn+= value

    return set(l_pfn)
# ----------------------
def _production_from_config(cfg : DictConfig) -> str:
    '''
    Parameters
    -------------
    cfg: COnfiguration used to slim ntuples

    Returns
    -------------
    Name of production (e.g. rx_2024).
    One and only one production is expected in the config.
    '''
    productions = cfg.productions
    if len(productions) != 1:
        yaml_str = OmegaConf.to_yaml(cfg=cfg)
        log.info(yaml_str)

        raise ValueError('Not found one and only one production')

    return list(productions)[0]
# ----------------------
def _get_processed_pfns(paths : set[Path]) -> set[str]:
    '''
    Parameters
    -------------
    paths: Paths to ROOT files obtained from slimming

    Returns
    -------------
    Set of PFNs that were slimmed to make these ROOT files
    '''
    hsh       = hashing.hash_object(obj=paths)
    pfns_list = Path(f'/tmp/{hsh}.json')
    if pfns_list.exists():
        log.info(f'Loading cached PFNs from: {pfns_list}')
        l_pfn = gut.load_json(pfns_list)

        _check_group_size(l_pfn=l_pfn)

        return set(l_pfn)

    l_pfn = []
    for path in tqdm.tqdm(paths, ascii=' -'):
        pfn = _get_pfn_from_path(path)
        l_pfn.append(pfn)

    pfns_list = Path(f'/tmp/{hsh}.json')

    log.info(f'Caching list of PFNs to: {pfns_list}')
    gut.dump_json(data=l_pfn, path=pfns_list)

    _check_group_size(l_pfn=l_pfn)

    return set(l_pfn)
# ----------------------
def _check_group_size(l_pfn : list[str]) -> bool:
    '''
    Parameters
    -------------
    l_pfn: List of PFNs collected from slimmed ntuples

    Returns
    -------------
    True if check is passed, false otherwise
    '''
    d_freq = {}
    for pfn in l_pfn:
        if pfn not in d_freq:
            d_freq[pfn] = 1
        else:
            d_freq[pfn]+= 1

    s_freq = set(d_freq.values())

    if len(s_freq) != 1:
        log.error(f'Not one and only one number of ntuples per PFN: {s_freq}')
        return False
    else:
        log.info(f'All PFNs produced {s_freq} ntuples')
        return True
# ----------------------
def _get_pfn_from_path(path : Path) -> str:
    '''
    Parameters
    -------------
    path: Path to ROOT file from slimming

    Returns
    -------------
    PFN used to make this ROOT file
    '''
    ifile   = TFile(str(path), 'read')
    data    = ifile.metadata.GetString().Data()
    ifile.Close()

    cfg     = json.loads(data)
    yml_str = OmegaConf.to_yaml(cfg)
    cfg     = OmegaConf.create(yml_str)

    return cfg.input
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg   = _get_conf()
    paths = _get_paths(cfg=cfg)

    s_pfn_proc = _get_processed_pfns(paths=paths)
    s_pfn_exist= _get_pfns_from_apd(cfg=cfg)

    if s_pfn_proc == s_pfn_exist:
        npfn = len(s_pfn_exist)
        log.info(f'Validated, found, {npfn} PFNs')
        return

    norig = len(s_pfn_exist)
    nproc = len(s_pfn_proc )

    log.warning(f'PFN to be processed: {norig}')
    log.warning(f'PFN processed: {nproc}')
# ----------------------
if __name__ == '__main__':
    main()
