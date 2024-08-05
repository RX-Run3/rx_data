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
        self._d_cns       = None

        self._d_par       = dict()
        self._df_mu       = None
        self._df_sg       = None

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

        self._df_mu = pnd.read_json(mu_path)
        self._df_sg = pnd.read_json(sg_path)
    #----------------------------------
    def _set_pars(self):
        s_par_flt = self._pdf.get_params(floating=True)
        s_par_fix = self._pdf.get_params(floating=False)

        s_par = s_par_flt | s_par_fix
        s_par = self._fix_mc(s_par)
        s_par = self._float_scales(s_par)
        s_par = self._fix_tails(s_par)

        return s_par
    #----------------------------------
    def _fix_mc(self, s_par):
        log.debug(40 * '-')
        log.debug('Fixing MC peak parameters')
        log.debug(40 * '-')
        for par in s_par:
            if '_mc_mc_' not in par.name:
                continue

            par.floating = False
            log.debug(f'{"":<20}{par.name:<20}')

        return s_par
    #----------------------------------
    def _fix_tails(self, s_par):
        log.debug(50 * '-')
        log.debug(f'Setting tails')
        log.debug(50 * '-')
        for par_name, par_value in self._d_par.items():
            if '_mc_mc_' in par_name:
                continue

            if par_name.startswith('nevt_'):
                continue

            par=self._get_par(s_par, par_name)
            par.set_value(par_value)
            par.floating = False

            log.debug(f'{par_name:<20}{"->":10}{par_value:<20.3}')

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

        log.debug(60 * '-')
        log.debug(f'{"Name":<20}{"Value":<20}{"Error":<20}')
        log.debug(60 * '-')
        for name, (val, err) in d_const.items():
            log.debug(f'{name:<20}{val:<20.3f}{err:<20.3f}')

        self._d_cns = d_const
    #----------------------------------
    @property
    def pdf(self):
        self._initialize()

        return self._pdf
    #----------------------------------
    @property
    def constraints(self):
        self._initialize()

        return self._d_cns
#-------------------------------------------
