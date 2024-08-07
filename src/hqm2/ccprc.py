import os
import zfit
import numpy
import matplotlib.pyplot as plt
import utils_noroot      as utnr
import zutils.utils      as zut

from hqm2.data_store     import data_store
from hqm2.trfc           import trfc

from importlib.resources import files
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
        self._bw_mumu = 15
        self._low_sb  = 5180

        self._proc_trf= 'psi2'
    #---------------------------------
    def _get_muon_pdf(self):
        #TODO: Combinatorial needs to be subtracted
        json_path = files('hqm2_data').joinpath(f'fits/data/{self._dset}_MTOS_{self._qsq_tgt}_lowsb.json')
        json_path = str(json_path)
        if os.path.isfile(json_path):
            log.info(f'Low sideband muon data found, loading')

            l_mass  = utnr.load_json(json_path)
            zdata   = zfit.Data.from_numpy(self._obs, array=numpy.array(l_mass))
            pdf_mmd = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bw_mumu, name='data muon')
        else:
            log.info(f'Low sideband muon data not found, getting it')

            obj       = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc='data')
            arr_dat   = obj.get_array(d_cut={'SB' : f'B_M < {self._low_sb}'})
            l_mass    = arr_dat.tolist()
            utnr.dump_json(l_mass, json_path)

            zdata     = zfit.Data.from_numpy(self._obs, array=arr_dat)
            pdf_mmd   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bw_mumu, name='data muon')

            obj=zfp(data=arr_dat, model=pdf_mmd, result=None)
            obj.plot(plot_range=[4200, self._low_sb])

            plot_path = json_path.replace('.json', '.png')
            plot_dir  = os.path.dirname(plot_path)
            os.makedirs(plot_dir, exist_ok=True)
            plt.savefig(plot_path)
            plt.close('all')

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
            d_par     = zut.get_fit_pars(pdf_ees, arr_dat, d_plt_opt = {'plot_path' : plot_path, 'plot_range' : [5000, 7000] })
            utnr.dump_json(d_par, json_path)

        pdf_res = zut.fix_pars(pdf_res, d_par)

        return pdf_res
    #---------------------------------
    def _get_ratio(self):
        return 0.6
    #---------------------------------
    def _get_trf(self):
        obj     = trfc(obs=self._obs, qsq_src=self._qsq_src, qsq_tgt=self._qsq_tgt, dset=self._dset, proc=self._proc_trf, pref=self._pref) 
        pdf_trf = obj.get_trf()

        return pdf_trf
    #---------------------------------
    def get_pdf(self):
        pdf_mmd = self._get_muon_pdf()
        pdf_trf = self._get_trf()
        pdf_res = self._get_reso()
        r       = self._get_ratio()

        pdf_prc = zfit.pdf.FFTConvPDFV1(func=pdf_trf, kernel=pdf_mmd, name='PRec', n=self._fft_npt)
        pdf     = zfit.pdf.SumPDF([pdf_prc, pdf_res], r)

        return pdf
#-----------------------------------

