'''
This script is meant to list information from AP productions
'''

import argparse
import apd
from typing                import Final
from apd                   import SampleCollection
from dataclasses           import dataclass
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('ap_utilities:list_ap_samples')
# ----------------------
@dataclass
class Config:
    '''
    Class used to store configuration
    '''
    version    : Final[str]
    production : Final[str]
# ----------------------
def _parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Script needed to parse samples from AP productions')
    parser.add_argument('-v', '--version'   , type=str, help='Version of production'           , required=True)
    parser.add_argument('-p', '--production', type=str, help='Production name, e.g. rd_ap_2024', required=True)

    args = parser.parse_args()
    cfg  = Config(version=args.version, production=args.production)

    return cfg
# ----------------------
def _list_samples(cfg : Config) -> None:
    '''
    Parameters
    -------------
    cfg: Config object
    '''
    dset = apd.get_analysis_data(working_group='RD', analysis=cfg.production)
    scol = dset.all_samples()
    if not isinstance(scol, SampleCollection):
        raise RuntimeError('Cannot extract SampleCollection instance')

    scol = scol.filter(version=cfg.version)
    nsam = len(scol)
    log.info(30 * '-')
    log.info(f'Found {nsam} samples:')
    log.info(30 * '-')
    samples = [ sample['name'] for sample in scol ]
    samples = sorted(samples)
    for sample in samples:
        log.info(sample)
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg = _parse_args()

    _list_samples(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
