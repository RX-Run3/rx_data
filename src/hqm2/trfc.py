import zutils.utils      as zut
import utils_noroot      as utnr
import matplotlib.pyplot as plt
import numpy
import zfit
import os

from zutils.plot         import plot      as zfp
from importlib.resources import files
from hqm2.data_store     import data_store
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
        self._obs_trf  = zfit.Space('B_M', limits=(-1000, +1000))
    #---------------------------------
    def _get_trf_pars(self, pdf_trf, json_path, plot_range):
        json_path = str(json_path)
        obj       = data_store(qsq=self._qsq_src, dset=self._dset, trig='MTOS', proc=self._proc)
        arr_dt_mm = obj.get_array()
        zdata     = zfit.Data.from_numpy(self._obs, array=arr_dt_mm)
        pdf_mms   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=self._bandwidth, name='mc psi2S muon')
        pdf_ees   = zfit.pdf.FFTConvPDFV1(func=pdf_mms, kernel=pdf_trf, name='pdf ee', n=self._fft_npt)

        obj       = data_store(qsq=self._qsq_tgt, dset=self._dset, trig='ETOS', proc=self._proc)
        arr_dt_ee = obj.get_array()

        plot_path = json_path.replace('.json', '_data.png')
        self._plot_datasets(arr_dt_mm, arr_dt_ee, plot_range, plot_path)

        plot_path = json_path.replace('.json', '.png')
        d_plt_opt = {'plot_path' : plot_path, 'plot_range' : plot_range, 'skip_pulls' : True , 'stacked' : True}
        d_fit_opt = {'ntries' : 5, 'pval_threshold' : 0.05}
        d_par     = zut.get_fit_pars(pdf_ees, arr_dt_ee, d_plt_opt=d_plt_opt, d_fit_opt=d_fit_opt)
        utnr.dump_json(d_par, json_path)

        plot_path = json_path.replace('.json', '_kde.png')
        self._plot_pdf(pdf_ees, plot_range, plot_path)

        return d_par 
    #---------------------------------
    def _plot_datasets(self, arr_dt_mm, arr_dt_ee, plot_range, plot_path):
        plt.hist(arr_dt_mm, bins=100, density=True, histtype='step', range=plot_range, label='$\mu\mu$')
        plt.hist(arr_dt_ee, bins=100, density=True, histtype='step', range=plot_range, label='$e^+e^-$')
        plt.legend()
        plt.title(f'$\mu$:{arr_dt_mm.shape[0]}; $e$:{arr_dt_ee.shape[0]}')
        plt.savefig(plot_path)
        plt.close('all')
    #---------------------------------
    def _plot_pdf(self, pdf, plot_range, plot_path) 
        [minx, maxx] = plot_range
        arr_x = numpy.linspace(minx, maxx, 300)
        arr_y = pdf.pdf(arr_x)
        plt.plot(arr_x, arr_y, label=f'{par_name}={par_val}')
        plt.legend()
        plt.savefig(plot_path)
        plt.close('all')
    #---------------------------------
    def _get_dscb(self):
        al  = zfit.param.Parameter(f'al_trf_{self._pref}', 1.5, 1e-3,   10)
        ar  = zfit.param.Parameter(f'ar_trf_{self._pref}', 1.5, 1e-3,   10)
        sg  = zfit.param.Parameter(f'sg_trf_{self._pref}',  40,  0.1,  100)
        nl  = zfit.param.Parameter(f'nl_trf_{self._pref}',   1, 1e-3,  110)
        nr  = zfit.param.Parameter(f'nr_trf_{self._pref}',   1, 1e-3,  110)
        mu  = zfit.param.Parameter(f'mu_trf_{self._pref}',   0, -100,  100)
        pdf = zfit.pdf.DoubleCB(mu=mu, sigma=sg, alphal=al, nl=nl, alphar=ar, nr=nr, obs=self._obs_trf)

        return pdf
    #---------------------------------
    def _get_3cb(self):
        mu  = zfit.param.Parameter(f'mu_trf_{self._pref}',    0, -100, 100)

        sg1 = zfit.param.Parameter(f'sg1_trf_{self._pref}',  10,  0.1, 200)
        sg2 = zfit.param.Parameter(f'sg2_trf_{self._pref}',  40,  0.1, 200)
        sg3 = zfit.param.Parameter(f'sg3_trf_{self._pref}',  40,  0.1, 200)
        
        al  = zfit.param.Parameter(f'al_trf_{self._pref}', 1.5, 1e-3,   10)
        ar  = zfit.param.Parameter(f'ar_trf_{self._pref}', 1.5, 1e-3,   10)
        ac  = zfit.param.Parameter(f'ac_trf_{self._pref}', 1.5, 1e-3,   10)

        nl  = zfit.param.Parameter(f'nl_trf_{self._pref}',   1, 1e-3,  110)
        nr  = zfit.param.Parameter(f'nr_trf_{self._pref}',   1, 1e-3,  110)
        nc  = zfit.param.Parameter(f'nc_trf_{self._pref}',   1, 1e-3,  110)
    
        cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, self._obs_trf, name='CB1')
        cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, self._obs_trf, name='CB2')
        cb3 = zfit.pdf.CrystalBall(mu, sg3, ac, nc, self._obs_trf, name='CB3')
    
        frc_1 = zfit.param.Parameter(f'frc_1{self._pref}', 0.5, 0, 1) 
        frc_2 = zfit.param.Parameter(f'frc_2{self._pref}', 0.5, 0, 1) 

        pdf   = zfit.pdf.SumPDF([cb1, cb2, cb3], fracs=[frc_1, frc_2])
    
        return pdf
    #---------------------------------
    def _get_cb(self):
        mu  = zfit.param.Parameter(f'mu_trf_{self._pref}',-300, -400, +400)
        sg  = zfit.param.Parameter(f'sg_trf_{self._pref}', 100,    1,  200)
        al  = zfit.param.Parameter(f'al_trf_{self._pref}',   2,   -3,   +3)
        nt  = zfit.param.Parameter(f'nt_trf_{self._pref}',   7,    0,  150)
        pdf = zfit.pdf.CrystalBall(mu, sg, al, nt, obs=self._obs_trf)

        return pdf
    #---------------------------------
    def _get_trf_pdf(self):
        if self._qsq_src == 'psi2' and self._qsq_tgt == 'high':
            pdf_trf = self._get_cb()
        else:
            pdf_trf = self._get_3cb()

        return pdf_trf
    #---------------------------------
    def get_trf(self, plot_range=[5000, 7000]):
        pdf_trf = self._get_trf_pdf()

        json_path = files('hqm2_data').joinpath(f'tfunc/{self._dset}_{self._qsq_src}_{self._qsq_tgt}_{self._proc}.json')
        if os.path.isfile(json_path):
            log.info('Transfer function parameters found, loading them')
            d_par = utnr.load_json(json_path)
        else:
            log.info('Transfer function parameters not found, fitting')
            d_par = self._get_trf_pars(pdf_trf, json_path, plot_range)

        pdf_trf = zut.fix_pars(pdf_trf, d_par)

        return pdf_trf
#---------------------------------

