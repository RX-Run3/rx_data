'''
Module holding PdfBuilder
'''
import matplotlib.pyplot as plt

from dmu.workflow   import Cache
from rx_common      import Component, Mass, Trigger, Qsq
from dmu.stats      import Fitter, Model, ModelFactory, ZFitPlotter, ZFitPlotterConf, zfit
from hqm.data_store import DataStore 

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
        mass = Mass.raw_from_project(project = self.__trig.project)
        if self.__trig.is_electron:
            values = {
                'sg': ( 100.,   10.,  500.),
                'mu': (5280., 4500., 6500.)}
            obs    = mass.obs 
            models = [Model.dscb]
        else:
            values = {
                'sg': ( 15.,   10.,    20.),
                'mu': (5280., 5270., 5310.)}
            obs    = zfit.Space('mass', limits = (5000, 5500))
            models = [Model.dscb, Model.gauss]

        obj  = DataStore(
            comp= self.__comp,
            trig= self.__trig,
            qsq = self.__qsq,)
        masses, weights = obj.get_array(mass = mass)

        data = zfit.Data.from_numpy(
            obs     = obs, 
            array   = masses, 
            weights = weights)
        if not isinstance(data, zfit.Data):
            raise ValueError('Invalid data')

        fac = ModelFactory(
            preffix  = 'prf',
            obs      = obs,
            l_shared = ['mu', 'sg'],
            l_float  = [],
            values   = values,
            l_pdf    = models)

        pdf = fac.get_pdf()

        ftr = Fitter(pdf = pdf, data = data)
        res = ftr.fit()
        print(res)

        plot_range = (4600, 6500) if self.__trig.is_electron else (5000, 5500)
        cfg        = ZFitPlotterConf.default()

        settings   = {
            'title'      : f'{self.__comp.latex}; {self.__trig.value} trigger; {self.__qsq.latex} bin',
            'plot_range' : plot_range}
        cfg        = cfg.model_copy(update = settings)

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg)

        cache_dir = Cache.get_cache_dir()
        plt.savefig(cache_dir / 'fit.png')
        plt.close()

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
