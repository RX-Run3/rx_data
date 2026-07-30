'''
Module with Cuts enum
'''
import yaml
from enum     import StrEnum, auto
from pydantic import BaseModel, ConfigDict

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
class Cut(BaseModel):
    '''
    Class meant to represent a cut 
    '''
    model_config = ConfigDict(frozen=True)
    # ----------------
    cut : Cuts
    var : str
    val : float
