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
    parser = argparse.ArgumentParser(description='Used to filter samples based on what exists in the GRID')
    parser.add_argument('-s', '--samples' , type =str, help='Name of file storing event types, e.g. by_priority', required=True)
    parser.add_argument('-c', '--config'  , type =str, help='Name of file storing configuration', required=True, choices=SETTINGS)
    parser.add_argument('-k', '--kind'    , type =str, help='Kind of printout'           , choices  = KINDS)
    parser.add_argument('-n', '--nthread' , type =int, help='Number of threads', default=1)
    parser.add_argument('-l', '--log_lvl' , type =int, help='Logging level', default=20, choices=[10,20,30,40])
    parser.add_argument('-p', '--priority', type =str, help='Category, e.g. sim10g, high', required = True)
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
def _print_total(df : pnd.DataFrame) -> None:
    '''
    Parameters
    ----------------
    df: DataFrame with Events column
    '''
    col_name = 'Events'

    if col_name not in df.columns:
        raise ValueError(f'{col_name} column missing')

    sum = df[col_name].sum()

    print(20 * '-')
    print(f'Total: {sum:,}')
    print('')
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
        _print_total(df = df_block)
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
        _print_total(df = df_sample)
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
    # Dirac does not show size for some samples
    df = dsi.df.drop(columns = ['Size [GB]'])

    if   cfg.kind == 'block':
        _print_by_block(df = df)
    elif cfg.kind == 'sample':
        _print_by_sample(df = df)
    else:
        raise ValueError(f'Invalid kind: {cfg.kind}')
# --------------------------------
if __name__ == '__main__':
    main()
