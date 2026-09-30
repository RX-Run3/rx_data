'''
File holding CCbarRatioCalculator and CCbarRatio classes
'''
import zfit
import numpy

from functools      import lru_cache
from typing         import Final, Literal
from pydantic       import BaseModel
from dmu.stats      import FitResult, print_pdf
from dmu.generic    import Serializable
from hqm.data_store import DataStore
from hqm.prec_maker import PrecMaker
from hqm.pdf_mc     import PdfBuilder
from dmu.generic    import Mode
from hqm.config     import CCbarRatioCalculatorConf, TransferFunctionMakerConf
from hqm.trfc       import TransferFunction, TransferFunctionMaker
from rx_common      import Channel, Component, Mass, Project, Qsq, Trigger, Cuts
from dmu            import LogStore
from dmu.stats      import utilities as sut

from .plotter       import Plotter

log=LogStore.add_logger('hqm:ratc')

type Loss = zfit.loss.ExtendedUnbinnedNLL
type zpdf = zfit.pdf.BasePDF

_QSQ_NAME       : Final[str          ] = 'q2'       # Name of q2 variable that cut is applied on to build signal regions in data
_SOURCE_CHANNEL : Final[Channel      ] = Channel.mm # Channel used to get original part reco distribution
_TARGET_CHANNEL : Final[Channel      ] = Channel.ee # Channel where ratio will be extracted

_LEGS : Final[dict[str,str]] = {
    'jpsi_jpsi'                    : r'$B \to J/\psi(\to e^+e^-) H_s + X$',
    'jpsi_psi2'                    : r'$B \to J/\psi(\to e^+e^-) H_s + X$',
    'psi2_jpsi'                    : r'$B \to \psi(2S)(\to e^+e^-) H_s + X$',
    'psi2_psi2'                    : r'$B \to \psi(2S)(\to e^+e^-) H_s + X$',
    Component.bpkpjpsiee.value     : Component.bpkpjpsiee.latex,
    Component.bpkppsi2ee.value     : Component.bpkppsi2ee.latex,
    Component.bdkstkpijpsiee.value : Component.bdkstkpijpsiee.latex,
    Component.bdkstkpipsi2ee.value : Component.bdkstkpipsi2ee.latex,
}
#-----------------------------
class CCbarRatio(BaseModel, Serializable, frozen = True):
    '''
    Class representing ratio between fully and partly reconstructed charmonium
    '''
    res : FitResult
    # ----------------------
    def get_value(self, name : str) -> tuple[float,float]:
        '''
        Parameters
        ---------------
        name: Name of fit parameter

        Returns
        ---------------
        Tuple with value and error
        '''
        return self.res[name]
#-----------------------------
class CCbarRatioCalculator:
    '''
    Class that builds model using:
    - smeared muon data to represent electron partially reconstructed
    - Analytical PDF to represent fully reconstructed components

    it then uses the model to fit electron channel data and extract the ratios
    of fully reconstructed over partially reconstructed
    '''
    #-----------------------------
    def __init__(
        self,
        cfg     : CCbarRatioCalculatorConf,
        project : Project,
        binning : str,
        ntoys   : int | None = None):
        '''
        Parameters
        ------------------
        cfg    : Object holding configuration
        block  : E.g. 1..8
        project: E.g. rk or rkst
        ntoys  : If running tests an integer, with None (default) will use real data
        '''
        self._cfg      = cfg
        self._project  = project
        self._binning  = binning
        self._out_dir  = self._cfg.make_path(kind='ratios', project = project)
        self._plotter  = Plotter(out_dir = self._out_dir)
        self._ntoys    = ntoys
    #-----------------------------
    def __get_ratio(self) -> CCbarRatio:
        '''
        Returns
        -------------
        Object representing CCbarRatio
        '''
        nll_jpsi  = self.__get_nll(qsq = Qsq.jpsi)
        nll_psi2  = self.__get_nll(qsq = Qsq.psi2)
        nll       = nll_jpsi + nll_psi2

        log.info('Fitting')
        minimizer = zfit.minimize.Minuit()
        res       = minimizer.minimize(nll)
        res.hesse(
            name  ='minuit_hesse',
            method='minuit_hesse')

        print(res)

        res = FitResult.from_zfit(res = res)

        self._plotter.plot_nll(
            legs = _LEGS,
            name = 'fit_jpsi',
            nll  = nll_jpsi)

        self._plotter.plot_nll(
            legs = _LEGS,
            name = 'fit_psi2',
            nll  = nll_psi2)

        return CCbarRatio(res = res)
    #-----------------------------
    def __get_nll(self, qsq : Qsq) -> Loss:
        '''
        Returns NLL for given q2 bin
        '''
        log.info(f'Building NLL in {qsq} bin')
        pdf   = self.__get_model(qsq = qsq)
        array = self.__get_target_data(qsq = qsq)
        data  = zfit.Data.from_numpy(
            obs  =self._cfg.observable.mass_obs,
            array=array)

        if not isinstance(data, zfit.Data):
            raise ValueError('Dataset is not unbinned')

        log.debug(f'Data  obs: {data.space}')
        log.debug(f'Model obs: {pdf.space}')

        nll = zfit.loss.ExtendedUnbinnedNLL(model = pdf, data = data)

        self._plotter.plot_array(name = f'all_data_{qsq}', array = array)
        self._plotter.plot_data( name = f'fit_data_{qsq}', data  =  data)

        return nll
    #-----------------------------
    def __get_target_data(self, qsq : Qsq) -> numpy.ndarray:
        '''
        Parameters
        -----------------
        qsq: Target q2-bin

        Returns
        -----------------
        Array of masses for given q2-bin in real data
        '''
        if self._ntoys:
            return self.__get_toy_data(qsq = qsq)

        trigger = Trigger.get_main_trigger(project = self._project, channel = _TARGET_CHANNEL)
        mass    = Mass.raw_from_project(project = self._project)
        qsq_cut = f'({_QSQ_NAME} > {qsq.lower_bound}) & ({_QSQ_NAME} < {qsq.upper_bound})'

        with DataStore.selection(sel = {Cuts.q2 : qsq_cut}, update = True):
            ds      = DataStore(trig=trigger, comp=Component.data_24)
            array, _= ds.get_array(mass = mass)

        ds.save_selection(path = self._out_dir / f'selection_{qsq}.json')

        return array
    #-----------------------------
    def __get_toy_data(self, qsq : Qsq) -> numpy.ndarray:
        '''
        Parameters
        ------------------
        qsq: q2-bin for which toy data is needed

        Returns
        ------------------
        Data produced from current model
        '''
        log.warning(f'Getting toy sample with {self._ntoys} entries')
        pdf = self.__get_model(qsq = qsq)
        data= pdf.create_sampler(n = self._ntoys)

        return data.numpy()
    #-----------------------------
    @lru_cache(maxsize = 5)
    def __get_model(self, qsq : Qsq) -> zfit.pdf.SumPDF:
        r'''
        Parameters
        ---------------
        qsq: $q^2$ bin for which model is needed

        Returns
        ---------------
        PDF with:

        - Part reco candidates with $J/\psi$ and $\psi(2S)$ decays
        - Fully reco candidates with same decays
        '''
        pdf_prjp = self.__get_pr_pdf(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        pdf_prjp = self.__extend_prc(qsq_src = Qsq.jpsi, qsq_tgt = qsq, pdf = pdf_prjp)

        pdf_frjp = self.__get_fr_pdf(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        pdf_frjp = self.__extend_fr(
            pdf_fr  = pdf_frjp,
            pdf_pr  = pdf_prjp,
            qsq_src = Qsq.jpsi,
            qsq_tgt = qsq)

        pdf_prps = self.__get_pr_pdf(qsq_src = Qsq.psi2, qsq_tgt = qsq)
        pdf_prps = self.__extend_prc(qsq_src = Qsq.psi2, qsq_tgt = qsq, pdf = pdf_prps)

        pdf_frps = self.__get_fr_pdf(qsq_src = Qsq.psi2, qsq_tgt = qsq)
        pdf_frps = self.__extend_fr(
            pdf_fr  = pdf_frps,
            pdf_pr  = pdf_prps,
            qsq_src = Qsq.psi2,
            qsq_tgt = qsq)

        pdfs = [pdf_prps, pdf_prjp, pdf_frps, pdf_frjp]
        for pdf in pdfs:
            log.debug(f'{pdf.name:<10}{pdf.space}')

        obs = self._cfg.observable.mass_obs
        try:
            pdf = zfit.pdf.SumPDF(pdfs, obs = obs)
        except Exception as exc:
            log.error(f'Full model observable: {obs}')
            for model in pdfs:
                log.error(f'{model.name:<30}{model.space}')

            raise ValueError('Cannot build model') from exc

        print_pdf(pdf = pdf)
        self._plotter.plot_model(name = f'model_{qsq}', pdf = pdf)

        return pdf
    #-----------------------------
    def __extend_fr(
        self,
        pdf_fr  : zpdf,
        pdf_pr  : zpdf,
        qsq_src : Qsq,
        qsq_tgt : Qsq) -> zpdf:
        '''
        ```math
        ratio       = npart_reco_total             / nfully_reco_total
        ratio       = (npart_reco / eff_part_reco) / (nfully_reco / eff_fully_reco)
        ratio       = (npart_reco / nfully_reco) * (eff_fully_reco / eff_part_reco)
        ratio       = (npart_reco / nfully_reco) * scale

        nfully_reco = (npart_reco / ratio) * scale
        nfully_reco = npart_reco  * (scale / ratio)
        nfully_reco = npart_reco  * fac

        scale = eff_fully_reco / eff_part_reco
        ```
        '''
        fac = self._cfg.parameters.get_factor(
            pdf_fr  = pdf_fr,
            pdf_pr  = pdf_pr,
            qsq_src = qsq_src,
            qsq_tgt = qsq_tgt)
        npr = self._cfg.parameters.get_part_reco_yield(qsq_comp = qsq_src, qsq_bin = qsq_tgt)
        nfr = zfit.ComposedParameter(
            f'nfr_{qsq_src}_{qsq_tgt}',
            func  = lambda d_par : d_par['npr'] * d_par['fac'],
            params= {'npr' : npr, 'fac' : fac} )

        pdf_fr.set_yield(nfr)

        return pdf_fr
    #-----------------------------
    def __extend_prc(self, qsq_src : Qsq, qsq_tgt : Qsq, pdf : zpdf) -> zpdf:
        '''
        Parameters
        ------------------
        qsq_src : q2-bin where data is taken
        qsq_tgt : q2-bin meant to be modelled
        pdf     : PDF to extend

        Returns
        ------------------
        PDF with yield set
        '''
        npr = self._cfg.parameters.get_part_reco_yield(qsq_comp = qsq_src, qsq_bin = qsq_tgt)
        pdf.set_yield(npr)

        return pdf
    #-----------------------------
    def __get_model_type(
        self,
        qsq_src : Qsq,
        qsq_tgt : Qsq) -> Literal['kde', 'parametric']:
        '''
        Parameters
        ---------------
        qsq_src : q2-bin where component originally exists
        qsq_tgt : q2-bin for which PDF is needed

        Returns
        ---------------
        Type of PDF used for this bin, either kde or parametric
        '''
        if _QSQ_NAME == 'q2_dtf': # DTF cut allows parametric fits, no tail shaping
            raise ValueError(f'Incorrect q2 used in ratio fits: {_QSQ_NAME}')

        if qsq_src == qsq_tgt: # non-dtf cut shapes tails in non-leaked components
            return 'kde'

        # Leakage components have less shaping with standard q2
        return 'parametric'
    #-----------------------------
    def __get_mc_pdf(
        self,
        comp    : Component,
        qsq_src : Qsq,
        qsq_tgt : Qsq) -> zpdf:
        '''
        Parameters
        ---------------
        comp    : Component associated to PDF needed
        qsq_src : q2-bin where component originally exists
        qsq_tgt : q2-bin for which PDF is needed

        Returns
        ---------------
        Zfit PDF from MC fit
        '''
        trigger = Trigger.get_main_trigger(project = self._project, channel = _TARGET_CHANNEL)
        obs     = self._cfg.observable.mass_obs
        model   = self.__get_model_type(qsq_src = qsq_src, qsq_tgt = qsq_tgt)

        sel       = dict()
        sel['q2'] = f'({_QSQ_NAME} > {qsq_tgt.lower_bound}) & ({_QSQ_NAME} < {qsq_tgt.upper_bound})'
        with DataStore.selection(sel = sel, update = True):
            obj = PdfBuilder(
                name    = f'{_QSQ_NAME}/{self._cfg.binning.dir_path}/{model}',
                comp    = comp,
                trigger = trigger,
                qsq     = qsq_tgt)

            mod = obj.get_model(
                obs_ext = obs,
                use_kde = model == 'kde',
                mode    = Mode.read)

            pdf = mod.get_pdf(name = comp.value)

        return pdf
    #-----------------------------
    def __get_fr_pdf(self, qsq_src : Qsq, qsq_tgt : Qsq) -> zpdf:
        '''
        Parameters
        ------------------
        qsq_src: q2-bin where data is taken
        qsq_tgt: q2-bin meant to be modelled

        Returns
        ------------------
        Fully reconstructed component's PDF, not extended
        '''
        comp = self.__component_from_qsq(
            qsq          = qsq_src,
            is_part_reco = False)

        pdf = self.__get_mc_pdf(
            comp    = comp,
            qsq_src = qsq_src,
            qsq_tgt = qsq_tgt)

        is_leakage = qsq_src != qsq_tgt
        self.__set_fr_pars(pdf = pdf, is_leakage = is_leakage)

        return pdf
    #-----------------------------
    def __set_fr_pars(self, pdf : zpdf, is_leakage : bool) -> None:
        '''
        Fix/Float parameters in PDF

        Parameters
        -----------------
        pdf: PDF used to describe fully reconstructed candidates
        '''
        pars = pdf.get_params(floating = None)
        for par in pars:
            par.floating = False

        if not is_leakage:
            return

        try:
            [mu] = [ par for par in pars if par.name.startswith('mu_') ]
            [sg] = [ par for par in pars if par.name.startswith('sg_') ]
        except Exception as exc:
            sut.print_pdf(pdf = pdf)
            raise ValueError('Cannot extract mean and width from fully reco PDF') from exc

        mu.floating = True
        sg.floating = True
    #-----------------------------
    def __component_from_qsq(self, qsq : Qsq, is_part_reco : bool) -> Component:
        '''
        Parameters
        -------------
        qsq         : q2-bin for which component is needed
        is_part_reco: If True will return part reco component

        Returns
        -------------
        Object representing decay
        '''
        if qsq == Qsq.jpsi and is_part_reco:
            return Component.bpjpsixee  if self._project == Project.rk else Component.bdjpsixee

        if qsq == Qsq.psi2 and is_part_reco:
            return Component.bppsi2xee  if self._project == Project.rk else Component.bdpsi2xee

        if qsq == Qsq.jpsi and not is_part_reco:
            return Component.bpkpjpsiee if self._project == Project.rk else Component.bdkstkpijpsiee

        if qsq == Qsq.psi2 and not is_part_reco:
            return Component.bpkppsi2ee if self._project == Project.rk else Component.bdkstkpipsi2ee

        raise ValueError(f'Cannot find component for: {qsq}/{is_part_reco}')
    #-----------------------------
    def __get_pr_pdf(self, qsq_src : Qsq, qsq_tgt : Qsq) -> zpdf:
        r'''
        Parameters
        ------------------
        qsq_src : q2 bin from which dataset to be smeared will be taken
        qsq_tgt : q2 bin where PDF lives, target q2.

        Returns
        ------------------
        Extended PDF from partially reconstructed component in `qsq_tgt` bin for component associated to `qsq_src`.
        E.g. $B -> \psi(2S) X$ PDF in high-q2 bin for `qsq_comp=psi2` and `qsq_tgt=high`
        '''
        cfg = TransferFunctionMakerConf.load(
            binning  = self._binning,
            project  = self._project,
            source   = qsq_src,
            target   = qsq_tgt)

        obj = PrecMaker(
            cfg     = cfg,
            binning = self._binning,
            project = self._project)

        pdf = obj.get_pdf(
            name = f'{qsq_src}_{qsq_tgt}',
            mode = Mode.read)

        return pdf
    #-----------------------------
    def __get_trfc(self, qsq_src : Qsq, qsq_tgt : Qsq) -> TransferFunction:
        '''
        Parameters
        ------------------
        qsq_src/tgt: Source and target q2-bin, needed to get transfer function

        Returns
        ------------------
        Transfer function
        '''
        cfg         = TransferFunctionMakerConf.load(
            source  = qsq_src,
            target  = qsq_tgt,
            project = self._project,
            binning = self._cfg.binning.to_str())

        obj          = TransferFunctionMaker(
            cfg      = cfg,
            project  = self._project)

        return obj.get_trf(mode = Mode.read)
    #-----------------------------
    def get_ratio(self, mode : Mode) -> CCbarRatio:
        '''
        Parameters
        -----------------
        update: If True will remake fits, etc even if outputs already exist

        Returns
        -----------------
        Ratio of part reco over fully reco components
        '''
        json_path = self._out_dir / 'parameters.json'

        mode.validate(path = json_path)
        if json_path.exists() and not mode.skip_reading:
            log.info(f'Parameters file found: {json_path}')
            rat = CCbarRatio.from_json(path = json_path)

            return rat

        log.info('Parameters file not found, recalculating ratio')

        rat = self.__get_ratio()
        rat.to_json(path = json_path)

        return rat
#-----------------------------
