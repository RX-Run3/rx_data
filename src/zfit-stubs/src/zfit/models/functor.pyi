from zfit import ComposedParameter
from zfit import Parameter
from .. import z as z
from ..core.basepdf import BasePDF as BasePDF
from ..core.serialmixin import SerializableMixin as SerializableMixin
from ..core.space import supports as supports
from ..models.basefunctor import FunctorMixin as FunctorMixin, extract_daughter_input_obs as extract_daughter_input_obs
from ..serialization import Serializer as Serializer
from ..util import ztyping as ztyping
from ..util.container import convert_to_container as convert_to_container
from ..util.exception import AnalyticIntegralNotImplemented as AnalyticIntegralNotImplemented, NormRangeUnderdefinedError as NormRangeUnderdefinedError, SpecificFunctionNotImplemented as SpecificFunctionNotImplemented
from ..util.plotter import PDFPlotter as PDFPlotter, SumCompPlotter as SumCompPlotter
from ..util.ztyping import ExtendedInputType as ExtendedInputType, NormInputType as NormInputType
from ..z.random import counts_multinomial as counts_multinomial
from .basefunctor import FunctorPDFRepr as FunctorPDFRepr
from _typeshed import Incomplete
from collections.abc import Iterable
from typing import Literal
from zfit._interfaces import ZfitData as ZfitData, ZfitPDF as ZfitPDF, ZfitSpace as ZfitSpace

class BaseFunctor(FunctorMixin, BasePDF):
    pdfs: Incomplete
    def __init__(self, pdfs, name: str = 'BaseFunctor', label=None, **kwargs) -> None: ...
    @property
    def pdfs_extended(self): ...

class SumPDF(BaseFunctor, SerializableMixin):
    pdfs: list[BasePDF]
    def __init__(
        self,
        pdfs: Iterable[ZfitPDF],
        fracs: Iterable[Parameter] | Iterable[ComposedParameter] | Iterable[float] | None = None,
        obs  : ztyping.ObsTypeInput = None,
        extended: ExtendedInputType = None,
        norm: NormInputType = None,
        name: str = 'SumPDF',
        label: str | None = None) -> None: ...

    @property
    def fracs(self): ...

class SumPDFRepr(FunctorPDFRepr):
    hs3_type: Literal['SumPDF']
    fracs: list[Serializer.types.ParamInputTypeDiscriminated] | None
    def validate_all_sumpdf(cls, values): ...

class ProductPDF(BaseFunctor, SerializableMixin):
    def __init__(self, pdfs: list[ZfitPDF], obs: ztyping.ObsTypeInput = None, extended: ExtendedInputType = None, norm: NormInputType = None, name: str = 'ProductPDF') -> None: ...

class ProductPDFRepr(FunctorPDFRepr):
    hs3_type: Literal['ProductPDF']
