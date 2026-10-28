'''
Module with SampleOrganizer class
'''

import os
import shutil
import tempfile

from functools   import cached_property
from typing      import Final, Protocol
from ROOT        import TFileMerger, TFile, gSystem
from pathlib     import Path
from dmu         import LogStore
from pydantic    import BaseModel
from rx_common   import Trigger

log=LogStore.add_logger('rx_data:sample_organizer')

val = os.environ.get('SCRATCH')
_SCRATCH : Final[Path | None] = val if val is None else Path(val)
# ----------------------------------
class SampleProtocol(Protocol):
    '''
    Class meant to represent how a sample should look like 
    to `SampleOrganizer`
    '''
    # -----------------
    @cached_property
    def is_mc(self) -> bool:
        '''
        True if sample is MC
        '''
        ...
    # -----------------
    @property
    def name(self) -> str:
        '''
        Name of AP job
        '''
        ...
    # -----------------
    def local_paths(
        self, 
        must_exist: bool) -> list[Path]:
        ...
    # -----------------
    @cached_property
    def target_paths(self) -> dict[Trigger,Path]:
        ...
    # -----------------
    @property
    def is_organized(self) -> bool:
        ...
# ----------------------------------
class SampleOrganizerConf(BaseModel):
    '''
    Class meant to describe how samples should be organized
    '''
    cleanup  : bool
    dry_run  : bool
    triggers : list[Trigger]
    # ------------------------------
    @classmethod
    def default(
        cls, 
        cleanup : bool,
        dry_run : bool) -> 'SampleOrganizerConf':
        '''
        Provides default instance of config
        '''
        return cls(
            cleanup  = cleanup,
            dry_run  = dry_run,
            triggers = list(Trigger))
# ----------------------------------
class SampleOrganizer:
    '''
    Class meant to reorganize ROOT files downloaded from AP jobs by:

    - Merging them
    - Relocating them
    - Relocating trees into analyses directories, e.g. rk, rkst
    - Renaming the files

    I.e.

    GRID -> downloaded_files/ -> /tmp/merged.root -> rk/signal.root rkst/signal.root ...
    '''
    # ---------------------------------------
    def __init__(
        self, 
        cleanup : bool,
        dry_run : bool):
        '''
        Parameters
        -------------
        dry_run: If True no copies or deletions will be made
        cleanup: If True will delete merged file
        '''
        self._cfg     = SampleOrganizerConf.default(
            cleanup = cleanup,
            dry_run = dry_run)

        if _SCRATCH:
            log.warning(f'Using custom scratch directory: {_SCRATCH}')
            _SCRATCH.mkdir(parents = True, exist_ok = True)
            gSystem.Setenv('TMPDIR', str(_SCRATCH))

        self._ana_dir : Final[Path] = Path(os.environ['ANADIR'])
    # ---------------------------------------
    def _merge_files(self, sample : SampleProtocol) -> Path:
        '''
        Parameters
        ---------------
        sample: Object representing sample 

        Return
        ---------------
        Merged file path
        '''
        paths = sample.local_paths(must_exist = True)

        fm = TFileMerger(isLocal=False)
        fm.SetFastMethod(True)
        for path in paths:
            if self._cfg.dry_run:
                continue

            log.debug(f'Adding: {path}')
            fm.AddFile(str(path), cpProgress = False)

        with tempfile.TemporaryDirectory(delete = False, dir = _SCRATCH) as tmp_dir:
            out_path = tmp_dir / Path('merged.root')
            log.debug(f'Merging into: {out_path}')

            if not self._cfg.dry_run:
                fm.OutputFile(str(out_path), 'RECREATE')
                success = fm.Merge()
                if not success:
                    raise ValueError(f'Merge failed for sample: {sample}')

        if self._cfg.dry_run:
            return out_path

        if not out_path.exists():
            raise FileNotFoundError(f'Cannot find: {out_path}')

        return out_path
    # ---------------------------------------
    def _split_file(
        self, 
        is_mc   : bool,
        cleanup : bool,
        path    : Path) -> dict[Trigger,Path]:
        '''
        Parameters
        -----------------
        is_mc  : True if it is MC
        path   : Path to ROOT file with multiple directories, i.e. the merged one
        cleanup: If True, it will delete file after splitting

        Returns
        -----------------
        Dictionary mapping project to path to ROOT file
        '''
        if self._cfg.dry_run:
            log.debug('Skipping splitting for dry-run')
            return dict()

        result = dict()
        for trigger in self._cfg.triggers:
            split_path = path.parent / f'{trigger}_{path.name}'
            log.debug(split_path)

            found = self._save_file(
                is_mc       = is_mc,
                trigger     = trigger, 
                input_path  = path,
                output_path = split_path)

            if not found:
                continue

            result[trigger] = split_path

        if self._cfg.dry_run:
            log.debug('Not deleting for dry-run')
            return result

        log.debug(f'Deleting {path}')
        if cleanup:
            path.unlink()

        return result
    # ---------------------------------------
    def _save_file(
        self, 
        is_mc       : bool,
        output_path : Path,
        input_path  : Path,
        trigger     : Trigger) -> bool:
        '''
        Parameters
        ------------
        output_path: Path where file will be saved
        input_path : Handle to file containing all trees
        project    : Project for which file will be saved

        Returns
        ------------
        True if trigger was found in input
        '''
        log.debug(f'Looking for {trigger} in {input_path}')
        ifile     = TFile(str(input_path))
        reco_tree = ifile.Get(f'{trigger}/DecayTree')
        if is_mc:
            extr_tree = ifile.Get('MCDT/MCDecayTree')
        else:
            extr_tree = ifile.Get('lumiTree')

        if not reco_tree:
            log.debug(f'Skipping: {trigger}')
            return False

        log.debug(f'Dumping to {output_path}')
        ofile   = TFile(str(output_path), 'recreate')
        max_evs = -1

        clone_reco_tree = reco_tree.CloneTree(max_evs, 'fast')
        clone_extr_tree = extr_tree.CloneTree(max_evs, 'fast')

        clone_reco_tree.Write()
        clone_extr_tree.Write()

        ofile.Close()
        ifile.Close()

        return True
    # ---------------------------------------
    def _copy_files(
        self, 
        sample: SampleProtocol, 
        paths : dict[Trigger,Path]) -> None:
        '''
        Parameters
        ---------------
        sample: Object representing MC sample 
        paths : Dictionary mapping trigger name to ROOT file path
        '''
        log.debug('Moving files')
        for trigger, source_path in paths.items():
            if self._cfg.dry_run:
                log.debug('Skipping copy for dry-run')
                continue

            target_path = sample.target_paths[trigger]
            target_path.parent.mkdir(exist_ok=True, parents=True)

            log.debug('')
            log.debug(source_path)
            log.debug('--->')
            log.debug(target_path)
            log.debug('')

            shutil.copy2(source_path, target_path)
            source_path.unlink()
    # ---------------------------------------
    def organize(self, sample : SampleProtocol) -> bool:
        '''
        Parameters
        ----------------
        sample: Object representing AP JOB

        Returns
        ---------------
        True if sample was organized, False if it was skipped
        '''
        if sample.is_organized is True:
            log.debug(f'Sample already processed: {sample}')
            return False

        log.debug(f'Sample not processed: {sample}')
        local_paths = sample.local_paths(must_exist = True)

        if len(local_paths) > 1:
            merged_path = self._merge_files(sample = sample)
            cleanup     = True # delete merged temporary file
        else:
            merged_path = local_paths[0]
            cleanup     = False

        split_paths = self._split_file(
            is_mc   = sample.is_mc,
            path    = merged_path, 
            cleanup = cleanup)

        self._copy_files(
            sample= sample,
            paths = split_paths)

        return True
# ----------------------------------
