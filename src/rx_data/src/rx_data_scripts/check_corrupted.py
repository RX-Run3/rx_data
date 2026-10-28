'''
Script meant to check if ROOT files are corrupted
'''
import os
import glob
import argparse

import tqdm
from ROOT                  import TFile
from dmu.logging.log_store import LogStore

log=LogStore.add_logger('rx_data:check_file')
# -----------------------------------
class Data:
    '''
    Data class
    '''
    inp_dir : str
    rgex    : str|None
    remove  : bool
    dry     : bool
    lvl     : int
# -----------------------------------
def _get_paths() -> list[str]:
    if Data.rgex is None:
        files_wc = f'{Data.inp_dir}/*.root'
    else:
        files_wc = f'{Data.inp_dir}/{Data.rgex}'

    l_path   = glob.glob(files_wc)
    npath    = len(l_path)

    if npath == 0:
        raise ValueError(f'No files found in {files_wc}')

    log.info(f'Found {npath} files')

    return l_path
# -----------------------------------
def _parse_args() -> None:
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to check if ROOT files in directory are OK')
    parser.add_argument('-p', '--path', type=str, help='Path to directory with files' , required=True)
    parser.add_argument('-x', '--rgex', type=str, help='Regular expression to filter file names')
    parser.add_argument('-r', '--remo',           help='If set, will remove bad files'    , action='store_true')
    parser.add_argument('-d', '--dry' ,           help='If set, will not remove bad files', action='store_true')
    parser.add_argument('-l', '--lvl' , type=int, help='log level', choices=[10, 20, 30], default=20)
    args = parser.parse_args()

    Data.inp_dir = args.path
    Data.rgex    = args.rgex
    Data.lvl     = args.lvl
    Data.dry     = args.dry
    Data.remove  = args.remo

    LogStore.set_level('rx_data:check_file', Data.lvl)
# -----------------------------------
def _is_good_file(path : str) -> bool:
    try:
        ifile = TFile.Open(path)
    except OSError:
        return False

    if ifile.IsZombie():
        ifile.Close()
        return False

    if ifile.TestBit(TFile.kRecovered) != 0:
        ifile.Close()
        return False

    ifile.Close()

    return True
# -----------------------------------
def _remove_files(l_path : list[str]) -> None:
    nfile = len(l_path)
    log.info(f'Found {nfile} bad files')

    log.info('Removing files:')
    for org_path in l_path:
        path = os.path.realpath(org_path)
        if not Data.dry:
            log.info(path)
            os.remove(path)
            if org_path != path:
                os.remove(org_path)
        else:
            log.info(f'Skipped {path}')
# -----------------------------------
def main():
    '''
    Start here
    '''
    _parse_args()

    l_all_path = _get_paths()
    l_bad_path = []
    for path in tqdm.tqdm(l_all_path, ascii=' -'):
        if _is_good_file(path):
            continue

        l_bad_path.append(path)

    _remove_files(l_bad_path)
# -----------------------------------
if __name__ == '__main__':
    main()
