'''
Module containing FilterFile class
'''

import os
import glob
import json
import fnmatch
import hashlib
import copy
from typing import Union

import tqdm
import pandas as pnd

from ROOT                  import RDataFrame, TFile, RDF, TObjString
from dmu.logging.log_store import LogStore

import dmu.rdataframe.utilities as ut
import dmu.generic.utilities    as gut
from dmu.rfile.rfprinter   import RFPrinter

import post_ap.utilities as utdc
from post_ap.selector        import Selector
from post_ap.data_vars_adder import DataVarsAdder
from post_ap.mc_vars_adder   import MCVarsAdder
from post_ap.part_vars_adder import ParticleVarsAdder

log = LogStore.add_logger('post_ap:FilterFile')
# --------------------------------------
class FilterFile:
    '''
    Class used to pick a ROOT file path and produce a smaller version
    '''
    # pylint: disable=too-many-instance-attributes
    # --------------------------------------
    def __init__(self, sample_name : str, file_path : str):
        '''
        sample_name : Sample name, e.g. mc_..., data_...
        file_path   : PFN or path to ROOT file
        '''
        self._sample_name  = sample_name
        self._file_path    = file_path

        self.max_run       : int  = -1
        self.max_save      : int  = -1
        self.proc_ntrees   : Union[int,None] = None

        self._cfg_dat      : dict
        self._d_trans      : dict
        self._is_mc        : bool
        self._l_line_name  : list[str]
        self._has_lumitree : bool
        self._store_branch : bool = False
        self._dump_contents: bool = False
        self._d_df_cf      : dict[str, pnd.DataFrame] = {}

        self._initialized  = False
    # --------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._cfg_dat = utdc.load_config()
        self._d_trans = self._cfg_dat['transformations']

        self._check_mcdt()
        self._set_tree_names()
        self._set_save_max()
        self._set_run_max()
        self._set_save_branches()

        self._initialized = True
    # --------------------------------------
    @property
    def dump_contents(self) -> bool:
        '''
        Flag indicating if a text file with the file contents will be saved or only the ROOT file
        '''
        return self._dump_contents

    @dump_contents.setter
    def dump_contents(self, value) -> None:
        if not isinstance(value, bool):
            raise ValueError('Value is not a bool: {value}')

        self._dump_contents = value
    # --------------------------------------
    def _check_mcdt(self):
        '''
        Will set self._is_mc flag based on config name
        '''

        if   self._sample_name.startswith('mc_'):
            self._is_mc = True
        elif self._sample_name.startswith('data_'):
            self._is_mc = False
        else:
            raise ValueError(f'Cannot determine Data/MC from sample name: {self._sample_name}')
    # --------------------------------------
    def _set_save_max(self) -> None:
        if self.max_save > 0:
            log.warning(f'Will save at most {self.max_save} entries')
            return

        if 'evt_max' in self._d_trans['saving']:
            self.max_save = self._d_trans['saving']['evt_max']
            log.warning(f'Will save at most {self.max_save} entries')
            return

        log.info('Saving all entries')
    # --------------------------------------
    def _set_run_max(self) -> None:
        if self.max_run > 0:
            log.warning(f'Will run over at most {self.max_run} entries')
            return

        if 'evt_max' in self._d_trans['selection']:
            self.max_run = self._d_trans['selection']['evt_max']
            log.warning(f'Will run over at most {self.max_run} entries')
            return

        log.info('Running over all entries')
    # --------------------------------------
    def _set_save_branches(self) -> None:
        if 'store_branch' in self._d_trans['saving']:
            self._store_branch = self._d_trans['saving']['store_branch']

        val = 'True' if self._store_branch else 'False'

        log.info(f'Storing branches: {val}')
    # --------------------------------------
    def _get_names_from_config(self) -> list[str]:
        '''
        Will return all the HLT line names from config
        '''
        d_l_name = self._d_trans['hlt_lines']
        l_name   = []
        for val in d_l_name.values():
            l_name += val

        nline = len(l_name)
        log.debug(f'Found {nline} lines in config')

        return l_name
    # --------------------------------------
    def _set_tree_names(self) -> None:
        '''
        Will set the list of line names `self._l_line_name`
        '''
        ifile = TFile.Open(self._file_path)
        l_key = ifile.GetListOfKeys()
        l_nam = [ key.GetName() for key in l_key]
        ifile.Close()

        self._has_lumitree = 'lumiTree' in l_nam

        l_hlt = [ hlt for hlt in l_nam if self._is_reco_dir(hlt) ]
        nline = len(l_hlt)
        log.info(f'Found {nline} lines in file:')
        for line in l_hlt:
            log.debug(f'{"":<10}{line:<30}')

        l_tree_name = self._get_names_from_config()
        l_flt = [ flt for flt in l_hlt if flt in l_tree_name  ]

        nline = len(l_flt)
        if nline == 0:
            log.warning(f'Found {nline} lines in file that match config')
            ifile.ls()
        else:
            log.info(f'Found {nline} lines in file that match config')

        for line in l_flt:
            log.debug(f'{"":<10}{line:<30}')

        if self.proc_ntrees is not None:
            l_flt = l_flt[:self.proc_ntrees]

        self._l_line_name = l_flt
    # --------------------------------------
    def _keep_branch(self, name : str) -> bool:
        '''
        Will take the name of a branch and return True (keep) or False (drop)
        '''
        l_svar = self._d_trans['drop_branches']['starts_with']
        for svar in l_svar:
            if name.startswith(svar):
                return False

        l_svar = self._d_trans['drop_branches']['ends_with']
        for svar in l_svar:
            if name.endswith(svar):
                return False

        l_ivar = self._d_trans['drop_branches']['includes'   ]
        for ivar in l_ivar:
            if ivar in name:
                return False

        return True
    # --------------------------------------
    def _get_column_names(self, rdf : RDataFrame) -> list[str]:
        '''
        Takes dataframe, returns list of column names as strings
        '''
        v_name = rdf.GetColumnNames()
        l_name = [ name.c_str() for name in v_name ]

        return l_name
    # --------------------------------------
    def _rename_branches(self, rdf : RDataFrame) -> RDataFrame:
        '''
        Will define branches from mapping in config. Original branches will be dropped later
        '''
        if 'rename' not in self._d_trans:
            log.info('Not renaming mapped branches')
            return rdf

        d_name = self._d_trans['rename']

        l_name = self._get_column_names(rdf)
        log.debug(110 * '-')
        log.info('Renaming mapped branches')
        log.debug(110 * '-')
        for org, new in d_name.items():
            if org not in l_name:
                log.debug(f'Skipping: {org}')
                continue

            log.debug(f'{org:<50}{"->":10}{new:<50}')
            rdf = rdf.Define(new, org)

        return rdf
    # --------------------------------------
    def _define_branches_all(self, rdf : RDataFrame) -> RDataFrame:
        '''
        Will take dataframe and define columns if "define_all" field found in config
        Returns dataframe
        '''
        if 'define_all' not in self._d_trans:
            log.debug('Not running category-independent definition')
            return rdf

        log.debug(110 * '-')
        log.info('Defining variables')
        log.debug(110 * '-')
        for name, expr in self._d_trans['define_all'].items():
            log.debug(f'{name:<50}{expr:<200}')

            rdf = rdf.Define(name, expr)

        rdf = self._define_kinematics(rdf)

        if not self._is_mc:
            log.info('Adding data only variables')
            obj = DataVarsAdder(rdf)
            rdf = obj.get_rdf()
        else:
            log.info('Adding MC only variables to reconstructed tree')
            obj = MCVarsAdder(rdf_rec = rdf, sample_name = self._sample_name)
            rdf = obj.get_rdf()

        return rdf
    # --------------------------------------
    def _define_branches_cat(self, rdf : RDataFrame, line_name : str) -> RDataFrame:
        '''
        Will define branches per category
        '''
        if 'define' not in self._d_trans:
            log.debug('Not running category-independent definition')
            return rdf

        category = self._get_sel_kind(line_name)
        if category not in self._d_trans['define']:
            log.debug(f'Not running category-independent definition for category: {category}')
            return rdf

        d_def    = self._d_trans['define'][category]

        log.debug(110 * '-')
        log.info(f'Defining variables for: {line_name} ({category})')
        log.debug(110 * '-')
        for name, expr in d_def.items():
            log.debug(f'{name:<50}{expr:<200}')

            rdf = rdf.Define(name, expr)

        return rdf
    # --------------------------------------
    def _define_branches(self, rdf : RDataFrame, line_name : str) -> RDataFrame:
        rdf = self._define_branches_all(rdf)
        rdf = self._define_branches_cat(rdf, line_name)

        return rdf
    # --------------------------------------
    def _define_kinematics(self, rdf : RDataFrame) -> RDataFrame:
        if 'particle_variables' not in self._d_trans:
            log.info('Not defining particle variables')

            return rdf

        d_var = self._d_trans['particle_variables']
        l_var = list(d_var)

        log.info(f'Adding particle variables: {l_var}')
        obj = ParticleVarsAdder(rdf, variables=d_var)
        rdf = obj.get_rdf()

        return rdf
    # --------------------------------------
    def _define_heads(self, rdf : RDataFrame) -> RDataFrame:
        '''
        In datafrme will define columns starting with head in _l_head to B_
        '''
        if 'redefine_head' not in self._d_trans:
            log.info('Not redefining heads')
            return rdf

        log.info('Defining heads')

        d_redef = self._d_trans['redefine_head']
        l_name  = self._get_column_names(rdf)
        for old_head, new_head in d_redef.items():
            l_to_redefine = [ name for name in l_name if name.startswith(old_head) ]
            if len(l_to_redefine) == 0:
                log.debug(f'Head {old_head} not found, skipping')
                continue

            rdf = self._define_head(rdf, l_to_redefine, old_head, new_head)

        return rdf
    # --------------------------------------
    def _define_head(self, rdf : RDataFrame, l_name : list, old_head : str, new_head : str) -> RDataFrame:
        '''
        Will define list of columns with a target head (e.g. B_some_name) from some original head (e.g. Lb_some_name)
        '''

        log.debug(f'Old: {old_head}')
        log.debug(f'New: {new_head}')
        log.debug(155 * '-')
        log.debug(f'{"Old":<70}{"--->":<15}{"New":<70}')
        log.debug(155 * '-')
        for old_name in l_name:
            tmp_name = old_name.removeprefix(old_head)
            new_name = f'{new_head}{tmp_name}'

            log.debug(f'{old_name:<70}{"--->":<15}{new_name:<70}')
            rdf      = rdf.Define(new_name, old_name)

        return rdf
    # --------------------------------------
    def _get_sel_kind(self, line_name : str) -> str:
        d_cat : dict[str,list[str]] = self._d_trans['categories']
        for cat, l_line_name in d_cat.items():
            if line_name in l_line_name:
                return cat

        raise ValueError(f'Cannot find category for line {line_name}')
    # --------------------------------------
    def _get_rdf(self, line_name : str) -> RDataFrame:
        '''
        Will build a dataframe from a given HLT line and return the dataframe
        _get_branches decides what branches are kept
        '''

        log.info(40 * '-')
        log.info(f'Filtering for {line_name}')
        log.info('')

        rdf      = RDataFrame(f'{line_name}/DecayTree', self._file_path)
        rdf      = self._define_heads(rdf)
        rdf      = self._define_branches(rdf, line_name)
        rdf      = self._rename_branches(rdf)
        rdf.lumi = False
        rdf      = self._attach_branches(rdf, line_name)
        l_branch = rdf.l_branch
        ninit    = rdf.ninit
        nfnal    = rdf.nfnal
        norg     = rdf.Count().GetValue()

        rdf  = self._apply_selection(rdf, line_name)
        nfnl = rdf.Count().GetValue()

        log.info('')
        log.info(f'{"Line    ":<20}{"     ":5}{line_name:<20}')
        log.info(f'{"Branches":<20}{ninit:<10}{"->":5}{nfnal:<20}')
        log.info(f'{"Entries ":<20}{norg:<10}{"->":5}{nfnl:<20}')
        log.info('')

        rdf.name     = line_name
        rdf.l_branch = l_branch

        return rdf
    # --------------------------------------
    def _apply_selection(self, rdf : RDataFrame, line_name : str) -> RDataFrame:
        if rdf.lumi:
            return rdf

        if 'cuts' not in self._d_trans['selection']:
            log.info('Not applying any cuts')
            self._store_cutflow(rdf, line_name, skip=True)
            return rdf

        sel_kin = self._get_sel_kind(line_name)
        obj     = Selector(rdf=rdf, is_mc=self._is_mc)
        rdf     = obj.run(sel_kind=sel_kin)

        self._store_cutflow(rdf, line_name)

        return rdf
    # --------------------------------------
    def _store_cutflow(self, rdf : RDataFrame, line_name : str, skip : bool = False):
        if skip:
            self._d_df_cf[line_name] = pnd.DataFrame()

        rep = rdf.Report()
        df  = ut.rdf_report_to_df(rep)

        self._d_df_cf[line_name] = df
    # --------------------------------------
    def _wild_card_filter(self, l_name : list[str]) -> list[str]:
        '''
        Takes list of branch names
        removes only the ones matching wild card
        returns remaining list
        '''

        l_wild_card = self._d_trans['drop_branches']['wild_card']

        l_to_drop = []
        ndrop     = 0
        for wild_card in l_wild_card:
            l_found    = fnmatch.filter(l_name, wild_card)
            if not l_found:
                log.debug(f'No branches dropped for wildcard {wild_card}')
                continue

            ndrop     += len(l_found)
            l_to_drop += l_found

        log.debug(f'Dropping {ndrop} wildcard branches')

        return [ name for name in l_name if name not in l_to_drop ]
    # --------------------------------------
    def _attach_branches(self, rdf : RDataFrame, line_name : str) -> RDataFrame:
        '''
        Will check branches in rdf
        Branches are dropped by:
            - keeping branches in _keep_branch function
            - Removing wildcarded branches in _wild_card_filter functio

        line_name used to name file where branches will be saved.
        '''
        log.debug(110 * '-')
        log.info('Getting list of branches to keep')
        log.debug(110 * '-')

        l_col = self._get_column_names(rdf)
        ninit = len(l_col)
        l_flt = [ flt for flt in l_col if self._keep_branch(flt) ]
        l_flt = self._wild_card_filter(l_flt)
        nfnal = len(l_flt)

        rdf.ninit    = ninit
        rdf.nfnal    = nfnal
        rdf.l_branch = l_flt
        rdf.name     = line_name

        if self._store_branch:
            gut.dump_json(l_flt, f'./{line_name}.json')

        return rdf
    # --------------------------------------
    def _get_out_file_name(self, line_name : str) -> str:
        file_path = self._file_path.encode('utf-8')

        hob = hashlib.sha256(file_path)
        hsh = hob.hexdigest()
        hsh = hsh[:10]

        file_name = f'{self._sample_name}_{line_name}_{hsh}.root'

        # Long names make grid jobs fail, drop stuff not needed, stored in metadata string
        file_name = file_name.replace( '_sim10f_'  , '_')
        file_name = file_name.replace( '_sim10d_'  , '_')
        file_name = file_name.replace(  '_tuple_'  , '_')
        file_name = file_name.replace('_24_w31_34_', '_')
        file_name = file_name.replace('_24_w31_'   , '_')
        file_name = file_name.replace('_24_w32_34_', '_')
        file_name = file_name.replace('_24_w35_37_', '_')
        file_name = file_name.replace('_24_w37_39_', '_')
        file_name = file_name.replace('_24_w40_41_', '_')
        file_name = file_name.replace('_24_w41_42_', '_')
        file_name = file_name.replace('_24_w40_42_', '_')
        file_name = file_name.replace('_hlt1bug_'  , '_')
        file_name = file_name.replace('_pythia8_'  , '_')

        # Remove commas, for sprucing
        file_name = file_name.replace(        ','  ,  '')

        return file_name
    # --------------------------------------
    def _get_snap_opts(self) -> RDF.RSnapshotOptions:
        opts                   = RDF.RSnapshotOptions()
        opts.fMode             = 'update'
        opts.fOverwriteIfExists= True
        opts.fCompressionLevel = self._d_trans['saving']['compression']

        return opts
    # --------------------------------------
    def _filter_save_max_entries(self, rdf : RDataFrame, tree_path : str) -> RDataFrame:
        if self.max_save <= 0:
            log.debug(f'Requested {self.max_save} entries => saving full {tree_path} tree')
            return rdf

        log.warning(f'Saving {tree_path} with at most {self.max_save} entries')
        rdf = rdf.Filter(f'rdfentry_ < {self.max_save}')

        return rdf
    # --------------------------------------
    def _save_file(self, d_rdf : dict[str,RDataFrame]) -> None:
        '''
        Will save all ROOT dataframes to a file
        '''
        opts  = self._get_snap_opts()
        for line_name, rdf in tqdm.tqdm(d_rdf.items(), ascii=' -'):
            l_branch  = rdf.l_branch
            file_path = self._get_out_file_name(line_name)
            rdf       = self._filter_save_max_entries(rdf, 'DecayTree')
            rdf.Snapshot('DecayTree', file_path, l_branch, opts)
            log.debug(f'Saved: {file_path}')

            self._save_contents(file_path)

            l_tree_path = self._get_ext_tree_path()
            for tree_path in l_tree_path:
                self._save_extra_tree(tree_path, file_path, opts, rdf_rec = rdf)

            self._add_metadata(file_path, line_name)
    # --------------------------------------
    def _fail_job(self, tree_path : str) -> None:
        '''
        If this function is called, there was a problem processing the input
        The function will remove the input files and raise an exception to end the job
        Unless the problem is with MCDT_HEADONLY, which is not really needed
        '''
        if tree_path == 'MCDT_HEADONLY/MCDecayTree':
            return

        l_path = glob.glob('*.root')
        for path in l_path:
            log.info(f'Removing: {path}')
            os.remove(path)

        raise RuntimeError(f'Could not save {tree_path}, failing the job')
    # --------------------------------------
    def _save_extra_tree(self,
                         tree_path : str,
                         file_path : str,
                         opts      : RDF.RSnapshotOptions,
                         rdf_rec   : RDataFrame) -> None:
        log.debug(f'Saving {tree_path}')

        try:
            rdf = RDataFrame(tree_path, self._file_path)
        except TypeError:
            log.warning(f'Cannot save: {self._file_path}:{tree_path}')
            self._fail_job(tree_path)
            return

        tree_name = self._get_extra_tree_name(tree_path)

        if tree_path.endswith('MCDecayTree'):
            log.info('Adding MC only variables to generator tree')
            obj = MCVarsAdder(rdf_gen = rdf, rdf_rec=rdf_rec, sample_name=self._sample_name)
            rdf = obj.get_rdf()

        rdf    = self._filter_save_max_entries(rdf, tree_name)
        l_name = self._get_column_names(rdf)
        rdf.Snapshot(tree_name, file_path, l_name, opts)
        log.info(f'Saved {file_path}/{tree_name}')
    # --------------------------------------
    def _get_extra_tree_name(self, tree_path : str) -> str:
        if '/' not in tree_path:
            return tree_path

        if tree_path == 'MCDT/MCDecayTree':
            return 'MCDecayTree'

        if tree_path == 'MCDT_HEADONLY/MCDecayTree':
            return 'MCDecayTree_HO'

        raise ValueError(f'Unrecognized tree path: {tree_path}')
    # --------------------------------------
    def _is_reco_dir(self, dir_name : str) -> bool:
        is_turbo_reco = dir_name.startswith('Hlt2')
        is_spruc_reco = dir_name.startswith('SpruceRD_')

        return is_turbo_reco or is_spruc_reco
    # --------------------------------------
    def _get_ext_tree_path(self) -> list[str]:
        '''
        Will return paths of trees that are not Hlt2
        For data lumiTree, for MC MCDecayTree head only and other
        '''
        ifile = TFile.Open(self._file_path)
        l_key = ifile.GetListOfKeys()
        l_obj = [ key.ReadObj() for key in l_key ]

        l_dir = [ obj for obj in l_obj if   obj.InheritsFrom('TDirectoryFile') ]
        l_dir = [ obj for obj in l_dir if not self._is_reco_dir(obj.GetName()) ]

        l_tre = [ obj for obj in l_obj if obj.InheritsFrom('TTree')          ]

        if len(l_tre) == 1 and len(l_dir) == 0 and not self._is_mc:
            tree = l_tre[0]
            name = tree.GetName()
            ifile.Close()

            return [name]

        if len(l_tre) == 0 and len(l_dir) == 2     and self._is_mc:
            l_name = [ dir_.GetName()        for dir_ in l_dir  ]
            l_name = [ f'{name}/MCDecayTree' for name in l_name ]

            ifile.Close()

            return l_name

        log.warning(f'Cannot find right number of trees in {self._file_path}:')
        for dir_ in l_dir:
            name = dir_.GetName()
            log.info(name)

        return []
    # --------------------------------------
    def _add_metadata(self, file_path : str, line_name : str) -> None:
        log.debug(f'Saving metadata to {file_path}')

        cfg_dat = copy.deepcopy(self._cfg_dat)

        df_cf              = self._d_df_cf[line_name]
        cfg_dat['input']   = self._file_path
        cfg_dat['output']  = file_path
        cfg_dat['cutflow'] = df_cf.to_dict()

        cfg_str = json.dumps(cfg_dat)
        meta    = TObjString(cfg_str)

        ifile   = TFile.Open(file_path, 'update')
        meta.Write('metadata')
        ifile.Close()
    # --------------------------------------
    def _save_contents(self, file_path : str) -> None:
        '''
        Saves textfile with list of branches
        '''
        if not self._dump_contents:
            log.debug('Not saving branch list')
            return

        log.debug('Saving branch list')

        obj = RFPrinter(path = file_path)
        obj.save()
    # --------------------------------------
    @gut.timeit
    def run(self, skip_saving : bool = False) -> None:
        '''
        Will run filtering of files

        skip_saving: By default false, if true, it won't save the ROOT file, useful when testing
        '''
        self._initialize()

        log.info(f'Filtering: {self._file_path}')
        d_rdf = { tree_name : self._get_rdf(tree_name) for tree_name in self._l_line_name }

        if not skip_saving:
            self._save_file(d_rdf)
# --------------------------------------
