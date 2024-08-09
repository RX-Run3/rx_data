import os
import ROOT
import zfit
import hqm2.model    as mod
import zutils.utils  as zut
import utils_noroot  as utnr 

from importlib.resources import files
from hqm2.data_store     import data_store
from hqm2.wgtc           import wgtc 
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
        self._mrange = [4500, 6000]
        self._pdf_suf= f'mc_{proc}_{dset}_{qsq}'

        self._out_dir     = None
        self._initialized = False
    #------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._out_dir = files('hqm2_data').joinpath(f'fits/{self._proc}/{self._dset}_{self._trig}_{self._qsq}')
        os.makedirs(self._out_dir, exist_ok=True)

        self._initialized = True
    #------------------------------------
    def _get_weight_rdf(self, proc=None):
        obj     = data_store(qsq=self._qsq, dset=self._dset, trig=self._trig, proc=proc)
        arr_cns = obj.get_array(variable='B_const_mass_M')
        arr_raw = obj.get_array(variable='B_M')

        d_data  = {'B_const_mass_M' : arr_cns, 'B_M' : arr_raw}
        rdf     = ROOT.RDF.FromNumpy(d_data)

        return rdf
    #------------------------------------
    def _get_weights(self, arr_mas):
        rdf_dt = self._get_weight_rdf(proc=    'data')
        rdf_mc = self._get_weight_rdf(proc=self._proc)

        obj         = wgtc(rdf_dt=rdf_dt, rdf_mc=rdf_mc, mrange=self._mrange)
        obj.out_dir = f'{self._out_dir}/weights'
        arr_wgt     = obj.get_weights(arr_mas=arr_mas)

        return arr_wgt
    #------------------------------------
    def _build_pdf(self, arr_mas, arr_wgt):
        zdt   = zfit.Data.from_numpy(obs=self._obs, array=arr_mas, weights=arr_wgt)
        pdf   = mod.get_dscb(self._pdf_suf, self._obs)

        zut.print_pdf(pdf, txt_path=f'{self._out_dir}/pdf.txt')

        plot_path = f'{self._out_dir}/fit.png'
        d_plt_opt = {'plot_path' : plot_path, 'plot_range' : self._mrange, 'skip_pulls' : True , 'stacked' : False}
        d_fit_opt = {'ntries' : 5, 'pval_threshold' : 0.05}
        d_par     = zut.get_fit_pars(pdf, zdt, d_plt_opt=d_plt_opt, d_fit_opt=d_fit_opt)

        return pdf, d_par
    #------------------------------------
    def _pdf_from_pars(self, json_path):
        d_par = utnr.load_json(json_path)
        pdf   = mod.get_dscb(self._pdf_suf, self._obs)
        pdf   = zut.fix_pars(pdf, d_par)

        return pdf
    #------------------------------------
    def get_pdf(self):
        self._initialize()

        json_path = f'{self._out_dir}/pars.json'
        if os.path.isfile(json_path):
            log.info(f'File with parameters found, loading it')
            pdf = self._pdf_from_pars(json_path)
            return pdf

        log.info(f'File with parameters not found, fitting')
        minm, maxm = self._mrange

        obj      = data_store(qsq=self._qsq, dset=self._dset, trig=self._trig, proc=self._proc)
        arr_mas  = obj.get_array(d_cut={'mass' : f'B_M > {minm} & B_M < {maxm}'})
        arr_wgt  = self._get_weights(arr_mas)
        pdf, d_par = self._build_pdf(arr_mas, arr_wgt)

        utnr.dump_json(d_par, json_path)

        return pdf
#------------------------------------

