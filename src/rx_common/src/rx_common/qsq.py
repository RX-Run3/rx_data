'''
Module containing Qsq and QsqDef enums
'''
import re

from functools   import cache
from pathlib     import Path
from enum        import StrEnum, auto, EnumMeta
from typing      import Final
from dmu.generic import utilities as gut

_MAX_QSQ : Final[float] = 100e6 # Largest q2 value that makes sense
_REGEX   : Final[str  ] = r'\((\w+)\s+>\s+(\d+)\)\s+&&\s+\((\w+)\s+<\s+(\d+)\)' # Used to extract bounds from q2 cut strings
# -----------------------
class QsqMeta[T : Qsq](EnumMeta):
    @property
    def rare(cls : T) -> list['Qsq']:
        '''
        List of q2 bins for rare mode
        '''
        return [cls.low, cls.central, cls.high]
# -----------------------
class Qsq(StrEnum, metaclass = QsqMeta):
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
    @property
    def upper_bound(self) -> float:
        '''
        Upper bound of current q2-bin
        '''
        data = _load_data()

        return data[f'{self}_upper']
    # --------------------------
    @property
    def lower_bound(self) -> float:
        '''
        Lower bound of current q2-bin
        '''
        data = _load_data()

        return data[f'{self}_lower']
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
    '''Default q2, using 4-vector from leptons'''
    constrained = auto()
    '''q2 obtained from constraining B mass to PDG value'''
    true        = auto()
    '''True q2, only available in MC'''
    trk = auto()
    '''q2 built from track information only'''
    # -----------------------
    @property
    def branch_name(self) -> str:
        '''
        Name of branch in tree storing this variable
        '''
        match self:
            case QsqDef.constrained:
                return 'q2_dtf'
            case QsqDef.default:
                return 'q2'
            case QsqDef.trk:
                return 'q2_trk'
            case QsqDef.true:
                return 'q2_true'
    # -----------------------
    def from_name(self, name : str) -> 'QsqDef':
        '''
        Parameters
        ---------------
        name: Name of branch associated to q2

        Returns
        ---------------
        QsqKind representation
        '''
        for kind in QsqDef:
            if name == kind.name:
                return kind

        raise ValueError(f'Variable {name} not associated to any q2 kind')
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
            case QsqDef.trk:
                return 'black'
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
            case QsqDef.trk:
                return '$q_{trk}^{2}$'
    # -----------------------
    def update_expression(self, expr : str) -> str:
        '''
        Parameters
        ------------------
        expr: Expression used to apply q2 cut

        Returns
        ------------------
        Cut expression with variable renamed
        '''
        if expr == 'true':
            return expr

        mtch = re.match(_REGEX, expr)
        if not mtch:
            raise ValueError(f'Cannot extract q2 variable from: {expr}')

        var_1 = mtch.group(1)
        var_2 = mtch.group(2)
        var_3 = mtch.group(3)
        var_4 = mtch.group(4)

        if var_1 != var_3:
            raise ValueError(f'Upper and lower bound q2 differ: {var_1}!={var_3}')

        return f'({self.name} > {var_2}) && ({self.name} < {var_4})'
# -----------------------
@cache
def _load_data() -> dict[str,float]:
    '''
    Returns
    -----------------
    dictionary mapping quantity with value, e.g.

    low_lower -> 1e5
    '''
    data = gut.load_data(package = 'rx_selection_data', fpath = 'selection/latest.yaml')

    q2_data : dict[str,str ] = data['q2_common']
    result : dict[str,float] = dict()
    for qsq in Qsq:
        if qsq == Qsq.none:
            result[f'{qsq}_lower'] = 0.0
            result[f'{qsq}_upper'] = _MAX_QSQ

            continue

        expr = q2_data[qsq]
        mtch = re.match(_REGEX, expr)
        if not mtch:
            raise ValueError(f'Cannot match {expr} with {_REGEX}')

        lower_val = float(mtch.group(2))
        upper_val = float(mtch.group(4))

        result[f'{qsq}_lower'] = lower_val
        result[f'{qsq}_upper'] = upper_val

    return result
# -----------------------
