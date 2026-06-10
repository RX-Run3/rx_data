'''
Script with code needed to merge outputs from branch_calculator
'''
import os
import argparse

from ROOT      import TFileMerger # type: ignore
from pathlib   import Path
from pydantic  import BaseModel
from rx_common import Project
from rx_data   import SampleSplitter # type: ignore
from dmu       import LogStore

log=LogStore.add_logger('rx_data:merge_friends')
# ----------------------
class Conf(BaseModel):
    '''
    Class needed to configure merging
    '''
    project : Project
    friend  : str
    version : str
    entries : int
# ----------------------
def _parse_args() -> Conf:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script needed to merge files from friend tree creation step')
    parser.add_argument('-p', '--project', type=Project, help='Needed to find the files E.g. rk')
    parser.add_argument('-f', '--friend' , type=str    , help='Needed to find the files E.g. mva')
    parser.add_argument('-v', '--version', type=str    , help='Needed to find the files E.g. v1')
    parser.add_argument('-e', '--entries', type=int    , help='Needed to find splitting that led to this sources')
    args = parser.parse_args()

    cfg = Conf(
        project = args.project,
        friend  = args.friend,
        version = args.version,
        entries = args.entries)

    return cfg
# ----------------------
def _merge(target : Path, sources : list[Path]) -> None:
    '''
    Parameters
    ---------------
    target : File into which to merge
    sources: List of files to be merged
    '''
    if target.exists():
        raise ValueError(f'Target already exists: {target}')

    if not os.access(target.parent, os.W_OK):
        raise ValueError(f'Target is not writable: {target}')

    fail = False
    for source in sources:
        if source.exists():
            continue

        fail = True
        log.error(f'Cannot find source: {source}')

    if fail:
        raise ValueError('At least one source is missing')

    fmrg = TFileMerger()
    for source in sources:
        fmrg.AddFile(source, cpProgress=False)

    fmrg.OutputFile(str(target))
    fmrg.Merge()
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg   = _parse_args()
    spt   = SampleSplitter(
        project = cfg.project,
        version = cfg.version)

    files   = spt.run()
    batches = files.split(entries = cfg.entries)

    to_merge : dict[Path,list[Path]] = {}
    for part in batches.parts:
        key = part.friend_path(friend = cfg.friend)
        val = part.friend_part_path(friend = cfg.friend)

        if key not in to_merge:
            to_merge[key] = [val]
        else:
            to_merge[key].append(val)

    for target, sources in to_merge.items():
        _merge(
            sources = sources,
            target  = target)
# ----------------------
if __name__ == '__main__':
    main()
