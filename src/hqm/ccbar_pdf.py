'''
Module holding CCbarPDF class
'''
from pathlib        import Path
from typing         import Final
from dmu.generic    import Serializable
from dmu.stats      import FittedModel, zfit
from pydantic       import BaseModel
from rx_common      import Channel, Component, Project, Qsq, Trigger
from dmu.stats      import SplineRepr
from hqm.binning    import BinningConf
from hqm.config     import CCbarRatioCalculatorConf, SerializationConf, TransferFunctionMakerConf

from hqm.data_store import DataStore
from hqm.pdf_mc     import PdfBuilder
from hqm.prec_maker import PrecMaker
from hqm.ratc       import CCbarRatioCalculator

type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space

_SOURCE_QSQ     : Final[Qsq]       = Qsq.psi2
_TARGET_QSQ     : Final[Qsq]       = Qsq.high
_TARGET_CHANNEL : Final[Channel]   = Channel.ee
_FULL_RECO_COMP : Final[Component] = Component.bpkppsi2ee
_RATIO_NAME     : Final[str]       = 'rat_psi2' # Fraction used between part_reco and fully reco components
# ---------------------------------
class CCbarPDF(BaseModel, Serializable, frozen = True):
    '''
    Class representing charmonium PDF
    '''
    part_reco : SplineRepr
    full_reco : FittedModel
    ratio     : tuple[float,float]
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
        pdf = obj.get_pdf(update = True)

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
        comp    = _FULL_RECO_COMP
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
                update = True)
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

            ratio = cal.get_ratio(update = False)

        return ratio.get_value(name = _RATIO_NAME)
    # ---------------------------------
    def get_pdf(
        self, 
        obs    : zobs,
        update : bool) -> CCbarPDF:
        '''
        Parameters
        ------------
        obs   : Observable of PDF
        update: If true will remake PDF even if found

        Returns
        ------------
        PDF representing ccbar component
        '''
        json_path = CCbarPDF.get_path(
            binning = self.__binning,
            project = self.__project)

        if json_path.exists() and not update:
            return CCbarPDF.from_json(path = json_path)

        pdf_pr = self.__get_pr()
        pdf_fr = self.__get_fr(obs = obs)
        ratio  = self.__get_ratio()

        model = CCbarPDF(
            part_reco = pdf_pr,
            full_reco = pdf_fr,
            ratio     = ratio)

        model.to_json(path = json_path)

        return model
# ---------------------------------
