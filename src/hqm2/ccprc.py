import os
import zfit
import numpy
import matplotlib.pyplot as plt
import utils_noroot      as utnr

from importlib.resources import files
from hqm2.data_store     import data_store
from zutils.plot         import plot      as zfp
from fitter              import zfitter
from log_store           import log_store

log=log_store.add_logger('rx_hqm2:ccprc')
#-----------------------------------
class ccprc:
    def __init__(self, obs=None, dset=None, preffix=None, syst=None, qsq_rng=None):
        self._obs   = obs
        self._dset  = dset 
        self._syst  = syst 
        self._pref  = preffix

        [self._qsq_src, self._qsq_tgt] = qsq_rng

        self._fft_npt = 1000
    #---------------------------------
    def _get_trf(self):
        mu      = zfit.param.Parameter(f'mu_trf_{self._pref}', 303, 0, 400)
        sg      = zfit.param.Parameter(f'sg_trf_{self._pref}',  40, 0, 100)
        al      = zfit.param.Parameter(f'al_trf_{self._pref}',-0.2,-1,  +1)
        nt      = zfit.param.Parameter(f'nt_trf_{self._pref}', 110, 0, 150)

        pdf_trf = zfit.pdf.CrystalBall(mu, sg, al, nt, obs=self._obs)

        return pdf_trf
    #---------------------------------
    def _get_muon_pdf(self):
        #TODO: Combinatorial needs to be subtracted
        obj     = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc='data')
        arr_dat = obj.get_array(cuts={'SB' : 'B_M < 5180'})
        zdata   = zfit.Data.from_numpy(self._obs, array=arr_dat)
        pdf_mmd = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, name='data muon')

        return pdf_mmd
    #---------------------------------
    def _get_reso(self):
        mu      = zfit.param.Parameter(f'mu_psi_{self._pref}', 5300, 5200, 5800)
        sg      = zfit.param.Parameter(f'sg_psi_{self._pref}',   40,   10,  500)
        al      = zfit.param.Parameter(f'al_psi_{self._pref}',    1,   -5,    5)
        nt      = zfit.param.Parameter(f'nt_psi_{self._pref}',    1,    0,   20)
        pdf_res = zfit.pdf.CrystalBall(mu, sg, al, nt, obs=self._obs)

        json_path = files('hqm2_data').joinpath(f'fits/psi2S/{self._dset}_ETOS_{self._qsq_tgt}.json')
        json_path = str(json_path)
        if os.path.isfile(json_path):
            log.info(f'Psi2S parameters found, not fitting')
            d_par = utnr.load_json(json_path)
        else:
            log.info(f'Psi2S parameters not found, fitting')
            plot_path = json_path.replace('.json', '.png')
            obj       = data_store(qsq=self._qsq_tgt, dset=self._dset, trig='ETOS', proc='psi2')
            arr_dat   = obj.get_array()
            d_par     = self._get_pars(pdf_res, arr_dat, plot_path)
            utnr.dump_json(d_par, json_path)

        pdf_res = self._fix_pars(pdf_res, d_par)

        return pdf_res
    #---------------------------------
    def _fix_pars(self, pdf, d_par):
        s_par = pdf.get_params(floating=True)

        for par in s_par:
            val = d_par[par.name]
            par.set_value(val)
            par.floating = False
    #---------------------------------
    def _get_pars(self, pdf, arr_dat, plot_path):
        obj=zfitter(pdf, arr_dat)
        res=obj.fit(ntries=10, pval_threshold=0.20) 

        plot_dir = os.path.dirname(plot_path)
        os.makedirs(plot_dir, exist_ok=True)

        obj=zfp(data=arr_dat, model=pdf, result=res)
        obj.plot(plot_range=[5000, 7000])
        plt.savefig(plot_path)
        plt.close('all')

        d_par = dict() 
        for par, d_val in res.params.items():
            d_par[par.name] = d_val['value']

        return d_par
    #---------------------------------
    def _get_ratio(self):
        return 0.6
   #---------------------------------
    def get_pdf(self):
        pdf_res = self._get_reso()
        pdf_trf = self._get_trf()
        pdf_mmd = self._get_muon_pdf()
        r       = self._get_ratio()

        pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_trf, kernel=pdf_mmd, name='PRc', n=self._fft_npt)
        pdf     = zfit.pdf.SumPDF([pdf_prc, pdf_res], r)

        return pdf
#-----------------------------------
