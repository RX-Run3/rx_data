'''
Module holding SplinePDF class
'''
import zfit
import numpy        as np
import numpy.typing as npt

from .regular_interpolator import RegularInterpolator

type zobs     = zfit.Space
type NpFltArr = npt.NDArray[np.float64]
# ------------------------------
class SplinePDF(zfit.pdf.ZPDF):
    _N_OBS = 1
    _PARAMS = []
    # ------------------------------
    def __init__(
        self, 
        obs   : zobs, 
        *,
        name  : str = 'unnamed',
        label : str = 'unlabeled',
        norm  : zobs | None = None,
        xs    : NpFltArr, 
        ys    : NpFltArr):

        self.__interpolator = RegularInterpolator(xs = xs, ys = ys)

        super().__init__(
            obs,
            name  = name,
            label = label,
            norm  = norm)
    # ------------------------------
    def _unnormalized_pdf(self, x):
        x = zfit.z.unstack_x(value = x)

        return self.__interpolator.interpolate(xs = x)
# ------------------------------
