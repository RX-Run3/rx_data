'''
Module meant to store types relevant for statistical analysis
'''

from enum      import StrEnum, auto
from .imports  import zfit

type Fft = type[zfit.pdf.KDE1DimFFT]
# ---------------------------------------
class ConstraintType(StrEnum):
    '''
    Used to label constraints
    '''
    gauss   = 'GaussianConstraint'
    poisson = 'PoissonConstraint'
# ---------------------------------------
class CorrectionImplementation(StrEnum):
    '''
    Enum meant to symbolize how a correction is
    implemented, e.g. as a weight, resolution, scale, etc
    '''
    scale = auto()
    reso  = auto()
    weight= auto()
# --------------------------
class Model(StrEnum):
    '''
    Enum meant to represent fitting models
    '''
    fermi_dirac = auto()
    ipatia      = auto()
    exp         = auto()
    hypexp      = auto()
    modexp      = auto()
    pol1        = auto()
    pol2        = auto()
    pol3        = auto()
    cbr         = auto()
    cbl         = auto()
    suj         = auto()
    gauss       = auto()
    dscb        = auto()
    voigt       = auto()
    qgauss      = auto()
    cauchy      = auto()
# --------------------------
class KDEModel(StrEnum):
    '''
    Enum meant to represent KDE PDFs
    '''
    KDE1DimFFT = 'KDE1DimFFT'
    # -----------------------
    @property
    def cls(self) -> Fft:
        match self:
            case KDEModel.KDE1DimFFT:
                return zfit.pdf.KDE1DimFFT
# --------------------------

