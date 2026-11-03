'''
Module with Cuts enum
'''
import yaml
from enum     import StrEnum, auto
from pydantic import BaseModel

# ------------------------------------------
class Cuts(StrEnum):
    '''
    Class meant to symbolize cuts
    '''
    truth     = auto()
    clean     = auto()
    block     = auto()
    q2        = auto()
    ghost     = auto()
    hlt1      = auto()
    hlt2      = auto()
    kinem_lep = auto()
    kinem_had = auto()
    clones    = auto()
    tr_ipchi2 = auto()
    pid_l     = auto()
    pid_k     = auto()
    pid_pi    = auto()
    rich      = auto()
    acceptance= auto()
    jpsi_misid= auto()
    cascade   = auto()
    kst_mass  = auto()
    kst_pt    = auto()
    hop       = auto()
    cmb       = auto()
    prc       = auto()
    mass      = auto()
    brem      = auto()
    leakage   = auto()
    extra     = auto()
    convert   = auto() # 1 if electrons are not from converted photon
    # -------------------
    # Used to define misID regions
    # -------------------
    bpkk      = auto()
    bppipi    = auto()
    # ----------------------------------
    @property
    def latex(self) -> str:
        '''
        Latex representation (for tables) of cut
        '''
        match self:
            case Cuts.truth:
                return 'Truth matching'
            case Cuts.q2:
                return r'$q^2$'
            case Cuts.clean:
                return r'Data quality'
            case Cuts.block:
                return r'Block'
            case Cuts.ghost:
                return 'Ghost prob'
            case Cuts.tr_ipchi2:
                return r'$\chi^2_{IP}$'
            case Cuts.cmb:
                return r'MVA${}_{cmb}$'
            case Cuts.prc:
                return r'MVA${}_{prc}$'
            case Cuts.kst_mass:
                return r'M$(K^*)$'
            case Cuts.kst_pt:
                return r'$p_{T}(K^*)$'
            case Cuts.mass:
                return r'M$(B)$'
            case Cuts.hlt1:
                return 'Hlt1'
            case Cuts.hlt2:
                return 'Hlt2'
            case Cuts.pid_l:
                return 'Lepton PID'
            case Cuts.pid_k:
                return 'Kaon PID'
            case Cuts.pid_pi:
                return 'Pion PID'
            case Cuts.rich:
                return 'Rich'
            case Cuts.acceptance:
                return 'Acceptance'
            case Cuts.cascade:
                return 'Cascade veto'
            case Cuts.jpsi_misid:
                return r'$J/\psi$ veto'
            case Cuts.leakage:
                return r'Charmonium veto'
            case Cuts.brem:
                return r'Bremsstrahlung requirement'
            case Cuts.clones:
                return r'Clones veto'
            case Cuts.kinem_lep:
                return r'Lepton kinematics'
            case Cuts.kinem_had:
                return r'Hadron kinematics'
            case Cuts.hop:
                return r'HOP mass'
            case Cuts.extra:
                return r'Extra cut'
            case Cuts.convert:
                return r'Photon convertion veto'
            case Cuts.bpkk:
                return r'$KK$ control region'
            case Cuts.bppipi:
                return r'$\pi\pi$ control region'
    # ----------------------------------
    @property
    def var(self) -> str:
        '''
        Variable name on which cut is applied
        If not defined/found, will raise ValueError
        '''
        match self:
            case Cuts.cmb:
                return 'mva_cmb'
            case Cuts.prc:
                return 'mva_prc'
            case _:
                raise ValueError(f'Cannot find variable for: {self}')
# ------------------------------------------
# NOTE: https://github.com/yaml/pyyaml/issues/722
yaml.SafeDumper.add_representer(
      Cuts,
      yaml.representer.SafeRepresenter.represent_str,
)
# --------------------------------
class Cut(BaseModel, frozen = True):
    '''
    Class meant to represent a cut
    '''
    cut : Cuts
    var : str
    val : float
    # ----------------
    def clone(self, value : float) -> 'Cut':
        '''
        Parameters
        -----------------
        value: Value of cut

        Returns
        -----------------
        Copy of current object with cut valur overriden
        '''
        return self.model_copy(update = {'val' : value})
    # ----------------
    def __str__(self):
        return f'{self.cut:<20}{self.val}'
# --------------------------------
