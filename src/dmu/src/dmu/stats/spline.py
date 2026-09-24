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
class SplineRepr(BaseModel, Serializable):
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
        self.representation.to_json(path = path)
    # ------------------------------
    @property
    def representation(self) -> SplineRepr:
        name, = self.obs

        return SplineRepr(
            obs_name = name,
            obs_range= range_from_obs(self.space),
            name = self.__name,
            label= self.__label,
            xs   = self.__xs.tolist(),
            ys   = self.__ys.tolist(),
        )
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

        pdf = cls(
            name = pdf.name,
            label= pdf.label,
            obs  = pdf.space,
            xs   = xs,
            ys   = ys)

        return pdf
    # ------------------------------
    @classmethod
    def from_json(
        cls,
        path : Path,
        name : str | None = None) -> 'SplinePDF':
        '''
        Parameters
        ---------------
        path: Path to JSON file where PDF is stored
        name: If specified, will name the PDF like this, otherwise will pick name from JSON file
        '''
        cfg = SplineRepr.from_json(path = path)

        if not name:
            name = cfg.name

        return cls(
            obs = cfg.obs,
            xs  = np.array(cfg.xs),
            ys  = np.array(cfg.ys),
            name= name)
    # ------------------------------
    def _unnormalized_pdf(self, x : Tensor):
        x = zfit.z.unstack_x(value = x)

        return self.__interpolator.interpolate(xs = x)
# ------------------------------
