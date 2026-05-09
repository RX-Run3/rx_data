'''
Module with SampleOrganizer class
'''

import os
from pathlib import Path
from post_ap import Sample
from dmu     import LogStore

log=LogStore.add_logger('rx_data:sample_organizer')
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
    def __init__(self, storage : Path):
        '''
        Parameters
        -------------
        storage: Path to directory with ROOT files before organizing them
        '''
        self._storage = storage
    # ---------------------------------------
    def _check_local_files(self, sample : Sample) -> None:
        '''
        Parameters
        ----------------
        sample: Object representing AP JOB
        '''
        fail = False
        for path in sample.local_paths(directory = self._storage):
            if not path.exists():
                log.error(path)
                fail = True

        if fail:
            raise ValueError(f'At least one file was not found in \n {sample}')
    # ---------------------------------------
    def _merge_files(self, sample : Sample) -> list[Path]:
        '''
        Parameters
        ---------------
        sample: Object representing AP job

        Return
        ---------------
        Paths to merged files, e.g. one per trigger
        '''
        local_paths = sample.local_paths(directory = self._storage)

    # ---------------------------------------
    def organize(self, sample : Sample) -> None:
        '''
        Parameters
        ----------------
        sample: Object representing AP JOB
        '''
        self._check_local_files(sample = sample)
        merged_paths = self._merge_files(sample = sample)
        self._copy_files(paths = merged_paths)
# ----------------------------------
