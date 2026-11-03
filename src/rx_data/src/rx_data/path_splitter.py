'''
Module containing PathSplitter class
'''
from itertools    import chain
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
    def _get_paths(self, sample : Component, trigger : Trigger) -> list[Path]:
        '''
        Parameters
        -------------
        sample : E.g. bpkpee
        trigger: E.g. rk_ee_os

        Returns
        -------------
        List of paths to ROOT files associated to sample and trigger
        '''
        if sample not in self.root:
            log.error(self)
            raise ValueError(f'Cannot find sample {sample}')

        paths : list[Path] = []

        # NOTE: For data, noPID trigger is made of misID + signal region triggers
        # while for MC, there is a dummy noPID trigger, made by running noPID AP
        subtriggers = [trigger] if sample.is_mc else trigger.subtriggers
        for sub_trigger in subtriggers:
            if sub_trigger not in self.root[sample]:
                log.error(self)
                raise ValueError(f'For sample {sample}, cannot find trigger: {sub_trigger.value}')

            paths += self.root[sample][sub_trigger]

        return paths
    # ------------------------------------------
    def __str__(self) -> str:
        return self.model_dump_json(indent = 2)
    # ------------------------------------------
    def get_paths(
        self,
        ftree  : str,
        sample : Component,
        trigger: Trigger) -> list[Path]:
        '''
        Parameters
        -----------------
        ftree  : Friend tree name, e.g. mva
        sample : E.g. bkpkee
        trigger: Hlt2 trigger

        Returns
        -----------------
        List of sorted paths to corresponding ROOT files
        '''
        nested_paths = [ self._get_paths(sample = sub_sample, trigger = trigger) for sub_sample in sample.subsamples ]
        flat_paths   = list(chain.from_iterable(nested_paths))
        friend_paths = [ path for path in flat_paths if f'/{ftree}/' in str(path) ]

        npath = len(flat_paths)
        log.debug(20 * '-')
        log.debug(f'Found {npath} paths for {ftree}|{sample}|{trigger}')
        for path in flat_paths:
            log.debug(f'   {path}')
        log.debug(20 * '-')

        return sorted(friend_paths)
# ------------------------------------------
class Samples(RootModel):
    root: dict[tuple[Component,Trigger], list[Path]]
    # -------------------------------------------------------
    @property
    def npaths(self) -> int:
        '''
        Number of ROOT file paths in this object
        '''
        size = 0
        for paths in self.root.values():
            size += len(paths)

        return size
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
        paths     : list[Path],
        max_files : int = -1):
        '''
        paths: List of LFNs/PFNs/Local paths
        max_files: If doing tests, the output lists will be limited to this number, default not truncate
        '''
        self._l_path       = sorted(paths)
        self._max_files    = max_files
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
        log.debug(f'Splitting {npath} paths into categories')

        samples = Samples(root = {})
        for path in self._l_path:
            sample, trigger = ut.info_from_path(path=path)
            component       = Component.from_sample(sample = sample)
            key             = component, trigger

            if key not in samples.root:
                samples.root[key] = []

            samples.root[key].append(path)

        if npath != samples.npaths:
            raise ValueError(f'Different size after/before splitting: {samples.npaths} != {npath}')

        samples = samples.get_subset(max_files = self._max_files)
        if log.getEffectiveLevel() < LogLevels.info:
            log.debug('Found samples:')
            log.debug(samples)

        if not nested:
            return samples

        return samples.nested
# ------------------------------------------
