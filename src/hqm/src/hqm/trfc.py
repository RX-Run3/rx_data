'''
Module holding TransferFunction
'''
import numpy
import matplotlib.pyplot as plt

from pathlib        import Path
from typing         import Final
from pydantic       import BaseModel
from rx_common      import Channel, Mass, Project, Trigger
from dmu            import LogStore
from dmu.generic    import Serializable
from dmu.stats      import FitResult, Fitter, Model, ModelFactory
from dmu.stats      import ZFitPlotter, zfit
from hqm.config     import TransferFunctionMakerConf
from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder
from dmu.generic    import Mode

log=LogStore.add_logger('rx_hqm:trfc')
_FLOAT          : Final[list[str]] = []
_SHARED         : Final[list[str]] = ['mu', 'sg'] # Shared parameters in transfer functions
_SOURCE_CHANNEL : Final[Channel  ] = Channel.mm
_TARGET_CHANNEL : Final[Channel  ] = Channel.ee
_RAW_QSQ        : Final[str      ] = 'q2'         # Used to switch between q2 cuts for rare
_DTF_QSQ        : Final[str      ] = 'q2_dtf'     # and resonant target shapes
_MIN_ENTRIES    : Final[int      ] = 200          # Target dataset has to have at least this number of entries
_MAX_ENTRIES    : Final[int      ] = 50_000       # Target dataset has to have at most this number of entries

type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space
#---------------------------------
class TransferFunction(BaseModel, Serializable, frozen = True):
    '''
    Class meant to represent a transfer function
    '''
    name       : str
    fit_result : FitResult
    models     : list[Model]
    trfc_cfg   : TransferFunctionMakerConf
    #----------------------
    @property
    def pdf(self) -> zpdf:
        '''
        PDF representing transfer function
        '''
        fac = ModelFactory(
            obs      = self.trfc_cfg.trn_obs,
            preffix  = self.name,
            l_pdf    = self.models,
            l_float  = _FLOAT,
            l_shared = _SHARED,
            values   = self.trfc_cfg.trn_vals)

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
        project: Project):
        '''
        Parameters
        ----------------
        cfg    : Configuration controling the building of TransferFunction
        project: E.g. rk or rkst
        '''
        self._cfg      = cfg
        self._project  = project
    #---------------------------------
    @property
    def _qsq_var(self) -> str:
        '''
        Returns
        -------------
        q2 cut used to select data in target q2-bin
        '''
        # Rare regions will use raw q2
        if self._cfg.target.is_rare:
            return _RAW_QSQ

        # There is no leakage with DTF q2
        if self._cfg.target != self._cfg.source:
            return _RAW_QSQ

        # No leakage and resonant mode -> Use DTF q2 to avoid
        # tail shaping distortion
        return _DTF_QSQ
    #---------------------------------
    def __get_target_masses(self, out_dir : Path) -> numpy.ndarray:
        '''
        Parameters
        ----------------
        out_dir: Path to directory with outputs

        Returns
        ----------------
        Numpy array with masses associated to the target distribution
        '''
        trigger     = Trigger.get_main_trigger(
            channel = _TARGET_CHANNEL,
            project = self._project)

        lo  = self._cfg.target.lower_bound
        hi  = self._cfg.target.upper_bound

        sel = {'q2' : f'({self._qsq_var} > {lo}) & ({self._qsq_var} < {hi})'}
        with DataStore.selection(sel = sel, update = True):
            obj = DataStore(
                trig        = trigger,
                comp        = self._cfg.target_component,
                max_entries = _MAX_ENTRIES,
                min_entries = _MIN_ENTRIES)

        mass      = Mass.raw_from_project(project = trigger.project)
        masses, _ = obj.get_array(mass = mass)

        obj.save_selection(path = out_dir / 'target_selection.json')

        return masses
    #---------------------------------
    def __get_source_pdf(self, obs : zobs, out_dir : Path) -> zpdf:
        '''
        Parameters
        -----------------------
        obs    : Observable to use with this PDF
        out_dir: Directory where outputs will be saved

        Returns
        -----------------------
        Zfit PDF built from source dataset, e.g. muon psi2S data
        '''
        trig = Trigger.get_main_trigger(
            channel = _SOURCE_CHANNEL,
            project = self._project)

        # NOTE: source PDF comes from muon channel
        # It will always use standard q2
        # It will always be a parametric fit
        bins = self._cfg.binning
        name = f'q2/{bins.dir_path}/parametric'

        obj         = PdfBuilder(
            trigger = trig,
            name    = name,
            comp    = self._cfg.source_component,
            qsq     = self._cfg.source)
        fmod = obj.get_model(obs_ext = obs, mode = Mode.read)

        pdf = fmod.fixed_pdf

        lower, upper = self._cfg.observable.mass_range
        xs  = numpy.linspace(lower, upper, self._cfg.fft_npt)
        ys  = pdf.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path = out_dir / 'source_pdf.png'
        log.info(f'Saving: {path}')
        plt.savefig(path)
        plt.close()

        return pdf
    #---------------------------------
    def __get_fit_result(self, pdf_trf : zpdf, out_dir : Path) -> FitResult:
        '''
        Parameters
        ------------------------
        pdf_trf: PDF used as the transfer function
        out_dir: Path to directory with outputs

        Returns
        ------------------------
        FitResult with transfer function parameters
        '''
        wide_obs= self._cfg.observable.wide_obs
        mass_obs= self._cfg.observable.mass_obs

        arr_tgt = self.__get_target_masses(out_dir = out_dir)
        pdf_src = self.__get_source_pdf(obs = wide_obs, out_dir = out_dir)

        pdf_tgt    = zfit.pdf.FFTConvPDFV1(
            obs    = mass_obs,
            name   = 'target_pdf',
            func   = pdf_src,
            kernel = pdf_trf,
            n      = self._cfg.fft_npt)

        lower, upper = self._cfg.observable.mass_range
        xs  = numpy.linspace(lower, upper, self._cfg.fft_npt)
        ys  = pdf_tgt.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path = out_dir / 'conv_prefit.png'
        log.info(f'Saving: {path}')
        plt.savefig(path)
        plt.close()

        res = self._fit_trf(data = arr_tgt, pdf = pdf_tgt, path = out_dir)

        ys  = pdf_tgt.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path = out_dir / 'conv_postfit.png'
        log.info(f'Saving: {path}')
        plt.savefig(path)
        plt.close()

        _, lower, upper = self._cfg.observable.tran_range[self._cfg.source][self._cfg.target]
        xs  = numpy.linspace(lower, upper, self._cfg.fft_npt)
        ys  = pdf_trf.pdf(xs)
        plt.scatter(xs, ys, s = 1)
        path= out_dir / 'trfc_postfit.png'
        log.info(f'Saving: {path}')
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

        log.info(res)

        src     = self._cfg.source
        tgt     = self._cfg.target
        title   = fr'{src.latex} $\to$ {tgt.latex}'
        cfg_plt = self._cfg.plots.model_copy(update = {'title' : title})
        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg_plt)

        fit_path = path / 'fit.png'
        log.info(f'Saving: {fit_path}')
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
        plt.title(rf'Trigger: {self._project}; $\mu$:{source.shape[0]}; $e$:{target.shape[0]}; {self._cfg.binning.to_str()}')

        log.info(f'Saving to: {path}')
        plt.savefig(path)
        plt.close('sim_dset')
    #---------------------------------
    def __get_trf_pdf(self, out_dir : Path) -> zpdf:
        '''
        Parameters
        --------------
        out_dir: Path to directory where outputs are saved

        Returns
        --------------
        zfit PDF used as transfer function
        '''
        fac = ModelFactory(
            preffix  = self._cfg.name,
            obs      = self._cfg.trn_obs,
            l_pdf    = self._cfg.models,
            l_shared = _SHARED,
            l_float  = _FLOAT,
            values   = self._cfg.trn_vals,
        )

        pdf = fac.get_pdf()

        _, lower, higher = self._cfg.observable.tran_range[self._cfg.source][self._cfg.target]
        xs  = numpy.linspace(lower, higher, self._cfg.fft_npt)
        ys  = pdf.pdf(xs)

        plt.scatter(xs, ys, s=2)

        out_dir = out_dir / 'trfc_prefit.png'
        plt.savefig(out_dir)
        plt.close()

        return pdf
    #---------------------------------
    def get_trf(self, mode : Mode) -> TransferFunction:
        '''
        Will return transfer function
        '''
        json_path = self._cfg.make_path(
            kind    = 'trfc',
            project = self._project,
            subdir  = f'{self._cfg.source}_to_{self._cfg.target}',
            fname   = 'trfc.json')

        mode.validate(path = json_path)
        if json_path.exists() and not mode.skip_reading:
            log.info(f'Transfer function found in {json_path}')
            return TransferFunction.from_json(path = json_path)

        log.info('Transfer function not found')
        pdf_trf = self.__get_trf_pdf(out_dir = json_path.parent)
        res     = self.__get_fit_result(pdf_trf = pdf_trf, out_dir = json_path.parent)

        trf            = TransferFunction(
            fit_result = res,
            trfc_cfg   = self._cfg,
            name       = self._cfg.name,
            models     = self._cfg.models)

        trf.to_json(path = json_path)

        return trf
#---------------------------------
