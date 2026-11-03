'''
Module with NonParametricModel class
'''
import numpy

from typing      import Final
from pydantic    import BaseModel
from dmu.generic import Serializable
from functools   import cached_property

from .imports   import zfit
from .utilities import range_from_obs
from .spline    import SplinePDF

type zpdf = zfit.pdf.BasePDF
type zdat = zfit.Data

KDE  = zfit.pdf.KDE1DimISJ

_NPOINTS : Final[int] = 300 # Number of points used to scan PDF
# ----------------------------------------
class NonParametricModel(BaseModel, Serializable, frozen = True):
    '''
    Class representing non-parametric PDF
    '''
    obs : str
    name: str
    xs  : list[float]
    ys  : list[float]
    # ------------------------
    @classmethod
    def from_data(
        cls,
        name : str,
        data : zdat) -> 'NonParametricModel':
        '''
        Parameters
        ----------------
        name: Name of PDF
        data: Zfit data object

        Returns
        ----------------
        Instance of NonParametricModel
        '''
        pdf          = KDE(data = data)
        obs_name,    = pdf.obs
        lower, upper = range_from_obs(obs = pdf.space)

        xs = numpy.linspace(lower, upper, _NPOINTS).tolist()
        ys = pdf.pdf(xs).numpy().tolist()

        return cls(
            xs   = xs,
            ys   = ys,
            obs  = obs_name,
            name = name)
    # ------------------------
    @cached_property
    def pdf(self) ->  zpdf:
        '''
        Underlying zfit PDF
        '''
        return self.get_pdf(name = self.name)
    # ------------------------
    @cached_property
    def fixed_pdf(self) ->  zpdf:
        '''
        Underlying zfit PDF
        '''
        return self.pdf
    # ------------------------
    def get_pdf(self, name : str) -> zpdf:
        '''
        Parameters
        --------------
        name: New PDF name

        Returns
        --------------
        Renamed zfit pdf
        '''
        obs = zfit.Space(self.obs, limits = (min(self.xs), max(self.xs)))
        xs  = numpy.array(self.xs)
        ys  = numpy.array(self.ys)

        pdf = SplinePDF(
            obs  = obs,
            xs   = xs,
            ys   = ys,
            name = name)

        return pdf
# ----------------------------------------
