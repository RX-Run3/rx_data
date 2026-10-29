'''
Module containing SamplePatcher
'''
import json

from typing           import Final
from pathlib          import Path
from dmu              import LogStore
from dmu.generic      import utilities as gut
from rx_common        import Component, Block

from .specification   import Specification, Sample
from .sample_emulator import EmulatorConf

log                     = LogStore.add_logger('rx_data:sample_patcher')
_MAIN_TREE : Final[str] = 'main'
# ------------------------------------
class SamplePatcher:
    '''
    Class in charge of modifying specifications to patch for missing
    blocks in simulated samples
    '''
    # ----------------------
    def __init__(
        self, 
        sample : Component, 
        spec   : Specification) -> None:
        '''
        Parameters
        -------------
        sample : E.g. bpkpee 
        spec   : Object specifying how to build dataframe withf riends
        '''
        self._sample                           = sample
        self._spec                             = spec.model_copy(deep=True)
        self._associations : dict[Block,Block] = self._get_patching_dictionary()
    # ----------------------
    def _get_patching_dictionary(self) -> dict[Block,Block]:
        '''
        This method will set redefinitions to an empty dictionary if patching
        not found

        Returns
        -------------
        Dictionary where the keys are the blocks needed 
        and the values are the blocks used to patch the needed blocks

        If no patching is available, dictionary will be empty
        '''
        log.debug('Loading emulation configuration')
        data = gut.load_data(package='rx_data_data', fpath='emulated_trees/config.yaml')
        data_string = json.dumps(data)
        cfg  = EmulatorConf.model_validate_json(data_string)

        associations : dict[Block,Block] = dict()
        if Component.mc in cfg.root:
            log.debug('Found patching section for simulation')
            cfg_sample = cfg.root[Component.mc]
            associations.update(cfg_sample.patching)

        if self._sample not in cfg.root:
            log.debug(f'No sample specific patching needed for {self._sample}')
            return associations 

        log.info(f'Using sample specific patching for {self._sample}')
        associations.update(cfg.root[self._sample].patching)

        log.info(20 * '-')
        log.info('Using associations:')
        log.info(20 * '-')
        for key, val in associations.items():
            log.info(f'{key:<20}{val}')
        log.info(20 * '-')

        return associations 
    # ----------------------
    def _patch_sample(
        self, 
        ftree          : str,
        sample         : Sample, 
        patching_files : dict[Block,list[Path]]) -> Sample:
        '''
        Parameters
        -------------
        ftree : Friend tree name, e.g. mva
        sample: Object holding list of paths to be patched
        patching_files: Dictionary with:
            Key  : Block numbers needed
            Value: List of paths of main sample that should be used for patching. 
                   These are full paths and only the file names are meant to be used
                   to identify the patching path

        Returns
        -------------
        Input object, but with patching paths added
        '''
        if not patching_files:
            raise ValueError('No patching files passed')

        for block_needed, file_paths in patching_files.items():
            nfile = len(file_paths)
            log.debug(f'Patching block {block_needed} with {nfile} files')

            file_names = [ file_path.name for file_path in file_paths ] 
            sample     = self._patch_sample_for_block(
                ftree        = ftree,
                block_needed = block_needed, 
                file_names   = file_names, 
                sample       = sample)


        return sample
    # ----------------------
    def _patch_sample_for_block(
        self, 
        ftree        : str,
        sample       : Sample,
        file_names   : list[str],
        block_needed : Block) -> Sample:
        '''
        Parameters
        -------------
        ftree       : Name of friend tree
        sample      : Object representing set of files
        block_needed: Block that needs to be patched
        file_names  : List of ROOT file names for files meant to patch `block_needed`

        Returns
        -------------
        Patched sample
        '''
        patching_paths : list[Path] = [ file.path for file in sample.files if file.path.name in file_names and not file.path.is_symlink() ]
        nfound    = len(patching_paths)
        nexpected = len(file_names)

        if nfound != nexpected:
            log.error('Files from main category')
            for expected in file_names:
                log.info(expected)

            log.error(f'Paths from {ftree} category')
            for file in sample.files:
                if file.path.is_symlink():
                    continue

                log.info(file.path)

            log.error(f'Files from {ftree} category')
            for found in patching_paths:
                log.info(found.name)

            raise ValueError(f'Size of patching paths is different from expected number of files for block {block_needed}')

        patched_sample = sample.patch(
            paths = patching_paths, 
            block = block_needed)

        return patched_sample
    # ----------------------
    def get_patched_specification(self) -> Specification:
        '''
        Parameters
        -------------
        spec: Specification needed to build ROOT dataframe

        Returns
        -------------
        Patched version of specification, which takes into account block patching
        '''
        # We expect to always have the full dataset for real data
        # Only MC can be missing
        if not self._sample.is_mc:
            log.info(f'Not patching real data: {self._sample}')
            return self._spec

        if not self._associations:
            log.debug('Returning unpatched specification')
            return self._spec

        main_sample : Sample = self._spec.samples['main']

        d_patching_files : dict[Block, list[Path]] = dict()
        for needed_block, patching_block in self._associations.items():
            d_patching_files[needed_block] = main_sample.get_file_paths(block = patching_block)
            log.debug(f'Patching block: {needed_block}')

        log.debug('Patching main tree')
        patched_main = self._patch_sample(
            ftree          = _MAIN_TREE,
            sample         = main_sample, 
            patching_files = d_patching_files)

        patched_friends : dict[str, Sample] = dict()
        for friend_name, friend_sample in self._spec.friends.items():
            log.debug(f'Patching friend: {friend_name}')
            patched_friends[friend_name] = self._patch_sample(
                ftree          = friend_name,
                sample         = friend_sample, 
                patching_files = d_patching_files)

        data = {'friends' : patched_friends, 'samples' : {'main' : patched_main }}

        spec = Specification(**data)
        log.info(spec.ranges)

        return spec
# ------------------------------------
