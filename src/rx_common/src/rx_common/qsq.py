'''
Module containing Qsq enum
'''
from pathlib import Path
from enum    import StrEnum, auto

# -----------------------
class Qsq(StrEnum):
    '''
    This class represents different q2 bins
    '''
    none    = auto()
    low     = auto()
    central = auto()
    jpsi    = auto()
    psi2    = auto()
    high    = auto()
    # --------------------------
    @classmethod
    def from_path(cls, path : Path) -> 'Qsq':
        '''
        Parameters
        ----------------
        path: Path to file containing '/{q2bin}/' substring

        Returns
        ----------------
        q2 bin
        '''
        q2bins : list[Qsq] = []
        for q2bin in Qsq:
            if f'/{q2bin}/' not in str(path):
                continue

            q2bins.append(q2bin)

        if len(q2bins) != 1:
            raise ValueError(f'Not found one and only one q2bin in: {path}')

        return q2bins[0]
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
