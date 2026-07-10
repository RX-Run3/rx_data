'''
Script used to check which MC samples are found in grid
'''
import argparse
import pandas    as pnd

from dataclasses  import dataclass
from typing       import Final
from ap_utilities import LogStore
from ap_utilities import BkkChecker
from ap_utilities import SampleConfig

log=LogStore.add_logger('ap_utilities_scripts:check_bkk_samples')

KINDS      : Final[list[str]] = ['block', 'sample']
SETTINGS   : Final[list[str]] = ['2024_sim10d', '2024_sim10f', '2024_sim10g']
# --------------------------------
@dataclass
class Conf:
    '''
    Class storing shared attributes
    '''
    kind    : str
    samples : str
    config  : str
    nthread : int
    log_lvl : int
    priority: str
    update  : bool
# ----------------------------------------
def _parse_args() -> Conf:
    parser = argparse.ArgumentParser(description='Used to make tables with all MC samples used')
    parser.add_argument('-c', '--config'  , type =str, help='Name of file storing configuration', required=True, choices=SETTINGS)
    parser.add_argument('-n', '--nthread' , type =int, help='Number of threads', default=1)
    parser.add_argument('-l', '--log_lvl' , type =int, help='Logging level', default=20, choices=[10,20,30,40])
    parser.add_argument('-u', '--update'  , action = 'store_true', help='If used, will not use cached information')
    args = parser.parse_args()

    cfg  = Conf(
        kind     = args.kind,
        samples  = args.samples,
        config   = args.config,
        nthread  = args.nthread,
        log_lvl  = args.log_lvl,
        update   = args.update,
        priority = args.priority)

    return cfg
# --------------------------------
def _set_logs(cfg : Conf) -> None:
    log.debug(f'Running with log level: {cfg.log_lvl}')

    LogStore.set_level('ap_utilities:bkk_checker'              , cfg.log_lvl)
    LogStore.set_level('ap_utilities:sample_config'            , cfg.log_lvl)
    LogStore.set_level('ap_utilities_scripts:check_bkk_samples', cfg.log_lvl)
# --------------------------------
def main():
    '''
    Script starts here
    '''
    cfg = _parse_args()
    _set_logs(cfg=cfg)

    obj     = SampleConfig(
        settings=cfg.config, 
        samples =cfg.samples)
    cfg_sam = obj.get_config(category=cfg.priority)

    obj= BkkChecker(
        name= cfg.priority, 
        dry = False,
        cfg = cfg_sam)
    dsi= obj.save(
        update  = cfg.update,
        nthreads= cfg.nthread)
# --------------------------------
if __name__ == '__main__':
    main()
