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

log=LogStore.add_logger('ap_utilities_scripts:check_samples')

KINDS      : Final[list[str]] = ['block', 'sample']
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
    kind    : str
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
    parser.add_argument('-k', '--kind'    , type =str, help='Kind of printout', default=KINDS)
    args = parser.parse_args()

    cfg  = Conf(
        kind     = args.kind,
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
def _print_by_block(df : pnd.DataFrame) -> None:
    df = df.set_index('Sample', drop = True)
    for block, df_block in df.groupby('Block'):
        df_block.drop(columns = ['Block'], inplace = True)
        string = df_block.to_markdown()
        print(30 * '-')
        print(block)
        print(30 * '-')
        print(string)
# --------------------------------
def _print_by_sample(df : pnd.DataFrame) -> None:
    df = df.set_index('Block', drop = True)
    for sample, df_sample in df.groupby('Sample'):
        df_sample.drop(columns = ['Sample'], inplace = True)
        string = df_sample.to_markdown()
        print(30 * '-')
        print(sample)
        print(30 * '-')
        print(string)
# --------------------------------
def main():
    '''
    Script starts here
    '''
    cfg = _parse_args()
    _set_logs(cfg=cfg)

    obj     = SampleConfig(settings=cfg.config, samples='by_priority')
    cfg_sam = obj.get_config(categories=cfg.priority)

    obj= BkkChecker(
        name= 'summary', 
        dry = False,
        cfg = cfg_sam)
    df = obj.save(nthreads=cfg.nthread)
    # Dirac does not show size for some samples
    df = df.drop(columns = ['Size [GB]'])

    if   cfg.kind == 'block':
        _print_by_block(df = df)
    elif cfg.kind == 'sample':
        _print_by_sample(df = df)
    else:
        raise ValueError(f'Invalid kind: {cfg.kind}')
# --------------------------------
if __name__ == '__main__':
    main()
