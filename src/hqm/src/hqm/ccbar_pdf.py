'''
Module holding CCbarPDF class
'''
import numpy

from functools      import cached_property
from pathlib        import Path
from typing         import Final
from dmu.generic    import Serializable
from dmu.stats      import FittedModel, ObsConf, zfit, SplinePDF
from pydantic       import BaseModel
from rx_common      import Channel, Component, Project, Qsq, Trigger
from dmu            import LogStore
from dmu.stats      import SplineRepr
from hqm.binning    import BinningConf
from hqm.config     import CCbarRatioCalculatorConf, SerializationConf, TransferFunctionMakerConf

from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder
from hqm.prec_maker import PrecMaker
from hqm.ratc       import CCbarRatioCalculator
from dmu.generic    import Mode

type zsum = zfit.pdf.SumPDF
type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space

_OBS_NAME       : Final[str]                     = 'Mass'    # Default observable name
_SOURCE_QSQ     : Final[Qsq]                     = Qsq.psi2
_TARGET_QSQ     : Final[Qsq]                     = Qsq.high
_TARGET_CHANNEL : Final[Channel]                 = Channel.ee
_RATIO_NAME     : Final[str]                     = 'rat_psi2' # Fraction used between part_reco and fully reco components
_FULL_RECO_COMP : Final[dict[Project,Component]] = {
         Project.rk   : Component.bpkppsi2ee,
         Project.rkst : Component.bdkstkpipsi2ee,
}

log=LogStore.add_logger('hqm:ccbar_pdf')
# ---------------------------------
class CCbarPDF(BaseModel, Serializable, frozen = True):
    '''
    Class representing charmonium PDF
    '''
    obs       : ObsConf
    part_reco : SplineRepr
    full_reco : FittedModel
    ratio     : tuple[float,float]
    # ---------------------------------
    @cached_property
    def pdf(self) -> zsum:
        '''
        Sum of part reco and fully reco PDFs
        '''
        return self.get_pdf(obs_name = _OBS_NAME, suffix = '')
    # ---------------------------------
    def get_pdf(
        self,
        obs_name: str,
        suffix  : str,
        name    : str = 'ccbar') -> zsum:
        '''
        Parameters
        ---------------
        obs_name: String used as observable name, e.g. Mass, B_Mass
        name    : Name of returned PDF
        suffix  : String that will be located at the end of
                PDF and parameter names. Meant to allow combining PDFs and avoiding
                name clashes

        Returns
        ---------------
        Sum of part reco and fully reco PDFs
        '''
        obs       = self.obs.model_copy(update = {'name' : obs_name})
        part_reco = self.part_reco.model_copy(update = {'obs_name' : obs_name})
        full_reco = self.full_reco.model_copy(update = {'obs_conf' : obs})

        if suffix:
            suffix = f'_{suffix}'

        pdf_pr = SplinePDF(
            obs = part_reco.obs,
            xs  = numpy.array(part_reco.xs),
            ys  = numpy.array(part_reco.ys),
            name= f'part-reco{suffix}')

        fr_name= full_reco.name
        pdf_fr = full_reco.get_pdf(name = f'{fr_name}{suffix}')

        val, _ = self.ratio # part-reco / fully-reco

        fval = val / (1 + val)  # part-reco / total
        pdfs = [pdf_pr, pdf_fr]

        frac = zfit.param.Parameter(f'fr_pr_fr{suffix}', fval, 0, 1)
        pdf  = zfit.pdf.SumPDF(
            name  = name,
            pdfs  = pdfs,
            fracs = frac,
            obs   = obs.obs)

        return pdf
    # ---------------------------------
    @classmethod
    def get_path(
        cls,
        project : Project,
        binning : str) -> Path:
        '''
        Parameters
        ---------------
        project: E.g. rk, rkst
        binning: String representing binning associated to this object

        Returns
        ---------------
        Path to JSON file with serialized instance of CCbarPDF
        '''
        bins_cfg = BinningConf.load()
        bin_cfg  = bins_cfg.from_str(binning = binning)
        cfg      = SerializationConf(binning = bin_cfg)

        return cfg.make_path(
            project= project,
            fname  = 'pdf.json',
            kind   = 'ccbar_pdf')
# ---------------------------------
class CCbarPDFMaker:
    '''
    Class mean to provide charmonium PDF for high-q2 bin
    The PDF consists of the sum of the part reco and fully reco PDF
    '''
    # ---------------------------------
    def __init__(self, binning : str, project : Project):
        '''
        Parameters
        ---------------
        binning: String specifying bin, e.g. "block-1 mva_cmb-3 mva_prc-3"
        project: rk or rkst
        '''
        self.__binning = binning
        self.__project = project
    # ---------------------------------
    def __get_pr(self) -> SplineRepr:
        '''
        Returns
        --------------
        Spline representation associated to part reco PDF
        '''
        cfg = TransferFunctionMakerConf.load(
            binning  = self.__binning,
            project  = self.__project,
            source   = _SOURCE_QSQ,
            target   = _TARGET_QSQ)

        obj = PrecMaker(
            cfg     = cfg,
            binning = self.__binning,
            project = self.__project)
        pdf = obj.get_pdf(
            name = 'part-reco',
            mode = Mode.read)

        return pdf.representation
    # ---------------------------------
    def __get_fr(self, obs : zobs) -> FittedModel:
        '''
        Parameters
        --------------
        obs: Observable used for fully reconstructed component

        Returns
        --------------
        Object representing fully reconstructed component's fit
        '''
        qsq     = _TARGET_QSQ
        comp    = _FULL_RECO_COMP[self.__project]
        channel = _TARGET_CHANNEL

        trig = Trigger.get_main_trigger(
            channel = channel,
            project = self.__project)

        bin_obj  = BinningConf.load()
        bins     = bin_obj.from_str(self.__binning)

        sel       = bins.selection
        sel['q2'] = f'(q2 > {qsq.lower_bound}) & (q2 < {qsq.upper_bound})'
        with DataStore.selection(sel = sel, update = False):
            obj = PdfBuilder(
                name    = f'q2/{bins.dir_path}/parametric',
                comp    = comp,
                trigger = trig,
                qsq     = qsq)

            return obj.get_model(
                obs_ext= obs,
                use_kde= False,
                mode   = Mode.read)
    # ---------------------------------
    def __get_ratio(self) -> tuple[float,float]:
        '''
        Returns
        --------------
        Tuple holding value and error of ratio of partly and fully
        reconstructed charmonium
        '''
        cfg = CCbarRatioCalculatorConf.load(binning = self.__binning)
        with DataStore.selection(sel = cfg.binning.selection, update = False):
            cal         = CCbarRatioCalculator(
                cfg     = cfg,
                binning = self.__binning,
                project = self.__project)

            ratio = cal.get_ratio(mode = Mode.read)

        return ratio.get_value(name = _RATIO_NAME)
    # ---------------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Directory where outputs go
        '''
        json_path = CCbarPDF.get_path(
            binning = self.__binning,
            project = self.__project)

        return json_path.parent
    # ---------------------------------
    def get_pdf(
        self,
        obs  : zobs,
        mode : Mode) -> CCbarPDF:
        '''
        Parameters
        ------------
        obs : Observable of PDF
        mode: Specifies how to make PDF, reuse, read, write, update

        Returns
        ------------
        PDF representing ccbar component
        '''
        json_path = CCbarPDF.get_path(
            binning = self.__binning,
            project = self.__project)

        mode.validate(path = json_path)

        if json_path.exists() and not mode.skip_reading:
            log.info('CCbar PDF found, reusing it')
            return CCbarPDF.from_json(path = json_path)

        log.info('CCbar PDF not found, remaking it')

        pdf_pr = self.__get_pr()
        pdf_fr = self.__get_fr(obs = obs)
        ratio  = self.__get_ratio()

        model = CCbarPDF(
            obs       = ObsConf.from_obs(obs = obs),
            part_reco = pdf_pr,
            full_reco = pdf_fr,
            ratio     = ratio)

        model.to_json(path = json_path)

        return model
# ---------------------------------
