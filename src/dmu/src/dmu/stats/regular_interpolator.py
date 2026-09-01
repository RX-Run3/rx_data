import numpy             as np
import numpy.typing      as npt
import tensorflow        as tf

from tensorflow_graphics.math.interpolation import bspline
from tensorflow                             import Tensor

type NpFltArr = npt.NDArray[np.float64]
# ------------------------------
class RegularInterpolator[T]:
    '''
    Class meant to interpolate regular grids of points
    '''
    # ------------------------------
    def __init__(
        self,
        xs     : NpFltArr,
        ys     : NpFltArr,
        degree : int = 3):
        '''
        Parameters
        ----------------
        xs : Regular numpy array of x values
        ys : Values of function at xs
        int: Interpolation degree
        '''
        self.__xs     = xs
        self.__ys     = tf.constant(ys, dtype=tf.float32)
        self.__degree = degree
        self.__dx     = xs[1] - xs[0]
    # ------------------------------
    def interpolate(self, xs : T) -> T:
        '''
        Parameters
        -------------
        xs: Values at which to interpolate, Tensor or numpy array

        Returns
        -------------
        Interpolated values, Tensor or numpy array
        '''
        min_ind   = 0.0
        max_ind   = len(self.__xs) - self.__degree - 1.0
        positions = (xs - self.__xs[0]) / self.__dx - 1.0

        positions = np.clip(
            a     = positions,
            a_min = min_ind,
            a_max = max_ind)

        positions = tf.constant(positions, dtype=tf.float32)

        result       = bspline.interpolate(
            positions= positions,
            knots    = self.__ys,
            degree   = self.__degree,
            cyclical = False)

        if isinstance(xs, Tensor):
            return result

        return result.numpy()
# ------------------------------
