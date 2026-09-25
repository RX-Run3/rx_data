'''
Module holding Enums
'''
from enum    import StrEnum, auto

# ----------------------------------------------------
class PRecRatio(StrEnum):
    '''
    Type representing the ratio of part reco over full reco
    '''
    psi2 = auto()
    '''
    Ratio of part reco and fully reco decays involving psi(2S) -> ee
    '''
    jpsi = auto()
    '''
    Ratio of part reco and fully reco decays involving jpsi -> ee
    '''
    # ----------------------------
    @property
    def variable(self) -> str:
        '''
        Name of this quantity as variable in fits
        '''
        match self:
            case PRecRatio.psi2:
                return 'rat_psi2'
            case PRecRatio.jpsi:
                return 'rat_jpsi'
    # ----------------------------
    @property
    def latex(self) -> str:
        '''
        Latex representation
        '''
        match self:
            case PRecRatio.psi2:
                return r'$r^{part-reco}_{\psi(2S)}$'
            case PRecRatio.jpsi:
                return r'$r^{part-reco}_{J/\psi}$'
# ----------------------------------------------------
