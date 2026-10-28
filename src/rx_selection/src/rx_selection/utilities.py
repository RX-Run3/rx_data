'''
Module containing utility functions
'''
import os
import json

import numpy

from ROOT                   import RDataFrame
from dmu.rdataframe.atr_mgr import AtrMgr
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('rx_selection:utilities')

#-------------------------------------------------------
def dump_json(data, json_path : str, sort_keys : bool = False):
    '''
    Will take a data structure and dump it to a JSON file
    '''
    json_dir = os.path.dirname(json_path)
    os.makedirs(json_dir, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as ofile:
        json.dump(data, ofile, indent=4, sort_keys=sort_keys)
#-------------------------------------------------------
def add_to_dic_lst(dic : dict, key, val) -> None:
    '''
    Takes a dictionary a key and a value, will add value to list mapped by key
    '''
    if key not in dic:
        dic[key] = [val]
    else:
        dic[key].append(val)
#-------------------------------------------------------
def check_file(filepath : str) -> None:
    '''
    Will check if file exists
    '''
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f'Cannot find {filepath}')
#-------------------------------------------------
def get_rdf_range(rdf : RDataFrame, index : int, npartition : int) -> RDataFrame:
    '''
    Will take a ROOT dataframe and return the index-th partition out of npartition(s)
    '''
    atr_obj = AtrMgr(rdf)

    if index >= npartition:
        raise ValueError(f'Index {index} cannot be larger than npartition {npartition}')

    tot_entries = rdf.Count().GetValue()

    arr_ind   = numpy.arange(0, tot_entries)
    l_arr_ind = numpy.array_split(arr_ind, npartition)
    sarr_ind  = l_arr_ind[index]

    start = int(sarr_ind[ 0])
    end   = int(sarr_ind[-1]) + 1

    log.info(f'Picking up ends [{start}, {end}] for {index}/{npartition}')

    rdf = rdf.Filter(f'rdfentry_ >= {start} && rdfentry_ < {end}')
    rdf = atr_obj.add_atr(rdf)

    return rdf
