'''
Module containing utility functions
'''
import os
import json
import numpy

from typing                 import Any
from pathlib                import Path
from ROOT                   import RDF
from dmu                    import LogStore
from dmu.rdataframe.atr_mgr import AtrMgr

log=LogStore.add_logger('rx_selection:utilities')
#-------------------------------------------------------
def dump_json(data : Any, json_path : Path, sort_keys : bool = False):
    '''
    Will take a data structure and dump it to a JSON file
    '''
    json_path.parent.mkdir(exist_ok=True, parents=True)
    string = json.dumps(data, sort_keys = sort_keys)
    json_path.write_text(string)
#-------------------------------------------------------
def add_to_dic_lst(dic : dict[str,Any], key : str, val : Any) -> None:
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
def get_rdf_range(rdf : RDF.RNode, index : int, npartition : int) -> RDF.RNode:
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
