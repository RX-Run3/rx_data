'''
Module holding PdfBuilder
'''
import matplotlib.pyplot as plt

from pathlib        import Path
from dmu.workflow   import Cache
from dmu.generic    import utilities as gut
from pydantic       import BaseModel
from rx_common      import Channel, Component, Mass, Trigger, Qsq
from dmu.stats      import Fitter, Model, ModelFactory, FittedModel
from dmu.stats      import ZFitPlotter, ZFitPlotterConf, zfit
from hqm.data_store import DataStore 

zpdf = zfit.pdf.BasePDF
zdat = zfit.data.Data
zobs = zfit.Space

_MODELS : dict[Channel,list[Model]] = {
    Channel.ee : [Model.dscb], 
    Channel.mm : [Model.dscb, Model.gauss]}
# ----------------------------
class RangesConf(BaseModel, frozen = True):
    '''
    Object meant to configure how parameter and plotting ranges are set
    '''
    mu : tuple[float,float,float]
    sg : tuple[float,float,float]
    rn : tuple[float,float]
# ----------------------------
class PdfBuilderConf(BaseModel, frozen = True):
    '''
    Class meant to configure PDF building
    '''
    electron : dict[Qsq,dict[Qsq,RangesConf]]
    muon     : dict[Qsq,dict[Qsq,RangesConf]]
    # ----------------------------
    def __qsq_from_component(self, comp : Component) -> Qsq:
        '''
        Parameters
        -----------------
        comp: Component to be fitted

        Returns
        -----------------
        q2-bin associated to component, i.e. where this component exists
        '''
        jpsi_comp = [
            Component.bpkpjpsiee, Component.bdkstkpijpsiee,
            Component.bpkpjpsimm, Component.bdkstkpijpsimm]

        psi2_comp = [
            Component.bpkppsi2ee, Component.bdkstkpipsi2ee,
            Component.bpkppsi2mm, Component.bdkstkpipsi2mm]

        high_comp = [Component.bpkpee, Component.bdkstkpiee]

        if comp in jpsi_comp:
            return Qsq.jpsi

        if comp in psi2_comp:
            return Qsq.psi2

        if comp in high_comp:
            return Qsq.high

        raise ValueError(f'Invalid component: {comp}')
    # ----------------------------
    def read_conf(
        self, 
        comp : Component, 
        trig : Trigger, 
        qsq  : Qsq) -> RangesConf:
        '''
        Returns
        -------------
        Configuration object storing range information
        '''
        inner_qsq = self.__qsq_from_component(comp = comp)
        data      = self.electron if trig.is_electron else self.muon

        return data[qsq][inner_qsq]
    # ----------------------------
    @classmethod
    def load(cls) -> 'PdfBuilderConf':
        '''
        Returns config object from YAML file
        '''
        data = gut.load_data(package = 'hqm_data', fpath = 'config/models.yaml')

        return cls(**data)
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
        self.__cfg  = PdfBuilderConf.load()
    # ----------------------------
    def _get_mc_pdf(self) -> zpdf:
        '''
        Returns
        ---------------
        PDF associated to MC
        '''
        if self.model_path.exists():
            fmod = FittedModel.from_json(path = self.model_path)
            return fmod.pdf

        cfg_par  = self.__cfg.read_conf(
            comp = self.__comp, 
            trig = self.__trig,
            qsq  = self.__qsq )

        values = {
            'mu': cfg_par.mu,
            'sg': cfg_par.sg}

        mass   = Mass.raw_from_project(project = self.__trig.project)
        obs    = mass.obs 

        models = _MODELS[self.__trig.channel] 
        obs    = zfit.Space('mass', limits = cfg_par.rn)

        name = 'pdf_mc'
        fac  = ModelFactory(
            preffix  = name,
            obs      = obs,
            l_shared = ['mu', 'sg'],
            l_float  = [],
            values   = values,
            l_pdf    = models)
        pdf = fac.get_pdf()

        data= self._get_data(obs = obs, mass = mass)
        ftr = Fitter(pdf = pdf, data = data)
        res = ftr.fit()
        print(res)

        self._plot_fit(cfg_par = cfg_par, data = data, pdf = pdf)

        fmod      = FittedModel.from_fit(cfg = fac.cfg, pdf = pdf, res = res)
        fmod.to_json(path = self.model_path)

        return pdf
    # ----------------------------
    def _get_data(self, obs : zobs, mass : Mass) -> zdat:
        obj    = DataStore(
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

        return data
    # ----------------------------
    def _plot_fit(
        self, 
        cfg_par : RangesConf, 
        data    : zdat, 
        pdf     : zpdf) -> None:
        cfg_plt    = ZFitPlotterConf.default()
        settings   = {
            'title'      : f'{self.__comp.latex}; {self.__trig.value} trigger; {self.__qsq.latex} bin',
            'plot_range' : cfg_par.rn}
        cfg_plt = cfg_plt.model_copy(update = settings)

        ptr = ZFitPlotter(data = data, model = pdf)
        ptr.run(cfg = cfg_plt)

        cache_dir = Cache.get_cache_dir()
        plt.savefig(cache_dir / 'fit.png')
        plt.close()
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
    @property
    def model_path(self) -> Path:
        '''
        Path to JSON file with model
        '''
        cache_dir = Cache.get_cache_dir()

        return cache_dir / 'model.json'
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
