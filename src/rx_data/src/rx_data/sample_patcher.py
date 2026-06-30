'''
Module containing SamplePatcher
'''
from ROOT           import RDataFrame # type: ignore
from pathlib        import Path
from dmu            import LogStore
from dmu.generic    import utilities as gut
from rx_common      import Component, Block

from .specification   import Specification, Sample
from .sample_emulator import EmulatorConf

log=LogStore.add_logger('rx_data:sample_patcher')
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
        '''
        self._sample                                  = sample
        self._spec                                    = spec.model_copy(deep=True)
        self._associations   : dict[Block,Block]      = self._get_patching_dictionary()
        self._conditions     : dict[Block,str]        = dict() 
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
            log.debug(f'{key:<20}{val}')
        log.info(20 * '-')

        return associations 
    # ----------------------
    @property
    def redefinitions(self) -> dict[str,str]:
        '''
        Here the conditions refer to redefinitions of the block column
        such that for the entries at the end of the dataframe a block is reused
        as a different block

        Returns
        --------------
        Dictionary between column name and string with new definition
        '''
        if self._conditions is None:
            raise ValueError(f'No conditions available for sample {self._sample}')

        if not self._conditions:
            return dict()

        nconditions = len(self._conditions)
        log.info(f'Using {nconditions} conditions')
        for block, condition in self._conditions.items():
            log.debug(f'{block:<10}{condition:<}')

        # block times condition for that block to be true
        terms     = [ f'{block} * ({condition})' for block, condition in self._conditions.items() ]

        # New block is picked based on condition
        new_block = ' + '.join(terms)

        log.debug(f'Block condition: {new_block}')

        # If this is a candidate where no new block is satisfied, pick old block
        condition = f'{new_block} == 0 ? block : {new_block}'

        log.debug(f'Block redefinition: {condition}')

        return {'block' : condition} 
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
                arr_block = rdf.AsNumpy(['block'])['block']
            except Exception as exc:
                raise ValueError(f'Cannot access block from: {path}:{tree}') from exc

            if block not in arr_block:
                continue

            patching_paths.append(path)

        self._patching_files[block] = patching_paths

        return patching_paths
    # ----------------------
    def _patch_sample(
        self, 
        sample         : Sample, 
        patching_files : dict[Block,list[Path]]) -> Sample:
        '''
        Parameters
        -------------
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
            sample     = self._patch_sample_for_block(
                block_needed = block_needed, 
                file_names   = file_names, 
                sample       = sample)

        return sample
    # ----------------------
    def _patch_sample_for_block(
        self, 
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

            log.error('Files from friend category')
            for found in patching_paths:
                log.info(found.name)

            raise ValueError(f'Size of patching paths is different from expected number of files for block {block_needed}')

        old_sample_size = sample.size
        sample.files    = sample.files + sorted(list(patching_paths))
        new_sample_size = sample.size

        if sample.metadata['kind'] == 'main':
            self._build_conditions(
                block_needed = block_needed,
                min_index    = old_sample_size,
                max_index    = new_sample_size)

        return sample
    # ----------------------
    def _build_conditions(
        self, 
        block_needed: Block,
        min_index   : int, 
        max_index   : int) -> None:
        '''
        If block 3 needs to be used between two entry indexes.
        This function will append the index condition and the block to _conditions.

        Parameters
        -------------
        block_needed : Block for which the condition is build
        *_index      : Index of first and last element that will be assigned this block
        '''
        condition = f'rdfentry_ + 1 > {min_index} && rdfentry_ < {max_index}'
        log.debug(f'Condition: {condition}')

        if self._conditions is None:
            self._conditions = dict()

        if block_needed in self._conditions:
            raise ValueError(f'Block {block_needed} already found in conditions dictionary')

        self._conditions[block_needed] = condition 
    # ----------------------
    def get_patched_specification(self) -> Specification:
        '''
        Parameters
        -------------
        spec: Specification needed to build ROOT dataframe

        Returns
        -------------
        Patched version, which takes into account block patching
        '''
        # We expect to always have the full dataset
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
            log.debug(f'Patching block: {needed_block}')
            d_patching_files[needed_block] = self._get_patching_files(block=patching_block, main_sample=main_sample)

        patched_friends : dict[str, Sample] = dict()
        for friend_name, friend_sample in self._spec.friends.items():
            log.debug(f'Patching friend: {friend_name}')
            patched_friends[friend_name] = self._patch_sample(sample=friend_sample, patching_files = d_patching_files)

        log.debug('Patching main tree')
        patched_main = self._patch_sample(sample=main_sample, patching_files = d_patching_files)
        data         = {'friends' : patched_friends, 'samples' : {'main' : patched_main }}

        return Specification(**data) 
# ------------------------------------
