'''
Module containing Qsq enum
'''
from enum import StrEnum, auto

# -----------------------
class Qsq(StrEnum):
    '''
    This class represents different q2 bins
    '''
    none    = 'none'
    all     = 'all'
    low     = 'low'
    central = 'central'
    jpsi    = 'jpsi'
    psi2    = 'psi2'
    high    = 'high'
    # --------------------------
    @classmethod
    def for_physics(cls) -> list['Qsq']:
        '''
        List of Qsq bins for physics
        '''
        return [cls.low, cls.central, cls.jpsi, cls.psi2, cls.high]
    # --------------------------
    @property
    def kind(self) -> str:
        '''
        E.g. rare or reso
        '''
        if self.is_rare:
            return 'rare'
        
        return 'reso'
    # --------------------------
    @property
    def is_rare(self) -> bool:
        if self in [Qsq.low, Qsq.central, Qsq.high]:
            return True

        return False
    # --------------------------
    @property
    def latex(self) -> str:
        '''
        Returns
        --------------
        Latex representation of this bin
        needed for plots 
        '''
        match self:
            case Qsq.low:
                return 'Low' 
            case Qsq.central:
                return 'Central' 
            case Qsq.jpsi:
                return r'$J/\psi$' 
            case Qsq.psi2:
                return r'$\psi(2S)$' 
            case Qsq.high:
                return 'High' 
            case Qsq.all:
                return 'All'
            case Qsq.none:
                return 'None'
    # --------------------------
    def __str__(self):
        return self.value
# -----------------------
class QsqDef(StrEnum):
    '''
    Enum meant to symbolize q2 definition
    '''
    default     = auto()
    constrained = auto()
    true        = auto()
    # -----------------------
    @property
    def color(self) -> str:
        '''
        Color used for plots
        '''
        match self:
            case QsqDef.default:
                return 'blue'
            case QsqDef.constrained:
                return 'green'
            case QsqDef.true:
                return 'red'
    # -----------------------
    @property
    def branch_name(self) -> str:
        '''
        Name of branch associated
        '''
        match self:
            case QsqDef.default:
                return 'q2'
            case QsqDef.constrained:
                return 'q2_dtf'
            case QsqDef.true:
                return 'q2_true'
    # -----------------------
    @property
    def latex(self) -> str:
        '''
        Latex version for plots
        '''
        match self:
            case QsqDef.default:
                return '$q^{2}$'
            case QsqDef.constrained:
                return '$q_{DTF}^{2}$'
            case QsqDef.true:
                return '$q_{True}^{2}$'
# -----------------------
