import os
import ROOT
import zfit
import numpy
import hqm2.model    as mod
import zutils.utils  as zut
import utils_noroot  as utnr
import matplotlib.pyplot as plt

from hqm2.data_store     import data_store
from hqm2.config         import Conf
from hqm2.wgtc           import wgtc

from importlib.resources import files
from log_store           import log_store

log=log_store.add_logger('rx_hqm2:pdfmc')
#------------------------------------
class pdfmc:
    '''
    This class is meant to provide PDFs with a fixed shape made from MC samples
    after the full selection and corrections for mass scales and resolutions calculated with data.
    '''
    #------------------------------------
    def __init__(self, obs=None, dset=None, proc=None, qsq=None):
        self._obs    = obs
        self._dset   = dset
        self._proc   = proc
        self._trig   = 'ETOS'
        self._qsq    = qsq

        self._pdf_suf     = None
        self._bin_suf     = None
        self._pdf         = None
        self._wrange      = None
        self._prange      = None
        self._out_dir     = None
        self._initialized = False
    #------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._out_dir=Conf.make_data_path(kind='fits', dset=self._dset, dname=f'{self._proc}_{self._trig}_{self._qsq}', fname=None)

        self._set_pdf_suffix()
        self._set_ranges()
        self._set_pdf()

        self._initialized = True
    #------------------------------------
    def _set_pdf_suffix(self):
        pdf_suf= f'mc_{self._proc}_{self._dset}_{self._qsq}'
        if len(Conf.binning) == 0:
            self._bin_suf = None
            self._pdf_suf = pdf_suf
            return

        varn = Conf.binning['var']
        ibin = Conf.binning['bin']

        self._bin_suf = f'{varn}_{ibin}'
        self._pdf_suf = f'{pdf_suf}_{self._bin_suf}'
    #------------------------------------
    def _set_pdf(self):
        if   self._proc == 'ctrl' and self._qsq != 'high':
            self._pdf = mod.get_dscb(self._pdf_suf, self._obs)
        elif self._proc == 'psi2' and self._qsq == 'high':
            self._pdf = mod.get_cb(self._pdf_suf, self._obs)
        elif self._proc == 'psi2' and self._qsq == 'psi2':
            self._pdf = mod.get_sujh_2cb(self._pdf_suf, self._obs)
        elif self._proc == 'psi2' and self._qsq == 'jpsi':
            self._pdf = mod.get_dscb(self._pdf_suf, self._obs)
        elif self._proc == 'ctrl' and self._qsq == 'high':
            self._pdf = mod.get_cb(self._pdf_suf, self._obs)
        else:
            log.error(f'Invalid process/qsq: {self._proc}/{self._qsq}')
            raise
    #------------------------------------
    def _set_ranges(self):
        if   self._proc == 'ctrl' and self._qsq != 'high':
            self._wrange = [4500, 6000]
            self._prange = [4500, 6000]
        elif self._proc == 'psi2' and self._qsq == 'psi2':
            self._wrange = [5000, 5350]
            self._prange = [4500, 5500]
        elif self._proc == 'psi2' and self._qsq == 'jpsi':
            self._wrange = [5000, 5310]
            self._prange = [4500, 5310]
        elif self._proc == 'psi2' and self._qsq == 'high':
            self._wrange = None
            self._prange = [5000, 6400]
        elif self._proc == 'ctrl' and self._qsq == 'high':
            self._wrange = None
            self._prange = [5500, 7000]
        else:
            log.error(f'Invalid process/qsq: {self._proc}/{self._qsq}')
            raise
    #------------------------------------
    def _get_weight_rdf(self, proc=None):
        obj     = data_store(qsq=self._qsq, dset=self._dset, trig=self._trig, proc=proc)
        rdf     = obj.get_rdf(variables=['B_M', 'B_const_mass_M', 'B_const_mass_psi2S_M'])

        return rdf
    #------------------------------------
    def _get_weights(self, arr_mas):
        if self._skip_weights():
            return

        rdf_dt = self._get_weight_rdf(proc=    'data')
        rdf_mc = self._get_weight_rdf(proc=self._proc)

        obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc, proc=self._proc, mrange=self._wrange)
        obj.out_dir = f'{self._out_dir}/weights'
        arr_wgt     = obj.get_weights(arr_mas=arr_mas)

        return arr_wgt
    #------------------------------------
    def _skip_weights(self):
        '''
        Will skip data driven scale and resolution weights if modelling high-q2 bin
        Will not skip weights if integrated OR if getting Jpsi shape in Jpsi bin
        '''
        if self._qsq == 'high':
            return True

        if len(Conf.binning) == 0:
            return False

        if self._proc == 'ctrl' and self._qsq == 'jpsi':
            return False

        log.warning(f'Skipping weights for proc/qsq: {self._proc}/{self._qsq}')

        return True
    #------------------------------------
    def _get_pdf_pars(self, arr_mas, arr_wgt):
        if self._proc == 'psi2' and self._qsq == 'jpsi':
            log.warning(f'Dropping weights for fit')
            arr_wgt = None

        zdt   = zfit.Data.from_numpy(obs=self._obs, array=arr_mas, weights=arr_wgt)

        zut.print_pdf(self._pdf, txt_path=f'{self._out_dir}/pdf.txt')

        if arr_wgt is None:
            title=None
        else:
            title=f'Unweighed: {arr_mas.size}; Weighed: {numpy.sum(arr_wgt):.0f}'

        plot_path = f'{self._out_dir}/fit.png'
        d_plt_opt = {'title' : title, 'plot_path' : plot_path, 'plot_range' : self._prange, 'skip_pulls' : True , 'stacked' : False}
        d_par     = zut.get_fit_pars(self._pdf, zdt, d_plt_opt=d_plt_opt, d_fit_opt=Conf.fitting)

        return d_par
    #------------------------------------
    def _fix_pdf_pars(self, json_path):
        d_par = utnr.load_json(json_path)
        d_par = self._rename_pars(d_par=d_par, suffix='add')
        zut.fix_pars(self._pdf, d_par)
    #------------------------------------
    def _rename_pars(self, d_par=None, suffix=None):
        if self._bin_suf is None:
            return d_par

        if   suffix == 'add':
            d_par_new = { f'{key}_{self._bin_suf}'             : val for key, val in d_par.items() }
        elif suffix == 'remove':
            d_par_new = { key.replace(f'_{self._bin_suf}', '') : val for key, val in d_par.items() }
        else:
            log.error(f'Invalid argument: {suffix}')
            raise

        return d_par_new
    #------------------------------------
    def get_pdf(self):
        self._initialize()

        json_path = f'{self._out_dir}/pars.json'
        samp_info = f'{self._proc}_{self._dset}_{self._qsq}'
        if os.path.isfile(json_path):
            log.info(f'File with parameters for {samp_info} found, loading {json_path}')
            self._fix_pdf_pars(json_path)
            return self._pdf

        log.info(f'File with parameters for {samp_info} not found, fitting')

        [minm, maxm] = self._prange

        obj     = data_store(qsq=self._qsq, dset=self._dset, trig=self._trig, proc=self._proc)
        arr_mas = obj.get_array(clean_repeated=True)
        arr_wgt = self._get_weights(arr_mas)

        d_par   = self._get_pdf_pars(arr_mas, arr_wgt)
        d_par   = self._rename_pars(d_par=d_par, suffix='remove')
        utnr.dump_json(d_par, json_path)

        self._fix_pdf_pars(json_path)

        return self._pdf
#------------------------------------

