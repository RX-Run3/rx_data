'''
File holding CCbarRatioCalculator and CCbarRatio classes
'''

import zfit
import numpy

from typing         import Final
from pydantic       import BaseModel
from dmu.stats      import FitResult
from dmu.generic    import Serializable
from hqm.data_store import DataStore
from hqm.prec_maker import PrecMaker
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
        self._plotter  = Plotter(out_dir = self._out_dir)
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
        pdf   = self.__get_model(qsq = qsq)
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
        pdf_prjp = self.__extend_prc(qsq_src = Qsq.jpsi, qsq_tgt = qsq, pdf = pdf_prjp)
        pdf_frjp = self.__get_fr_pdf(qsq_src = Qsq.jpsi, qsq_tgt = qsq)
        self._cfg.parameters.set_scale(
            fr  = pdf_frjp,
            pr  = pdf_prjp,
            qsq = qsq)

        pdf_prps = self.__get_pr_pdf(qsq_src = Qsq.psi2, qsq_tgt = qsq)
        pdf_prps = self.__extend_prc(qsq_src = Qsq.jpsi, qsq_tgt = qsq, pdf = pdf_prps)
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
    def __get_mc_pdf(
        self, 
        comp    : Component, 
        qsq     : Qsq, 
        channel : Channel) -> zpdf:
        '''
        Parameters
        ---------------
        comp: Component associated to PDF needed
        qsq : q2-bin for which PDF is needed

        Returns
        ---------------
        Zfit PDF from MC fit
        '''
        trigger = Trigger.get_main_trigger(project = self._project, channel = channel)
        obs     = self._cfg.observable.fit_obs

        obj = PdfBuilder(
            name    = 'pdf_mc',
            comp    = comp,
            trigger = trigger,
            qsq     = qsq)

        mod = obj.get_model(obs = obs)

        return mod.pdf
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
        ratio       = npart_reco_total             / nfully_reco_total
        ratio       = (npart_reco / eff_part_reco) / (nfully_reco / eff_fully_reco)
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

        pdf = self.__get_mc_pdf(comp = comp, qsq = qsq_tgt, channel = _TARGET_CHANNEL)
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
        cfg = TransferFunctionMakerConf.load(
            variable = 'none',
            project  = self._project,
            source   = qsq_src,
            target   = qsq_tgt)

        obj = PrecMaker(
            cfg     = cfg[0], 
            block   = self._block,
            project = self._project)

        return obj.get_pdf(update = False)
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
            project  = self._project,
            bin      = self._cfg.binning.bin,
            variable = self._cfg.binning.variable)

        obj          = TransferFunctionMaker(
            cfg      = cfg,
            project  = self._project,
            block    = self._block)

        return obj.get_trf(update = False)
    #-----------------------------
    def get_ratio(self, update : bool) -> CCbarRatio:
        '''
        Parameters
        -----------------
        update: If True will remake fits, etc even if outputs already exist

        Returns
        -----------------
        Ratio of part reco over fully reco components
        '''
        json_path = self._out_dir / 'parameters.json'
        if json_path.exists() and not update:
            log.info(f'Parameters file found: {json_path}')
            rat = CCbarRatio.from_json(path = json_path)

            return rat

        log.info('Parameters file not found, recalculating ratio')

        rat = self.__get_ratio()
        rat.to_json(path = json_path)

        return rat
#-----------------------------
