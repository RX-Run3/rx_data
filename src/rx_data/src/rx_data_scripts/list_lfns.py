'''
This script should create a list of LFNs based on the
versions provided by the user
'''
import tqdm
import argparse

from dataclasses import dataclass
from dmu.generic import utilities as gut

from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_data:list_lfns')
# ----------------------
@dataclass
class Conf:
    '''
    Data class meant to contain configuration
    '''
    project : str
    vers    : list[str]
# ----------------------
def _parse_args() -> Conf:
    parser = argparse.ArgumentParser(description='Script used to make list of LFNs')
    parser.add_argument('-p', '--project', type =str, help='E.g. rx'         , required=True, choices=['rx', 'nopid'])
    parser.add_argument('-v', '--vers'   , nargs='+', help='List of versions', required=True)
    parser.add_argument('-l', '--loglvl' , type =str, help='Logging level'   , default =  20)
    args = parser.parse_args()

    LogStore.set_level('rx_data:list_lfns', args.loglvl)

    return Conf(project=args.project, vers=args.vers)
# ----------------------
def _lfns_from_version(version : str, project : str) -> list[str]:
    '''
    Parameters
    -------------
    version: Version of LFNs
    Project: E.g. rx

    Returns
    -------------
    List of LFns associated
    '''
    l_cfg = gut.load_from_wcard(package='rx_data_lfns', fwcard=f'{project}/{version}/*.json')
    ncfg  = len(l_cfg)

    log.debug(f'Found {ncfg} lists')

    l_lfn = []
    for cfg in tqdm.tqdm(l_cfg, ascii=' -'):
        l_lfn += cfg

    return l_lfn
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg = _parse_args()

    l_lfn = []
    for version in cfg.vers:
        l_lfn += _lfns_from_version(version=version, project=cfg.project)

    gut.dump_text(lines=l_lfn, path='./lfns.txt')
# ----------------------
if __name__ == '__main__':
    main()
