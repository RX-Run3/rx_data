import os
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

        self._set_pars()
        self._build_constraints()

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
        return
    #----------------------------------
    def _build_constraints(self):
        return
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
