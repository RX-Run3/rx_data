'''
Module with SpecMaker class
'''
import os
import yaml
import copy
import secrets
import fnmatch
import pprint
import tempfile

from contextlib       import contextmanager
from pathlib          import Path
from typing           import overload, Literal, Final
from rx_common        import Project, Trigger
from rx_common        import Component
from dmu              import LogStore
from dmu.generic      import hashing
from dmu.generic      import version_management as vmn
from dmu.generic      import utilities          as gut

from .path_splitter   import PathSplitter, NestedSamples
from .sample_patcher  import SamplePatcher
from .specification   import Sample, Specification
from .sample_emulator import SampleEmulator

log=LogStore.add_logger('rx_data:spec_maker')

_MAIN_TREE           : Final[str]       = 'main'
_ELECTRON_ONLY_TREES : Final[list[str]] = ['brem_track_2']
# --------------------------
class SpecMaker:
    '''
    Class meant to:

    - Find samples and use them to create a JSON file with them
    - Save file and make path available to user
    '''
    _custom_versions : dict[str,str] = {}
    _custom_project  : Project | None= None        # If set, will use this project instead of the one deduced from trigger
    _default_excluded: list[str]     = []          # These friend trees will always be excluded, unless explicitly changed
    _excluded_friends: list[str]     = []          # Will not pick up any of the friend trees in this list
    _only_friends    : set[str]|None = None        # Will only pick up the friend trees in this list, if the list is not None
    _identifier      : Final[int]    = os.getpid() # In order to create JSON files with file lists, this string
                                                   # will be used to identify those files. This is needed to avoid collisions
                                                   # when sending jobs to clusters with shared file systems
    # ----------------------
    def __init__(
        self, 
        component  : Component, 
        trigger    : Trigger,
        skip_patch : bool = False,
        tree       : str  = 'DecayTree') -> None:
        '''
        Parameters
        -------------
        sample    : E.g. Bu_JpsiK_ee_eq_DPC
        trigger   : Hlt2RD_BuToKpEE_MVA
        skip_patch: If true, it will not patch for missing samples, false by default
        '''
        self._component = component
        self._emulator  = SampleEmulator(sample=component.sample)
        self._cfg_samp  = self._emulator.get_samples()

        cache_dir       = tempfile.mkdtemp(prefix=f'{component}_{trigger}_{tree}')
        self._cache_dir = Path(cache_dir)

        self._trigger   = trigger
        self._tree_name = tree

        self._project   = self._set_project(trigger=trigger) 
        self._samples   = self._get_json_paths()
        self._l_path : list[Path] = [] # list of paths to all the ROOT files

        if skip_patch:
            log.warning(f'Skipping patching of {component}')
            self._spec    = self._get_specification()
        else:
            spec          = self._get_specification()
            self._patcher = SamplePatcher(sample = component, spec = spec)
            self._spec    = self._patcher.get_patched_specification()
            self._emulator.extend_redefinitions(redefinitions = self._patcher.redefinitions)
    # ----------------------
    def _set_project(self, trigger : Trigger) -> Project:
        '''
        Parameters
        -------------
        trigger: HLT2 trigger

        Returns
        -------------
        E.g. rk, rkst
        '''
        if self._custom_project:
            log.warning(f'Using custom project: {self._custom_project}')
            return self._custom_project

        if self._component.is_mc:
            log.debug(f'Using project: {trigger.project}')
            return trigger.project

        # If this is Data, use the PID project, even if noPID was requested
        # Data has no noPID version, only MC does, can't remove PID to data
        # No PID is achieved by merging, misID trigger with main trigger

        return trigger.project.with_pid
    # ---------------------------------------------------
    def _skip_ftree(self, ftree : str) -> bool:
        '''
        Will decide if a friend tree should be skipped

        Parameters
        ----------------
        ftree: Name of friend tree, e.g. mva
        '''
        if ftree == 'not_used': # This is the directory where old samples will go
            return True

        # The main tree is never skipped
        if ftree == _MAIN_TREE: 
            return False

        if ftree in self._excluded_friends:
            log.debug(f'Excluding {ftree}')
            return True

        if ftree in self._default_excluded:
            log.debug(f'Default excluding {ftree}')
            return True

        if ftree in _ELECTRON_ONLY_TREES and self._trigger.is_muon:
            log.info(f'Excluding friend tree {ftree} for muon trigger {self._trigger}')
            return True

        if self._only_friends is None: # If _only_friends is unset, do not skip current tree
            return False

        # This check is needed to silence pyright error
        # otherwise the line above should be enough
        if self._only_friends is not None:
            if ftree not in self._only_friends: # If _only_friends was set and ftree is not one of them, skip
                return True

        log.debug(f'Not excluding {ftree} friend')

        return False
    # ---------------------------------------------------
    def _get_specification(self) -> Specification:
        '''
        Returns a dictionary with information on the main samples and the friend trees, needed to build dataframes
        '''
        data : dict[str,dict[str, Sample]] = {'samples' : {}, 'friends' : {}}

        log.info('Adding samples')
        for ftree, json_path in self._samples.items():
            log.debug(f'{"":<4}{ftree:<15}{json_path}')

            sample = self._get_sample(json_path=json_path, ftree=ftree)
            if ftree == _MAIN_TREE:
                data['samples'][ftree] = sample
            else:
                data['friends'][ftree] = sample

        return Specification(**data) 
    # ---------------------------------------------------
    def _get_trigger_paths(
        self,
        sample    : str,
        ftree     : str,
        d_trigger : dict[str,list[Path]]) -> list[Path]:
        '''
        On EXT trigger: This is a _fake_ trigger made from the merge of the OS electron trigger and
        the misID trigger, when the later is given a weight of 10, to account for prescale in 2024 data.
        For 2025, prescale is gone.

        Parameters
        ----------------
        d_trigger : Dictionary mapping HLT2 trigger names to lists of ROOT files
        sample    : Name of sample, e.g Bu_Kp...
        ftree     : Name of friend tree, e.g. mva

        Returns
        ----------------
        Gets list of paths to ROOT files for a given HLT2 trigger
        '''
        component = Component.from_sample(sample = sample)

        if component.is_mc and self._trigger in d_trigger:
            log.debug(f'Found paths for ROOT files associated to: {self._trigger}/{sample}/{ftree}')
            return d_trigger[self._trigger]

        if component.is_mc:
            raise ValueError(f'Invalid trigger {self._trigger} for sample {sample}, project {self._project} and friend tree {ftree}')

        if self._trigger.has_pid:
            log.debug(f'Found paths for ROOT files associated to: {self._trigger}/{sample}/{ftree}')
            return d_trigger[self._trigger]

        # NOTE: If it was not explicitly stated that this is 2024 data, ext trigger does not make sense
        log.debug(f'Found extended trigger: {self._trigger}')
        trig_misid   = self._trigger.replace('_noPID', '_misid')
        trig_default = self._trigger.replace('_noPID',       '')

        l_path = []
        l_path+= d_trigger[trig_default]
        l_path+= d_trigger[trig_misid  ]

        return l_path
    # ---------------------------------------------------
    def _get_sample(self, json_path : Path, ftree : str) -> Sample:
        '''
        Parameters:
        --------------------
        json_path : Path to JSON file specifying samples:trigger:files
        ftree     : Friend tree name, e.g mva, main

        Returns
        --------------------
        Sample object, e.g. main, mva, hop, etc needed to build Specification object
        '''
        log.debug(f'Building section from: {json_path}')

        d_data = gut.load_json(path=json_path)
        if d_data is None:
            raise ValueError(f'Cannot load {json_path}')

        l_path = []
        nopath = False
        nosamp = True
        for sample in d_data:
            if not fnmatch.fnmatch(sample, self._sample):
                log.debug(f'For target {self._sample} skipping {sample}')
                continue

            nosamp = False
            try:
                d_trigger = d_data[sample]
            except KeyError as exc:
                for val in d_data:
                    log.info(val)
                raise KeyError(f'Sample {sample} not found') from exc

            l_path_sample = self._get_trigger_paths(
                d_trigger= d_trigger,
                ftree    = ftree,
                sample   = sample)

            nsamp = len(l_path_sample)
            if nsamp == 0:
                log.error(f'No paths found for {sample}/{self._trigger} in {json_path} and friend tree {ftree}')
                nopath = True
            else:
                log.debug(f'Found {nsamp} paths for {sample}/{self._trigger} in {json_path}')

            l_path += l_path_sample

        if nopath:
            raise ValueError('Samples with paths missing')

        if nosamp:
            data = yaml.dump(d_data, sort_keys=False)
            log.error(data)
            raise ValueError(f'Could not find any sample matching {self._cfg_samp} with friend tree {ftree} in {json_path}')

        self._l_path += l_path

        return Sample(trees = [self._tree_name], files = l_path, metadata = {'kind' : ftree})
    # ---------------------------------------------------
    def _filter_friends(
        self, 
        d_ftree_dir : dict[str,Path]) -> dict[str,Path]:
        '''
        Parameters
        --------------
        d_ftree_dir: Dictionary where:
            key : Is the friend tree name
            val : Is the path to the directory with the friend trees

        Returns
        --------------
        Same as input, but after filtering for not needed samples
        '''
        d_ftree_dir_flt = { ftree : ftree_dir for ftree, ftree_dir in d_ftree_dir.items() if not self._skip_ftree(ftree=ftree) }
        d_ftree_dir_flt = dict(sorted(d_ftree_dir_flt.items()))

        if self._tree_name == 'DecayTree':
            return d_ftree_dir_flt

        # MCDecayTree has no friends
        if self._tree_name == 'MCDecayTree':
            path = d_ftree_dir_flt[_MAIN_TREE]
            return {_MAIN_TREE : path}

        raise ValueError(f'Invalid tree name: {self._tree_name}')
    # ---------------------------------------------------
    def _get_json_paths(self) -> dict[str,Path]:
        '''
        This function will return a dictionary with:

        key  : Name of sample, e.g. main, mva
        value: Path to JSON file with the directory structure needed to make an RDataFrame
        '''
        data_dir     = Path(os.environ['ANADIR'])
        ftree_wc     = data_dir / f'Data/{self._project}'
        l_ftree_dir  = list(ftree_wc.glob(pattern='*'))
        if not l_ftree_dir:
            raise ValueError(f'No directories with samples found in: {ftree_wc}')

        d_ftree_dir  = { os.path.basename(ftree_dir) : ftree_dir for ftree_dir in l_ftree_dir }
        d_ftree_dir  = self._filter_friends(d_ftree_dir=d_ftree_dir)
        self._s_ftree= { ftree for ftree in d_ftree_dir if ftree != _MAIN_TREE } # These friend trees both exist and are picked up

        log.info(40 * '-')
        log.info(f'{"Friend":<20}{"Version":<20}')
        log.info(40 * '-')
        d_vers_dir   = { ftree_name : self._versioned_from_ftrees(ftree_dir)        for ftree_name, ftree_dir in d_ftree_dir.items() }
        log.info(40 * '-')

        d_json_path  = { ftree_name : self._json_path_from_ftree(dir_path=vers_dir) for ftree_name,  vers_dir in d_vers_dir.items()  }
        log.info('')

        return d_json_path
    # ---------------------------------------------------
    def _versioned_from_ftrees(self, ftree_dir :  Path) -> Path:
        '''
        Takes path to directory corresponding to a friend tree.
        Finds latest/custom version and returns this path
        '''
        friend_name = ftree_dir.name
        if friend_name in self._custom_versions:
            version     = self._custom_versions[friend_name]
            version_dir = ftree_dir / version

            log.warning(f'{friend_name:<20}{version:<20}')

            return version_dir

        version = vmn.get_last_version(dir_path=ftree_dir, version_only=True)
        log.info(f'{friend_name:<20}{version:<20}')

        return ftree_dir / version
    # ---------------------------------------------------
    def _json_path_from_ftree(self, dir_path : Path) -> Path:
        '''
        Takes path to directory with ROOT files associated to friend tree
        returns path to YAML file with correctly structured files
        '''
        log.debug(f'Looking for files in: {dir_path}')

        l_root_path = list(dir_path.glob(pattern='*.root'))
        if not l_root_path: 
            raise ValueError(f'No ROOT files found in {dir_path}')

        spl  = PathSplitter(paths=l_root_path)
        data = spl.split(nested=True)

        out_path = self._get_tmp_path(identifier='tree_structure', data=data)
        log.debug(f'Saving friend tree structure to {out_path}')
        gut.dump_json(data, out_path)

        return out_path
    # ---------------------------------------------------
    def _split_per_file(self, spec : Specification, main : str) -> dict[Path,Path]:
        '''
        Parameters
        --------------------
        data      : Dictionary representing _spec_ needed to build ROOT dataframe with friend trees
        main      : Name of the main category, e.g. not the friend trees.

        Returns
        --------------------
        Dictionary with the:

        key  : As the ROOT file path in the main category
        Value: The path to the JSON config file
        '''
        try:
            l_file = spec.samples[main].files
        except KeyError as exc:
            pprint.pprint(spec)
            raise KeyError('Cannot access list of files from JSON config needed by FromSpec') from exc

        nfiles = len(l_file)
        log.info(f'Found {nfiles} files')

        d_config : dict[Path, Path] = {}
        for ifile in range(nfiles):
            log.debug(f'Removing {ifile}-th file')
            single_file_spec, fpath = self._remove_all_but(spec=spec, ifile=ifile, main=main)
            config_path             = self._get_tmp_path(identifier='rdframe_config', data=single_file_spec)

            log.debug(f'Saving per-file config path to {config_path}')
            config_path.write_text(single_file_spec.model_dump_json(indent=2))
            d_config[fpath] = config_path 

        return d_config
    # ---------------------------------------------------
    def _remove_all_but(
        self, 
        spec  : Specification, 
        ifile : int, 
        main  : str) -> tuple[Specification, Path]:
        '''
        Will:

        - Take the specification object 
        - Make a local copy
        - Remove all the paths except the ifile th entry

        Returns
        ----------------
        Tuple with: 

        - Copy of specification after removal of all but the ifile
        - The path to the ROOT file associated to the main samples
        '''

        data       = spec.model_dump()
        try:
            fpath_main = spec.samples[main].files[ifile]
        except IndexError as exc:
            model_str = spec.model_dump(mode='json')
            log.error(yaml.safe_dump(model_str))
            raise IndexError(f'Cannot access tree {main} at {ifile}') from exc

        data['samples'][main]['files'] = [fpath_main]

        for friend_name, sample in spec.friends.items():
            try:
                fpath_friend = sample.files[ifile]
            except IndexError as exc:
                data_string = yaml.dump(sample)
                log.warning(20 * '-')
                log.info(data_string)
                log.warning(20 * '-')
                raise KeyError(f'Cannot retrieve file at {ifile} for friend {friend_name}, sample {self._cfg_samp}/{self._trigger}/{self._tree_name}') from exc

            data['friends'][friend_name]['files'] = [fpath_friend]

        return Specification(**data), fpath_main
    # ---------------------------------------------------
    def _get_tmp_path(
        self, 
        identifier : str, 
        data       : NestedSamples | Specification) -> Path:
        '''
        This method creates paths to temporary config files in /tmp.
        Needed to configure creation of dataframes

        Parameters
        ----------------
        identifier : String identifying sample/file whose configuration will be stored
        data       : Dictionary with structure as needed by ROOT to make dataframe with friend trees

        Returns
        ----------------
        Path to JSON file that will be used to dump configuration
        '''
        if not isinstance(self._cache_dir, Path):
            raise ValueError(f'Caching directory not a path but: {type(self._cache_dir)}')

        if isinstance(data, Specification):
            serializable = data.model_dump_json()
        else:
            serializable = data

        val      = hashing.hash_object(obj=[serializable])
        val      = val[:10]

        # Id of process plus random number 
        proc_id  = self._identifier + secrets.randbelow(1000_000_000)
        tmp_path = self._cache_dir / f'{identifier}_{proc_id}_{val}.json'

        log.debug(f'Using config JSON: {tmp_path}')

        return tmp_path
    # ----------------------
    @property
    def spec(self) -> Specification:
        '''
        Returns specification object, needed
        to make ROOT dataframe
        '''
        if not isinstance(self._spec, Specification):
            raise ValueError('Cannot find specification')

        return self._spec
    # ----------------------
    @overload
    def get_spec_path(self, per_file : Literal[False]) -> Path:...
    @overload
    def get_spec_path(self, per_file : Literal[True] ) -> dict[Path,Path]:...
    def get_spec_path(self, per_file : bool          ) -> dict[Path,Path] | Path:
        '''
        Parameters
        ----------------------
        per_file : If true will process configs per file, otherwise it will do the full sample

        Returns
        ----------------------
        If per_file is false, path to the JSON specification file.

        If per_file is true, dictionary with:

        key  : Path to the main sample ROOT file, i.e. the file that is not the main tree.
               If per_file is False, key will be ''
        value: Path to JSON config file, needed to build dataframe though FromSpec
        '''

        log.debug(f'This instance/process ID is: {self._identifier}')
        if not per_file:
            log.debug('Not splitting per file')
            cfg_path = self._get_tmp_path(identifier='rdframe_config', data=self._spec)
            log.debug(f'Saving config path to {cfg_path}')
            cfg_path.write_text(data=self._spec.model_dump_json(indent=2))

            return cfg_path

        log.debug('Splitting per file')

        paths : dict[Path,Path] = self._split_per_file(spec=self._spec, main = _MAIN_TREE)

        return paths
    # ----------------------
    # Context managers
    # ----------------------
    @classmethod
    def default_excluded(cls, names : list[str]):
        '''
        Contextmanager that will (re)define which
        trees are excluded as friend trees by default
        '''
        log.debug(f'Default excluding: {names}')

        @contextmanager
        def _context():
            old_val = cls._default_excluded
            cls._default_excluded = names

            try:
                yield
            finally:
                cls._default_excluded = old_val

        return _context()
    # ---------------------------------------------------
    @classmethod
    def exclude_friends(cls, names : list[str]):
        '''
        It will build the dataframe, excluding the friend trees
        in the `names` list
        '''
        @contextmanager
        def _context():
            old_val = cls._excluded_friends
            cls._excluded_friends = copy.deepcopy(names)

            if cls._excluded_friends:
                log.warning(f'Excluding friend trees: {cls._excluded_friends}')

            try:
                yield
            finally:
                cls._excluded_friends = old_val

        return _context()
    # ---------------------------------------------------
    @classmethod
    def custom_friends(cls, versions : dict[str,str]):
        '''
        It will pick a dictionary between:

        key: Friend tree names, e.g. mva
        val: Versions, e.g. v5

        and override the version used for this friend tree
        '''
        @contextmanager
        def _context():
            old_val = cls._custom_versions
            cls._custom_versions = copy.deepcopy(versions)
            log.warning(f'Using custom friend tree versions: {cls._custom_versions}')

            try:
                yield
            finally:
                cls._custom_versions = old_val

        return _context()
    # ---------------------------------------------------
    @classmethod
    def only_friends(cls, s_friend : set[str]):
        '''
        This context manager sets the accepted friend trees
        to what is passed. Every other friend tree will be dropped

        Parameters
        --------------
        s_friend : Set of friend tree names, e.g ['mva', 'hop']
        '''

        old_val = cls._only_friends
        cls._only_friends = s_friend
        @contextmanager
        def _context():
            try:
                yield
            finally:
                cls._only_friends = old_val

        return _context()
    # ---------------------------------------------------
    @classmethod
    def project(cls, name : Project):
        '''
        Parameters
        --------------
        name : Name of project where ntuples will be taken from, e.g. rk 
        '''
        if cls._custom_project:
            raise ValueError(f'Custom project already set to: {cls._custom_project}')

        cls._custom_project = name 
        @contextmanager
        def _context():
            try:
                yield
            finally:
                cls._custom_project = None 

        return _context()
# --------------------------
