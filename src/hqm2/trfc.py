'''
Module holding TransferFunction
'''

import zutils.utils      as zut
import utils_noroot      as utnr
import matplotlib.pyplot as plt
import numpy
import os

from typing              import Final
from rx_common           import Component, Qsq, Trigger
from dmu.stats           import zfit
from zutils.pdf          import SUJohnson as zpdf_jh
from dmu                 import LogStore

from hqm2.data_store     import data_store
from hqm2.config         import config

log=LogStore.add_logger('rx_hqm:trfc')

_BANDWIDTH : Final[int] = 15
_FFT_NPT   : Final[int] = 1000
#---------------------------------
class TransferFunction:
    '''
    Class used to provide transfer functions to go from a given q2 bin to another, using a given process in MC for the fitting/training
    '''
    def __init__(
        self, 
        obs    : zfit.Space, 
        source : Qsq, 
        target : Qsq, 
        sample : Component, 
        trigger: Trigger, 
        prefix : str):
        '''
        Parameters
        ----------------
        obs    : Observable to be used in PDFs
        source : q2bin used to get sideband dataset to be smeared
        target : q2bin that needs to be obtained from transfer function
        trigger: Describes dataset, channel and rk vs rkst
        prefix : Used for naming
        '''
        self._obs      = obs
        self._trigger  = trigger
        self._prefix   = prefix
        self._sample   = sample
        self._source   = source
        self._target   = target

        self._obs_trf  = zfit.Space('B_M', limits=(-1000, +1000))

        self._bin_suf  = None

        self._set_suffix()
    #---------------------------------
    def _set_suffix(self):
        if len(config.binning) == 0:
            return

        varn = config.binning['var']
        ibin = config.binning['bin']

        self._bin_suf = f'{varn}_{ibin}'
        self._prefix     = f'{self._prefix}_{self._bin_suf}'
    #---------------------------------
    def _get_trf_pars(self, pdf_trf, json_path, plot_range):
        obj       = data_store(qsq=self._source, dset=self._trigger, trig='MTOS', proc=self._sample)
        arr_dt_mm = obj.get_array()
        zdata     = zfit.Data.from_numpy(self._obs, array=arr_dt_mm)
        pdf_mms   = zfit.pdf.KDE1DimFFT(obs=self._obs, data=zdata, bandwidth=_BANDWIDTH, name='mc psi2S muon')
        pdf_ees   = zfit.pdf.FFTConvPDFV1(func=pdf_mms, kernel=pdf_trf, name='pdf ee', n=_FFT_NPT)

        obj       = data_store(qsq=self._target, dset=self._trigger, trig='ETOS', proc=self._sample)
        arr_dt_ee = obj.get_array()

        plot_path = json_path.replace('.json', '_data.png')
        self._plot_datasets(arr_dt_mm, arr_dt_ee, plot_path)

        plot_path = json_path.replace('.json', '.png')

        d_plt_opt = {'plot_path' : plot_path, 'plot_range' : plot_range, 'skip_pulls' : True , 'stacked' : False}
        d_fit_opt = dict(config.fitting)
        d_fit_opt['ignore_status'] = True
        d_par     = zut.get_fit_pars(pdf_ees, arr_dt_ee, d_plt_opt=d_plt_opt, d_fit_opt=d_fit_opt)
        d_par     = self._rename_pars(d_par, suffix='remove')
        utnr.dump_json(d_par, json_path)

        plot_path = json_path.replace('.json', '_kde.png')
        self._plot_pdf(pdf_ees, plot_range, plot_path)

        return d_par
    #---------------------------------
    def _plot_datasets(self, arr_dt_mm, arr_dt_ee, plot_path):
        plt.figure('sim_dset')
        plt.hist(arr_dt_mm, bins=100, density=True, histtype='step', label=rf'$\mu\mu\in${self._source}')
        plt.hist(arr_dt_ee, bins=100, density=True, histtype='step', label=rf'$e^+e^-\in${self._target}')
        plt.legend()
        plt.title(rf'Process: {self._sample}; Trigger: {self._trigger}; $\mu$:{arr_dt_mm.shape[0]}; $e$:{arr_dt_ee.shape[0]}' + self._get_bin_title() )
        plt.savefig(plot_path)
        plt.close('sim_dset')
    #---------------------------------
    def _get_bin_title(self):
        if len(config.binning) == 0:
            return ''

        cut = config.binning['cut']

        return f'; {cut}'
    #---------------------------------
    def _plot_pdf(self, pdf, plot_range, plot_path):
        [minx, maxx] = plot_range
        arr_x = numpy.linspace(minx, maxx, 300)
        arr_y = pdf.pdf(arr_x)

        plt.figure('pdf_only')
        plt.plot(arr_x, arr_y)
        plt.legend()
        plt.title(self._get_bin_title())
        plt.savefig(plot_path)
        plt.close('pdf_only')
    #---------------------------------
    def _get_pdf_name(self, kind):
        if self._bin_suf is None:
            return kind

        return f'{kind}_{self._bin_suf}'
    #---------------------------------
    def _get_dscb(self):
        al  = zfit.param.Parameter(f'al_trf_{self._prefix}', 1.5, 1e-3,   10)
        ar  = zfit.param.Parameter(f'ar_trf_{self._prefix}', 1.5, 1e-3,   10)
        sg  = zfit.param.Parameter(f'sg_trf_{self._prefix}',  40,  0.1,  100)
        nl  = zfit.param.Parameter(f'nl_trf_{self._prefix}',   1, 1e-3,  110)
        nr  = zfit.param.Parameter(f'nr_trf_{self._prefix}',   1, 1e-3,  110)
        mu  = zfit.param.Parameter(f'mu_trf_{self._prefix}',   0, -100,  100)
        pdf = zfit.pdf.DoubleCB(
                obs   = self._obs_trf,
                mu    = mu,
                sigma = sg,
                alphal= al,
                alphar= ar,
                nl    = nl,
                nr    = nr,
                name  = self._get_pdf_name('DSCB'),
                )

        return pdf
    #---------------------------------
    def _get_3cb(self):
        mu  = zfit.param.Parameter(f'mu_trf_{self._prefix}',    0, -200, 200)

        sg1 = zfit.param.Parameter(f'sg1_trf_{self._prefix}',  10,  0.1, 400)
        sg2 = zfit.param.Parameter(f'sg2_trf_{self._prefix}',  40,  0.1, 400)
        sg3 = zfit.param.Parameter(f'sg3_trf_{self._prefix}',  40,  0.1, 400)

        al  = zfit.param.Parameter(f'al_trf_{self._prefix}', 1.5, 1e-3,   10)
        ar  = zfit.param.Parameter(f'ar_trf_{self._prefix}', 1.5, 1e-3,   10)
        ac  = zfit.param.Parameter(f'ac_trf_{self._prefix}', 1.5, 1e-3,   10)

        nl  = zfit.param.Parameter(f'nl_trf_{self._prefix}',   1, 1e-3,  110)
        nr  = zfit.param.Parameter(f'nr_trf_{self._prefix}',   1, 1e-3,  110)
        nc  = zfit.param.Parameter(f'nc_trf_{self._prefix}',   1, 1e-3,  110)

        cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, self._obs_trf, name='CB1')
        cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, self._obs_trf, name='CB2')
        cb3 = zfit.pdf.CrystalBall(mu, sg3, ac, nc, self._obs_trf, name='CB3')

        frc_1 = zfit.param.Parameter(f'frc_1_trf_{self._prefix}', 0.5, 0, 1)
        frc_2 = zfit.param.Parameter(f'frc_2_trf_{self._prefix}', 0.5, 0, 1)

        pdf   = zfit.pdf.SumPDF(
                [cb1, cb2, cb3],
                fracs=[frc_1, frc_2],
                name =self._get_pdf_name('3CB'),
                )

        return pdf
    #---------------------------------
    def _get_2cb(self):
        mu  = zfit.param.Parameter(f'mu_trf_{self._prefix}',    0, -200, 200)

        sg1 = zfit.param.Parameter(f'sg1_trf_{self._prefix}',  10,  0.1, 400)
        sg2 = zfit.param.Parameter(f'sg2_trf_{self._prefix}',  40,  0.1, 400)

        al  = zfit.param.Parameter(f'al_trf_{self._prefix}',  -1,  -10,    0)
        ar  = zfit.param.Parameter(f'ar_trf_{self._prefix}',  +1,    0,   10)

        nl  = zfit.param.Parameter(f'nl_trf_{self._prefix}',   1, 1e-3,  110)
        nr  = zfit.param.Parameter(f'nr_trf_{self._prefix}',   1, 1e-3,  110)

        cb1 = zfit.pdf.CrystalBall(mu, sg1, ar, nr, self._obs_trf, name='CB1')
        cb2 = zfit.pdf.CrystalBall(mu, sg2, al, nl, self._obs_trf, name='CB2')

        frc_1 = zfit.param.Parameter(f'frc_1_trf_{self._prefix}', 0.5, 0, 1)
        frc_2 = zfit.param.Parameter(f'frc_2_trf_{self._prefix}', 0.5, 0, 1)

        pdf   = zfit.pdf.SumPDF(
                [cb1, cb2],
                fracs=[frc_1, frc_2],
                name =self._get_pdf_name('2CB'),
                )

        return pdf
    #---------------------------------
    def _get_cb(self):
        mu  = zfit.param.Parameter(f'mu_trf_{self._prefix}',-300, -400, 2400)
        sg  = zfit.param.Parameter(f'sg_trf_{self._prefix}', 100,    1,  600)
        al  = zfit.param.Parameter(f'al_trf_{self._prefix}',   0,   -9,   +9)
        nt  = zfit.param.Parameter(f'nt_trf_{self._prefix}',   7,    0,  150)
        pdf = zfit.pdf.CrystalBall(
                mu,
                sg,
                al,
                nt,
                obs =self._obs_trf,
                name=self._get_pdf_name('CB'),
                )

        return pdf
    #---------------------------------
    def _get_sj(self):
        ms = zfit.Parameter(f'ms_trf_{self._prefix}',    0, -300,  300)
        lm = zfit.Parameter(f'lm_trf_{self._prefix}',   50,   10,  200)
        gm = zfit.Parameter(f'gm_trf_{self._prefix}',    0,  -10,   10)
        dl = zfit.Parameter(f'dl_trf_{self._prefix}',    2,  -10,   10)

        pdf= zpdf_jh(
                obs  = self._obs_trf,
                mu   = ms,
                lm   = lm,
                gamma= gm,
                delta= dl,
                name = self._get_pdf_name('SUJohnson'),
                )

        return pdf
    #---------------------------------
    def _get_sjcb(self):
        pdf_sj = self._get_sj()
        pdf_cb = self._get_cb()
        frc    = zfit.param.Parameter(f'frc_trf_{self._prefix}', 0.5, 0, 1)

        pdf    = zfit.pdf.SumPDF(
                [pdf_sj, pdf_cb],
                fracs=frc,
                name =self._get_pdf_name('SUJ_CB'),
                )

        return pdf
    #---------------------------------
    def _get_trf_pdf(self):
        if   self._source == 'psi2' and self._target == 'high':
            pdf_trf = self._get_cb()
        elif self._source == 'jpsi' and self._target == 'high':
            pdf_trf = self._get_cb()
        elif self._source == 'jpsi' and self._target == 'jpsi':
            pdf_trf = self._get_3cb()
        elif self._source == 'jpsi' and self._target == 'psi2':
            pdf_trf = self._get_sjcb()
        elif self._source == 'psi2' and self._target == 'jpsi':
            pdf_trf = self._get_sjcb()
        elif self._source == 'psi2' and self._target == 'psi2':
            pdf_trf = self._get_sjcb()
        else:
            log.error(f'Invalid source/target q2: {self._source}/{self._target}')
            raise

        return pdf_trf
    #---------------------------------
    def _is_binned(self):
        return len(config.binning) > 0
    #---------------------------------
    def _get_plot_range(self):
        if self._source == 'psi2' and self._target == 'psi2':
            return [4500, 6000]

        if self._source == 'jpsi' and self._target == 'jpsi':
            return [4500, 5800]

        if self._source == 'psi2' and self._target == 'jpsi':
            return [4500, 5500]

        if self._source == 'jpsi' and self._target == 'psi2':
            return [5000, 6000]

        if self._source == 'psi2' and self._target == 'high':
            return [5000, 6400]

        if self._source == 'jpsi' and self._target == 'high':
            return [5500, 7000]

        log.error(f'Invalid src/trg q2: {self._source}/{self._target}')
        raise
    #---------------------------------
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
    #---------------------------------
    def get_trf(self):
        '''
        Will return zfit PDF representing transfer function
        '''
        self._initialize()

        plot_range = self._get_plot_range()
        pdf_trf    = self._get_trf_pdf()
        json_path  = config.make_data_path(kind='tfunc', dset=self._trigger, fname=f'{self._source}_{self._target}_{self._sample}.json')

        if os.path.isfile(json_path):
            log.info(f'Transfer function for {self._trigger}, {self._source} -> {self._target} found, i.e. {json_path}')
            d_par = utnr.load_json(json_path)
        else:
            log.info(f'Transfer function for {self._trigger}, {self._source} -> {self._target} not found, i.e. {json_path}')
            d_par = self._get_trf_pars(pdf_trf, json_path, plot_range)

        d_par   = self._rename_pars(d_par, suffix='add')
        pdf_trf = zut.fix_pars(pdf_trf, d_par)

        return pdf_trf
#---------------------------------

