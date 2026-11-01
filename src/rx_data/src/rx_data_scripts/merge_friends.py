'''
Script with code needed to merge outputs from branch_calculator
'''
import os
import argparse

from typing      import Final
from ROOT        import TFileMerger
from pathlib     import Path
from pydantic    import BaseModel, RootModel
from rx_common   import Project
from rx_data     import SampleSplitter
from dmu         import LogStore
from dmu.generic import Mode

log=LogStore.add_logger('rx_data:merge_friends')
_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------
class Paths(RootModel[list[Path]]):
    '''
    Interface to collection of paths
    '''
    root : list[Path]
    # ----------------------
    def unlink(self) -> None:
        '''
        Will remove all files that exist
        '''
        for source in self.root:
            if not source.exists():
                continue

            source.unlink()
    # ----------------------
    def newer_than(self, path : Path) -> bool:
        '''
        True if ALL paths are newer than `path`
        '''
        return all( source.stat().st_mtime > path.stat().st_mtime for source in self.root )
    # ----------------------
    @property
    def exist(self) -> bool:
        '''
        True if all paths exist
        '''
        return all( path.exists() for path in self.root )
# ----------------------
class Conf(BaseModel):
    '''
    Class needed to configure merging
    '''
    proj    : Project
    friend  : str
    entries : int
    vmain   : str
    vfrnd   : str
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
    parser.add_argument('-M', '--vmain'  , type=str    , help='Main tree version, E.g. v1')
    parser.add_argument('-F', '--vfrnd'  , type=str    , help='Friend tree version, E.g. v1')
    parser.add_argument('-e', '--entries', type=int    , help='Needed to find splitting that led to this sources')
    args = parser.parse_args()

    cfg = Conf(
        proj    = args.project,
        friend  = args.friend,
        vmain   = args.vmain,
        vfrnd   = args.vfrnd,
        entries = args.entries)

    return cfg
# ----------------------
def _merge(target : Path, sources : Paths) -> None:
    '''
    Parameters
    ---------------
    target : File into which to merge
    sources: List of files to be merged
    '''
    if not os.access(target.parent, os.W_OK):
        raise ValueError(f'Target is not writable: {target}')

    fmrg = TFileMerger()
    for source in sorted(sources.root):
        fmrg.AddFile(str(source), cpProgress=False)

    fmrg.OutputFile(str(target))
    success = fmrg.Merge()
    if not success:
        raise ValueError(f'Merge for {target} failed')

    log.info('Merge finished, removing pre-merge files')
    sources.unlink()
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg = _parse_args()
    spt = SampleSplitter(
        project = cfg.proj,
        version = cfg.vmain)

    out_path = _ANADIR / f'DB/statistics/{cfg.vmain}/{cfg.proj}.json'
    files    = spt.run(out_path = out_path, mode = Mode.read)
    batches  = files.split(entries = cfg.entries)

    to_merge : dict[Path,Paths] = {}
    for part in batches.parts:
        key = part.friend_path(friend = cfg.friend, version = cfg.vfrnd)
        val = part.friend_part_path(friend = cfg.friend, version = cfg.vfrnd)

        if key not in to_merge:
            to_merge[key] = Paths(root = [val])
        else:
            to_merge[key].root.append(val)

    for target, sources in to_merge.items():
        log.info(f'Creating: {target}')
        if     target.exists() and not sources.exist:
            continue

        if not target.exists() and not sources.exist:
            raise ValueError(f'Cannot find {target} or sources')

        if not target.exists():
            _merge(
                sources = sources,
                target  = target)
            continue

        if sources.newer_than(path = target):
            target.unlink()
            _merge(
                sources = sources,
                target  = target)
            continue

        raise ValueError(f'Sources are older than target: {target}')
# ----------------------
if __name__ == '__main__':
    main()
