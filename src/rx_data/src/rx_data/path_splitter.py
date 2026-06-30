'''
Module containing PathSplitter class
'''
from pathlib      import Path
from typing       import Literal, overload
from dmu          import LogLevels, LogStore
from pydantic     import RootModel
from rx_common    import Component, Trigger
from rx_data      import utilities as ut

log = LogStore.add_logger('rx_data:path_splitter')
# ------------------------------------------
class NestedSamples(RootModel):
    '''
    Nested structure like:

    sample:
        trigger:
            - path 1
            - path 2
            - path 3
    '''
    root : dict[Component, dict[Trigger, list[Path]]]
# ------------------------------------------
class Samples(RootModel):
    root: dict[tuple[Component,Trigger], list[Path]]
    # -------------------------------------------------------
    def get_subset(self, max_files : int) -> 'Samples': 
        '''
        Will limit the number of paths in the values if Data.Max is larger than zero
        '''
        if max_files < 0:
            return self 

        log.warning(f'Truncating to {max_files} paths')

        d_path_trunc = { key : val[:max_files] for key, val in self.root.items() }

        return Samples(root = d_path_trunc)
    # -------------------------------------------------------
    def __str__(self):
        msg = '\n' 
        for sample, line in self.root:
            msg += f'{sample:<50}{line:<30}\n'

        return msg
    # ------------------------------------------
    @property
    def nested(self) -> NestedSamples:
        '''
        Nested version of current object, i.e. component -> trigger -> ROOT paths
        '''
        samples = NestedSamples(root = {})
        for (sample, line), l_path in self.root.items():
            if sample not in samples.root:
                samples.root[sample] = {}

            samples.root[sample][line] = l_path

        return samples 
# ------------------------------------------
class PathSplitter:
    '''
    Class meant to split lists of LFNs/paths/PFNs of ROOT files into
    Samples and HLT2 trigger categories
    '''
    # ------------------------------------------
    def __init__(
        self, 
        paths         : list[Path], 
        max_files     : int = -1, 
        sample_naming : str = 'new'):
        '''
        paths: List of LFNs/PFNs/Local paths
        max_files: If doing tests, the output lists will be limited to this number, default not truncate
        sample_naming : Either `new` (for Run3) or `old` (for Run1/2 compatibility)
        '''
        self._l_path       = paths
        self._max_files    = max_files
        self._sample_naming= sample_naming
    # ------------------------------------------
    @overload
    def split(self, nested : Literal[False]) -> Samples:...
    @overload
    def split(self, nested : Literal[True] ) -> NestedSamples:...
    def split(self, nested : bool = False) -> Samples | NestedSamples:
        '''
        Takes list of paths to ROOT files and splits them in an easier to read structure

        Parameters
        ------------------------
        nested: If False, splits them into categories and returns a dictionary:

        category : [path_1, path_2, ...]

        If True, it will use a nested structure like:

        sample:
            trigger:
                - path 1
                - path 2
                - path 3
        '''
        npath = len(self._l_path)
        log.info(f'Splitting {npath} paths into categories')

        samples = Samples(root = {})
        for path in self._l_path:
            sample, trigger = ut.info_from_path(path=path)
            component       = Component.from_sample(sample = sample)
            key             = component, trigger

            if key not in samples:
                samples.root[key] = []

            samples.root[key].append(path)

        samples = samples.get_subset(max_files = self._max_files) 
        if log.getEffectiveLevel() < LogLevels.info:
            log.debug('Found samples:')
            log.debug(samples)

        if not nested:
            return samples

        return samples.nested 
# ------------------------------------------
