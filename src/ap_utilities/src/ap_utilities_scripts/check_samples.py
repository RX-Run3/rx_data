'''
Script used to check which MC samples are found in grid
'''
import argparse
import pandas    as pnd

from dataclasses                            import dataclass
from typing                                 import Final
from ap_utilities.logging.log_store         import LogStore
from ap_utilities.bookkeeping.bkk_checker   import BkkChecker
from ap_utilities.bookkeeping.sample_config import SampleConfig

log=LogStore.add_logger('ap_utilities_scripts:check_samples')

SETTINGS   : Final[list[str]] = ['2024_sim10d', '2024_sim10f', '2024_sim10g']
PRIORITIES : Final[list[str]] = [
        'high_priority', 
        'medium_priority', 
        'low_priority', 
        'very_low_priority']
# --------------------------------
@dataclass
class Conf:
    '''
    Class storing shared attributes
    '''
    samples : str
    config  : str
    nthread : int
    log_lvl : int
    priority: list[str]
# ----------------------------------------
def _parse_args() -> Conf:
    parser = argparse.ArgumentParser(description='Used to filter samples based on what exists in the GRID')
    parser.add_argument('-s', '--samples' , type =str, help='Name of file storing event types, e.g. by_priority', required=True)
    parser.add_argument('-c', '--config'  , type =str, help='Name of file storing configuration', required=True, choices=SETTINGS)
    parser.add_argument('-n', '--nthread' , type =int, help='Number of threads', default=1)
    parser.add_argument('-l', '--log_lvl' , type =int, help='Logging level', default=20, choices=[10,20,30,40])
    parser.add_argument('-p', '--priority', nargs='+', help='Priority of the samples to check, default all', default=PRIORITIES)
    args = parser.parse_args()

    cfg  = Conf(
    samples  = args.samples,
    config   = args.config,
    nthread  = args.nthread,
    log_lvl  = args.log_lvl,
    priority = args.priority)

    return cfg
# --------------------------------
def _set_logs(cfg : Conf) -> None:
    log.debug(f'Running with log level: {cfg.log_lvl}')

    LogStore.set_level('ap_utilities:bkk_checker'          , cfg.log_lvl)
    LogStore.set_level('ap_utilities:sample_config'        , cfg.log_lvl)
    LogStore.set_level('ap_utilities_scripts:check_samples', cfg.log_lvl)
# --------------------------------
def main():
    '''
    Script starts here
    '''
    cfg = _parse_args()
    _set_logs(cfg=cfg)

    obj     = SampleConfig(settings=cfg.config, samples='by_priority')
    sam_cfg = obj.get_config(categories=cfg.priority)

    l_df : list[pnd.DataFrame] = []
    for name, section in sam_cfg.sections.items():
        log.info(f'Processing section: {name}')
        obj= BkkChecker(name=name, cfg=section)
        df = obj.save(nthreads=cfg.nthread)

        df['section'] = name

        l_df.append(df)

    df = pnd.concat(l_df)
    df.to_parquet(path = '/tmp/ap_utilities/output/bkk_checker/stats.parquet')
# --------------------------------
if __name__ == '__main__':
    main()
