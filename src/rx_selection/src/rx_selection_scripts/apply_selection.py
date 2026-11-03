#!/usr/bin/env python3
'''
Script used to apply selections to ROOT files
provided by DaVinci
'''

import os
import argparse
from dmu.logging.log_store   import LogStore
from rx_selection.cache_data import CacheData

log=LogStore.add_logger('rx_selection:apply_selection')
# ----------------------------------------
class Data:
    '''
    Class used to share attributes
    '''

    mva_dir = os.environ['MVADIR']
# ----------------------------------------
def _set_threads() -> None:
    '''
    Need to use one thread to lower memory usage
    '''
    os.environ['MKL_NUM_THREADS']     ='1'
    os.environ['OMP_NUM_THREADS']     ='1'
    os.environ['NUMEXPR_NUM_THREADS'] ='1'
    os.environ['OPENBLAS_NUM_THREADS']='1'
# ----------------------------------------
def _initialize(args : argparse.Namespace) -> None:
    _set_threads()

    LogStore.set_level('rx_selection:ds_getter'      , args.loglvl)
    LogStore.set_level('rx_selection:cache_data'     , args.loglvl)
    LogStore.set_level('rx_selection:apply_selection', args.loglvl)
# ----------------------------------------
def _get_args() -> argparse.Namespace:
    '''
    Argument parsing happens here
    '''
    parser = argparse.ArgumentParser(description='Script used to apply selection and produce samples for Run 3')
    parser.add_argument('-i', '--ipart'  , type = int, help='Part to process'                                     , required=True)
    parser.add_argument('-n', '--npart'  , type = int, help='Total number of parts'                               , required=True)
    parser.add_argument('-d', '--ipath'  , type = str, help='Path to YAML file containing sample list'            , required=True)
    parser.add_argument('-s', '--sample' , type = str, help='Name of sample to process, e.g. data_24_magdown_24c2', required=True)
    parser.add_argument('-p', '--project', type = str, help='Name of project, e.g RK, RKstr'                      , required=True)
    parser.add_argument('-q', '--q2bin'  , type = str, help='q2 bin, e.g. central'                                , required=True)
    parser.add_argument('-t', '--hlt2'   , type = str, help='Name of HLT2 trigger, e.g. Hlt2RD_B0ToKpPimMuMu'     , required=True)
    parser.add_argument('-c', '--cutver' , type = str, help='Version of selection, by default, latest'            , default =  '')
    parser.add_argument('-r', '--remove' , nargs= '+', help='List of cuts to remove from the full selection'      , default =  [])
    parser.add_argument('-l', '--loglvl' , type = int, help='Logging level, default 20'                           , default =20, choices=[10, 20, 30])

    args = parser.parse_args()

    return args
# ----------------------------------------
def main():
    '''
    Script starts here
    '''
    args = _get_args()
    _initialize(args)

    cfg  = vars(args)
    obj  = CacheData(cfg = cfg)
    obj.save()
# ----------------------------------------
if __name__ == '__main__':
    main()
