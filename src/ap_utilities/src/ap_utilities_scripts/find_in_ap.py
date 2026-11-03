'''
This script is meant to:

- Search for all the lines in:

$ANADIR/bkk_checker/block_*/info.yaml

- Check if ntuples corresponding to each line exist in BKK.
- Build a new info.yaml for missing samples
'''
import os
import glob
import argparse
import apd
import pandas as pnd

from tqdm import tqdm
from apd  import SampleCollection
from dmu  import LogStore

log=LogStore.add_logger('ap_utilities:find_in_ap')
# ----------------------
def _info_from_line(line : str) -> tuple[str, str, str]:
    '''
    Parameters
    -------------
    line: Line meant to go in info.yaml

    Returns
    -------------
    Tuple with:

    Event type
    Block, e.g w32_32
    Line meant to be added to info.yaml
    '''
    reform  = line.replace('(', '').replace(')', '')
    reform  = reform.replace('"', '').replace('"', '')
    l_field = reform.split(',')
    evt_type= l_field[1].replace(' ', '')
    block   = l_field[2].replace('2024.', '').replace('.', '_').lower().replace(' ', '')

    return evt_type, block, line
# ----------------------
def _get_info() -> list[tuple[str, str, str]]:
    '''
    Returns
    -------------
    Dictionary with:

    Key  : EventType
    Value: Line that would go in info.yaml
    '''
    ana_dir = os.environ['ANADIR']
    path_wc = f'{ana_dir}/bkk_checker/block_*/info.yaml'
    l_path  = glob.glob(path_wc)
    l_path  = sorted(l_path)

    l_line  = []
    log.info('Reading files')
    for path in l_path:
        log.info(f'    {path}')
        with open(path) as ifile:
            l_line += ifile.read().splitlines()

    return [ _info_from_line(line=line) for line in l_line ]
# ----------------------
def _found_type(
    col      : SampleCollection,
    evt_type : str,
    block    : str) -> bool:
    '''
    Parameters
    -------------
    col     : Instance of SampleCollection
    evt_type: Event type
    block   : E.g. w40_42

    Returns
    -------------
    True if already found in AP
    '''
    rep  = col.filter(eventtype=evt_type).report()
    df   = pnd.DataFrame(rep[1:], columns=rep[0])
    found= False

    if 'name' not in df.columns:
        return False

    for name in df['name']:
        if block not in name:
            log.verbose(f'Block {block} not in {name}')
            continue

        if not name.endswith('_tuple'):
            log.verbose(f'{name} does not end in _tuple')
            continue

        if '_spr,' in name:
            log.verbose(f'{name} contains _spr,')
            continue

        log.debug(f'Found {evt_type}/{block} in {name}')
        found = True
        break

    if not found:
        log.debug(f'Cannot find: {evt_type}/{block}')

    return found
# ----------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to find missing ntupled samples')
    parser.add_argument('-l', '--log_level' , type=int, help='Logging level', choices=[5, 10, 20, 30, 40], default=20)
    args = parser.parse_args()

    LogStore.set_level('ap_utilities:find_in_ap', args.log_level)
# ----------------------
def main():
    '''
    Entry point
    '''
    _parse_args()

    dset      = apd.get_analysis_data(working_group='RD', analysis='rx_2024')
    scol      = dset.all_samples()
    if not isinstance(scol, SampleCollection):
        raise RuntimeError('Cannot extract SampleCollection instance')

    t_info    = _get_info()
    l_missing = [ line for etype, block, line in tqdm(t_info, ascii=' -') if not _found_type(col=scol, evt_type=etype, block=block) ]
    l_missing = sorted(l_missing)

    total     = len(t_info)
    missing   = len(l_missing)
    out_file  = './info.yaml'

    log.info(f'Missing: {missing}/{total}')
    with open(out_file, 'w') as ofile:
        for line in l_missing:
            ofile.write(f'{line}\n')

    log.info(f'Saving lines for missing ntuples to: {out_file}')
# ----------------------
if __name__ == '__main__':
    main()
