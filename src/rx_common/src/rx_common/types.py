'''
This module contains classes derived from Enum
'''
from pathlib     import Path
from enum        import StrEnum, IntEnum, auto
from typing      import Final
from dmu.stats   import CorrectionImplementation
from dmu         import LogStore
from pydantic    import BaseModel, ConfigDict, model_validator

from .mass       import Mass
from .region     import Region

_ALL_BLOCKS : Final[set[int]] = {-1, 1, 2, 3, 4, 5, 6, 7, 8}
log=LogStore.add_logger('rx_common:types')
# ------------------------------
class DataSet(StrEnum):
    dat = auto()
    sim = auto()
    # ---------------------
    @property
    def latex(self) -> str:
        match self:
            case DataSet.dat:
                return 'Data'
            case DataSet.sim:
                return 'MC'
# ------------------------------
class Particle(StrEnum):
    '''
    Model meant to store particle properties
    '''
    kaon = auto() 
    pion = auto() 
# ------------------------------
class Parameter(StrEnum):
    '''
    Class meant to store parameters of interest

    Attributes:

    rpk   : RpK
    irjpsi: Inverse of rjpsi
    '''
    rk     = 'rk'
    rx     = 'rx'
    rpk    = 'rpk'
    rkst   = 'rkst'

    rjpsi  = 'rjpsi'
    irjpsi = 'rjpsi_inv'
# ---------------------------------------
class Block(BaseModel):
    r'''
    Type meant to represent data blocks, e.g. block 1
    '''
    model_config = ConfigDict(frozen=True)

    value : int | set[int] 
    # ----------------
    @model_validator(mode='before')
    @classmethod
    def coerce_from_primitive(
        cls,
        data : dict[str,set[int] | int] | int):
        if isinstance(data, int):
            return {'value' : data}

        value : int | set[int] = data['value']

        if isinstance(value, set):
            for val in value:
                cls._validate_elementary_block(value = val)

            return data

        cls._validate_elementary_block(value = value)

        return data
    # ----------------
    @classmethod
    def _validate_elementary_block(cls, value) -> None:
        if not isinstance(value, int):
            raise ValueError(f'Expected an int, found: {value}')

        if value not in _ALL_BLOCKS:
            raise ValueError(f'Invalid block: {value}')
    # ----------------
    def to_int(self) -> int:
        '''
        Integer version of block, e.g. 

        - b1     ->  1
        - b1, b2 -> 12
        - all    -> -1 
        '''
        if isinstance(self.value, int):
            return self.value

        values = list(self.value)
        values = sorted(values)
        values = [ str(value) for value in values ]

        total  = ''.join(values)

        return int(total)
    # ----------------
    @classmethod
    def blocks(cls) -> list['Block']:
        '''
        Returns
        --------------
        List of elementary blocks
        '''
        return [ cls(value = block) for block in _ALL_BLOCKS if block != -1 ]
    # ----------------
    @classmethod
    def from_str(cls, value : str) -> 'Block':
        '''
        Parameters
        --------------
        value: String symbolizing block, e.g. 3, all

        Returns
        --------------
        Block instance
        '''
        if value == 'all':
            return cls(value=-1)

        if len(value) == 1:
            return cls(value = int(value))

        val = { int(elm) for elm in value } 

        return cls(value=val)
    # ----------------
    def __add__(self, other : 'Block') -> 'Block':
        '''
        Addition of block types. If blocks are the same
        sum will be the same as the input block.

        Use case: Adding datasets from same block and different brem categories 
        '''
        if self == other:
            return self

        this_val  = {self.value}  if isinstance(self.value,  int) else self.value
        other_val = {other.value} if isinstance(other.value, int) else other.value

        new_value = this_val | other_val

        return Block(value=new_value)
    # ----------------
    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)
    # ----------------
    def __str__(self):
        if self.value == -1:
            return 'all'

        if isinstance(self.value, int):
            return str(self.value)

        values = list(self.value)
        values = sorted(values)
        values = [ str(val) for val in values ]

        return ''.join(values)
    # ----------------
    def __lt__(self, other : 'Block') -> bool:
        if isinstance(self.value, int) and isinstance(other.value, int):
            return self.value < other.value

        raise ValueError(f'Cannot order composite blocks: {self} and {other}')
    # ----------------
    def __hash__(self):
        return hash(self.value)
# ---------------------------------------
class Correction(StrEnum):
    r'''
    Class meant to represent differences between data and MC
    measured in control regions, which can be used to correct MC
    e.g. DeltaMu = Mu(data) - Mu(simulation)
    '''
    pid             = 'PID'
    mass_scale      = 'smu'
    mass_resolution = 'rsg'
    brem_fraction   = 'rfr'
    blok_fraction   =  'bk'
    # ------------------------
    @property
    def var(self) -> str:
        '''
        Variable associated to this correction
        '''
        match self:
            case Correction.mass_scale:
                return 'mu'
            case Correction.mass_resolution:
                return 'sg'
            case Correction.brem_fraction:
                return 'fr'
            case Correction.blok_fraction:
                return 'bk'
            case _:
                raise ValueError(f'Invalid correction: {self}')
    # ------------------------
    @property
    def kind(self) -> CorrectionImplementation:
        '''
        Returns
        --------------
        reso or scale
        '''
        if self in [Correction.mass_scale]:
            return CorrectionImplementation.scale 

        if self in [Correction.mass_resolution, Correction.brem_fraction, Correction.blok_fraction]:
            return CorrectionImplementation.reso

        if self in [Correction.pid]:
            return CorrectionImplementation.weight

        raise ValueError(f'Cannot retrieve kind for correction: {self}')
    # ------------------------
    @property
    def latex(self) -> str:
        '''
        Returns
        --------------
        Latex string corresponding to correction
        '''
        match self:
            case Correction.mass_scale:
                return r'$\Delta\mu$[MeV]' 
            case Correction.mass_resolution:
                return r'$\frac{\sigma^{Data}}{\sigma^{MC}}$'
            case Correction.brem_fraction:
                return r'$\frac{BFr^{Data}}{BFr^{MC}}$'
            case Correction.blok_fraction:
                return r'$\frac{Block^{Data}}{Block^{MC}}$'
            case Correction.pid:
                return 'PID'
    # ------------------------
    @property
    def nickname(self) -> str:
        '''
        String to be used when naming variables, etc
        '''
        match self:
            case Correction.mass_scale:
                return 'dmu' 
            case Correction.mass_resolution:
                return 'rsg' 
            case Correction.brem_fraction:
                return 'brem' 
            case Correction.blok_fraction:
                return 'block' 
            case Correction.pid:
                return 'weight'
# ---------------------------------------
class MVA(StrEnum):
    r'''
    This class is meant to hold types representing kinds of MVA classifiers 

    cmb : Combinatorial 
    prc : Partially reconstructed 
    '''
    cmb = 'cmb'
    prc = 'prc'
# ---------------------------------------
class Brem(IntEnum):
    '''
    Enum meant to represent brem category
    '''
    zero    = 10
    one     = 100
    two     = 1000
    # ----------
    # Composite brem
    # ----------
    br01x   =  110 
    br0x2   = 1010 
    brx12   = 1100 
    br012   = 1110 
    # ----------------------
    def in_string(self, string : str) -> bool:
        '''
        Parameters
        ---------------
        string: String

        Returns
        ---------------
        True if string has substring associated to this brem
        '''
        substring = f'brem_{self}'

        return substring in string 
    # ----------------------
    @property
    def components(self) -> list['Brem']:
        '''
        List of elementary brem categories
        '''
        if not self.is_composite:
            return [self]

        if self == Brem.br01x:
            return [Brem.zero, Brem.one]

        if self == Brem.br0x2:
            return [Brem.zero, Brem.two]

        if self == Brem.brx12:
            return [Brem.one , Brem.two]

        if self == Brem.br012:
            return [Brem.zero, Brem.one, Brem.two]

        raise ValueError(f'Invalid brem: {self}')
    # ----------------------
    @property
    def is_composite(self) -> bool:
        if self in {Brem.zero, Brem.one, Brem.two}:
            return False 

        return True 
    # ----------------------
    @property
    def region(self) -> Region:
        '''
        Signal region associated to category
        '''
        match self:
            case Brem.zero:
                return Region.brem_xx0
            case Brem.one:
                return Region.brem_xx1
            case Brem.two:
                return Region.brem_xx2
            case Brem.brx12:
                return Region.brem_x12
            case Brem.br01x:
                return Region.brem_01x
            case Brem.br0x2:
                return Region.brem_0x2
            case Brem.br012:
                return Region.brem_012
    # ----------------------
    @property
    def color(self) -> str:
        '''
        Color associated to category
        '''
        match self:
            case Brem.zero:
                return '#1f77b4'
            case Brem.one:
                return '#ff7f0e'
            case Brem.two:
                return '#2ca02c'
            case _:
                raise ValueError(f'No color assciated to {self}')
    # ----------------------
    @property
    def latex(self) -> str:
        '''
        latex associated to category
        '''
        match self:
            case Brem.zero:
                return r'$0\gamma$'
            case Brem.one:
                return r'$1\gamma$'
            case Brem.two:
                return r'$2\gamma$'
            case Brem.brx12:
                return r'$1\gamma + 2\gamma$'
            case _:
                raise ValueError(f'No color assciated to {self}')
    # ----------------------
    @classmethod
    def from_int(cls, value : int) -> 'Brem':
        '''
        Parameters
        ---------------
        value: Integer representing brem category
               in old representation, i.e. 0, 1, 2

        Returns
        ---------------
        Corresponding brem object
        '''
        match value:
            case 0:
                return cls.zero
            case 1:
                return cls.one
            case 2:
                return cls.two
            case _:
                raise ValueError(f'Invalid brem: {value}')
    # ----------------------
    def to_int(self) -> int:
        '''
        Returns
        ---------------
        Int version of brem
        '''
        match self:
            case self.zero:
                return 0 
            case self.one:
                return 1 
            case self.two:
                return 2 
            case _:
                raise ValueError(f'Invalid brem: {self}')
    # ----------------------
    @classmethod
    def brems(cls) -> list['Brem']:
        '''
        Returns
        -------------
        List of elementary brem categories
        '''
        return [cls.zero, cls.one, cls.two]
    # ----------------------
    def __add__(self, other : 'Brem') -> 'Brem': # type: ignore[reportIncompatibleMethodOverride]
        '''
        Parameters
        -------------
        other: Value of brem to add to this one 

        Returns
        -------------
        Brem category resulting from sum, when sum means
        merging corresponding samples
        '''
        if self == other:
            return self

        total = self.value + other.value

        try:
            brem = Brem(total)
        except Exception as exc:
            raise ValueError(f'Cannot add {self} to {other}') from exc

        return brem
    # ----------------------
    def __str__(self) -> str:
        '''
        Returns string representation
        '''
        return self.region
    # ----------------------
    @staticmethod
    def from_str(value : str) -> 'Brem':
        '''
        Returns Brem for given string, e.g. xx0
        '''
        if value == '001':
            value = 'xx1'

        if value == '002':
            value = 'xx2'

        match value:
            case 'xx0':
                return Brem.zero
            case 'xx1':
                return Brem.one
            case 'xx2':
                return Brem.two
            case '01x':
                return Brem.br01x
            case '0x2':
                return Brem.br0x2
            case 'x12':
                return Brem.brx12
            case '012':
                return Brem.br012
            case _:
                raise ValueError(f'Invalid brem string: {value}')
    # ----------------------
    @staticmethod
    def from_path(path : Path) -> 'Brem':
        '''
        Parameters
        ----------------
        path: Path to file containing brem in the form '/{brem}/'

        Returns
        ----------------
        Brem category in path
        '''
        brems : list[Brem] = []
        for brem in Brem:
            if f'/{brem}/' not in str(path):
                continue

            brems.append(brem)

        if len(brems) != 1:
            raise ValueError(f'Not found one and only one brem category in: {path}')

        return brems[0]
    # ----------------------
    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.value == other 

        if isinstance(other, Brem):
            return self.value == other.value

        return False
    # ----------------
    def __lt__(self, other : 'Brem') -> bool: # type: ignore[reportIncompatibleMethodOverride]
        return self.value < other.value
    # ----------------------
    def __hash__(self) -> int:
        return super().__hash__()
# ---------------------------------------
class MisID(StrEnum):
    '''
    Class meant to represent different
    misID control regions
    '''
    bp_kk   = 'bp_kk'
    bp_pipi = 'bp_pipi'

    bd_kk   = 'bd_kk'
    bd_pipi = 'bd_pipi'
    # ----------------------------
    def __str__(self):
        return self.value
    # ----------------------------
    @property
    def mass(self) -> Mass:
        '''
        Mass meant to be fitted in this region
        '''
        match self:
            case MisID.bp_kk:
                return Mass.bp_kk
            case MisID.bp_pipi:
                return Mass.bp_pipi
            case MisID.bd_kk:
                return Mass.bd_kk
            case MisID.bd_pipi:
                return Mass.bd_pipi
# ---------------------------------------
