'''
Module holding PdfBuilder
'''
from fitter import ObservableConf
from rx_common   import Component, Trigger, Qsq
from dmu.stats   import zfit
from dmu.generic import utilities as gut

# Use direct imports to avoid circular imports
from fitter.sim_fitter import SimFitter
from fitter.configs    import ParametricConf 

zpdf = zfit.pdf.BasePDF
# ----------------------------
class PdfBuilder:
    '''
    Class meant to:

    - Load simulated data
    - Fit it
    - Scale PDF
    '''
    # ----------------------------
    def __init__(
        self, 
        comp   : Component,
        trigger: Trigger,
        qsq    : Qsq):
        '''
        Parameters
        ------------------
        qsq    : q2-bin
        comp   : Describes sample used for fit
        trigger: E.g. rk_ee_os
        '''
        self.__comp = comp
        self.__trig = trigger
        self.__qsq  = qsq
    # ----------------------------
    def _get_mc_pdf(self) -> zpdf:
        '''
        Returns
        -----------
        PDF from fit to MC sample
        '''
        data = gut.load_data(
            package='fitter_data', 
            fpath  =f'reso/{self.__trig.project}/{self.__trig.channel}/{self.__comp}_no_dtf.yaml')

        cfg     = ParametricConf(**data)
        cfg_obs = ObservableConf.default()
        cfg     = cfg.model_copy(update = {'cfg_obs' : cfg_obs})

        ftr = SimFitter(
            name     = 'main',
            cfg      = cfg,
            component= self.__comp,
            trigger  = self.__trig,
            q2bin    = self.__qsq)
        pdf = ftr.get_model()

        if pdf is None:
            raise ValueError('PDF not built')

        return pdf
    # ----------------------------
    def _scale_pdf(self, pdf : zpdf) -> zpdf:
        '''
        Parameters
        ----------------
        pdf: PDF from fit to MC

        Returns
        ----------------
        PDF with parameters scales for data/MC differences
        '''
        return pdf
    # ----------------------------
    def get_pdf(self) -> zpdf:
        '''
        Returns
        --------------
        zfit PDF representing MC after
        scaling for data/mc differences
        '''
        pdf = self._get_mc_pdf()
        pdf = self._scale_pdf(pdf = pdf)

        return pdf
# ----------------------------
