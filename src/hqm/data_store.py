import os
import ROOT
import glob
import utils
import numpy
import pandas             as pnd
import hashlib
import read_selection     as rs
import version_management as vm

from rk.calc_utility     import addDiffVars as add_vars
from storage.cache       import cache       as scache
from log_store           import log_store
from hqm2.config         import Conf

log = log_store.add_logger('rx_hqm:data_store')
# ----------------------------------
class DataStore:
    '''
    Class used to provide data, simulated or real after full selection
    '''

    def __init__(self, qsq=None, dset=None, trig=None, proc=None):
        self._qsq  = qsq
        self._dset = dset
        self._trig = trig
        self._proc = proc

        self._l_vec_var = ['B_const_mass_M', 'B_const_mass_psi2S_M']
    # ----------------------------------
    def _get_root_wc(self, year):
        d_dir = {
            'data' : 'r_fits',
            'psi2' : 'r_fits',
            'ctrl' : 'r_fits',
            'sign' : 'rare_backgrounds',
            'bpks' : 'rare_backgrounds',
            'bdks' : 'rare_backgrounds',
            'bsph' : 'rare_backgrounds',
        }

        if self._proc is None:
            log.error('Invalid process None')
            raise ValueError

        dat_dir  = d_dir[self._proc]
        asl_dir  = os.environ['ASLDIR']
        ver_dir  = vm.get_last_version(dir_path=f'{asl_dir}/{dat_dir}', version_only=False)
        root_wc  = f'{ver_dir}/{self._proc}/v10.21p2/{year}_{self._trig}/*.root'

        log.info(f'Picking data from {root_wc}')

        return root_wc
    # ----------------------------------
    def _get_year_array(self, year, var_name, d_cut=None):
        root_wc = self._get_root_wc(year=year)
        json_wc = root_wc.replace('.root', '.json')

        l_json  = self._wc_to_list(json_wc)
        l_df    = [ self._df_from_json(json_path) for json_path in l_json ]
        df_cf   = self._merge_cf_df(l_df)

        l_file  = self._wc_to_list(root_wc)
        rdf     = ROOT.RDataFrame(self._trig, l_file)
        rdf     = self._vec_to_float(rdf)
        rdf     = self._define_vars(rdf)
        rdf     = self._apply_selection(rdf, year, d_cut)

        log.debug(f'Picking up {var_name}/{year} from ROOT dataframe')
        arr_val = rdf.AsNumpy([var_name])[var_name]

        df_cf   = pnd.concat([df_cf, rdf.df_cf])
        df_cf.attrs['cut'    ] = df_cf.Cut
        df_cf.attrs['arr_val'] = arr_val

        return df_cf
    # ----------------------------------
    def _define_vars(self, rdf):
        rdf.q2   = 'none'
        rdf.trig = self._trig
        rdf      = add_vars(rdf)
        rdf      = rdf.Define('cbrem', 'xbrem < 2 ? xbrem : 2')

        return rdf
    # ----------------------------------
    def _df_from_json(self, json_path):
        df              = pnd.read_json(json_path)
        sr_cut          = df.Cut
        df              = df.drop(columns=['file', 'tree', 'Cumulative', 'Efficiency', 'Cut'])
        df.attrs['cut'] = sr_cut

        return df
    # ----------------------------------
    def _wc_to_list(self, wc):
        l_file  = glob.glob(wc)
        nfiles  = len(l_file)

        if nfiles == 0:
            log.error(f'No files found in: {wc}')
            raise

        log.debug(f'{nfiles} files found in: {wc}')

        return l_file
    # ----------------------------------
    def _vec_to_float(self, rdf):
        for var_name in self._l_vec_var:
            rdf = rdf.Redefine(var_name, f'{var_name}[0]')

        return rdf
    # ----------------------------------
    def _apply_selection(self, rdf, year, d_cut):
        qsq = rs.get('q2' , self._trig, q2bin=self._qsq, year=year)
        bdt = rs.get('bdt', self._trig, q2bin=self._qsq, year=year)
        rdf = rdf.Filter(qsq, 'QSQ')
        rdf = rdf.Filter(bdt, 'BDT')

        l_cut = [qsq, bdt]
        d_cut = dict() if d_cut is None else d_cut
        for name, cut in d_cut.items():
            rdf  = rdf.Filter(cut, name)
            l_cut.append(cut)

        rep = rdf.Report()
        rep.Print()

        df = utils.rdf_report_to_df(rep)
        df = df.set_index('cut', drop=True)
        df = df.drop(columns=['Efficiency', 'Cummulative'])
        df = df.rename(columns={'All' : 'Total', 'Passed' : 'Pased'})

        df['Cut'] = l_cut
        rdf.df_cf = df

        return rdf
    # ----------------------------------
    def get_rdf(self, variables=None):
        if variables is None:
            log.error('Variables not passed')
            raise ValueError

        d_arr_val = { variable : self.get_array(variable, clean_repeated=False) for variable in variables }
        rdf       = ROOT.RDF.FromNumpy(d_arr_val)

        return rdf
    # ----------------------------------
    def _hash_from_dict(self, d_val):
        hash_gen = hashlib.sha256()
        for val in d_val.values():
            inp = val.encode('utf-8')
            hash_gen.update(inp)

        val = hash_gen.hexdigest()

        return str(val)
    # ----------------------------------
    def get_array(self, variable='B_M', d_cut=None, clean_repeated=False):
        d_cut             = self._update_cuts(d_cut)
        cut_hash          = self._hash_from_dict(d_cut)

        scache.cache_path = Conf.make_path(
            kind ='data',
            block =self._dset,
            trigger=f'{self._qsq}_{self._proc}_{self._trig}',
            fname=f'{variable}_{cut_hash}.json')

        df_cf             = self._calculate_array(variable=variable, d_cut=d_cut)
        arr_val           = df_cf.attrs['arr_val']

        if clean_repeated:
            arr_val = numpy.unique(arr_val)

        if len(arr_val) == 0:
            log.error('Empty array found')
            raise

        return arr_val
    # ----------------------------------
    def _update_cuts(self, d_cut):
        d_cut = dict() if d_cut is None else d_cut
        if len(Conf.binning) == 0:
            return d_cut

        var = Conf.binning['var']
        ibin= Conf.binning['bin']
        cut = Conf.binning['cut']

        #Do not cut in brem category for muon channel
        if var == 'cbrem' and self._trig == 'MTOS':
            return d_cut

        name        = f'{var}_{ibin}'
        d_cut[name] = cut

        log.info(f'Adding cut: {name} -> {cut}')

        return d_cut
    # ----------------------------------
    def _merge_arrays(self, l_df):
        '''
        Merges dataframes with cutflows and the data associated
        in form of numpy arrays
        '''
        l_arr_val     = [ df.attrs['arr_val'] for df in l_df ]
        df_tot        = self._merge_cf_df(l_df     )
        df_tot.arr_val= numpy.concatenate(l_arr_val)

        return df_tot
    # ----------------------------------
    def _merge_cf_df(self, l_df):
        '''
        Takes: List of dataframes with cuts attached as sr_cut and cutflow numbers as content
        Does:  Merges all dataframes by adding  them
        Returns: Merged dataframes
        '''
        df_tot = l_df[0]
        sr_cut = df_tot.attrs['cut']
        l_df   = l_df[1:]

        for df in l_df:
            df_tot = df_tot.add(df)

        df_tot['Cut'] = sr_cut

        return df_tot
    # ----------------------------------
    @scache.cache_selection
    def _calculate_array(self, variable=None, d_cut=None):
        if   self._dset == 'r1':
            df_11 = self._get_year_array('2011', var_name=variable, d_cut=d_cut)
            df_12 = self._get_year_array('2012', var_name=variable, d_cut=d_cut)

            df_mr = self._merge_arrays([df_11, df_12])
        elif self._dset == 'r2p1':
            df_15 = self._get_year_array('2015', var_name=variable, d_cut=d_cut)
            df_16 = self._get_year_array('2016', var_name=variable, d_cut=d_cut)

            df_mr = self._merge_arrays([df_15, df_16])
        elif self._dset == 'comb':
            df_11 = self._get_year_array('2011', var_name=variable, d_cut=d_cut)
            df_12 = self._get_year_array('2012', var_name=variable, d_cut=d_cut)

            df_15 = self._get_year_array('2015', var_name=variable, d_cut=d_cut)
            df_16 = self._get_year_array('2016', var_name=variable, d_cut=d_cut)

            df_17 = self._get_year_array('2017', var_name=variable, d_cut=d_cut)
            df_18 = self._get_year_array('2018', var_name=variable, d_cut=d_cut)

            df_mr = self._merge_arrays([df_11, df_12, df_15, df_16, df_17, df_18])
        else:
            df_mr = self._get_year_array(self._dset, var_name=variable, d_cut=d_cut)

        return df_mr
# ----------------------------------
