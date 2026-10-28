'''
Script used to check what samples are present in the main trees
but missing among the friend trees
'''
import os
import re
import argparse
from pathlib import Path

import tqdm
from ROOT import TFile
from dmu.generic                    import utilities          as gut
from dmu.generic.version_management import get_last_version
from dmu.logging.log_store          import LogStore

log           = LogStore.add_logger('rx_data:check_missing')
# Key is path to ROOT file of main category
# Value is tuple of entries, for the main and friend trees
# If friend not found, it can also be a string
StatsInfo     = dict[str,tuple[int,int]|str]
SampleInfo    = str|list[Path]|StatsInfo
SampStructure = dict[str,dict[str,list[Path]]]
FileStructure = dict[str,SampStructure]
# ---------------------------------
class Data:
    '''
    Used to store shared information 
    '''
    only_friend     : str|None
    friends_skipped : list[str]
    log_level       : int
    data_dir        : Path
    project         : str
    data_rgx        = r'(data_24_mag(?:down|up)_24c\d)_(.*)\.root'
    mc_rgx          = r'mc_mag(?:up|down)_(?:.*_)?\d{8}_(.*)_(Hlt2RD.*)_\w{10}\.root'

    l_electron_samples                = ['brem_track_2', 'mass']
    l_to_be_deleted : list[Path|None] = []
# ---------------------------------
def _initialize() -> None:
    '''
    This should run at the beggining of the script
    '''
    LogStore.set_level('rx_data:check_missing', Data.log_level)
# ---------------------------------
def _get_data_dir(project : str) -> Path:
    '''
    Parameters
    ----------------------
    project : E.g. rx, needed for path building

    Returns
    ----------------------
    Path to directory whose sub directories are the friend trees
    '''
    ana_dir = os.environ['ANADIR']
    data_dir= Path(f'{ana_dir}/Data/{project}')
    if not data_dir.is_dir():
        raise FileNotFoundError(f'Cannot find {data_dir}')

    return data_dir
# ---------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script meant to check for missing friend trees')
    parser.add_argument('-p', '--project'  , type=str , help='E.g. rk', choices=['rk', 'rkst', 'rk_nopid', 'rkst_nopid'], required=True)
    parser.add_argument('-o', '--only'     , type=str , help='Do only these friend tree, optional') 
    parser.add_argument('-s', '--skip_sam' , nargs='+', help='Samples to skip', default=[])
    parser.add_argument('-l', '--log_level', type=int , help='Logging level', default=20, choices=[10, 20, 30])

    args = parser.parse_args()

    Data.project         = args.project
    Data.only_friend     = args.only
    Data.data_dir        = _get_data_dir(project = args.project)
    Data.friends_skipped = args.skip_sam
    Data.log_level       = args.log_level
# ---------------------------------
def _version_from_path(path : Path) -> str|None:
    try:
        version=get_last_version(dir_path=path, version_only=True)
    except ValueError:
        log.debug(f'No version found for {path}')
        return None

    return version
# ---------------------------------
def _paths_from_sample(friend_path : Path, version : str) -> set[Path]:
    '''
    Parameters
    -----------------
    friend_path: Path to directory with friend trees, e.g. /some/path/mva
    version    : Version requested for these trees

    Returns
    -----------------
    Set of paths to ROOT files associated
    '''
    ver_dir = Path(f'{friend_path}/{version}')
    s_path  = set(ver_dir.glob('*.root'))

    if len(s_path) == 0:
        log.warning(f'No file found in: {ver_dir}')

    return s_path 
# ---------------------------------
def _info_from_fname(fname : str) -> tuple[str,str]:
    '''
    Parameters
    ---------------
    fname: Name of ROOT file associated to friend tree, e.g. file.root

    Returns
    ---------------
    Tuple with name of sample and HLT2 trigger
    '''

    if fname.startswith('data_'):
        rgx = Data.data_rgx
    elif fname.startswith('mc_'):
        rgx = Data.mc_rgx
    else:
        raise ValueError(f'File cannot be identified as MC or data: {fname}')

    mtch = re.match(rgx, fname)
    if not mtch:
        raise ValueError(f'Cannot extract sample and trigger from: {fname}')

    [sample, trigger] = mtch.groups()

    return sample, trigger
# ---------------------------------
def _paths_to_dict(s_path : set[Path]) -> SampStructure:
    '''
    Parameters
    ---------------------
    s_path : Set paths associated to friend trees 

    Returns
    ---------------------
    Nested dictionary with:

    sample -> { trigger -> list[path] }
    '''
    d_data = {}

    nipath = len(s_path)
    nadded = 0
    for path in s_path:
        sample, trigger = _info_from_fname(fname=path.name)

        if sample  not in d_data:
            d_data[sample] = {}

        if trigger not in d_data[sample]:
            d_data[sample][trigger] = []

        d_data[sample][trigger].append(path)
        nadded += 1

    nfpath = _count_paths(d_data)

    if nipath != nfpath:
        raise ValueError(f'Number of paths changed: {nipath} --> {nfpath}, added {nadded}')

    return d_data
# ---------------------------------
def _count_paths(d_data : dict[str, dict]) -> int:
    npath = 0

    log.debug('Counting paths')
    for d_trig in d_data.values():
        for l_path in d_trig.values():
            npath += len(l_path)

    return npath
# ----------------------
def _skip_friend(fname : str) -> bool:
    '''
    Parameters
    -------------
    fname: Name of friend tree

    Returns
    -------------
    True if meant to be skipped
    '''
    if fname == 'main':
        return False

    if fname in Data.friends_skipped:
        return True

    if Data.only_friend and fname != Data.only_friend:
        return True

    return False
# ---------------------------------
def _find_paths() -> FileStructure:
    '''
    Returns
    -----------------
    Deeply nested dictionary with:

    friend -> { sample -> { trigger -> list[file_name] } }

    e.g. 

    mva    -> { DATA_24... -> { HLT2... -> [f1.root, f2.root...] } }
    '''
    l_friend = Data.data_dir.glob('*')
    d_fname  = {}

    l_msg = []
    for friend_path in l_friend:
        if _skip_friend(fname=friend_path.name):
            continue

        version = _version_from_path(path=friend_path)
        if not version:
            continue

        log.debug(f'Finding paths for sample: {friend_path.name}/{version}')

        s_path  = _paths_from_sample(friend_path=friend_path, version=version)
        d_path  = _paths_to_dict(s_path=s_path)
        fname   = friend_path.name
        d_fname[fname] = d_path
        nfname  = len(s_path)

        l_msg.append(f'{friend_path.name:<20}{version:<10}{nfname:<10}')

    log.info(40 * '-')
    log.info(f'{"Tree":<20}{"Latest":<10}{"Files":<10}')
    log.info(40 * '-')
    for msg in l_msg:
        log.info(msg)
    log.info(40 * '-')

    return d_fname
# ---------------------------------
def _get_sample_files(sample : dict[str,list[Path]]) -> set[Path]:
    '''
    Parameters
    -----------------
    sample : Dictionary with 
            key  : HLT2 trigger name 
            Value: List of names of ROOT files
    Returns
    -----------------
    Set of paths, concatenated for each trigger
    '''
    l_path = []
    for paths in sample.values():
        l_path += paths

    return set(l_path)
# ---------------------------------
def _sample_difference(
    sample_1 : dict[str,list[Path]],
    sample_2 : dict[str,list[Path]]) -> StatsInfo:
    '''
    Parameters
    --------------------
    sample_*: Dictionary where:
        key  : Hlt2 trigger name 
        Value: List of paths to ROOT files

    1 represents the main tree, 2 represents the friend tree

    Returns
    --------------------
    Dictionary where:
        Key  : Path to ROOT file
        Value: Tuple with entries in main tree and friend tree

    If the friend tree does not exist, -1, 0
    If every friend tree exists with the same entries, the output will be empty
    '''
    s_path_1 = _get_sample_files(sample=sample_1)
    s_path_2 = _get_sample_files(sample=sample_2)

    # Check for missing friend path
    s_diff   = { main_path for main_path in s_path_1 if all( main_path.name != friend_path.name  for friend_path in s_path_2) }

    # Friend tree missing -> no entries
    d_diff : dict[str,tuple[int,int]|str]  = { str(path) : 'missing_friend' for path in s_diff }

    # Check differences for common files
    d_stat   = _get_file_stat(
        main  = s_path_1, 
        friend= s_path_2)

    d_diff.update(d_stat)

    return dict(sorted(d_diff.items()))
# ----------------------
def _get_file_stat(
    main   : set[Path], 
    friend : set[Path]) -> StatsInfo:
    '''
    Parameters
    -------------
    common      : Set of filenames for files found in main and friend trees
    main(friend): Set of paths to main (friend) trees, all triggers have been merged

    Returns
    -------------
    Dictionary with:
        Keys : Path to friend ROOT file
        Value: Tuple with entries in main tree and friend tree

    If the number agrees, the file will not be added to the dictionary
    '''
    d_main  : dict[str,Path] = { path.name : path for path in main   }
    d_friend: dict[str,Path] = { path.name : path for path in friend }

    d_stats : StatsInfo = {}
    for main_name, main_path in d_main.items():
        if main_name not in d_friend:
            continue

        friend_path = d_friend[main_name]

        tup_stat = _get_stats(main_path=main_path, friend_path=friend_path)
        if tup_stat is None:
            continue

        d_stats[str(friend_path)] = tup_stat

    return d_stats 
# ----------------------
def _get_stats(main_path : Path, friend_path : Path) -> tuple[int,int]|None:
    '''
    Parameters
    -------------
    main(friend)_path: Path to ROOT file for main(friend) sample

    Returns
    -------------
    Tuple with either:

    If numbers differ, number of entries in the main and friend tree.
    If numbers are equal, None
    '''
    nmain = _get_tree_entries(path=  main_path)
    nfrnd = _get_tree_entries(path=friend_path)

    if nmain == nfrnd:
        Data.l_to_be_deleted.append(None)
        return None

    Data.l_to_be_deleted.append(friend_path)

    return nmain, nfrnd
# ----------------------
def _get_tree_entries(path : Path) -> int:
    '''
    Parameters
    -------------
    path: Path to ROOT file

    Returns
    -------------
    Number of entries, if tree found, -1 otherwise
    '''
    path_string = path.as_posix()
    fpath       = TFile(path_string)
    tree        = getattr(fpath, 'DecayTree', None)
    nentr       = -1 if tree is None else tree.GetEntries()

    fpath.Close()

    return nentr
# ---------------------------------
def _is_muon_sample(d_path : StatsInfo) -> bool:
    '''
    Parameters
    ----------------------
    d_path: Dictionary where the keys are the names of ROOT files

    Returns
    ----------------------
    If file corresponds to muon trigger, True, otherwise False
    '''
    is_muon = True
    for path in d_path:
        is_muon = 'MuMu_' in os.path.basename(path)

    return is_muon
# ---------------------------------
def _should_exist(frn_name : str, sample : dict[str,list[Path]]) -> bool:
    '''
    Checks if for a friend tree type (e.g. brem_track_2) the sample should exist

    Sample is the dictionary:

    HltTrigger -> list of files

    It will be true if the sample contains AT LEAST one file that should exist
    '''
    has_electron = False
    for trigger in sample:
        has_electron = 'MuMu_' not in trigger

    if has_electron and frn_name in Data.l_electron_samples:
        return True

    return False
# ---------------------------------
def _compare_against_main(
    frn_name : str,
    main_sam : dict[str,dict[str,list[Path]]],
    frnd_sam : dict[str,dict[str,list[Path]]]) -> dict[str,SampleInfo]:
    '''
    Compares dictionaries associated to main and friend trees

    Parameters
    -------------
    frn_name : Name of the friend tree kind, e.g. mva
    *_sam: Dictionary mapping:

    sample -> { HltTrigger -> list[file path] }

    for either main or friend sample

    Returns
    -------------
    A dictionary with key as the name of the sample, e.g. DATA... and value either:

    - `all_missing` string. When the files are missing for all the triggers of a given sample
    - List of file names that are missing as friend tree. When some files are missing
    - Dictionary mapping file names with tuple with entries in main and friend trees. When some files have different tentries
    '''
    s_main_sample = set(main_sam.keys())
    s_frnd_sample = set(frnd_sam.keys())
    s_diff        = s_main_sample - s_frnd_sample
    l_diff        = list(s_diff)
    l_diff        = sorted(l_diff)

    # If whole sample is missing, add 'all'
    d_diff : dict[str,SampleInfo] = { sample : 'all_missing' for sample in l_diff if _should_exist(frn_name=frn_name, sample=main_sam[sample])}

    # Else check which files are missing
    s_both = s_main_sample & s_frnd_sample
    for sample in tqdm.tqdm(s_both, ascii=' -'):
        m_sample = main_sam[sample]
        f_sample = frnd_sam[sample]

        log.debug(f'Sample: {sample}')
        d_path : StatsInfo = _sample_difference(sample_1=m_sample, sample_2=f_sample)
        npath  = len(d_path)
        if npath == 0:
            continue

        if _is_muon_sample(d_path) and frn_name in Data.l_electron_samples:
            log.debug(f'Skipping {sample} for {frn_name}')
            continue

        d_diff[sample] = d_path

    return d_diff
# ----------------------
def _delete_files() -> None:
    '''
    This should delete corrupted/invalid files
    '''
    if all(fpath is None for fpath in Data.l_to_be_deleted):
        log.info('No invalid files found')
        return

    l_bad= [ path for path in Data.l_to_be_deleted if path is not None ]

    ntot = len(Data.l_to_be_deleted)
    nbad = len(l_bad)

    log.warning(f'Found {nbad}/{ntot} bad files')
    val = input('Delete files? [y/n]: ')
    if val != 'y':
        return

    for path in tqdm.tqdm(l_bad, ascii=' -'):
        if path.exists():
            path.unlink()
# ---------------------------------
def main():
    '''
    Start here
    '''
    _parse_args()
    _initialize()

    d_sample = _find_paths()

    main_sam = d_sample['main']
    d_mis    = {}
    for friend_name, data in d_sample.items():
        if friend_name == 'main':
            continue                      # main is what we are comparing against

        if friend_name in Data.friends_skipped:
            continue

        log.debug(30 * '-')
        log.info(f'Comparing WRT: {friend_name}')
        log.debug(30 * '-')
        d_mis[friend_name] = _compare_against_main(
            frn_name = friend_name,
            main_sam = main_sam,
            frnd_sam = data)

    gut.dump_json(data=d_mis, path=f'missing_{Data.project}.yaml', exists_ok=True)

    _delete_files()
# ---------------------------------
if __name__ == '__main__':
    main()
