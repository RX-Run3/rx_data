'''
Script used to compare ROOT files
'''

import re
import os
from dataclasses import dataclass
from typing import ClassVar

import argparse

import yaml
import numpy
from dmu.logging.log_store import LogStore

from ROOT import TFile, TTree, RDataFrame

import dmu.rfile.utilities   as rfut


log=LogStore.add_logger('rx_scripts:compare_files')
#------------------
@dataclass
class Data:
    '''
    Class used to store shared attributes
    '''
    max_entries   : int
    max_trees     : int
    l_exclude     : list[str]
    raise_if_diff : bool
    file_name_1   : str
    file_name_2   : str

    d_summary     : ClassVar[dict]= {}
#------------------
def _print_trees_difference(l_val_1 : list[str], l_val_2 : list[str]) -> None:
    s_val_1 = set(l_val_1)
    s_val_2 = set(l_val_2)

    s_only_1 = s_val_1 - s_val_2
    s_only_2 = s_val_2 - s_val_1

    Data.d_summary[f'Trees only in {Data.file_name_1}'] = list(s_only_1)
    Data.d_summary[f'Trees only in {Data.file_name_2}'] = list(s_only_2)

    nonly_1  = len(s_only_1)
    nonly_2  = len(s_only_2)

    if nonly_1 > 0:
        log.info(f'Found {nonly_1} trees in first file but not second')
        for name in s_only_1:
            log.info(f'{"":<4}{name:<20}')

    if nonly_2 > 0:
        log.info(f'Found {nonly_2} trees in second file but not first')
        for name in s_only_2:
            log.info(f'{"":<4}{name:<20}')
#------------------
def _check_trees(d_tree_1 : dict[str, TTree], d_tree_2 : dict[str, TTree]):
    '''
    Check if dictionaries have same trees
    For corresponding trees, check if number of entries is the same
    '''
    l_treename_1 = list(d_tree_1.keys())
    l_treename_2 = list(d_tree_2.keys())

    if l_treename_1 != l_treename_2:
        log.warning('Files contain different trees')
        _print_trees_difference(l_treename_1, l_treename_2)

    s_treename_1 = set(l_treename_1)
    s_treename_2 = set(l_treename_2)
    s_treename   = s_treename_1 & s_treename_2

    for treename in s_treename:
        if treename in Data.l_exclude:
            continue

        tree_1 = d_tree_1[treename]
        tree_2 = d_tree_2[treename]

        entries_1 = tree_1.GetEntries()
        entries_2 = tree_2.GetEntries()

        if entries_1 != entries_2:
            raise ValueError(f'Tree {treename} differs in entries {entries_1}/{entries_2}')

    return list(s_treename)
#------------------
def _get_data(tree : TTree) -> dict[str, numpy.ndarray]:
    rdf = RDataFrame(tree)
    if Data.max_entries > 0:
        log.warning(f'Limiting to {Data.max_entries} entries')
        rdf = rdf.Filter(f'rdfentry_ < {Data.max_entries}')

    d_data = rdf.AsNumpy()

    return d_data
#------------------
def _check_branches(tree_name : str, l_branch_1 : list[str], l_branch_2 : list[str]) -> None:
    '''
    Takes lists of branch names
    Checks if they are the same, if not print differences

    if raise_if_diff is True, will raise exception if branches are not the same
    '''
    if l_branch_1 == l_branch_2:
        return

    s_branch_1 = set(l_branch_1)
    s_branch_2 = set(l_branch_2)

    s_branch_1_m_2 = s_branch_1.difference(s_branch_2)
    log.info(f'Found len({s_branch_1_m_2}) branches in first tree but not second')
    for branch_name in s_branch_1_m_2:
        log.debug(f'{"":<4}{branch_name:<20}')

    s_branch_2_m_1 = s_branch_2.difference(s_branch_1)
    log.info(f'Found len({s_branch_2_m_1}) branches in second tree but not first')
    for branch_name in s_branch_2_m_1:
        log.debug(f'{"":<4}{branch_name:<20}')

    Data.d_summary[tree_name] = {
            f'Only {Data.file_name_1}' : list(s_branch_1_m_2),
            f'Only {Data.file_name_2}' : list(s_branch_2_m_1),
            }

    if Data.raise_if_diff:
        raise ValueError('Branches differ')
#------------------
def _compare_branches(tree_name : str, d_data_1 : dict[str, list], d_data_2 : dict[str, list]) -> list[str]:
    '''
    Will check for different branches in trees
    Will return list of branch names for common branches
    '''
    l_branch_1 = list(d_data_1.keys())
    l_branch_2 = list(d_data_2.keys())

    l_branch_1.sort()
    l_branch_2.sort()
    _check_branches(tree_name, l_branch_1, l_branch_2)

    s_branch_1 = set(l_branch_1)
    s_branch_2 = set(l_branch_2)

    s_branch = s_branch_1.intersection(s_branch_2)

    return list(s_branch)
#------------------
def _compare(tree_name : str, d_data_1, d_data_2) -> None:
    log.info('')
    log.debug('Comparing branches')
    l_branch_name = _compare_branches(tree_name, d_data_1, d_data_2)

    log.debug('Comparing contents of branches')
    l_diff_branch = []
    for branch_name in l_branch_name:
        arr_val_1 = d_data_1[branch_name]
        arr_val_2 = d_data_2[branch_name]

        if _contents_differ(tree_name, branch_name, arr_val_1, arr_val_2):
            l_diff_branch.append(branch_name)

    ndiff = len(l_diff_branch)
    ntot  = len(l_branch_name)

    Data.d_summary[f'Branches that differ for tree: {tree_name}'] = l_diff_branch

    if ndiff == 0:
        log.debug(f'Trees {tree_name} have same contents')
        return

    log.warning(f'{ndiff:<10}{"differing branches out of":<20}{ntot:<10}{"in":<10}{tree_name:<50}')
    for branch_name in l_diff_branch:
        log.debug(f'{"":<4}{branch_name:<20}')
#------------------
def _contents_differ(tree_name : str, branch_name : str, arr_val_1 : numpy.ndarray, arr_val_2 : numpy.ndarray) -> bool:
    is_different = False
    str_type = str(arr_val_1.dtype)
    if   str_type == 'object':
        return is_different

    if str_type not in ['bool', 'int32', 'uint32', 'uint64', 'float64', 'float32']:
        log.info(f'Skipping {branch_name}, {str_type}')
        return is_different

    if not numpy.array_equal(arr_val_1, arr_val_2):
        is_different = True

        log.debug(20 * '-')
        log.debug(f'Branch {branch_name} in tree {tree_name} differ')
        log.debug(20 * '-')
        log.debug(arr_val_1)
        log.debug(arr_val_2)
        log.debug(20 * '-')

    return is_different
#------------------
def _update_keys(d_tree):
    d_out = {}

    for key, val in d_tree.items():
        #Remove everything before .root/ and use it as new key
        new_key = re.sub(r'^.*\.root/', '', key)
        d_out[new_key] = val

    return d_out
#------------------
def _check_file_existence(path : str) -> None:
    if not os.path.isfile(path):
        raise FileNotFoundError(f'Cannot find {path}')
#------------------
def _validate(file_1 : str, file_2 : str) -> None:
    _check_file_existence(file_1)
    _check_file_existence(file_2)

    ifile_1     = TFile(file_1)
    ifile_2     = TFile(file_2)

    d_tree_1    =  rfut.get_trees_from_file(ifile_1)
    d_tree_1    = _update_keys(d_tree_1)

    d_tree_2    =  rfut.get_trees_from_file(ifile_2)
    d_tree_2    = _update_keys(d_tree_2)

    l_tree_name = _check_trees(d_tree_1, d_tree_2)

    if Data.max_trees > -1:
        log.warning(f'Limiting to {Data.max_trees} trees')
        l_tree_name = l_tree_name[:Data.max_trees]

    ncommon = len(l_tree_name)
    log.debug(f'Found common {ncommon} trees')
    for name in l_tree_name:
        log.debug(f'{"":<4}{name}')

    log.info('Checking trees')
    for treename in l_tree_name:
        if treename in Data.l_exclude:
            log.debug(f'Skipping {treename}')
            continue

        log.debug(f'{"":<4}{treename}')

        tree_1 = d_tree_1[treename]
        tree_2 = d_tree_2[treename]

        log.debug('Getting data from reference')
        d_data_1= _get_data(tree_1)

        log.debug('Getting data from new')
        d_data_2= _get_data(tree_2)

        log.debug(f'Comparing {treename}')
        _compare(treename, d_data_1, d_data_2)

    ifile_1.Close()
    ifile_2.Close()
#------------------
def _save_summary() -> None:
    '''
    Saves Data.d_summary to summary.yaml
    '''

    with open('summary.yaml', 'w', encoding='utf-8') as ofile:
        yaml.dump(Data.d_summary, ofile, indent=2, default_flow_style=False)
#------------------
def main():
    '''
    Script starts here
    '''
    parser = argparse.ArgumentParser(description='Used to validate versions of code that produce potentially different files')
    parser.add_argument('-f', '--files'         , nargs=  2, help='List of files to compare')
    parser.add_argument('-n', '--max_entries'   , type=int , help='Limit running over this number of entries. By default will run over everything', default=-1)
    parser.add_argument('-t', '--max_trees'     , type=int , help='Limit running over this number of trees. By default will run over everything'  , default=-1)
    parser.add_argument('-l', '--log_level'     , type=int , help='Logging level'                              , default=20, choices=[10, 20, 30, 40])
    parser.add_argument('-e', '--exclude'       , nargs='+', help='List of trees that should not be compared'  , default=[], )
    parser.add_argument('-r', '--raise_if_diff' ,            help='If used, will fail as soon as it finds trees with different branches.', action='store_true')

    args = parser.parse_args()

    LogStore.set_level('rx_scripts:compare_files', args.log_level)

    Data.max_entries   = args.max_entries
    Data.max_trees     = args.max_trees
    Data.l_exclude     = args.exclude
    Data.raise_if_diff = args.raise_if_diff

    [file_1, file_2] = args.files

    Data.file_name_1 = file_1
    Data.file_name_2 = file_2

    _validate(file_1, file_2)
    _save_summary()
#------------------
if __name__ == '__main__':
    main()
