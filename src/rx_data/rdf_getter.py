'''
Module holding RDFGetter class
'''
from contextlib import contextmanager
import os
import glob
import copy
import pprint
import fnmatch
import secrets
from typing              import Any, Final, overload, Literal

import yaml
import dmu.generic.utilities as gut

from ROOT                  import RDF
from ROOT                  import GetThreadPoolSize, TFile, EnableImplicitMT, DisableImplicitMT # type: ignore
from dmu.generic           import version_management as vmn
from dmu.generic           import hashing
from dmu.logging.log_store import LogStore
from omegaconf             import DictConfig, OmegaConf
from rx_common             import info
from rx_data.path_splitter import PathSplitter

log=LogStore.add_logger('rx_data:rdf_getter')
# ---------------------------------------------------
class AlreadySetColumns(Exception):
    '''
    Class used to raise exception when columns have already been defined.
    This is supposed to be done once per session
    '''
    def __init__(self, message : str):
        '''
        Takes message to show in exception
        '''
        super().__init__(message)
# ---------------------------------------------------
class RDFGetter:
    '''
    Class meant to load dataframes with friend trees

    This class has the following attributes:

    max_entries : Limits the number of entries that will be provided
    friends     : List of names of samples, to be treated as friend trees. By default this is None and everything will be processed
    main_tree   : Name of tree treated as the main tree when building dataframes with friend trees through `FromSpec`
    skip_adding_columns : By default false. If true, it will skip defining new columns.
    '''
    _user      = os.environ['USER']
    _cache_dir = f'/tmp/{_user}/rx_data/cache/rdf_getter' # Here is where all the temporary output will go

    _max_entries         = -1
    _skip_adding_columns = False

    _custom_versions     : dict[str,str] = {}
    _main_tree           : str

    _default_excluded                 = ['mass']# These friend trees will always be excluded, unless explicitly changed
    _excluded_friends                 = []      # Will not pick up any of the friend trees in this list
    _only_friends : set[str]|None     = None    # Will only pick up the friend trees in this list, if the list is not None
    _d_custom_columns : dict[str,str] = {}
    _allow_multithreading             = False
    _nthreads                         = None
    _identifier : Final[int]          = os.getpid()  # In order to create JSON files with file lists, this string
                                                # will be used to identify those files. This is needed to avoid collisions
                                                # when sending jobs to clusters with shared file systems
    # ---------------------------------------------------
    def __init__(
        self,
        sample  : str,
        trigger : str,
        project : str = 'none',
        tree    : str = 'DecayTree'):
        '''
        Parameters
        ----------------
        sample : Sample's nickname, e.g. DATA_24_MagDown_24c2
        trigger: HLT2 trigger, e.g. Hlt2RD_BuToKpEE_MVA
        project: Project name, if not passed, trigger will be used to deduce project
        tree   : E.g. DecayTree or MCDecayTree, default DecayTree
        '''
        os.makedirs(RDFGetter._cache_dir, exist_ok=True)

        log.debug(f'Process identifier: {RDFGetter._identifier}')

        self._sample          = sample
        self._trigger         = trigger
        self._tree_name       = tree

        if project == 'none':
            log.debug(f'Deducing project from trigger: {trigger}')
            self._project     = info.project_from_trigger(trigger=trigger, lower_case=True) 
        else:
            log.debug(f'Using user defined project: {project}')
            self._project     = project

        self._samples         : dict[str,str]
        self._l_columns       : list[str]
        self._s_ftree         : set[str] # list of friend trees actually used

        self._cfg : DictConfig= self._load_config()
        self._main_tree       = self._get_main_tree()
        self._l_electron_only = self._cfg['trees']['electron_only']
        self._ext_weight      = '(L1_PID_E > 1 && L2_PID_E > 1) ? 1 : 10'

        _l_bu_ee_trigger      = [
            'Hlt2RD_BuToKpEE_MVA',
            'Hlt2RD_BuToKpEE_MVA_cal',
            'Hlt2RD_BuToKpEE_MVA_misid',
            'Hlt2RD_BuToKpEE_MVA_ext',
            'Hlt2RD_BuToKpEE_SameSign_MVA']

        _l_bd_ee_trigger = [
            'Hlt2RD_B0ToKpPimEE_MVA',
            'Hlt2RD_B0ToKpPimEE_MVA_cal',
            'Hlt2RD_B0ToKpPimEE_MVA_misid',
            'Hlt2RD_B0ToKpPimEE_MVA_ext',
            'Hlt2RD_B0ToKpPimEE_SameSign_MVA']

        self._l_ee_trigger  = _l_bd_ee_trigger + _l_bu_ee_trigger

        _l_bu_mm_trigger    = [
            'Hlt2RD_BuToKpMuMu_MVA',
            'Hlt2RD_BuToKpMuMu_SameSign_MVA']

        _l_bd_mm_trigger    = [
            'Hlt2RD_B0ToKpPimMuMu_MVA',
            'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA']

        self._l_mm_trigger  = _l_bd_mm_trigger + _l_bu_mm_trigger

        self._rdf    : RDF.RNode           # This is where the dataframe will be stored, prevents recalculation
        self._d_rdf  : dict[str,RDF.RNode] # This is where the dataframes are stored, when per_file splitting was
                                           # requested. They keys are the main tree file path, the value is the dataframe
                                           # with the main and friend trees

        self._d_info : dict[str,Any] = {} # Used to store information related to transformations done to dataframe (e.g. Range), needed for hashing
        self._l_path : list[str]     = [] # list of paths to all the ROOT files
        self._channel                = self._channel_from_trigger()

        self._set_logs()
        self._check_multithreading()

        self._samples = self._get_json_paths()
    # ---------------------------------------------------
    def _get_main_tree(self) -> str:
        if not hasattr(RDFGetter, '_main_tree'):
            return self._cfg['trees']['main']

        log.warning(f'Overriding main tree with: {RDFGetter._main_tree}')

        return RDFGetter._main_tree
    # ---------------------------------------------------
    def _channel_from_trigger(self) -> str:
        '''
        Returns EE or MM given the HLT2 trigger
        '''
        # noPID files should be assigned same channel as PID files
        trigger = self._trigger.removesuffix('_noPID')

        if trigger in self._l_mm_trigger:
            return 'MM'

        if trigger in self._l_ee_trigger:
            return 'EE'

        raise NotImplementedError(f'Cannot deduce channel from trigger: {self._trigger}')
    # ---------------------------------------------------
    def _load_config(self) -> DictConfig:
        '''
        Loads yaml files with configuration needed to rename and define
        new columns in dataframe
        '''
        cfg_com = gut.load_conf(package='rx_data_data', fpath='rdf_getter/common.yaml')
        cfg_ana = gut.load_conf(package='rx_data_data', fpath=f'rdf_getter/{self._project}.yaml')
        cfg     = OmegaConf.merge(cfg_com, cfg_ana)
        if not isinstance(cfg, DictConfig):
            raise ValueError('Merged config not a DictConfig')

        return cfg
    # ---------------------------------------------------
    def _set_logs(self) -> None:
        '''
        Set log levels of dependent tools to WARNING
        to reduce noise
        '''
        LogStore.set_level('rx_data:path_splitter', 30)
    # ---------------------------------------------------
    def _get_json_paths(self) -> dict[str,str]:
        '''
        This function will return a dictionary with:

        key  : Name of sample, e.g. main, mva
        value: Path to JSON file with the directory structure needed to make an RDataFrame
        '''
        data_dir     = os.environ['ANADIR']
        ftree_wc     = f'{data_dir}/Data/{self._project}/*'
        l_ftree_dir  = glob.glob(ftree_wc)
        if len(l_ftree_dir) == 0:
            raise ValueError(f'No directories with samples found in: {ftree_wc}')

        d_ftree_dir  = { os.path.basename(ftree_dir) : ftree_dir for ftree_dir in l_ftree_dir }
        d_ftree_dir  = self._filter_samples(d_ftree_dir=d_ftree_dir)
        self._s_ftree= { ftree for ftree in list(d_ftree_dir) if ftree != self._main_tree } # These friend trees both exist and are picked up

        log.info(40 * '-')
        log.info(f'{"Friend":<20}{"Version":<20}')
        log.info(40 * '-')
        d_vers_dir   = { ftree_name : self._versioned_from_ftrees(ftree_dir)        for ftree_name, ftree_dir in d_ftree_dir.items() }
        d_json_path  = { ftree_name : self._json_path_from_ftree(dir_path=vers_dir) for ftree_name,  vers_dir in d_vers_dir.items()  }
        log.info(40 * '-')
        log.info('')

        return d_json_path
    # ---------------------------------------------------
    def _versioned_from_ftrees(self, ftree_dir :  str) -> str:
        '''
        Takes path to directory corresponding to a friend tree.
        Finds latest/custom version and returns this path
        '''
        ftree = os.path.basename(ftree_dir)
        if ftree in RDFGetter._custom_versions:
            version     = RDFGetter._custom_versions[ftree]
            version_dir = f'{ftree_dir}/{version}'

            log.warning(f'{ftree:<20}{version:<20}')

            return version_dir

        version = vmn.get_last_version(dir_path=ftree_dir, version_only=True)
        log.info(f'{ftree:<20}{version:<20}')

        return f'{ftree_dir}/{version}'
    # ---------------------------------------------------
    def _json_path_from_ftree(self, dir_path : str) -> str:
        '''
        Takes path to directory with ROOT files associated to friend tree
        returns path to YAML file with correctly structured files
        '''
        l_root_path = glob.glob(f'{dir_path}/*.root')
        nroot_path  = len(l_root_path)
        if nroot_path == 0:
            raise ValueError(f'No ROOT files found in {dir_path}')

        spl  = PathSplitter(paths=l_root_path)
        data = spl.split(nested=True)

        out_path = self._get_tmp_path(identifier='tree_structure', data=data)
        log.debug(f'Saving friend tree structure to {out_path}')
        gut.dump_json(data, out_path)

        return out_path
    # ---------------------------------------------------
    def _check_multithreading(self) -> None:
        '''
        This method will raise if running with mulithreading and if it was not explicitly allowed
        '''
        if RDFGetter._allow_multithreading:
            log.info(f'Using {RDFGetter._nthreads} threads')
            return

        nthreads = GetThreadPoolSize()
        if nthreads > 1:
            raise ValueError(f'Cannot run with mulithreading, using {nthreads} threads')

        log.debug('Not using multithreading')
    # ---------------------------------------------------
    def _filter_samples(self, d_ftree_dir : dict[str,str]) -> dict[str,str]:
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
            path = d_ftree_dir_flt[self._main_tree]
            return {self._main_tree : path}

        raise ValueError(f'Invalid tree name: {self._tree_name}')
    # ---------------------------------------------------
    def _get_trigger_paths(
            self,
            sample    : str,
            ftree     : str,
            d_trigger : dict[str,list[str]]) -> list[str]:
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
        if self._trigger in d_trigger:
            return d_trigger[self._trigger]

        if not self._trigger.endswith('_ext'):
            raise ValueError(f'Invalid trigger name {self._trigger} for sample {sample} and friend tree {ftree}')

        # TODO: When misid trigger be processed also for MC, this has to be updated
        if self._sample.startswith('mc_'):
            trigger = self._trigger.replace('_ext', '')
            log.warning(f'For sample {self._sample} will use {trigger} instead of {self._trigger}')
            return d_trigger[trigger]

        # NOTE: If it was not explicitly stated that this is 2024 data, ext trigger does not make sense
        if not self._sample.startswith('DATA_24'):
            raise ValueError(f'Requested EXT trigger for non-2024 data sample: {self._sample}')

        log.debug(f'Found extended trigger: {self._trigger}')
        trig_misid   = self._trigger.replace('_ext', '_misid')
        trig_channel = self._trigger.replace('_ext',       '')

        l_path = []
        l_path+= d_trigger[trig_channel]
        l_path+= d_trigger[trig_misid  ]

        return l_path
    # ---------------------------------------------------
    def _get_section(
        self,
        json_path : str,
        ftree     : str) -> dict:
        '''
        This method should return the different sections (friend/main tree)
        needed to make the JSON file taken by FromSpec

        Parameters:
        --------------------
        json_path : Path to JSON file specifying samples:trigger:files
        ftree     : Friend tree name, e.g mva, main
        '''
        d_section = {'trees' : [self._tree_name]}

        log.debug(f'Building section from: {json_path}')

        d_data = gut.load_json(path=json_path)
        if d_data is None:
            raise ValueError(f'Cannot load {json_path}')

        l_path = []
        nopath = False
        nosamp = True
        for sample in d_data:
            if not fnmatch.fnmatch(sample, self._sample):
                continue

            nosamp = False
            try:
                d_trigger = d_data[sample]
            except KeyError as exc:
                for sample in d_data:
                    log.info(sample)
                raise KeyError(f'Sample {sample} not found') from exc

            l_path_sample = self._get_trigger_paths(
                d_trigger= d_trigger,
                ftree    = ftree,
                sample   = sample)

            nsamp = len(l_path_sample)
            if nsamp == 0:
                log.error(f'No paths found for {sample} in {json_path} and friend tree {ftree}')
                nopath = True
            else:
                log.debug(f'Found {nsamp} paths for {sample} in {json_path}')

            l_path += l_path_sample

        if nopath:
            raise ValueError('Samples with paths missing')

        if nosamp:
            data = yaml.dump(d_data, sort_keys=False)
            log.error(data)
            raise ValueError(f'Could not find any sample matching {self._sample} with friend tree {ftree} in {json_path}')

        self._l_path      += l_path
        d_section['files'] = l_path

        return d_section
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

        if ftree == self._main_tree: # should always do main tree
            return False

        if ftree in RDFGetter._excluded_friends:
            log.debug(f'Excluding {ftree}')
            return True

        if ftree in RDFGetter._default_excluded:
            log.debug(f'Default excluding {ftree}')
            return True

        if ftree in self._l_electron_only and 'MuMu' in self._trigger:
            log.info(f'Excluding friend tree {ftree} for muon trigger {self._trigger}')
            return True

        if RDFGetter._only_friends is None: # If _only_friends is unset, do not skip current tree
            return False

        # This check is needed to silence pyright error
        # otherwise the line above should be enough
        if RDFGetter._only_friends is not None:
            if ftree not in RDFGetter._only_friends: # If _only_friends was set and ftree is not one of them, skip
                return True

        return False
    # ---------------------------------------------------
    def _get_paths_to_conf(self, per_file : bool) -> dict[str,str]:
        '''
        Parameters
        ----------------------
        per_file : If true will process configs per file, otherwise it will do the full sample

        Returns
        ----------------------
        Dictionary with:

        key  : Path to the main sample ROOT file, i.e. the file that is not the main tree.
               If per_file is False, key will be ''
        value: Path to JSON config file, needed to build dataframe though FromSpec
        '''
        d_data = self._get_samples()
        log.debug(f'This instance/process ID is: {RDFGetter._identifier}')
        if not per_file:
            log.debug('Not splitting per file')
            cfg_path = self._get_tmp_path(identifier='rdframe_config', data=d_data)
            log.debug(f'Saving config path to {cfg_path}')
            gut.dump_json(path=cfg_path, data=d_data, sort_keys=True)

            return {'' : cfg_path}

        log.debug('Splitting per file')
        return self._split_per_file(data=d_data, main=self._main_tree)
    # ---------------------------------------------------
    def _get_samples(self) -> dict[str,dict]:
        '''
        Returns a dictionary with information on the main samples and the friend trees, needed to build dataframes
        '''
        d_data = {'samples' : {}, 'friends' : {}}

        log.info('Adding samples')
        for ftree, json_path in self._samples.items():
            log.debug(f'{"":<4}{ftree:<15}{json_path}')

            d_section = self._get_section(json_path=json_path, ftree=ftree)
            if ftree == self._main_tree:
                d_data['samples'][ftree] = d_section
            else:
                d_data['friends'][ftree] = d_section

        return d_data
    # ---------------------------------------------------
    # TODO: This class is pretty large, all the lines below
    # have one job, adding columns to dataframe, put them in a class
    # ---------------------------------------------------
    def _skip_brem_track_2_definition(self, name: str, definition : str) -> bool:
        '''
        This method checks if this is a brem_track_2 definition. If not, returns False.
        If it is AND if the brem_track_2 tree is missing, return True.

        Parameters
        -------------------
        name      : Name of variable to be defined
        definition: Definition...

        Returns
        -------------------
        True: This definition is not possible, due to absence of brem_track_2
        False: Definition possible
        '''

        if 'brem_track_2' in self._s_ftree:
            log.debug('Not skipping brem_track_2 definitions')
            return False

        # Variables containing these in their definitions, cannot be defined
        # without brem_track_2
        l_substr = ['brem_track_2', '_smr ', 'Jpsi_Mass', 'B_Mass']

        for substr in l_substr:
            # This variable does not depend on this brem_track_2 substring
            if substr not in definition:
                continue

            # Trees do not exist
            if not self._ftree_was_excluded(ftree='brem_track_2'):
                log.warning(f'Skipping definition {name}={definition}')
                return True

            # Trees might exist, but they were excluded by user
            log.debug(f'Skipping definition {name}={definition}')
            return True

        log.debug(f'Not a brem track 2 definition: {definition}')

        return False
    # ---------------------------------------------------
    def _ftree_was_excluded(self, ftree : str) -> bool:
        '''
        Parameters
        -------------
        ftree: Name of friend tree

        Returns
        -------------
        True if the user excluded it
        '''
        if ftree in self._s_ftree:
            return False

        if ftree in RDFGetter._excluded_friends:
            return True

        if RDFGetter._only_friends is None:
            return False

        return ftree not in RDFGetter._only_friends
    # ---------------------------------------------------
    def _add_column(
        self,
        redefine   : bool,
        rdf        : RDF.RNode,
        name       : str,
        definition : str) -> RDF.RNode:
        '''
        Parameters
        ------------------
        redefine  : If true will redefine or else define a dataframe column
        rdf       : ROOT dataframe where columns will be added
        name      : Name of the column to be (re)defined
        definition: Expression to be used in (re)definition
        '''
        # If this is a brem_track_2 dependent definition
        # and the definition is not possible, skip
        if self._skip_brem_track_2_definition(name, definition):
            return rdf

        if redefine:
            log.debug(f'Redefining: {name}={definition}')
            rdf = rdf.Redefine(name, definition)

            return rdf

        if name in self._l_columns:
            raise ValueError(f'Cannot add {name}={definition}, column already found')

        log.debug(f'Defining: {name}={definition}')
        rdf = rdf.Define(name, definition)

        self._l_columns.append(name)

        return rdf
    # ---------------------------------------------------
    def _define_common_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        log.info('Adding common columns')

        d_def = self._cfg['definitions'][self._channel]
        if hasattr(RDFGetter, '_d_custom_columns'):
            log.debug('Adding custom column definitions')
            d_def.update(RDFGetter._d_custom_columns)

        for name, definition in d_def.items():
            rdf = self._add_column(redefine=False, rdf=rdf, name=name, definition=definition)

        # TODO: The weight (taking into account prescale) should be removed
        # for 2025 data
        if self._trigger.endswith('_ext'):
            log.info('Adding weight of 10 to MisID sample')
            rdf = rdf.Define('weight', self._ext_weight)
        else:
            rdf = rdf.Define('weight',              '1')

        return rdf
    # ---------------------------------------------------
    def _define_mc_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        if self._sample.startswith('DATA'):
            log.debug(f'Not adding MC only columns for: {self._sample}')
            return rdf

        log.info('Adding MC only columns')
        d_def = self._cfg.definitions.MC
        for var, expr in d_def.items():
            rdf = self._add_column(redefine=False, rdf=rdf, name=var, definition=expr)

        try:
            rdf = RDFGetter.add_truem(rdf=rdf, cfg=self._cfg)
        except TypeError as exc:
            raise TypeError(f'Cannot add TRUEM branches to {self._sample}/{self._trigger}') from exc

        return rdf
    # ---------------------------------------------------
    def _define_data_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        if not self._sample.startswith('DATA'):
            log.info(f'Not adding data columns for: {self._sample}')
            return rdf

        log.info('Adding data only columns')
        d_def = self._cfg['definitions']['DATA']
        for name, definition in d_def.items():
            rdf = self._add_column(redefine=False, rdf=rdf, name=name, definition=definition)

        return rdf
    # ----------------------
    def _define_temporary_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe

        Returns
        -------------
        Dataframe with new columns defined
        '''
        if 'temporary_definitions' not in self._cfg:
            log.debug('No temporary definitions found')
            return rdf

        log.warning('Found temporary definitions')
        for name, expr in self._cfg.temporary_definitions.items():
            log.debug(f'{name:20}{expr}')
            if name in self._l_columns:
                log.warning('Already defined column')
                log.warning(f'dropping temporary definition: {name}')
                continue

            rdf = rdf.Define(name, expr)

        return rdf
    # ---------------------------------------------------
    def _redefine_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        log.info('Redefining columns')

        d_def = self._cfg['redefinitions']
        for name, definition in d_def.items():
            if name == 'block':
                log.debug('Sending pre-UT candidates to block 0')
            else:
                log.debug(f'Redefining: {name}={definition}')

            rdf = self._add_column(redefine=True, rdf=rdf, name=name, definition=definition)

        return rdf
    # ---------------------------------------------------
    def _add_mcdt_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe symbolizing MCDecatTree

        Returns
        -------------
        Same dataframe with extra variables added
        '''
        log.debug('Adding MCDT columns')

        q2_def = self._cfg['definitions']['MCDT'][self._channel]['q2']
        rdf    = self._add_column(redefine=False, rdf=rdf, name='q2', definition=q2_def)

        return rdf
    # ---------------------------------------------------
    def _add_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        if self._tree_name == 'MCDecayTree':
            rdf = self._add_mcdt_columns(rdf=rdf)
            return rdf

        if self._tree_name != 'DecayTree':
            log.debug(f'Not adding columns to {self._tree_name}')
            return rdf

        rdf = self._define_mc_columns(rdf=rdf)
        rdf = self._define_data_columns(rdf=rdf)

        # Common definitions need to happen after sample specific ones
        # e.g. TRACK_PT needs to be put in place before q2_track
        rdf = self._define_common_columns(rdf=rdf)

        # Redefinitions need to come after definitions
        # Because they might be in function of defined columns
        # E.g. q2 -> Jpsi_Mass
        rdf = self._redefine_columns(rdf=rdf)

        # This should add placeholder branches for columns
        # not yet added to dataframe.
        # It needs to go at the end of function
        rdf = self._define_temporary_columns(rdf=rdf)

        return rdf
    # ---------------------------------------------------
    def _rdf_from_conf(
        self, 
        fpath     : str,
        conf_path : str) -> RDF.RNode:
        '''
        Parameters
        ------------------
        fpath    : Path to ROOT file corresponding to main category
        conf_path: Path to JSON file with configuration needed to build dataframe

        Returns
        ------------------
        Dataframe after some basic preprocessing
        '''
        log.debug(f'Building dataframe from {conf_path} for {fpath}')
        rdf = RDF.Experimental.FromSpec(conf_path)

        nentries = rdf.Count().GetValue()
        if nentries == 0:
            log.warning(f'Found empty dataframe for {fpath}')
            return rdf 

        self._l_columns = [ name.c_str() for name in rdf.GetColumnNames() ]
        log.debug(f'Dataframe at: {id(rdf)}')

        rdf = self._filter_dataframe(rdf=rdf)
        if RDFGetter._skip_adding_columns:
            log.warning('Not adding new columns')
            return rdf
        try:
            rdf = self._add_columns(rdf=rdf)
        except Exception as exc:
            raise ValueError(f'Cannot define columns for: {fpath}') from exc

        return rdf
    # ---------------------------------------------------
    def _filter_dataframe(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ------------
        rdf :  DataFame built from JSON spec file

        Returns
        ------------
        Dataframe after optional filter
        '''
        nent = RDFGetter._max_entries
        if nent < 0:
            return rdf

        ntot = rdf.Count().GetValue()
        if nent > ntot:
            log.warning(f'Required number of entries {nent} larger than dataset size {ntot}')
            return rdf

        log.debug(f'Filtering for a range of {nent} entries')
        # Append information on transformations
        # done to dataframe in order to calculate
        # hash properly
        nlow = ntot - nent
        self._d_info['range'] = nlow, ntot 
        rdf  = rdf.Range(nlow, ntot)

        log.warning(f'Picking up range: [{nlow}, {ntot}] ')

        return rdf
    # ---------------------------------------------------
    def _split_per_file(
        self,
        data       : dict,
        main       : str) -> dict[str,str]:
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
            l_file = data['samples'][main]['files']
        except KeyError as exc:
            pprint.pprint(data)
            raise KeyError('Cannot access list of files from JSON config needed by FromSpec') from exc

        nfiles     = len(l_file)
        d_config   = {}
        for ifile in range(nfiles):
            data_copy, fpath = self._remove_all_but(data, ifile, main)
            config_path      = self._get_tmp_path(identifier='rdframe_config', data=data_copy)
            log.debug(f'Saving per-file config path to {config_path}')
            gut.dump_json(data_copy, config_path)
            d_config[fpath]  = config_path 

        return d_config
    # ----------------------
    @overload
    def get_rdf(self, per_file : Literal[False]) -> RDF.RNode:...
    @overload
    def get_rdf(self, per_file : Literal[True ]) -> dict[str,RDF.RNode]:...
    # ---------------------------------------------------
    def get_rdf(self, per_file :  bool = False ) -> RDF.RNode|dict[str,RDF.RNode]:
        '''
        Returns sample in the form of dataframes

        Parameters
        -----------------
        per_file : Flag controlling returned object

        Returns
        -----------------
        Based on `per_file` flag it will return:

        - A dictionary with the key as the path to the ROOT file and the value as the dataframe
        - The dataframe for the full sample
        '''
        if hasattr(self, '_rdf')   and not per_file:
            log.debug('Returning already calculated dataframe')
            return self._rdf

        if hasattr(self, '_d_rdf') and     per_file:
            log.debug('Returning already calculated dataframe dictionary')
            return self._d_rdf

        # This is a dictionary with:
        #
        # key  : Path to ROOT file from the main sample, if per_file==True. Otherwise empty string
        # Value: Path to config used to build DataFrame
        d_sample = self._get_paths_to_conf(per_file=per_file)
        if per_file:
            log.info('Building one dataframe per file')
            self._d_rdf = { fpath : self._rdf_from_conf(fpath=fpath, conf_path=conf_path) for fpath, conf_path in d_sample.items() }

            return self._d_rdf

        nconf = len(d_sample)
        if nconf != 1:
            raise ValueError(f'Sample-wise config dictionary expects only one entry, found {nconf}')

        _, conf_path = next(iter(d_sample.items()))
        log.debug(f'Building datarame from file {conf_path}')

        self._rdf = self._rdf_from_conf(fpath='joint_files', conf_path=conf_path)

        return self._rdf
    # ---------------------------------------------------
    def get_uid(self) -> str:
        '''
        Retrieves unique identifier for this sample
        Build on top of the UUID from each file
        '''
        if not hasattr(self, '_rdf') and not hasattr(self, '_d_rdf'):
            raise ValueError('get_uid can only be called after get_rdf')

        if len(self._l_path) == 0:
            raise ValueError('No path to ROOT files was found')

        log.debug('Calculating GUUIDs')
        all_guuid = ''
        for path in self._l_path:
            ifile = TFile(path)
            all_guuid += ifile.GetUUID().AsString()
            ifile.Close()

        val = hashing.hash_object([ all_guuid, self._d_info ])
        val = val[:10]

        return val
    # ---------------------------------------------------
    @property
    def friend_trees(self) -> set[str]:
        '''
        Returns
        -----------------
        The list of friend tree names that are
        used for this dataframe, e.g. ['mva', 'hop']
        '''
        return self._s_ftree
    # ---------------------------------------------------
    @staticmethod
    def add_truem(rdf : RDF.RNode, cfg : DictConfig) -> RDF.RNode:
        '''
        Parameters
        -------------------
        rdf: ROOT dataframe associated to MC sample
        cfg: Config with the definitions of branches

        Returns 
        -------------------
        Data frame after adding TRUEM branches missing from the AP
        '''
        log.info('Adding TRUEM branches')

        rdf = rdf.Define('B_TRUEM', cfg.TRUEM.Bu)

        return rdf
    # ---------------------------------------------------
    def _remove_all_but(self, data : dict, ifile : int, main : str) -> tuple[dict,str]:
        '''
        Will:

        - Take the file specification structure `data`
        - Make a local copy
        - Remove all the paths except the ifile th entry
        - Return the copy after removal alongside the path not removed AND beloging to the main sample
        '''

        datac      = copy.deepcopy(data)
        fpath_main = data['samples'][main]['files'][ifile]

        datac['samples'][main]['files'] = [fpath_main]

        data_frnd = data['friends']
        for kind, data_kind in data_frnd.items():
            try:
                fpath_friend = data_kind['files'][ifile]
            except IndexError as exc:
                data_string = yaml.dump(data_kind)
                log.warning(20 * '-')
                log.info(data_string)
                log.warning(20 * '-')
                raise KeyError(f'Cannot retrieve file at {ifile} for friend {kind}, sample {self._sample}/{self._trigger}/{self._tree_name}') from exc

            datac['friends'][kind]['files'] = [fpath_friend]

        return datac, fpath_main
    # ---------------------------------------------------
    def _get_tmp_path(self, identifier : str, data : dict) -> str:
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
        val      = hashing.hash_object(obj=data)
        val      = val[:10]

        # Id of process plus random number 
        proc_id  = self._identifier + secrets.randbelow(1000_000_000) 
        tmp_path = f'{RDFGetter._cache_dir}/{identifier}_{proc_id}_{val}.json'

        log.debug(f'Using config JSON: {tmp_path}')

        return tmp_path
    # ---------------------------------------------------
    @classmethod
    def max_entries(cls, value : int):
        '''
        Contextmanager to limit number of entries in dataframe

        value: number of entries, by default -1 (all). If the value passed is negative, will do all entries
        '''
        @contextmanager
        def _context():
            old_val = cls._max_entries
            cls._max_entries = value

            log.warning(f'Running over at most {cls._max_entries} entries')

            try:
                yield
            finally:
                cls._max_entries = old_val

        return _context()
    # ---------------------------------------------------
    @classmethod
    def skip_adding_columns(cls, value : bool):
        '''
        Contextmanager to control if column (re)definitions from config are used or not

        value: If true it will not define any column in dataframe, i.e. this is what is in the ROOT files, False by default
        '''
        @contextmanager
        def _context():
            old_val = RDFGetter._skip_adding_columns
            try:
                RDFGetter._skip_adding_columns = value
                log.warning('Skipping addition of extra columns to dataframe: {RDFGetter._skip_adding_columns}')
                yield
            finally:
                RDFGetter._skip_adding_columns = old_val

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
    def custom_columns(cls, columns : dict[str,str]):
        '''
        Contextmanager that will define new columns

        key: Name of column
        val: Definition
        '''
        @contextmanager
        def _context():
            old_val = cls._d_custom_columns
            cls._d_custom_columns = copy.deepcopy(columns)
            log.warning('Using custom columns:')
            for key, val in cls._d_custom_columns.items():
                log.info(f'{"":<4}{key:<20}{val}')

            try:
                yield
            finally:
                cls._d_custom_columns = old_val

        return _context()
    # ---------------------------------------------------
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
    def multithreading(cls, nthreads : int):
        '''
        Multithreading should be used with care. This should be the only
        place where multithreading is allowed to be turned on.

        Parameters
        ----------------
        nthreads: Number of threads for EnableImplicitMT. If number
        of threads is 1, multithreading will be off
        '''

        if nthreads <= 0:
            raise ValueError(f'Invalid number of threads: {nthreads}')

        if cls._allow_multithreading:
            raise ValueError(f'Multithreading was already set to {cls._nthreads}, cannot set to {nthreads}')

        @contextmanager
        def _context():
            if nthreads == 1:
                yield
                return

            old_val = cls._allow_multithreading
            old_nth = cls._nthreads

            cls._nthreads             = nthreads
            cls._allow_multithreading = True
            EnableImplicitMT(nthreads)

            try:
                yield
            finally:
                DisableImplicitMT()
                cls._allow_multithreading = old_val
                cls._nthreads             = old_nth

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
