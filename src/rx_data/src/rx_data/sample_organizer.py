'''
Module with SampleOrganizer class
'''

import os
import shutil
import tempfile

from typing      import Final, Protocol
from ROOT        import TFileMerger, TFile # type: ignore
from pathlib     import Path
from dmu         import LogStore
from pydantic    import BaseModel
from rx_common   import Project, Trigger
from dmu.generic import version_management as vmn 
from dmu.generic import NoVersions 

log=LogStore.add_logger('rx_data:sample_organizer')
# ----------------------------------
class SampleProtocol(Protocol):
    '''
    Class meant to define how a Sample instance
    should look like for `SampleOrganizer`
    '''
    # -----------------
    @property
    def name(self) -> str:
        ...
    # -----------------
    def local_paths(
        self, 
        directory : Path,
        must_exist: bool) -> list[Path]:
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
        triggers = [
            Trigger.rk_ee_os, 
            Trigger.rk_ee_ss, 
            Trigger.rk_mm_os, 
            Trigger.rk_mm_ss, 
            # ----------
            Trigger.rkst_ee_os, 
            Trigger.rkst_ee_ss, 
            Trigger.rkst_mm_os, 
            Trigger.rkst_mm_ss, 
        ]

        return cls(
            cleanup  = cleanup,
            dry_run  = dry_run,
            triggers = triggers)
# ----------------------------------
class SampleOrganizer:
    '''
    Class meant to reorganize ROOT files downloaded from AP jobs by:

    - Merging them
    - Relocating them
    - Relocating trees into analyses directories, e.g. rk, rkst
    - Renaming the files
    '''
    # ---------------------------------------
    def __init__(
        self, 
        cleanup : bool,
        dry_run : bool,
        storage : Path):
        '''
        Parameters
        -------------
        dry_run: If True no copies or deletions will be made
        storage: Path to directory with ROOT files before organizing them
        '''
        self._storage = storage
        self._cfg     = SampleOrganizerConf.default(
            cleanup = cleanup,
            dry_run = dry_run)

        self._ana_dir : Final[Path] = Path(os.environ['ANADIR'])
    # ---------------------------------------
    def _merge_files(self, paths : list[Path]) -> Path:
        '''
        Parameters
        ---------------
        paths: List of paths to ROOT files

        Return
        ---------------
        Merged file path
        '''
        fm = TFileMerger(isLocal=True)
        fm.SetFastMethod(True)
        for path in paths:
            if self._cfg.dry_run:
                continue

            log.debug(f'Adding: {path}')
            fm.AddFile(str(path), cpProgress = False)

        with tempfile.TemporaryDirectory(delete = False) as tmp_dir:
            out_path = tmp_dir / Path('merged.root')
            log.debug(f'Merging into: {out_path}')

            if not self._cfg.dry_run:
                fm.OutputFile(str(out_path), 'RECREATE')
                success = fm.Merge()
                if not success:
                    raise ValueError('Merge failed')

        if self._cfg.dry_run:
            return out_path

        if not out_path.exists():
            raise FileNotFoundError(f'Cannot find: {out_path}')

        if not self._cfg.cleanup:
            return out_path

        #log.debug('Deleting pre-merge paths')
        #for path in local_paths:
        #    if self._cfg.dry_run:
        #        continue

        #    path.unlink()

        return out_path
    # ---------------------------------------
    def _split_file(
        self, 
        cleanup : bool,
        path    : Path) -> dict[Trigger,Path]:
        '''
        Parameters
        -----------------
        path   : Path to ROOT file with multiple directories
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
        true_tree = ifile.Get('MCDT/MCDecayTree')

        if not reco_tree:
            log.debug(f'Skipping: {trigger}')
            return False

        log.debug(f'Dumping to {output_path}')
        ofile     = TFile(str(output_path), 'update')
        reco_tree.Write()
        true_tree.Write()

        ofile.Close()
        ifile.Close()

        return True
    # ---------------------------------------
    def _get_target_path(
        self, 
        file_name : str,
        project   : Project) -> Path:
        '''
        Parameters
        ---------------
        file_name: E.g. mc_signal.root
        project  : E.g. rk

        Returns
        ---------------
        '''
        target_dir   = self._ana_dir / f'Data/{project}/main'
        target_dir.mkdir(parents = True, exist_ok = True)

        try:
            last_version = vmn.get_last_version(dir_path = target_dir, version_only = True)
        except NoVersions:
            log.info(f'No version found in: {target_dir}')
            last_version = None

        next_version = 'v0' if last_version is None else vmn.get_next_version(version = last_version)
        target_path  = target_dir / next_version / f'{file_name}.root'

        return target_path
    # ---------------------------------------
    def _copy_files(
        self, 
        name  : str, 
        paths : dict[Trigger,Path]) -> None:
        '''
        Parameters
        ---------------
        name : Name of AP job, needed to name ROOT file
        paths: Dictionary mapping trigger name to ROOT file path
        '''
        for trigger, source_path in paths.items():
            target_path = self._get_target_path(project = trigger.project, file_name = name)
            target_path.parent.mkdir(exist_ok=True, parents=True)

            log.debug(f'{str(source_path):<50}{target_path}')
            if self._cfg.dry_run:
                log.debug('Skipping copy for dry-run')
                continue

            log.debug('Moving files')
            shutil.copy2(source_path, target_path)
            source_path.unlink()
    # ---------------------------------------
    def organize(self, sample : SampleProtocol) -> None:
        '''
        Parameters
        ----------------
        sample: Object representing AP JOB
        '''
        local_paths = sample.local_paths(
            directory  = self._storage, 
            must_exist = True)

        if len(local_paths) > 1:
            merged_path = self._merge_files(paths = local_paths)
            cleanup     = True # delete merged temporary file
        else:
            merged_path = local_paths[0]
            cleanup     = False

        split_paths = self._split_file(path = merged_path, cleanup = cleanup)

        self._copy_files(
            name  = sample.name,
            paths = split_paths)
# ----------------------------------
