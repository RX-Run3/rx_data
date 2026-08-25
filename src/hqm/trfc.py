'''
Module holding TransferFunction
'''
import numpy
import matplotlib.pyplot as plt

from pathlib        import Path
from typing         import Final, TypeAlias
from pydantic       import BaseModel
from rx_common      import Block, Channel, Component, Project, Trigger
from dmu            import LogStore
from dmu.generic    import Serializable
from dmu.stats      import FitResult, Fitter, Model, ModelFactory
from dmu.stats      import ZFitPlotter, zfit
from hqm.config     import TransferFunctionMakerConf, ObsConf

log=LogStore.add_logger('rx_hqm:trfc')
_FLOAT          : Final[list[str]] = []
_SHARED         : Final[list[str]] = ['mu', 'sg'] # Shared parameters in transfer functions
_SOURCE_CHANNEL : Final[Channel  ] = Channel.mm
_TARGET_CHANNEL : Final[Channel  ] = Channel.ee

mu_vals = 0., -500., 500. # Value and range for observable of transffer function
_TRF_VALS : Final[dict[str,tuple[float,float,float]]] = {'mu' : mu_vals}

zpdf = zfit.pdf.BasePDF
kpdf : TypeAlias = zfit.pdf.KDE1DimFFT
#---------------------------------
class TransferFunction(BaseModel, Serializable, frozen = True):
    '''
    Class meant to represent a transfer function
    '''
    name       : str
    observable : ObsConf
    fit_result : FitResult
    models     : list[Model]
    #----------------------
    @property
    def pdf(self) -> zpdf:
        '''
        PDF representing transfer function
        '''
        fac = ModelFactory(
            obs      = self.observable.trn_obs,
            preffix  = self.name,
            l_pdf    = self.models,
            l_float  = _FLOAT,
            l_shared = _SHARED,
            values   = _TRF_VALS)

        pdf  = fac.get_pdf()
        pars = pdf.get_params()

        self.fit_result.set_pars(pars = pars)

        for par in pars:
            par.floating = False

        return pdf
#---------------------------------
class TransferFunctionMaker:
    '''
    Class meant to:

    - Loading datasets
    - Building KDE and non-KDE (transfer function itself) models
    - Fitting to get transfer function parameters
    - Save plots of data and fit
    - Use fit parameters to build and return TransferFunction instance
    '''
    #---------------------------------
    def __init__(
        self, 
        cfg    : TransferFunctionMakerConf,
        sample : Component, 
        project: Project, 
        block  : Block):
        '''
        Parameters
        ----------------
        cfg    : Configuration controling the building of TransferFunction
        sample : Describes simulated sample needed to make function
        project: E.g. rk or rkst 
        block  : E.g. 1 to 8
        '''
        self._cfg      = cfg
        self._project  = project 
        self._sample   = sample
        self._block    = block
    #---------------------------------
    def __get_masses(self, is_source : bool) -> numpy.ndarray:
        '''
        Parameters
        ----------------
        is_source: True if dataset is from the starting distribution, e.g. muon

        Returns
        ----------------
        Numpy array with masses
        '''
        from hqm.data_store import DataStore

        trigger     = Trigger.get_main_trigger(
            channel = _TARGET_CHANNEL, 
            project = self._project)

        obj     = DataStore(
            qsq = self._cfg.target, 
            dset= self._block, 
            trig= trigger, 
            proc= self._sample)

        return obj.get_array()
    #---------------------------------
    def __get_source_pdf(self, path : Path) -> tuple[kpdf,numpy.ndarray]:
        '''
        Parameters
        -----------------------
        path: Path to JSON file with parameters, to be repurposed for fit

        Returns
        -----------------------
        Zfit PDF built from source dataset, e.g. muon psi2S data
        '''
        obs   = self._cfg.observable.fit_obs
        array = self.__get_masses(is_source = True)
        zdata = zfit.Data.from_numpy(obs, array=array)

        pdf          = zfit.pdf.KDE1DimFFT(
            data     = zdata, 
            obs      = obs, 
            bandwidth= self._cfg.bandwidth, 
            name     = 'source_pdf')

        ptr = ZFitPlotter(data = array, model = pdf)
        ptr.run(cfg = self._cfg.plots)

        fit_path = path.with_name(f'{path.stem}_source.png')
        plt.savefig(fit_path)
        plt.close()

        return pdf, array
    #---------------------------------
    def __get_fit_result(self, pdf_trf : zpdf, json_path : Path) -> FitResult:
        '''
        Parameters
        ------------------------
        pdf_trf  : PDF used as the transfer function
        json_path: Path to JSON where transfer function will be saved

        Returns
        ------------------------
        FitResult with transfer function parameters
        '''
        arr_tgt          = self.__get_masses(is_source = False)
        pdf_src, arr_src = self.__get_source_pdf(path = json_path)

        plot_path = json_path.with_name(f'{json_path.stem}_data.png')
        self.__plot_datasets(
            source = arr_src, 
            target = arr_tgt, 
            path   = plot_path)

        pdf_tgt    = zfit.pdf.FFTConvPDFV1(
            name   = 'target_pdf', 
            func   = pdf_src, 
            kernel = pdf_trf, 
            n      = self._cfg.fft_npt)

        lower, upper = self._cfg.observable.mass_range
        xs  = numpy.linspace(lower, upper, self._cfg.fft_npt)
        ys  = pdf_tgt.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path= json_path.with_name(f'{json_path.stem}_conv_prefit.png')
        plt.savefig(path)
        plt.close()

        res = self._fit_trf(data = arr_tgt, pdf = pdf_tgt, path = json_path)

        ys  = pdf_tgt.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path= json_path.with_name(f'{json_path.stem}_conv_postfit.png')
        plt.savefig(path)
        plt.close()

        return res
    #---------------------------------
    def _fit_trf(
        self, 
        path : Path,
        data : numpy.ndarray, 
        pdf  : zpdf) -> FitResult:
        '''
        Parameters
        ----------------
        path: JSON file path, will override ending to save fit plot

        Returns
        --------------
        Fit result
        '''
        ftr = Fitter(pdf = pdf, data = data)
        res = ftr.fit(cfg = self._cfg.fits)

        print(res)

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = self._cfg.plots)

        fit_path = path.with_name(f'{path.stem}_fit.png')
        plt.savefig(fit_path)
        plt.close()

        return res
    #---------------------------------
    def __plot_datasets(self, 
        source : numpy.ndarray, 
        target : numpy.ndarray, 
        path   : Path) -> None:
        '''
        Parameters:
        -----------------
        source/target: Arrays with masses from source/target distributions
        path         : Path to plot
        '''
        log.info(f'Plotting datasets {source.shape}, {target.shape}')

        plt.figure('sim_dset')
        plt.hist(source, bins=100, density=True, histtype='step', label=rf'$\mu\mu\in${self._cfg.source}')
        plt.hist(target, bins=100, density=True, histtype='step', label=rf'$e^+e^-\in${self._cfg.target}')
        plt.legend()
        plt.title(rf'Process: {self._sample}; Trigger: {self._project}; $\mu$:{source.shape[0]}; $e$:{target.shape[0]}; {self._cfg.binning.variable}')

        log.info(f'Saving to: {path}')
        plt.savefig(path)
        plt.close('sim_dset')
    #---------------------------------
    def __get_trf_pdf(self, path : Path) -> zpdf:
        '''
        Parameters
        --------------
        path : Path to JSON file, needed to save plot after overriding ending

        Returns
        --------------
        zfit PDF used as transfer function
        '''
        obs = self._cfg.observable.trn_obs

        fac = ModelFactory(
            preffix  = self._cfg.name,
            obs      = obs,
            l_pdf    = self._cfg.models,
            l_shared = _SHARED,
            l_float  = _FLOAT,
            values   = _TRF_VALS,
        )

        pdf = fac.get_pdf()

        lower, higher = self._cfg.observable.tran_range 
        xs  = numpy.linspace(lower, higher, self._cfg.fft_npt)
        ys  = pdf.pdf(xs)

        plt.scatter(xs, ys, s=2)

        path = path.with_name(f'{path.stem}_trf.png')
        plt.savefig(path)
        plt.close()

        return pdf
    #---------------------------------
    def get_trf(self) -> TransferFunction:
        '''
        Will return transfer function 
        '''
        json_path = self._cfg.make_path(
            kind    = 'trfc',
            project = self._project,
            fname   = f'block_{self._block}_{self._cfg.name}.json')

        if json_path.exists():
            log.info(f'Transfer function found in {json_path}')
            return TransferFunction.from_json(path = json_path)

        log.info('Transfer function not found')
        pdf_trf = self.__get_trf_pdf(path = json_path)
        res     = self.__get_fit_result(pdf_trf, json_path)

        trf            = TransferFunction(
            name       = self._cfg.name,
            fit_result = res, 
            observable = self._cfg.observable,
            models     = self._cfg.models) 

        return trf
#---------------------------------
