import abc
import tensorflow as tf
import zfit
import zfit.z.numpy as znp

from typing import Literal, Self
from .. import settings as settings, z as z
from ..exception import AutogradNotSupported as AutogradNotSupported, OutsideLimitsError as OutsideLimitsError, SpecificFunctionNotImplemented as SpecificFunctionNotImplemented
from ..serialization.serializer import BaseRepr as BaseRepr, Serializer as Serializer
from ..util import ztyping as ztyping
from ..util.checks import NONE as NONE
from ..util.container import convert_to_container as convert_to_container, is_container as is_container
from ..util.deprecation import deprecated_args as deprecated_args
from ..util.exception import BehaviorUnderDiscussion as BehaviorUnderDiscussion, BreakingAPIChangeError as BreakingAPIChangeError, IntentionAmbiguousError as IntentionAmbiguousError, NotExtendedPDFError as NotExtendedPDFError
from ..util.warnings import warn_advanced_feature as warn_advanced_feature
from ..z.math import autodiff_gradient as autodiff_gradient, autodiff_hessian as autodiff_hessian, autodiff_value_gradient as autodiff_value_gradient, automatic_value_gradient_hessian as automatic_value_gradient_hessian, numerical_gradient as numerical_gradient, numerical_hessian as numerical_hessian, numerical_value_gradient as numerical_value_gradient, numerical_value_gradients_hessian as numerical_value_gradients_hessian
from .baseobject import BaseNumeric as BaseNumeric, extract_filter_params as extract_filter_params
from .constraint import BaseConstraint as BaseConstraint
from .data import convert_to_data as convert_to_data
from .parameter import convert_to_parameters as convert_to_parameters, set_values as set_values
from .serialmixin import SerializableMixin as SerializableMixin
from collections.abc import Callable as Callable, Iterable, Mapping
from zfit._interfaces import ZfitBinnedData as ZfitBinnedData, ZfitData as ZfitData, ZfitIndependentParameter as ZfitIndependentParameter, ZfitLoss as ZfitLoss, ZfitPDF as ZfitPDF, ZfitParameter as ZfitParameter, ZfitSpace as ZfitSpace, ZfitUnbinnedData as ZfitUnbinnedData

from zfit.pdf import BasePDF

DEFAULT_FULL_ARG: bool

class BaseLossRepr(BaseRepr):
    hs3_type: Literal['BaseLoss']
    model: Serializer.types.PDFTypeDiscriminated | list[Serializer.types.PDFTypeDiscriminated]
    data: Serializer.types.DataTypeDiscriminated | list[Serializer.types.DataTypeDiscriminated]
    constraints: list[Serializer.types.ConstraintTypeDiscriminated] | None
    options: Mapping | None

class GradientNotImplementedError(SpecificFunctionNotImplemented): ...
class ValueGradientNotImplementedError(SpecificFunctionNotImplemented): ...
class ValueGradientHessianNotImplementedError(SpecificFunctionNotImplemented): ...
class HessianNotImplementedError(SpecificFunctionNotImplemented): ...

class BaseLoss(ZfitLoss, BaseNumeric, metaclass=abc.ABCMeta):
    def __init__(
            self, 
            model      : ztyping.ModelsInputType, 
            data       : ztyping.DataInputType, 
            fit_range  : ztyping.LimitsTypeInput | None = None, 
            constraints: ztyping.ConstraintsTypeInput   = None, 
            options    : Mapping | None = None) -> None: ...
    @property
    def is_weighted(self): ...
    @property
    def is_precompiled(self): ...
    @is_precompiled.setter
    def is_precompiled(self, value) -> None: ...
    def __init_subclass__(cls, **kwargs) -> None: ...
    def check_precompile(self, *, params=None, force: bool = False): ...
    def add_constraints(self, constraints): ...
    @property
    def name(self): ...
    @property
    def model(self) -> list[BasePDF]: ...
    @property
    def data(self) -> list[zfit.Data]: ...
    @property
    def fit_range(self): ...
    @property
    def constraints(self) -> list[BaseConstraint]: ...
    @property
    def errordef(self) -> float | int: ...
    def __call__(self, _x: ztyping.DataInputType = None) -> znp.array: ...
    def value(self, *, params: ztyping.ParamTypeInput = None, full: bool | None = None) -> znp.ndarray: ...
    def __add__(self, other) -> Self: ...
    def gradient(self, params: ztyping.ParamTypeInput = None, *, numgrad=None, paramvals: ztyping.ParamTypeInput = None) -> tf.Tensor: ...
    def gradients(self, *_, **__) -> None: ...
    def value_gradient(self, params: ztyping.ParamTypeInput = None, *, full: bool | None = None, numgrad: bool | None = None, paramvals: ztyping.ParamTypeInput = None) -> tuple[tf.Tensor, tf.Tensor]: ...
    def value_gradients(self, *_, **__) -> None: ...
    def hessian(self, params: ztyping.ParamTypeInput = None, hessian=None, *, numgrad: bool | None = None, paramvals: ztyping.ParamTypeInput = None) -> tf.Tensor: ...
    def value_gradient_hessian(self, params: ztyping.ParamTypeInput = None, *, hessian=None, full: bool | None = None, numgrad=None, paramvals: ztyping.ParamTypeInput = None) -> tuple[tf.Tensor, tf.Tensor, tf.Tensor]: ...
    def value_gradients_hessian(self, *_, **__) -> None: ...

def one_two_many(values, n: int = 3, many: str = 'multiple'): ...

class BaseUnbinnedNLL(BaseLoss, SerializableMixin, metaclass=abc.ABCMeta):
    def __init__(
        self, 
        model      : ZfitPDF | Iterable[ZfitPDF], 
        data       : ZfitData | Iterable[ZfitData], 
        fit_range  : tuple[float,float] | None    = None, 
        constraints: ztyping.ConstraintsInputType = None, 
        options    : Mapping[str, object] | None  = None) -> None: ...

    def create_new(
        self, 
        model: ZfitPDF | Iterable[ZfitPDF] | None = ..., 
        data : ZfitData | Iterable[ZfitData] | None = ..., 
        fit_range=..., 
        constraints=..., 
        options=...) -> Self: ...

class UnbinnedNLL(BaseUnbinnedNLL):
    def __init__(
        self, 
        model       : ZfitPDF | Iterable[ZfitPDF], 
        data        : ZfitData | Iterable[ZfitData], 
        fit_range   : tuple[float,float] | None    = None, 
        constraints : ztyping.ConstraintsInputType = None, 
        options     : Mapping[str, object] | None  = None) -> None: ...
    @property
    def is_extended(self): ...

class UnbinnedNLLRepr(BaseLossRepr):
    hs3_type: Literal['UnbinnedNLL']

class ExtendedUnbinnedNLL(BaseUnbinnedNLL):
    def __init__(
        self, 
        model      : ZfitPDF | Iterable[ZfitPDF], 
        data       : ZfitData | Iterable[ZfitData], 
        fit_range  : tuple[float,float] | None    = None, 
        constraints: ztyping.ConstraintsInputType = None, 
        options    : Mapping[str, object] | None  = None) -> None: ...
    @property
    def is_extended(self): ...

class ExtendedUnbinnedNLLRepr(BaseLossRepr):
    hs3_type: Literal['ExtendedUnbinnedNLL']

class SimpleLoss(BaseLoss):
    def __init__(self, func: Callable, params: Iterable[zfit.Parameter] | None = None, errordef: float | None = None, *, gradient: Callable | str | None = None, hessian: Callable | str | None = None, jit: bool | None = None, deps: Iterable[zfit.Parameter] = ..., dependents: Iterable[zfit.Parameter] = ...) -> None: ...
    @classmethod
    def register_convertable_loss(cls, constructor, *, priority: int = 0): ...
    @classmethod
    def from_any(cls, func, params=None, **kwargs): ...
    @property
    def errordef(self): ...
    def __add__(self, other): ...
    def create_new(self, func: Callable = ..., params: Iterable[zfit.Parameter] = ..., errordef: float | None = ...): ...
