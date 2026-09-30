'''
Module holding the FittedModel class
'''
from functools      import cached_property
from typing         import Self
from pydantic       import BaseModel
from dmu.generic    import Serializable
from dmu.stats      import utilities as sut

from .fit_result    import FitResult
from .model_factory import ModelFactoryConf
from .imports       import zfit
from .model_factory import ModelFactory

type zpdf = zfit.pdf.BasePDF
type zobs = zfit.Space
# -------------------------------------------------------------------
class ObsConf(BaseModel, frozen = True):
    '''
    Representation of zfit observable
    '''
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

        if obs.obs is None:
            raise ValueError(f'Invalid observable: {obs}')

        name, = obs.obs

        return cls(name = name, lower = lower, upper = upper)
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
    def with_obs(self, obs : zobs) -> Self:
        '''
        Parameters
        -------------------
        obs: Observable for which model is needed

        Returns
        -------------------
        Instance with observable overriden
        '''
        obs_conf = ObsConf.from_obs(obs = obs)

        return self.model_copy(update = {'obs_conf' : obs_conf})
    #----------------------
    @classmethod
    def from_fit(
        cls,
        name: str,
        cfg : ModelFactoryConf,
        pdf : zpdf,
        res : FitResult) -> 'FittedModel':
        '''
        Parameters
        -----------------
        name: Name of object, needed to name PDF parameters, etc
        mfc : Model factory configuration
        pdf : PDF used in the fit
        res : Result of fit
        '''
        return cls(
            name       = name,
            obs_conf   = ObsConf.from_obs(obs = pdf.space),
            model_conf = cfg,
            fit_result = res)
    #----------------------
    @cached_property
    def fixed_pdf(self) -> zpdf:
        '''
        PDF with fixed shape
        '''
        pdf = self.pdf
        for par in pdf.get_params():
            par.floating = False

        return pdf
    #----------------------
    @cached_property
    def pdf(self) -> zpdf:
        '''
        PDF representing transfer function
        '''
        return self.get_pdf(name = self.name)
    #----------------------
    def get_pdf(self, name : str) -> zpdf:
        '''
        Parameters
        ----------------
        name: Used to rename PDF paramenters

        Returns
        ----------------
        zfit PDF
        '''
        fac = ModelFactory.from_conf(
            prefix = name,
            obs    = self.obs_conf.obs,
            cfg    = self.model_conf)

        pdf  = fac.get_pdf()
        pars = pdf.get_params()

        if name != self.name:
            fit_result = self.fit_result.rename(
                original = self.name,
                new      = name)
        else:
            fit_result = self.fit_result

        fit_result.fix_pars(pars = pars)

        for phys_par_name in self.model_conf.floating:
            par_res   = fit_result.get_par(prefix = phys_par_name)
            try:
                [par_pdf] = [ par for par in pars if par.name == par_res.name ]
            except Exception as exc:
                raise ValueError(f'Cannot extract {par_res.name} from PDF') from exc

            par_pdf.floating = True

        return pdf
#---------------------------------
