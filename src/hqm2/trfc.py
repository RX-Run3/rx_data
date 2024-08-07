import zutils.utils      as zut
import utils_noroot      as utnr
import zfit
import os

from importlib.resources import files
from hqm2.data_store     import data_store
from fitter              import zfitter
from log_store           import log_store

log=log_store.add_logger('rx_hqm2:trfc')
#---------------------------------
class trfc:
    '''
    Class used to provide transfer functions to go from a given q2 bin to another, using a given process in MC for the fitting/training
    '''
    def __init__(self, obs=None, qsq_src=None, qsq_tgt=None, proc=None, dset=None, pref=None):
        self._obs     = obs
        self._dset    = dset
        self._pref    = pref
        self._proc    = proc
        self._qsq_src = qsq_src
        self._qsq_tgt = qsq_tgt

        self._bandwidth= 15
        self._fft_npt  = 1000
    #---------------------------------
    def _get_trf_pars(self, pdf_trf, json_path):
        json_path = str(json_path)
        obj       = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc=self._proc)
        arr_dat   = obj.get_array()
        zdata     = zfit.Data.from_numpy(self._obs, array=arr_dat)
        pdf_mms   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bandwidth, name='mc psi2S muon')

        pdf_ees   = zfit.pdf.FFTConvPDFV1(func=pdf_trf, kernel=pdf_mms, name='pdf ee', n=self._fft_npt)

        obj       = data_store(qsq=self._qsq_tgt, dset=self._dset, trig='ETOS', proc=self._proc)
        arr_dat   = obj.get_array()

        plot_path = json_path.replace('.json', '.png')
        d_par     = zut.get_fit_pars(pdf_ees, arr_dat, d_plt_opt = {'plot_path' : plot_path, 'plot_range' : [5000, 7000] })

        utnr.dump_json(d_par, json_path)

        return d_par 
    #---------------------------------
    def get_trf(self):
        mu      = zfit.param.Parameter(f'mu_trf_{self._pref}', 303, 0, 400)
        sg      = zfit.param.Parameter(f'sg_trf_{self._pref}',  40, 0, 100)
        al      = zfit.param.Parameter(f'al_trf_{self._pref}',-0.2,-1,  +1)
        nt      = zfit.param.Parameter(f'nt_trf_{self._pref}', 110, 0, 150)
        pdf_trf = zfit.pdf.CrystalBall(mu, sg, al, nt, obs=self._obs)

        json_path = files('hqm2_data').joinpath(f'tfunc/{self._dset}_{self._qsq_src}_{self._qsq_tgt}_{self._proc}.json')
        if os.path.isfile(json_path):
            log.info(f'Transfer function parameters found, loading them')
            d_par = utnr.load_json(json_path)
        else:
            log.info(f'Transfer function parameters not found, fitting')
            d_par = self._get_trf_pars(pdf_trf, json_path)

        pdf_trf = zut.fix_pars(pdf_trf, d_par)

        return pdf_trf
#---------------------------------

