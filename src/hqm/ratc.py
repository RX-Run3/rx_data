'''
File holding CCbarRatioCalculator and CCbarRatio classes
'''

import zfit
import numpy

from typing         import Final
from pydantic       import BaseModel
from dmu.stats      import FitResult, FittedModel
from dmu.generic    import Serializable
from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder
from hqm.config     import CCbarRatioCalculatorConf, TransferFunctionMakerConf
from hqm.trfc       import TransferFunction, TransferFunctionMaker
from rx_common      import Block, Channel, Component, Mass, Project, Qsq, Trigger
from dmu            import LogStore

from .plotter       import Plotter

log=LogStore.add_logger('hqm:ratc')

Loss = zfit.loss.ExtendedUnbinnedNLL
zpdf = zfit.pdf.BasePDF

_SOURCE_CHANNEL : Final[Channel] = Channel.mm # Channel used to get original part reco distribution
_TARGET_CHANNEL : Final[Channel] = Channel.ee # Channel where ratio will be extracted
#-----------------------------
class CCbarRatio(BaseModel, Serializable, frozen = True):
    '''
    Class representing ratio between fully and partly reconstructed charmonium
    '''
    res : FitResult
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
        block   : Block):
        '''
        Parameters
        ------------------
        cfg    : Object holding configuration
        block  : E.g. 1..8
        project: E.g. rk or rkst
        '''
        self._cfg      = cfg
        self._project  = project
        self._block    = block
        self._out_dir  = self._cfg.make_path(kind='ratios', project = project)
        self._plotter  = Plotter()
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
            name = 'fit_jpsi',
            nll  = nll_jpsi)

        self._plotter.plot_nll(
            name = 'fit_psi2',
            nll  = nll_psi2)

        return CCbarRatio(res = res)
    #-----------------------------
    def __get_nll(self, qsq : Qsq) -> Loss:
        '''
        Returns NLL for given q2 bin
        '''
        log.info(f'Building NLL in {qsq} bin')
        pdf   = self.__get_model(qsq= qsq)
        array = self.__get_target_data(qsq = qsq)
        zdat  = zfit.Data.from_numpy(
            obs  =self._cfg.observable.fit_obs,
            array=array)

        if not isinstance(zdat, zfit.Data):
            raise ValueError('Dataset is not unbinned')

        nll = zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=zdat)

        self._plotter.plot_array(name = f'data_arr_{qsq}', array = array)
        self._plotter.plot_data( name = f'dataset_{qsq}' , data  =  zdat)

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
        trigger = Trigger.get_main_trigger(project = self._project, channel = _TARGET_CHANNEL)
        mass    = Mass.raw_from_project(project = self._project)

        ds      = DataStore(
            qsq =qsq,
            trig=trigger,
            comp=Component.data_24)
        array, _= ds.get_array(mass = mass)

        return array
    #-----------------------------
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
        pdf_frjp = self.__get_fr_pdf(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        self._cfg.parameters.set_scale(
            fr  = pdf_frjp,
            pr  = pdf_prjp,
            qsq = qsq)

        pdf_prps = self.__get_pr_pdf(qsq_src = Qsq.psi2, qsq_tgt = qsq)
        pdf_frps = self.__get_fr_pdf(qsq_src = Qsq.psi2, qsq_tgt = qsq)
        self._cfg.parameters.set_scale(
            fr  = pdf_frps,
            pr  = pdf_prps,
            qsq = qsq)

        pdf  = zfit.pdf.SumPDF([pdf_prps, pdf_prjp, pdf_frps, pdf_frjp],
        obs  = self._cfg.observable.fit_obs)

        self._plotter.plot_model(name = f'model_{qsq}', pdf = pdf)

        return pdf
    #-----------------------------
    def __get_mc_pdf(self, comp : Component, qsq : Qsq, channel : Channel) -> FittedModel:
        '''
        Parameters
        ---------------
        comp: Component associated to PDF needed
        qsq : q2-bin for which PDF is needed

        Returns
        ---------------
        Zfit PDF from MC fit plus scaling
        '''
        trigger = Trigger.get_main_trigger(project = self._project, channel = channel)

        obj = PdfBuilder(
            comp    = comp,
            trigger = trigger,
            qsq     = qsq)

        return obj.get_model()
    #-----------------------------
    def __get_fr_pdf(self, qsq_src : Qsq, qsq_tgt : Qsq) -> zpdf:
        '''
        Parameters
        ------------------
        qsq_src: q2-bin where data is taken
        qsq_tgt: q2-bin meant to be modelled

        Returns
        ------------------
        Fully reconstructed component's PDF, with following parametrization

        ```math
        ratio       = (npart_reco / nfully_reco) * (eff_fully_reco / eff_part_reco)
        ratio       = (npart_reco / nfully_reco) * scale
        nfully_reco = (npart_reco / ratio) * scale
        nfully_reco = npart_reco  * (scale / ratio)
        nfully_reco = npart_reco  * fac
        ```
        '''
        comp = self.__component_from_qsq(
            qsq          = qsq_src,
            is_part_reco = False)

        mod = self.__get_mc_pdf(comp = comp, qsq = qsq_tgt, channel = _TARGET_CHANNEL)
        rat = self._cfg.parameters.get_ratio(qsq = qsq_tgt)
        scl = self._cfg.parameters.get_scale(qsq = qsq_tgt)

        fac = zfit.ComposedParameter(
            f'fac_{qsq_src}_{qsq_tgt}',
            func  = lambda d_par : d_par['scl'] / d_par['rat'],
            params= {'scl' : scl, 'rat' : rat} )

        npr = self._cfg.parameters.get_part_reco_yield(qsq_comp = qsq_src, qsq_bin = qsq_tgt)
        nfr = zfit.ComposedParameter(
            f'nfr_{qsq_src}_{qsq_tgt}',
            func  = lambda d_par : d_par['npr'] * d_par['fac'],
            params= {'npr' : npr, 'fac' : fac} )

        pdf = mod.pdf
        pdf.set_yield(nfr)

        return pdf
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
        trf       = self.__get_trfc(qsq_src = qsq_src, qsq_tgt = qsq_tgt)
        arr_src   = self.__get_source_data(qsq = qsq_src)

        kde_obs   = self._cfg.observable.kde_obs
        zdata     = zfit.Data.from_numpy(kde_obs, array=arr_src)
        pdf_src   = zfit.pdf.KDE1DimISJ(
            obs      = kde_obs,
            norm     = self._cfg.observable.fit_obs,
            data     = zdata,
            name     = 'PRec')

        comp             = self.__component_from_qsq(
            qsq          = qsq_src,
            is_part_reco = True)

        pdf_tgt   = zfit.pdf.FFTConvPDFV1(
            func  = pdf_src,
            kernel= trf.pdf,
            name  = comp,
            obs   = self._cfg.observable.kde_obs,
            norm  = self._cfg.observable.fit_obs,
            n     = self._cfg.fft_npt)

        nevt = self._cfg.parameters.get_part_reco_yield(qsq_comp = qsq_src, qsq_bin = qsq_tgt)
        pdf_tgt.set_yield(nevt)

        self._plotter.plot_model(name = f'trf_{qsq_src}_{qsq_tgt}', pdf = trf.pdf)
        self._plotter.plot_model(name = f'prc_{qsq_src}_{qsq_tgt}', pdf = pdf_tgt)
        self._plotter.plot_fit(name = f'kde_{qsq_src}_{qsq_tgt}', data= arr_src, pdf = pdf_src)

        return pdf_tgt
    #-----------------------------
    def __get_source_data(self, qsq : Qsq) -> numpy.ndarray:
        '''
        Parameters
        -------------
        qsq: q2-bin from which the data meant to be smeared will be taken

        Returns
        -------------
        Array with muon channel data to be smeared
        '''
        mass_cns = Mass.dtf_from_qsq(qsq = qsq, project = self._project)
        mass_raw = Mass.raw_from_project(project = self._project)
        trig     = Trigger.get_main_trigger(
            project = self._project,
            channel = _SOURCE_CHANNEL)

        obj     = DataStore(
            qsq = qsq,
            trig= trig,
            comp= Component.data_24)

        arr_raw, _   = obj.get_array(mass = mass_raw)
        arr_dtf, _   = obj.get_array(mass = mass_cns)

        mask         = arr_dtf < self._cfg.sb_mass
        arr_sideband = arr_raw[mask]

        return arr_sideband
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
        cfg          = TransferFunctionMakerConf.load_bin_cfg(
            source   = qsq_src,
            target   = qsq_tgt,
            bin      = self._cfg.binning.bin,
            variable = self._cfg.binning.variable)

        comp         = self.__component_from_qsq(qsq = qsq_src, is_part_reco = False)
        obj          = TransferFunctionMaker(
            cfg      = cfg,
            sample   = comp,
            project  = self._project,
            block    = self._block)

        return obj.get_trf()
    #-----------------------------
    def get_ratio(self) -> CCbarRatio:
        '''
        Returns
        -----------------
        Ratio of part reco over fully reco components
        '''
        json_path = self._out_dir / 'parameters.json'
        if json_path.exists():
            log.info(f'Parameters file found: {json_path}')
            rat = CCbarRatio.from_json(path = json_path)

            return rat

        log.info('Parameters file not found, recalculating ratio')

        rat = self.__get_ratio()
        rat.to_json(path = json_path)

        return rat
#-----------------------------
