import numpy as np
import tensorflow as tf
import zfit.z.numpy as znp
import zfit
from .. import z as z
from ..core.basepdf import BasePDF as BasePDF
from ..core.serialmixin import SerializableMixin as SerializableMixin
from ..core.space import supports as supports
from ..serialization import Serializer as Serializer, SpaceRepr as SpaceRepr
from ..serialization.pdfrepr import BasePDFRepr as BasePDFRepr
from ..settings import run as run, ztypes as ztypes
from ..util import ztyping as ztyping
from ..util.exception import OverdefinedError as OverdefinedError, ShapeIncompatibleError as ShapeIncompatibleError
from ..util.ztyping import ExtendedInputType as ExtendedInputType, NormInputType as NormInputType
from ..z.math import weighted_quantile as weighted_quantile
from .dist_tfp import WrapDistribution as WrapDistribution
from collections.abc import Callable as Callable
from tensorflow_probability.python import distributions as tfd
from typing import Literal
from zfit._interfaces import ZfitData as ZfitData, ZfitParameter as ZfitParameter, ZfitSpace as ZfitSpace

def bandwidth_rule_of_thumb(data: znp.array, weights: znp.array | None, factor: float | int | znp.array = None) -> znp.array: ...
def bandwidth_silverman(data, weights): ...
def bandwidth_scott(data, weights): ...
def bandwidth_isj(data, weights): ...
def bandwidth_adaptive_geomV1(data, func, weights): ...
def bandwidth_adaptive_zfitV1(data, func, weights) -> znp.array: ...
def bandwidth_adaptive_stdV1(data, func, weights): ...
def adaptive_factory(func, grid): ...
def check_bw_grid_shapes(bandwidth, grid=None, n_grid=None) -> None: ...
def min_std_or_iqr(x, weights): ...
def calc_kernel_probs(size, weights): ...

class KDEHelper: ...

def padreflect_data_weights_1dim(data, mode, weights=None, limits=None, bandwidth=None): ...

class GaussianKDE1DimV1(KDEHelper, WrapDistribution):
    def __init__(self, obs: ztyping.ObsTypeInput, data: ztyping.ParamTypeInput, bandwidth: ztyping.ParamTypeInput | str = None, weights: None | np.ndarray | tf.Tensor = None, truncate: bool = False, *, extended: ExtendedInputType = None, norm: NormInputType = None, name: str = 'GaussianKDE1DimV1', label: str | None = None) -> None: ...

class KDE1DimExact(KDEHelper, WrapDistribution, SerializableMixin):
    bandwidth : float
    def __init__(
            self, 
            data: ztyping.XTypeInput, 
            *, 
            obs: ztyping.ObsTypeInput | None = None, 
            bandwidth: ztyping.ParamTypeInput | str | Callable | None = None, 
            kernel: tfd.Distribution = None, 
            padding: Callable | str | bool | dict[str,float] | None = None, 
            weights: np.ndarray | tf.Tensor | None = None, 
            extended: ExtendedInputType = None, 
            norm: NormInputType = None, 
            name: str | None = 'ExactKDE1DimV1', 
            label: str | None = None) -> None: ...

class KDE1DimExactRepr(BasePDFRepr):
    hs3_type: Literal['KDE1DimExact']
    data: np.ndarray | Serializer.types.DataTypeDiscriminated
    obs: SpaceRepr | None
    bandwidth: str | float | None
    kernel: None
    padding: bool | str | None
    weights: np.ndarray | tf.Tensor | None
    name: str | None
    def validate_kernel(cls, v): ...
    def validate_all(cls, values): ...

class KDE1DimGrid(KDEHelper, WrapDistribution, SerializableMixin):
    bandwidth : float
    def __init__(self, data: ztyping.XTypeInput, *, bandwidth: ztyping.ParamTypeInput | str | Callable | None = None, kernel: tfd.Distribution = None, padding: callable | str | bool | None = None, num_grid_points: int | None = None, binning_method: str | None = None, obs: ztyping.ObsTypeInput | None = None, weights: np.ndarray | tf.Tensor | None = None, extended: ExtendedInputType = None, norm: NormInputType = None, name: str = 'GridKDE1DimV1', label: str | None = None) -> None: ...

def bw_is_arraylike(bw, allow1d): ...

class KDE1DimGridRepr(BasePDFRepr):
    hs3_type: Literal['KDE1DimGrid']
    data: np.ndarray | Serializer.types.DataTypeDiscriminated
    obs: SpaceRepr | None
    bandwidth: str | float | None
    num_grid_points: int | None
    binning_method: str | None
    kernel: None
    padding: bool | str | None
    weights: np.ndarray | tf.Tensor | None
    name: str | None
    def validate_kernel(cls, v): ...
    def validate_all(cls, values): ...

class KDE1DimFFT(KDEHelper, BasePDF, SerializableMixin):
    bandwidth : float
    def __init__(
        self, 
        data: np.ndarray | tf.Tensor | "zfit.Data", 
        *, 
        obs: ztyping.ObsTypeInput | None = None, 
        bandwidth: ztyping.ParamTypeInput | str | Callable | None = None, 
        kernel: tfd.Distribution = None, 
        num_grid_points: int | None = None, 
        binning_method: str | None = None, 
        support=None, 
        fft_method: str | None = None, 
        padding: Callable | str | bool | dict[str,float] | None = None, 
        weights: np.ndarray | tf.Tensor | None = None, 
        extended: ExtendedInputType = None, 
        norm: NormInputType = None, 
        name: str = 'KDE1DimFFT', 
        label: str | None = None) -> None: ...

class KDE1DimFFTRepr(BasePDFRepr):
    hs3_type: Literal['KDE1DimFFT']
    data: np.ndarray | Serializer.types.DataTypeDiscriminated
    obs: SpaceRepr | None
    bandwidth: str | float | None
    num_grid_points: int | None
    binning_method: str | None
    kernel: None
    support: float | None
    fft_method: str | None
    padding: bool | str | None
    weights: np.ndarray | tf.Tensor | None
    name: str | None
    def validate_kernel(cls, v): ...
    def validate_all(cls, values): ...

class KDE1DimISJ(KDEHelper, BasePDF, SerializableMixin):
    def __init__(self, data: ztyping.XTypeInput, *, obs: ztyping.ObsTypeInput | None = None, padding: callable | str | bool | None = None, num_grid_points: int | None = None, binning_method: str | None = None, weights: np.ndarray | tf.Tensor | None = None, extended: ExtendedInputType = None, norm: NormInputType = None, name: str = 'KDE1DimISJ', label: str | None = None) -> None: ...

class KDE1DimISJRepr(BasePDFRepr):
    hs3_type: Literal['KDE1DimISJ']
    data: np.ndarray | Serializer.types.DataTypeDiscriminated
    obs: SpaceRepr | None
    bandwidth: str | float | None
    num_grid_points: int | None
    binning_method: str | None
    kernel: None
    padding: bool | str | None
    weights: np.ndarray | tf.Tensor | None
    name: str | None
    def validate_kernel(cls, v): ...
    def validate_all(cls, values): ...
