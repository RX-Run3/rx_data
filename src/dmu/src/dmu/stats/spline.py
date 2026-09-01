'''
Module holding SplinePDF class
'''
import zfit
import numpy        as np
import numpy.typing as npt

from pathlib               import Path
from tensorflow            import Tensor
from pydantic              import BaseModel
from dmu.generic           import Serializable

from .utilities            import range_from_obs
from .regular_interpolator import RegularInterpolator

type zobs     = zfit.Space
type zpdf     = zfit.pdf.BasePDF
type NpFltArr = npt.NDArray[np.float64]
# ------------------------------
class _SplineRepr(BaseModel, Serializable):
    '''
    Pydantic representation of SplinePDF
    '''
    obs_name : str
    obs_range: tuple[float,float]
    name     : str
    label    : str
    xs       : list[float]
    ys       : list[float]
    # ----------------------------
    @property
    def obs(self) -> zobs:
        '''
        Observable of SplinePDF
        '''
        return zfit.Space(self.obs_name, limits = self.obs_range)
# ------------------------------
class SplinePDF(zfit.pdf.ZPDF):
    _N_OBS = 1
    _PARAMS = []
    # ------------------------------
    def __init__( # noqa: PLR0913
        self, 
        obs   : zobs, 
        *,
        name  : str = 'unnamed',
        label : str = 'unlabeled',
        norm  : zobs | None = None,
        xs    : NpFltArr, 
        ys    : NpFltArr):

        self.__name = name
        self.__label= label
        self.__xs   = xs
        self.__ys   = ys

        self.__interpolator = RegularInterpolator(xs = xs, ys = ys)

        super().__init__(
            obs,
            name  = name,
            label = label,
            norm  = norm)
    # ------------------------------
    def to_json(self, path : Path) -> None:
        '''
        Parameters
        ----------------
        path: Path to JSON file where PDF will be saved
        '''
        name, = self.obs

        repr = _SplineRepr(
            obs_name = name,
            obs_range= range_from_obs(self.space),
            name = self.__name,
            label= self.__label,
            xs   = self.__xs.tolist(),
            ys   = self.__ys.tolist(),
        )

        repr.to_json(path = path)
    # ------------------------------
    @classmethod
    def from_non_spline(cls, pdf : zpdf, npoints : int = 400) -> 'SplinePDF':
        '''
        Parameters
        --------------
        pdf    : zfit PDF
        npoints: Number of points needed to scan PDF
        '''
        lower, upper = range_from_obs(obs = pdf.space)
        xs = np.linspace(lower, upper, npoints)
        ys = pdf.pdf(xs)

        if isinstance(ys, Tensor):
            ys = ys.numpy()

        return cls(obs = pdf.space, xs = xs, ys = ys)
    # ------------------------------
    @classmethod
    def from_json(cls, path : Path) -> 'SplinePDF':
        '''
        Parameters
        ---------------
        path: Path to JSON file where PDF is stored 
        '''
        cfg = _SplineRepr.from_json(path = path)

        return cls(
            obs = cfg.obs,
            xs  = np.array(cfg.xs),
            ys  = np.array(cfg.ys),
            name= cfg.name)
    # ------------------------------
    def _unnormalized_pdf(self, x):
        x = zfit.z.unstack_x(value = x)

        return self.__interpolator.interpolate(xs = x)
# ------------------------------
