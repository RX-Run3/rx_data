import os
import pprint
import pandas       as pnd
import utils_noroot as utnr

from version_management  import get_last_version 
from log_store           import log_store
from importlib.resources import files

log=log_store.add_logger('rx_hqm2:par_setter')
#-------------------------------------------
class par_setter:
    '''
    Class used to set values of parameters of signal PDF before been used to fit data
    It also should provide dictionary of contraints on parameters
    '''
    def __init__(self, pdf):
        self._pdf         = pdf

        self._dset        = None
        self._trig        = None
        self._syst        = None

        self._d_cns       = dict() 
        self._d_par       = dict()
        self._df_mu       = None
        self._df_sg       = None
        self._df_br       = None

        self._initialized = False
    #----------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._extract_pdf_info()
        self._load_pars()
        self._load_scales()

        s_par = self._set_pars()
        self._build_constraints(s_par)

        self._initialized = True
    #----------------------------------
    def _extract_pdf_info(self):
        self._dset = self._pdf.dset
        self._trig = self._pdf.trig
        self._syst = self._pdf.syst
    #----------------------------------
    def _load_pars(self):
        log.debug('Loading parameters')

        pars_path = files('hqm2_data').joinpath(f'mc_pars/{self._dset}_{self._trig}.json')
        if not os.path.isfile(pars_path):
            log.error(f'File not found: {pars_path}')
            raise

        self._d_par = utnr.load_json(pars_path)
    #----------------------------------
    def _load_scales(self):
        mon_dat = files('monitor_data')
        mon_dir = get_last_version(dir_path=mon_dat, version_only=False)
        log.debug(f'Picking up scales from: {mon_dir}')

        mu_path = f'{mon_dir}/mu.json'
        sg_path = f'{mon_dir}/sg.json'
        br_path = f'{mon_dir}/br.json'

        self._df_mu = pnd.read_json(mu_path)
        self._df_sg = pnd.read_json(sg_path)
        self._df_br = pnd.read_json(br_path)
    #----------------------------------
    def _set_pars(self):
        s_par_flt = self._pdf.get_params(floating=True)
        s_par_fix = self._pdf.get_params(floating=False)

        s_par = s_par_flt | s_par_fix
        s_par = self._set_fix_mc(s_par)
        s_par = self._float_scales(s_par)
        s_par = self._set_fix_mc_brem(s_par)
        s_par = self._set_dt_brem(s_par)

        return s_par
    #----------------------------------
    def _set_fix_mc_brem(self, s_par):
        if self._trig == 'MTOS':
            return s_par

        fz_par = self._get_par(s_par, f'fr_mc_z_mc_fit_{self._dset}_{self._trig}')
        fo_par = self._get_par(s_par, f'fr_mc_o_mc_fit_{self._dset}_{self._trig}')
        ft_par = self._get_par(s_par, f'fr_mc_t_mc_fit_{self._dset}_{self._trig}')

        fr_mc_z, fr_mc_o, fr_mc_t = self._get_mc_brem_frac()

        fz_par.set_value(fr_mc_z)
        fo_par.set_value(fr_mc_o)
        ft_par.set_value(fr_mc_t)

        fz_par.floating = False
        fo_par.floating = False
        ft_par.floating = False

        return s_par
    #----------------------------------
    def _set_dt_brem(self, s_par):
        if self._trig == 'MTOS':
            return s_par

        fz_par = self._get_par(s_par, f'fr_sc_z_mc_fit_{self._dset}_{self._trig}')
        fo_par = self._get_par(s_par, f'fr_sc_o_mc_fit_{self._dset}_{self._trig}')
        ft_par = self._get_par(s_par, f'fr_sc_t_mc_fit_{self._dset}_{self._trig}')

        fr_mc_z, fr_mc_o, fr_mc_t = self._get_brem_scale(value=True)

        fz_par.set_value(fr_mc_z)
        fo_par.set_value(fr_mc_o)
        ft_par.set_value(fr_mc_t)

        fz_par.floating = True 
        fo_par.floating = True 
        ft_par.floating = True 

        return s_par
    #----------------------------------
    def _get_mc_brem_frac(self):
        nbrem_z = self._d_par[f'nevt_{self._dset}_{self._trig}_brem_0']
        nbrem_o = self._d_par[f'nevt_{self._dset}_{self._trig}_brem_1']
        nbrem_t = self._d_par[f'nevt_{self._dset}_{self._trig}_brem_2']

        fr_mc_z = nbrem_z / (nbrem_z + nbrem_o + nbrem_t)
        fr_mc_o = nbrem_o / (nbrem_z + nbrem_o + nbrem_t)
        fr_mc_t = nbrem_t / (nbrem_z + nbrem_o + nbrem_t)

        return fr_mc_z, fr_mc_o, fr_mc_t
    #----------------------------------
    def _get_brem_scale(self, value=True):
        kind = {True: 'v' , False : 'e'}[value]

        fr_z = self._df_br[f'{kind}_0'].loc[f'{self._trig} {self._dset}']
        fr_o = self._df_br[f'{kind}_1'].loc[f'{self._trig} {self._dset}']
        fr_t = self._df_br[f'{kind}_2'].loc[f'{self._trig} {self._dset}']

        return fr_z, fr_o, fr_t
    #----------------------------------
    def _set_fix_mc(self, s_par):
        log.debug(60 * '-')
        log.debug(f'Setting MC parameters')
        log.debug(60 * '-')
        for par_name, par_value in self._d_par.items():
            if par_name.startswith('nevt_'):
                continue

            par=self._get_par(s_par, par_name)
            par.set_value(par_value)
            par.floating = False

            log.debug(f'{par_name:<40}{"->":10}{par_value:<10.3}')

        return s_par
    #----------------------------------
    def _get_par(self, s_par, par_name):
        try:
            [par] = [par for par in s_par if par.name == par_name]
        except:
            log.error(f'Parameter {par_name} not found among:')
            for par in s_par:
                log.info(par.name)

            raise

        return par
    #----------------------------------
    def _float_scales(self, s_par):
        log.debug(40 * '-')
        log.debug('Floating resolutions and scales')
        log.debug(40 * '-')

        for par in s_par:
            is_resol = par.name.startswith('rs_')
            is_scale = par.name.startswith('sc_')

            if is_resol or is_scale:
                par.floating = True 
                log.debug(f'{"":<20}{par.name:<20}')

        return s_par
    #----------------------------------
    def _build_constraints(self, s_par):
        d_const_m = self._get_mass_constraints(s_par)
        d_const_b = self._get_brem_constraints(s_par)
        self._d_cns.update(d_const_m) 
        self._d_cns.update(d_const_b) 

        log.debug(70 * '-')
        log.debug(f'{"Name":<40}{"Value":<15}{"Error":<15}')
        log.debug(70 * '-')
        for name, (val, err) in self._d_cns.items():
            log.debug(f'{name:<40}{val:<15.3f}{err:<15.3f}')
    #----------------------------------
    def _get_brem_constraints(self, s_par):
        sc_vz, sc_vo, sc_vt = self._get_brem_scale(value=True)
        sc_ez, sc_eo, sc_et = self._get_brem_scale(value=False)

        d_const = dict()
        d_const[f'fr_sc_z_mc_fit_{self._dset}_{self._trig}'] = sc_vz, sc_ez
        d_const[f'fr_sc_o_mc_fit_{self._dset}_{self._trig}'] = sc_vo, sc_eo
        d_const[f'fr_sc_t_mc_fit_{self._dset}_{self._trig}'] = sc_vt, sc_et

        return d_const
    #----------------------------------
    def _get_mass_constraints(self, s_par):
        sc_v=self._df_mu[f'v_{self._trig}'].loc[self._dset]
        sc_e=self._df_mu[f'e_{self._trig}'].loc[self._dset]

        rs_v=self._df_sg[f'v_{self._trig}'].loc[self._dset]
        rs_e=self._df_sg[f'e_{self._trig}'].loc[self._dset]

        [sc]= [ par for par in s_par if par.name.startswith('sc_') ]
        [rs]= [ par for par in s_par if par.name.startswith('rs_') ]

        d_const = {
                sc.name : (sc_v, sc_e),
                rs.name : (rs_v, rs_e),
                }

        return d_const
    #----------------------------------
    def pdf(self, brem=None):
        self._initialize()

        if brem is None:
            return self._pdf

        if brem not in [0, 1, 2]:
            log.error(f'Invalid value of brem arg: {brem}')
            raise

        l_pdf = self._pdf.models

        return l_pdf[brem]
    #----------------------------------
    def constraints(self, brem=None):
        self._initialize()

        if brem is None:
            return self._pdf

        if brem not in [0, 1, 2]:
            log.error(f'Invalid value of brem arg: {brem}')
            raise

        l_pdf = self._pdf.models
        pdf   = l_pdf[brem]
        s_par = pdf.get_params(floating=True)
        l_par = [ par.name for par in s_par ]
        d_cns = { name : value for name, value in self._d_cns.items()  if name in l_par }

        return d_cns
#-------------------------------------------

