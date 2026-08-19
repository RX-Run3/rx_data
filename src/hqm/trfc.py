'''
Module holding TransferFunction
'''
import matplotlib.pyplot as plt
import numpy

from typing          import Final
from rx_common       import Block, Component, Qsq, Trigger
from dmu.stats       import ModelFactory, zfit
from dmu             import LogStore

from hqm2.data_store import data_store
from hqm2.config     import Conf

log=LogStore.add_logger('rx_hqm:trfc')

_BANDWIDTH : Final[int]       = 15
_FFT_NPT   : Final[int]       = 1000
_SHARED    : Final[list[str]] = ['mu', 'sg'] # Shared parameters in transfer functions

zpdf = zfit.pdf.BasePDF
#---------------------------------
class TransferFunctionMaker:
    '''
    Class used to provide transfer functions to go from a given q2 bin to another, using a given process in MC for the fitting/training
    '''
    #---------------------------------
    def __init__(
        self, 
        obs    : zfit.Space, 
        source : Qsq, 
        target : Qsq, 
        sample : Component, 
        trigger: Trigger, 
        block  : Block,
        prefix : str):
        '''
        Parameters
        ----------------
        obs    : Observable to be used in PDFs
        source : q2bin used to get sideband dataset to be smeared
        target : q2bin that needs to be obtained from transfer function
        trigger: Describes dataset, channel and rk vs rkst
        block  : E.g. 1 to 8
        prefix : Used for naming
        '''
        self._obs      = obs
        self._trigger  = trigger
        self._sample   = sample
        self._source   = source
        self._target   = target
        self._block    = block

        self._obs_trf  = zfit.Space('B_M', limits=(-1000, +1000))
        self._prefix   = self._update_prefix(prefix = prefix)
        self._cfg      = Conf.load(name = 'transfer')
    #---------------------------------
    def _update_prefix(self, prefix : str) -> str:
        '''
        Returns prefix updated with binning information
        '''
        if self._cfg.binning is None:
            return prefix

        varn = self._cfg.binning.variable
        ibin = self._cfg.binning.bin

        return f'{self._prefix}_{varn}_{ibin}'
    #---------------------------------
    def _get_trf_pars(self, pdf_trf, json_path):
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
        plot_range= self._cfg.q2_cfg(source = self._source, target = self._target).plot_range

        d_plt_opt = {'plot_path' : plot_path, 'plot_range' : plot_range, 'skip_pulls' : True , 'stacked' : False}
        d_fit_opt = dict(Conf.fitting)
        d_fit_opt['ignore_status'] = True
        d_par     = zut.get_fit_pars(pdf_ees, arr_dt_ee, d_plt_opt=d_plt_opt, d_fit_opt=d_fit_opt)
        d_par     = self._rename_pars(d_par, suffix='remove')
        utnr.dump_json(d_par, json_path)

        plot_path = json_path.fits('.json', '_kde.png')
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
    def _get_bin_title(self) -> str:
        if self._cfg.binning is None:
            return ''

        return f'; {self._cfg.binning.cut}'
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
    def _get_pdf_name(self, kind : str) -> str:
        if self._cfg.binning is None:
            return kind

        return f'{kind}_{self._cfg.variable}_{self._cfg.bin}'
    #---------------------------------
    def _get_trf_pdf(self) -> zpdf:
        '''
        Returns
        --------------
        zfit PDF used as transfer function
        '''
        models = self._cfg.q2_cfg(
            source = self._source,
            target = self._target)

        fac = ModelFactory(
            obs      = self._obs,
            preffix  = self._prefix,
            l_pdf    = models,
            l_shared = _SHARED,
            l_float  = [])

        return fac.get_pdf()
    #---------------------------------
    def _rename_pars(self, d_par=None, suffix=None):
        if self._cfg.binning is None:
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
        pdf_trf   = self._get_trf_pdf()
        json_path = self._cfg.make_path(
            kind    = 'tfunc', 
            block   = self._block, 
            trigger = self._trigger,
            fname   = f'{self._source}_{self._target}_{self._sample}.json')

        if json_path.exists():
            log.info(f'Transfer function for {self._trigger}, {self._source} -> {self._target} found, i.e. {json_path}')
            d_par = utnr.load_json(json_path)
        else:
            log.info(f'Transfer function for {self._trigger}, {self._source} -> {self._target} not found, i.e. {json_path}')
            d_par = self._get_trf_pars(pdf_trf, json_path)

        d_par   = self._rename_pars(d_par, suffix='add')
        pdf_trf = zut.fix_pars(pdf_trf, d_par)

        return pdf_trf
#---------------------------------
