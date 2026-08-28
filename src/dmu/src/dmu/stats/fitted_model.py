'''
Module holding the FittedModel class
'''

from pydantic       import BaseModel
from dmu.generic    import Serializable
from dmu.stats      import utilities as sut

from .fit_result    import FitResult
from .model_factory import ModelFactoryConf
from .imports       import zfit
from .model_factory import ModelFactory

zpdf = zfit.pdf.BasePDF
zobs = zfit.Space
# -------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    name  : str
    upper : float
    lower : float
    #---------------------------------
    @classmethod
    def from_obs(cls, obs : zobs) -> 'ObsConf':
        '''
        Parameters
        --------------
        obs: Observable

        Returns
        --------------
        Configuration needed to build observable
        '''
        lower, upper = sut.range_from_obs(obs = obs)

        return cls(name = obs.name, lower = lower, upper = upper)
    #---------------------------------
    @property
    def obs(self) -> zfit.Space:
        '''
        Observable that will be fitted for source datasets
        '''
        return zfit.Space(self.name, limits = (self.lower, self.upper))
#---------------------------------
class FittedModel(BaseModel, Serializable, frozen = True):
    '''
    Class meant to represent a transfer function
    '''
    name       : str
    obs_conf   : ObsConf
    model_conf : ModelFactoryConf
    fit_result : FitResult
    #----------------------
    @classmethod
    def from_fit(
        cls,
        cfg : ModelFactoryConf,
        pdf : zpdf,
        res : FitResult) -> 'FittedModel':
        '''
        Parameters
        -----------------
        mfc : Model factory configuration 
        pdf : PDF used in the fit
        res : Result of fit
        '''
        return cls(
            name       = pdf.name,
            obs_conf   = ObsConf.from_obs(obs = pdf.space),
            model_conf = cfg,
            fit_result = res)
    #----------------------
    @property
    def pdf(self) -> zpdf:
        '''
        PDF representing transfer function
        '''
        fac = ModelFactory.from_conf(
            prefix = self.name,
            obs    = self.obs_conf.obs,
            cfg    = self.model_conf)

        pdf  = fac.get_pdf()
        pars = pdf.get_params()

        self.fit_result.set_pars(pars = pars)

        return pdf
#---------------------------------
