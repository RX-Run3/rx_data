'''
Module holding RDFGetter class
'''
import copy
import numpy

from contextlib     import contextmanager
from pathlib        import Path
from typing         import Any, overload, Literal
from ROOT           import RDF, TFile # type: ignore
from dmu            import LogStore
from dmu.generic    import hashing
from dmu.generic    import utilities as gut
from dmu.rdataframe import utilities as rut
from omegaconf      import DictConfig, OmegaConf
from rx_common      import Component, Trigger
from .spec_maker    import SpecMaker
from .rdf_loader    import RDFLoader

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
class RDFGetter(SpecMaker):
    '''
    Class meant to load dataframes with friend trees

    This class has the following attributes:

    max_entries : Limits the number of entries that will be provided
    friends     : List of names of samples, to be treated as friend trees. By default this is None and everything will be processed
    skip_adding_columns : By default false. If true, it will skip defining new columns.
    '''
    _ENABLE_ALIGNMENT_CHECK : bool    = False
    _max_entries                      = -1
    _skip_adding_columns              = False
    _d_custom_columns : dict[str,str] = {}
    # ---------------------------------------------------
    def __init__(
        self,
        sample  : Component,
        trigger : Trigger,
        tree    : str = 'DecayTree'):
        '''
        Parameters
        ----------------
        sample : Sample's nickname, e.g. DATA_24_MagDown_24c2
        trigger: HLT2 trigger, e.g. Hlt2RD_BuToKpEE_MVA
        tree   : E.g. DecayTree or MCDecayTree, default DecayTree
        '''
        super().__init__(component=sample, trigger=trigger, tree=tree)

        log.debug(f'Process identifier: {RDFGetter._identifier}')

        self._trigger         = trigger

        self._l_columns       : list[str]
        self._s_ftree         : set[str] # list of friend trees actually used

        self._cfg : DictConfig= self._load_config()
        self._ext_weight      = '(L1_PIDe > 1 && L2_PIDe > 1) ? 1 : 10'

        self._rdf    : RDF.RNode            # This is where the dataframe will be stored, prevents recalculation
        self._d_rdf  : dict[Path,RDF.RNode] # This is where the dataframes are stored, when per_file splitting was
                                            # requested. They keys are the main tree file path, the value is the dataframe
                                            # with the main and friend trees

        self._d_info : dict[str,Any] = {} # Used to store information related to transformations done to dataframe (e.g. Cuts), needed for hashing

        self._set_logs()
    # ---------------------------------------------------
    def _load_config(self) -> DictConfig:
        '''
        Loads yaml files with configuration needed to rename and define
        new columns in dataframe
        '''
        if   self._project.startswith('rkst'):
            main_project = 'rkst'
        elif self._project.startswith('rk'):
            main_project = 'rk'
        else:
            raise ValueError(f'Invalid project {self._project}')

        log.debug(f'Using config for project: {main_project}')

        cfg_com = gut.load_conf(package='rx_data_data', fpath='rdf_getter/common.yaml')
        cfg_ana = gut.load_conf(package='rx_data_data', fpath=f'rdf_getter/{main_project}.yaml')
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
    # TODO: This class is pretty large, all the lines below
    # have one job, adding columns to dataframe, put them in a class
    # ---------------------------------------------------
    def _skip_smear_definition(self, name: str, definition : str) -> bool:
        '''
        This method will allow to skip definitions that use smear tree branches

        Parameters
        -------------------
        name      : Name of variable to be defined
        definition: Definition...

        Returns
        -------------------
        True: This definition is not possible, due to absence of brem_track_2
        False: Definition possible
        '''
        if 'smear' in self._s_ftree:
            log.debug('Not skipping smear definitions')
            return False

        if 'smear.' not in definition:
            log.debug(f'Not skipping smear definitions for: {name} = {definition}')
            return False

        log.debug(f'Skipping definition of {name}')

        return True
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
        l_substr = ['brem_track_2']

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
        if self._skip_brem_track_2_definition(
            name       = name, 
            definition = definition):

            return rdf

        if self._skip_smear_definition(
            name       = name, 
            definition = definition):

            return rdf

        if redefine:
            log.debug(f'Redefining: {name}={definition}')
            rdf = rdf.Redefine(name, definition)

            return rdf

        if name in self._l_columns:
            log.debug(f'Column {name} already defined, skipping')
            return rdf

        log.debug(f'Defining: {name}={definition}')
        rdf = rdf.Define(name, definition)

        self._l_columns.append(name)

        return rdf
    # ---------------------------------------------------
    def _define_common_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        log.info('Adding common columns')

        d_def : dict[str,str] = self._cfg['definitions'][self._trigger.channel]
        if self._d_custom_columns:
            log.debug('Adding custom column definitions')
            d_def.update(self._d_custom_columns)

        for name, definition in d_def.items():
            rdf = self._add_column(redefine=False, rdf=rdf, name=name, definition=definition)

        # TODO: The weight (taking into account prescale) should be removed
        # for 2025 data
        
        # If doing data with noPID trigger, undo prescale
        # of misID trigger candidates
        if not self._component.is_mc and not self._trigger.has_pid:
            log.info('Adding weight of 10 to MisID sample')
            rdf = rdf.Define('weight', self._ext_weight)
        else:
            rdf = rdf.Define('weight',              '1')

        return rdf
    # ---------------------------------------------------
    def _define_mc_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        if self._cfg_samp.is_data:
            log.debug(f'Not adding MC only columns for: {self._cfg_samp}')
            return rdf

        log.info('Adding MC only columns')
        d_def : dict[str,str] = self._cfg.definitions.MC
        for var, expr in d_def.items():
            rdf = self._add_column(redefine=False, rdf=rdf, name=var, definition=expr)

        try:
            rdf = RDFGetter.add_truem(rdf=rdf, cfg=self._cfg)
        except TypeError as exc:
            raise TypeError(f'Cannot add TRUEM branches to {self._cfg_samp}/{self._trigger}') from exc

        return rdf
    # ---------------------------------------------------
    def _define_data_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        if not self._cfg_samp.is_data:
            log.info(f'Not adding data columns for: {self._cfg_samp}')
            return rdf

        log.info('Adding data only columns')
        d_def : dict[str,str] = self._cfg['definitions']['DATA']
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
        definitions : dict[str,str] = self._cfg.temporary_definitions
        for name, expr in definitions.items():
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

        d_def : dict[str,str] = self._cfg['redefinitions']
        for name, definition in d_def.items():
            if name == 'block':
                log.debug('Sending pre-UT candidates to block 0')
            else:
                log.debug(f'Redefining: {name}={definition}')

            # noPID samples are B-> 3h or B -> 4h, no need to smear these
            # and no smear friend trees available yet
            if name == 'B_Mass_smr' and self._trigger.endswith('_noPID'):
                log.warning(f'Not redefining {name} for trigger {self._trigger}')
                continue

            rdf = self._add_column(
                redefine  = True, 
                rdf       = rdf, 
                name      = name, 
                definition= definition)

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

        q2_def : str = self._cfg['definitions']['MCDT'][self._trigger.channel]['q2']
        rdf    = self._add_column(redefine=False, rdf=rdf, name='q2', definition=q2_def)

        return rdf
    # ---------------------------------------------------
    def _add_patching_redefinitions(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Adds block patching definition of `_block`
        '''
        patching_cpp_code = rut.get_sample_definer_expression(samples = self._spec.ranges.root)

        rdf = rdf.DefinePerSample('_block', patching_cpp_code)
        # NOTE: This -999 is in specification.py
        rdf = rdf.Redefine('block', '_block == -999 ? block : _block')

        return rdf
    # ---------------------------------------------------
    def _add_columns(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Adds and redefines columns (e.g. block patching) to dataframe
        '''
        if self._component.is_mc:
            # NOTE:Do not patch data
            rdf = self._add_patching_redefinitions(rdf = rdf)

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
        fpath     : Path | str,
        conf_path : Path) -> RDF.RNode:
        '''
        Parameters
        ------------------
        fpath    : Path to ROOT file corresponding to main category or 'joint_files' string when doing the full sample
        conf_path: Path to JSON file with configuration needed to build dataframe

        Returns
        ------------------
        Dataframe after some basic preprocessing
        '''
        log.debug(f'Building dataframe from {conf_path} for {fpath}')

        rdf = RDFLoader.from_conf(
            ntries = 10,
            wait   = 30,
            path   = conf_path)
        
        nentries = rdf.Count().GetValue()
        if nentries == 0:
            log.warning(f'Found empty dataframe for {fpath}')
            return rdf 

        self._l_columns = [ name.c_str() for name in rdf.GetColumnNames() ]
        log.debug(f'Dataframe at: {id(rdf)}')

        rdf = self._filter_dataframe(rdf=rdf)
        if self._skip_adding_columns:
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
        nent = self._max_entries
        if nent < 0:
            return rdf

        ntot = rdf.Count().GetValue()
        if nent > ntot:
            log.warning(f'Required number of entries {nent} larger than dataset size {ntot}')
            return rdf

        log.debug(f'Filtering for a range of {nent} entries')
        self._d_info['range'] = 0, nent 
        rdf  = rdf.Filter(f'rdfentry_ < {nent}')

        log.warning(f'Picking up range: [{0}, {nent}] ')

        return rdf
    # ----------------------
    @overload
    def get_rdf(self, per_file : Literal[False]) -> RDF.RNode:...
    @overload
    def get_rdf(self, per_file : Literal[True ]) -> dict[Path,RDF.RNode]:...
    # ---------------------------------------------------
    def get_rdf(self, per_file :  bool = False ) -> dict[Path,RDF.RNode] | RDF.RNode:
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

        if per_file:
            d_sample = self.get_spec_path(per_file=per_file)
            log.info('Building one dataframe per file')
            d_rdf       = { fpath : self._rdf_from_conf(fpath=fpath, conf_path=conf_path) for fpath, conf_path in d_sample.items() }
            d_rdf       = { fpath : self._emulator.post_process(rdf=rdf)                  for fpath, rdf       in d_rdf.items() }
            self._d_rdf = { fpath : self._check_rdf(rdf = rdf)                            for fpath, rdf       in d_rdf.items() }

            return self._d_rdf

        conf_path = self.get_spec_path(per_file=per_file)
        self._rdf = self._rdf_from_conf(fpath='joint_files', conf_path=conf_path)

        if self._tree_name == 'DecayTree':
            rdf = self._emulator.post_process(rdf=self._rdf)
        else:
            rdf = self._rdf
            log.info(f'Not emulating tree: {self._tree_name}')

        rdf = self._check_rdf(rdf = rdf)

        return rdf
    # ----------------------
    def _check_rdf(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe

        Returns
        -------------
        ROOT dataframe after checks
        '''
        if self._tree_name == 'MCDecayTree':
            log.debug(f'Skipping alignment check for: {self._tree_name}')
            return rdf

        self.check_alignment(rdf = rdf, index = 'EVENTNUMBER')
        self.check_alignment(rdf = rdf, index = 'RUNNUMBER')

        return rdf
    # ----------------------
    @classmethod
    def check_alignment(
        cls,
        rdf    : RDF.RNode,
        index  : str) -> None:
        '''
        Method used to check alignment of indexes

        Parameters
        -------------
        rdf   : ROOT dataframe
        index : Name of column whose values need to be aligned
        '''
        if not cls._ENABLE_ALIGNMENT_CHECK:
            return

        columns = [ name.c_str() for name in rdf.GetColumnNames() ]
        indexes = [ name         for name in columns if index in name ]
        ncol    = len(indexes)

        log.info(f'Checking {ncol} columns for {index}')

        rdf_small = rdf.Filter('rdfentry_ < 100')

        data    = rdf_small.AsNumpy(indexes)
        arrays  = [ array for array in data.values() ]
        aligned = all( numpy.array_equal(array, arrays[0]) for array in arrays)

        if not aligned:
            for name, values in data.items():
                log.info('----------')
                log.info(name)
                log.info('----------')
                log.info(values[:10])
            raise ValueError(f'{index} columns are not aligned')

        log.info(f'Checked {index}')
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
            path_str   = str(path)
            ifile      = TFile(path_str)
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

        definition : str = cfg.TRUEM.B_mass
        if not isinstance(definition, str):
            raise ValueError('True B mass definition is not a string')

        rdf = rdf.Define('B_TRUEM', definition)

        return rdf
    # ---------------------------------------------------
    # Context managers
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

            if cls._max_entries != -1:
                log.warning(f'Running over at most {cls._max_entries} entries')
            else:
                log.warning('Running over all entries')

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
    def alignment_check(cls):
        '''
        Context manager that turns on alignment check
        needed for tests
        '''
        old_val = cls._ENABLE_ALIGNMENT_CHECK

        @contextmanager
        def _context():
            cls._ENABLE_ALIGNMENT_CHECK = True

            try:
                yield
            finally:
                cls._ENABLE_ALIGNMENT_CHECK = old_val

        return _context()
# ---------------------------------------------------
