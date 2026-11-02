'''
Module holding FitConf class
'''
from pydantic    import BaseModel, model_validator
from typing      import Self, Final
from .constraint import Constraint
from .types      import KDEModel

_PVALUE : Final[float] = 0.05
_NTRIES : Final[int  ] = 3
#------------------------------
# Non-parametric
#------------------------------
class PaddingConf(BaseModel, frozen = True):
    '''
    Class meant to configure padding in zfit KDEs
    '''
    lowermirror : float = 0.0
    uppermirror : float = 0.0
    flag        : bool  = False
    #------------------------------
    @model_validator(mode = 'after')
    def check_values(self) -> Self:
        '''
        - Do not allow negative padding
        - If mirror is used, set flag = True
        '''
        if self.lowermirror < 0.0 or self.uppermirror < 0:
            raise ValueError('Either upper/lower mirror is negative')

        return self
    #------------------------------
    @model_validator(mode = 'before')
    @classmethod
    def check_mirror(cls, data):
        lowermirror : float = data.get('lowermirror')
        uppermirror : float = data.get('uppermirror')

        # Use default padding config
        if lowermirror is None and uppermirror is None:
            data['flag'] = False
            return data

        # This is padded -> set flag and return
        if lowermirror != 0.0 or uppermirror != 0:
            data['flag'] = True
            return data

        # User wants no padding
        data['flag'] = False

        return data
    #------------------------------
    @property
    def value(self) -> dict[str,float] | bool:
        '''
        This is meant to be used as argument to zfit KDE
        padding argument
        '''
        if not self.flag:
            return False

        padding = {'lowermirror' : self.lowermirror,
                   'uppermirror' : self.uppermirror}

        return padding
    #-----------
    @classmethod
    def default(cls) -> Self:
        return cls()
#------------------------------
class KDEConf(BaseModel, frozen = True):
    '''
    Class meant to configure building of KDE PDFs
    '''
    kind      : KDEModel
    bandwidth : int
    padding   : PaddingConf
    #-----------
    @classmethod
    def default(cls) -> Self:
        return cls(
            kind      = KDEModel.KDE1DimFFT,
            bandwidth = 20,
            padding   = PaddingConf.default())
#------------------------------
# Strategies
#------------------------------
class Retries(BaseModel, frozen = True):
    '''
    Constrols fit when it is retried multiple times
    '''
    ntries : int
    pvalue : float
    #------------
    @classmethod
    def default(cls) -> Self:
        return cls(ntries = _NTRIES, pvalue = _PVALUE)
#------------------------------
class Context(BaseModel, frozen = True):
    '''
    Used if minimization should be run in a separate process
    '''
#------------------------------
# Minimization itself
#------------------------------
class Minimization(BaseModel, frozen = True):
    '''
    Used to hold parameters needed for zfit's Minuit class
    '''
    mode    : int  = 0
    '''
    0: Do not call Hesse, use approximation to calculate step size
    1: Calculate step size with Hesse, more expensive
    '''
    gradient: bool = False
    '''
    True : Use Minuit numerical gradient
    False: Use TensorFlow's gradient, faster
    '''
#------------------------------
class FitConf(BaseModel, frozen = True, strict = True, extra = 'forbid'):
    '''
    Class meant to define how a fit will be done
    '''
    minimization: Minimization                       = Minimization()
    nentries    : int                                = -1
    run_gof     : bool                               = True
    do_errors   : bool                               = True
    ranges      : list[tuple[float,float] ]  | None  = None
    constraints : list[Constraint]           | None  = None
    strategy    : Retries | Context | None           = None
    # --------------------------
    @classmethod
    def default(cls) -> Self:
        '''
        Returns
        ----------
        Default fit configuration for minimal fit
        '''
        return cls()
#------------------------------
