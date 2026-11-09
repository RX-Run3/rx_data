'''
Module holding enums needed for fitting models
'''

from rx_common import Brem
from rx_common import Region
from rx_common import Trigger
from enum      import StrEnum, auto

# ------------------------------
class CCbarWeight(StrEnum):
    '''
    Weights needed to correct ccbar samples
    in order to build cocktails

    Attributes

    dec: Decay weights, needed to correct branching fractions within cocktail
    sam: Sample weights, needed to correct for hadronization fraction, etc between Bs, Bd and Bp decays
    '''
    dec = 'dec'
    sam = 'sam'
# ------------------------------
class SimFit(StrEnum):
    '''
    Enum meant to describe type of
    simultaneous fit
    '''
    bp_mm = auto()
    '''Represents fit to B+ -> K+ mumu, not simultaneous'''
    bp_ee = auto()
    '''Represents fit to B+ -> K+ ee, not simultaneous'''

    bd_mm = auto()
    '''Represents fit to Bd -> K* mumu, not simultaneous'''

    bd_ee = auto()
    '''Represents fit to Bd -> K* ee, not simultaneous'''

    rk = auto()
    '''
    Simultaneous between rare electron and muon for rk
    '''
    rkst = auto()
    '''
    Simultaneous between rare electron and muon for rkst
    '''
    rx = auto()
    '''
    Fully simultaneous fit in rare mode, putting together
    electron and muon rk and rkst
    '''
    # ------------------------------------
    @property
    def regions(self) -> list[Region]:
        '''
        List of signal regions associated to this fit
        '''
        rkst_ee = Region(brem = Brem.brx12, trigger = Trigger.rkst_ee_os)
        rkst_mm = Region(brem = Brem.zero , trigger = Trigger.rkst_mm_os)

        rk_ee   = Region(brem = Brem.brx12, trigger = Trigger.rk_ee_os)
        rk_mm   = Region(brem = Brem.zero , trigger = Trigger.rk_mm_os)

        match self:
            case SimFit.bp_mm | SimFit.bd_mm:
                return [rk_mm, rkst_mm]
            case SimFit.bp_ee | SimFit.bd_ee:
                return [rk_ee, rkst_ee]
            case SimFit.rk:
                return [rk_ee, rk_mm]
            case SimFit.rkst:
                return [rkst_ee, rkst_mm]
            case SimFit.rx:
                return [rkst_ee, rkst_mm, rk_ee, rk_mm]
# ------------------------------
class Systematic(StrEnum):
    '''
    Enum meant to represent systematics
    '''
    nominal   = auto()
    '''Nominal model'''

    rk_mm_sig = auto()
    '''
    Systematic associated to signal model in rk muon region
    '''
    rk_ee_sig = auto()
    '''
    Systematic associated to signal model in rk electron region
    '''
    rkst_mm_sig = auto()
    '''
    Systematic associated to signal model in rkst muon region
    '''
    rkst_ee_sig = auto()
    '''
    Systematic associated to signal model in rkst electron region
    '''
    rk_mm_cmb = auto()
    '''
    Systematic associated to combinatorial model in rk muon region
    '''
    rk_ee_cmb = auto()
    '''
    Systematic associated to combinatorial model in rk electron region
    '''
    rk_ee_cmb_ss = auto()
    '''
    Variation in SameSign model used to calculate constraints associated to
    systematic variation in OpossiteSign model
    '''
    rkst_mm_cmb = auto()
    '''
    Systematic associated to combinatorial model in rkst muon region
    '''
    rkst_ee_cmb = auto()
    '''
    Systematic associated to combinatorial model in rkst electron region
    '''
    rkst_ee_cmb_ss = auto()
    '''
    Variation in SameSign model used to calculate constraints associated to
    systematic variation in OpossiteSign model
    '''
    # --------------------------------
    @property
    def entries(self) -> list['Systematic']:
        '''
        List of systematics needed to perform config replacements
        for current systematic.

        E.g. if combinatorial model changes for OS fit, SS fit needed
        to extract constraints has to have the model changed too.
        '''
        match self:
            case Systematic.rk_ee_cmb:
                return [Systematic.rk_ee_cmb  , Systematic.rk_ee_cmb_ss]
            case Systematic.rkst_ee_cmb:
                return [Systematic.rkst_ee_cmb, Systematic.rkst_ee_cmb_ss]
            case _:
                return [self]
    # --------------------------------
    @property
    def is_nominal(self) -> bool:
        '''True if nominal model'''
        return self == Systematic.nominal
# ------------------------------
