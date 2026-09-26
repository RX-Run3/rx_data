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
from .project    import Project
from .channel    import Channel
from .component  import Component
from .qsq        import Qsq
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
class Trigger(StrEnum):
    '''
    Class meant to represent MVA HLT2 triggers
    '''
    rk_ee_os     = auto()
    rk_me_os     = auto()
    rk_ee_ss     = auto()
    rk_ee_nopid  = auto()
    rk_ee_cal    = auto()
    rk_ee_misid  = auto()
    rk_mm_os     = auto()
    rk_mm_nopid  = auto()
    rk_mm_ss     = auto()
    # -----------
    rkst_ee_os   = auto()
    rkst_me_os   = auto()
    rkst_ee_ss   = auto()
    rkst_ee_nopid= auto()
    rkst_ee_cal  = auto()
    rkst_ee_misid= auto()
    rkst_mm_os   = auto()
    rkst_mm_nopid= auto()
    rkst_mm_ss   = auto()
    # -----------
    @classmethod
    def get_main_trigger(
        cls, 
        channel : Channel, 
        project : Project) -> 'Trigger':
        '''
        Parameters
        ----------------
        channel: E.g. ee, mm
        project: E.g. rk, rkst

        Returns
        ----------------
        Trigger used for this project/channel combination
        for actual measurement
        '''
        for trig in cls:
            if not trig.is_main:
                continue

            if trig.channel != channel:
                continue

            if trig.project != project:
                continue

            return trig

        raise ValueError(f'Cannot find main trigger for: {project}/{channel}')
    # -----------
    @property
    def reso_jpsi_signal(self) -> Component:
        '''
        Component associated to trigger in resonant mode
        for the jpsi bin
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkpjpsiee
            case Trigger.rk_mm_os:
                return Component.bpkpjpsimm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpijpsiee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpijpsimm
            case _:
                raise ValueError(f'No resonant signal component for: {self}')
    # -----------
    @property
    def reso_psi2_signal(self) -> Component:
        '''
        Component associated to trigger in resonant mode
        for the psi2S bin
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkppsi2ee
            case Trigger.rk_mm_os:
                return Component.bpkppsi2mm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpipsi2ee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpipsi2mm
            case _:
                raise ValueError(f'No resonant signal component for: {self}')
    # -----------
    @property
    def rare_signal(self) -> Component:
        '''
        Component associated to trigger in rare mode
        '''
        match self:
            case Trigger.rk_ee_os:
                return Component.bpkpee
            case Trigger.rk_mm_os:
                return Component.bpkpmm
            case Trigger.rkst_ee_os:
                return Component.bdkstkpiee
            case Trigger.rkst_mm_os:
                return Component.bdkstkpimm
            case _:
                raise ValueError(f'No rare signal component for: {self}')
    # -----------
    @property
    def misid_version(self) -> 'Trigger':
        '''
        MisID version of this trigger, if it exists
        '''
        match self:
            case Trigger.rk_ee_os:
                return Trigger.rk_ee_misid
            case Trigger.rkst_ee_os:
                return Trigger.rkst_ee_misid
            case _:
                raise ValueError(f'Cannot find misid version for: {self}')
    # -----------
    @property
    def pid_version(self) -> 'Trigger':
        '''
        MisID version of this trigger, if it exists
        '''
        match self:
            case Trigger.rk_ee_nopid:
                return Trigger.rk_ee_os
            case Trigger.rkst_ee_nopid:
                return Trigger.rkst_ee_os
            case Trigger.rk_mm_nopid:
                return Trigger.rk_mm_os
            case Trigger.rkst_mm_nopid:
                return Trigger.rkst_mm_os
            case _:
                raise ValueError(f'Version with PID not defined for: {self}')
    # -----------
    def get_signal_component(
        self, 
        qsq : Qsq) -> Component:
        '''
        Parameters
        -------------
        qsq : q2 bin

        Returns
        -------------
        Signal component for given q2 bin 
        '''
        # ----------------
        if qsq == Qsq.jpsi and self == Trigger.rk_ee_os:
            return Component.bpkpjpsiee

        if qsq == Qsq.jpsi and self == Trigger.rk_mm_os:
            return Component.bpkpjpsimm

        if qsq == Qsq.psi2 and self == Trigger.rk_ee_os:
            return Component.bpkppsi2ee

        if qsq == Qsq.psi2 and self == Trigger.rk_mm_os:
            return Component.bpkppsi2mm

        if self == Trigger.rk_ee_os:
            return Component.bpkpee

        if self == Trigger.rk_mm_os:
            return Component.bpkpmm
        # ----------------
        if qsq == Qsq.jpsi and self == Trigger.rkst_ee_os:
            return Component.bdkstkpijpsiee

        if qsq == Qsq.jpsi and self == Trigger.rkst_mm_os:
            return Component.bdkstkpijpsimm

        if qsq == Qsq.psi2 and self == Trigger.rkst_ee_os:
            return Component.bdkstkpipsi2ee

        if qsq == Qsq.psi2 and self == Trigger.rkst_mm_os:
            return Component.bdkstkpipsi2mm

        if self == Trigger.rkst_ee_os:
            return Component.bdkstkpiee

        if self == Trigger.rkst_mm_os:
            return Component.bdkstkpimm
        # ----------------

        raise ValueError(f'Cannot get signal component for: {qsq}/{self}')
    # -----------
    @property
    def subtriggers(self) -> list['Trigger']:
        '''
        List of triggers into which this trigger can be
        decomposed, e.g. nopid = misID + signal region

        If not decomposable, return list with only this trigger 
        '''
        match self:
            case Trigger.rk_ee_nopid:
                return [Trigger.rk_ee_os  , Trigger.rk_ee_misid  ]
            case Trigger.rkst_ee_nopid:
                return [Trigger.rkst_ee_os, Trigger.rkst_ee_misid]
            case _:
                return [self]
    # -----------
    @property
    def has_pid(self) -> bool:
        '''
        False for triggers associated to PID removed samples
        '''
        return 'nopid' not in self.name
    # -----------
    def __str__(self) -> str:
        match self:
            case Trigger.rk_ee_os:
                return 'Hlt2RD_BuToKpEE_MVA'
            case Trigger.rk_me_os:
                return 'Hlt2RD_BuToKpMuE_MVA'
            case Trigger.rk_ee_ss:
                return 'Hlt2RD_BuToKpEE_SameSign_MVA'
            case Trigger.rk_ee_nopid:
                return 'Hlt2RD_BuToKpEE_MVA_noPID'
            case Trigger.rk_ee_cal:
                return 'Hlt2RD_BuToKpEE_MVA_cal'
            case Trigger.rk_ee_misid:
                return 'Hlt2RD_BuToKpEE_MVA_misid'
            case Trigger.rk_mm_os:
                return 'Hlt2RD_BuToKpMuMu_MVA'
            case Trigger.rk_mm_nopid:
                return 'Hlt2RD_BuToKpMuMu_MVA_noPID'
            case Trigger.rk_mm_ss:
                return 'Hlt2RD_BuToKpMuMu_SameSign_MVA'
            case Trigger.rkst_ee_os:
                return 'Hlt2RD_B0ToKpPimEE_MVA'
            case Trigger.rkst_me_os:
                return 'Hlt2RD_B0ToKpPimMuE_MVA'
            case Trigger.rkst_ee_ss:
                return 'Hlt2RD_B0ToKpPimEE_SameSign_MVA'
            case Trigger.rkst_ee_nopid:
                return 'Hlt2RD_B0ToKpPimEE_MVA_noPID'
            case Trigger.rkst_ee_cal:
                return 'Hlt2RD_B0ToKpPimEE_MVA_cal'
            case Trigger.rkst_ee_misid:
                return 'Hlt2RD_B0ToKpPimEE_MVA_misid'
            case Trigger.rkst_mm_os:
                return 'Hlt2RD_B0ToKpPimMuMu_MVA'
            case Trigger.rkst_mm_nopid:
                return 'Hlt2RD_B0ToKpPimMuMu_MVA_noPID'
            case Trigger.rkst_mm_ss:
                return 'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA'
    # -----------
    @classmethod
    def from_name(cls, name: str) -> 'Trigger':
        '''
        Parameters
        --------------
        name: Trigger name, i.e. Hlt2RD_BuToKpEE_MVA

        Returns
        --------------
        Corresponding trigger object
        '''
        match name:
            case 'Hlt2RD_BuToKpEE_MVA':
                return cls.rk_ee_os
            case 'Hlt2RD_BuToKpMuE_MVA':
                return cls.rk_me_os
            case 'Hlt2RD_BuToKpEE_SameSign_MVA':
                return cls.rk_ee_ss
            case 'Hlt2RD_BuToKpEE_MVA_noPID':
                return cls.rk_ee_nopid
            case 'Hlt2RD_BuToKpEE_MVA_cal':
                return cls.rk_ee_cal
            case 'Hlt2RD_BuToKpEE_MVA_misid':
                return cls.rk_ee_misid
            case 'Hlt2RD_BuToKpMuMu_MVA':
                return cls.rk_mm_os
            case 'Hlt2RD_BuToKpMuMu_MVA_noPID':
                return cls.rk_mm_nopid
            case 'Hlt2RD_BuToKpMuMu_SameSign_MVA':
                return cls.rk_mm_ss
            case 'Hlt2RD_B0ToKpPimEE_MVA':
                return cls.rkst_ee_os
            case 'Hlt2RD_B0ToKpPimMuE_MVA':
                return cls.rkst_me_os
            case 'Hlt2RD_B0ToKpPimEE_SameSign_MVA':
                return cls.rkst_ee_ss
            case 'Hlt2RD_B0ToKpPimEE_MVA_noPID':
                return cls.rkst_ee_nopid
            case 'Hlt2RD_B0ToKpPimEE_MVA_cal':
                return cls.rkst_ee_cal
            case 'Hlt2RD_B0ToKpPimEE_MVA_misid':
                return cls.rkst_ee_misid
            case 'Hlt2RD_B0ToKpPimMuMu_MVA':
                return cls.rkst_mm_os
            case 'Hlt2RD_B0ToKpPimMuMu_MVA_noPID':
                return cls.rkst_mm_nopid
            case 'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA':
                return cls.rkst_mm_ss
            case _:
                raise ValueError(f'Unknown trigger name: {name!r}')
    # -----------
    @property
    def is_electron(self) -> bool:
        return self.channel == Channel.ee
    # -----------
    @property
    def is_muon(self) -> bool:
        return self.channel == Channel.mm
    # -----------
    @property
    def channel(self) -> Channel:
        '''
        Either 'muon' or 'electron'
        '''
        if 'ee' in self.name:
            return Channel.ee
    
        if 'mm' in self.name:
            return Channel.mm
    
        raise ValueError(f'Cannot determine channel for trigger: {self}')
    # -----------
    @property
    def is_ss(self) -> bool:
        '''
        True if it is a same sign trigger
        '''
        return 'SameSign' in str(self)
    # -----------
    @property
    def is_main(self) -> bool:
        '''
        True if trigger is used for actual measurement
        '''
        ee_trig = [Trigger.rk_ee_os, Trigger.rkst_ee_os]
        mm_trig = [Trigger.rk_mm_os, Trigger.rkst_mm_os]

        return self in ee_trig + mm_trig
    # -----------
    @property
    def project(self) -> Project:
        '''
        Returns
        -----------------
        Project for which this trigger is meant to be used, e.g. rk, rkst etc
        '''
        match self:
            # --------------
            # rk
            # --------------
            case Trigger.rk_ee_os:
                return Project.rk
            case Trigger.rk_me_os:
                return Project.rk
            case Trigger.rk_ee_ss:
                return Project.rk
            case Trigger.rk_ee_cal:
                return Project.rk
            case Trigger.rk_ee_misid:
                return Project.rk
            case Trigger.rk_ee_nopid:
                return Project.rk_no_pid
            # --------------
            case Trigger.rk_mm_os:
                return Project.rk
            case Trigger.rk_mm_ss:
                return Project.rk
            case Trigger.rk_mm_nopid:
                return Project.rk_no_pid
            # --------------
            # rkst
            # --------------
            case Trigger.rkst_ee_os:
                return Project.rkst
            case Trigger.rkst_me_os:
                return Project.rkst
            case Trigger.rkst_ee_ss:
                return Project.rkst
            case Trigger.rkst_ee_cal:
                return Project.rkst
            case Trigger.rkst_ee_misid:
                return Project.rkst
            case Trigger.rkst_ee_nopid:
                return Project.rkst_no_pid
            # --------------
            case Trigger.rkst_mm_os:
                return Project.rkst
            case Trigger.rkst_mm_ss:
                return Project.rkst
            case Trigger.rkst_mm_nopid:
                return Project.rkst_no_pid
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
