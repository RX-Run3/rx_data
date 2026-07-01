'''
Module containing SamplePatcher
'''
from typing           import Final
from ROOT             import RDataFrame # type: ignore
from pathlib          import Path
from dmu              import LogStore
from dmu.generic      import utilities as gut
from pydantic         import RootModel, model_validator
from rx_common        import Component, Block

from .specification   import Specification, Sample
from .sample_emulator import EmulatorConf

log                 = LogStore.add_logger('rx_data:sample_patcher')
_BLOCK : Final[str] = 'block' # name of branch with block number
# ------------------------------------
class PatchRanges(RootModel[list[tuple[int,int,int]]]):
    root : list[tuple[int,int,int]]
    # ---------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'PatchRanges':
        fail = False 
        for lower, upper, _ in self.root:
            if lower < upper:
                continue

            fail = True
            log.error(f'{lower} >= {upper}')

        if fail:
            raise ValueError('Range validation failed')

        return self
# ------------------------------------
class SamplePatcher:
    '''
    Class in charge of modifying specifications to patch for missing
    blocks in simulated samples
    '''
    # ----------------------
    def __init__(
        self, 
        sample   : Component, 
        spec     : Specification) -> None:
        '''
        Parameters
        -------------
        sample   : E.g. bpkpee 
        spec     : Object specifying how to build dataframe withf riends
        '''
        self._sample                                  = sample
        self._spec                                    = spec.model_copy(deep=True)
        self._associations   : dict[Block,Block]      = self._get_patching_dictionary()
        self._patching_ranges                         = PatchRanges(root = [])           
        self._patching_files : dict[Block,list[Path]] = dict()
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
        cfg  = EmulatorConf(**data)

        associations : dict[Block,Block] = dict()
        if Component.mc in cfg.root:
            log.debug('Found patching section for simulation')
            cfg_sample = cfg.root[Component.mc]
            associations.update(cfg_sample.patching)

        if self._sample not in cfg.root:
            log.error(f'No sample specific patching needed for {self._sample}')
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
    def _get_patching_files(
        self, 
        block       : Block, 
        main_sample : Sample) -> list[Path]:
        '''
        Parameters
        -------------
        block      : Block that will be used for patching
        main_sample: Object containing list of paths to files in the main sample 

        Returns
        -------------
        List of paths to files containing block
        '''
        if block in self._patching_files:
            return self._patching_files[block]

        paths  = main_sample.files
        [tree] = main_sample.trees

        log.info(f'Finding patching files for block {block}')
        patching_paths : list[Path] = []
        for path in paths:
            rdf = RDataFrame(tree, str(path))
            if rdf.Count().GetValue() == 0:
                log.debug(f'Found empty file: {path}:{tree}, skipping')
                continue

            try:
                arr_block = rdf.AsNumpy([_BLOCK])[_BLOCK]
            except Exception as exc:
                raise ValueError(f'Cannot access block from: {path}:{tree}') from exc

            if block.to_int() not in arr_block:
                continue

            patching_paths.append(path)

        npatch = len(patching_paths)
        ntotal = len(paths)
        if not patching_paths:
            raise ValueError(f'Found {npatch}/{ntotal} patching files for: {block}')
        else:
            log.debug(f'Found {npatch}/{ntotal} patching paths for: {block}')

        self._patching_files[block] = patching_paths

        return patching_paths
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
        for block_needed, file_paths in patching_files.items():
            file_names = [ file_path.name for file_path in file_paths ] 
            start      = sample.size
            sample     = self._patch_sample_for_block(
                ftree        = ftree,
                block_needed = block_needed, 
                file_names   = file_names, 
                sample       = sample)
            end = sample.size

            log.debug(f'Patched block {block_needed} appended extra files: {start} -> {end}')

        return sample
    # ----------------------
    def _patch_sample_for_block(
        self, 
        ftree        : str,
        sample       : Sample,
        block_needed : Block, 
        file_names   : list[str]) -> Sample:
        '''
        Parameters
        -------------
        block_needed: Block that needs to be patched
        file_names  : Names (not paths) of files that will be used to patch `block_needed`

        Returns
        -------------
        Patched sample
        '''
        patching_paths : set[Path] = { path for path in sample.files if path.name in file_names }
        nfound    = len(patching_paths)
        nexpected = len(file_names)

        if nfound != nexpected:
            log.error('Files from main category')
            for expected in file_names:
                log.info(expected)

            log.error(f'Files from {ftree} category')
            for found in patching_paths:
                log.info(found.name)

            raise ValueError(f'Size of patching paths is different from expected number of files for block {block_needed}')

        isize  = sample.size - 1
        sample.files = sample.files + sorted(list(patching_paths))
        fsize  = sample.size - 1
        iblock = block_needed.to_int()
        self._patching_ranges.root.append((isize, fsize, iblock))

        return sample
    # ----------------------
    def get_patched_specification(self) -> tuple[Specification, PatchRanges]:
        '''
        Parameters
        -------------
        spec: Specification needed to build ROOT dataframe

        Returns
        -------------
        Tuple with:

        Patched version of specification, which takes into account block patching
        Patching tuples, holding the event range for each file and the block number
        '''
        # We expect to always have the full dataset
        # Only MC can be missing
        if not self._sample.is_mc:
            log.info(f'Not patching real data: {self._sample}')
            return self._spec, PatchRanges(root = [])

        if not self._associations:
            log.debug('Returning unpatched specification')
            return self._spec, PatchRanges(root = [])

        main_sample : Sample = self._spec.samples['main']

        d_patching_files : dict[Block, list[Path]] = dict()
        for needed_block, patching_block in self._associations.items():
            d_patching_files[needed_block] = self._get_patching_files(block=patching_block, main_sample=main_sample)
            log.debug(f'Patching block: {needed_block}')

        log.debug('Patching main tree')
        patched_main = self._patch_sample(
            ftree          = 'main',
            sample         = main_sample, 
            patching_files = d_patching_files)

        log.debug(20 * '-')
        log.debug('Patching ranges:')
        for ientry, fentry, iblock in self._patching_ranges.root:
            log.debug(f'{ientry:<10}{fentry:<10}{iblock:<10}')
        log.debug(20 * '-')

        patched_friends : dict[str, Sample] = dict()
        for friend_name, friend_sample in self._spec.friends.items():
            log.debug(f'Patching friend: {friend_name}')
            patched_friends[friend_name] = self._patch_sample(
                ftree          = friend_name,
                sample         = friend_sample, 
                patching_files = d_patching_files)

        data = {'friends' : patched_friends, 'samples' : {'main' : patched_main }}

        return Specification(**data), self._patching_ranges
# ------------------------------------
