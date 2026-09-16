'''
Module holding Enums
'''
from enum    import StrEnum, auto
from pathlib import Path

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
class Mode(StrEnum):
    '''
    Type describing how an action should be ran
    '''
    read  = auto()
    '''
    Output expected to exist, raise if not found
    '''
    write = auto()
    '''
    Output not expected to exist, raise if found
    '''
    update= auto()
    '''
    Make object, even if already exists
    '''
    reuse = auto()
    '''
    If object found, use it, if not make it
    '''
    # ----------------
    @property
    def skip_reading(self) -> bool:
        '''
        If true, won't read any data but process all over again 
        '''
        return self in {Mode.write, Mode.update}
    # ----------------
    def validate(self, path : Path) -> None:
        '''
        Will raise an exception if path is not consistent with current mode

        Parameters
        -------------
        path: Path to a file
        '''
        if self == Mode.read and not path.exists():
            raise ValueError(f'Model not found: {path}')

        if self == Mode.write and    path.exists():
            raise ValueError(f'Model already found: {path}')
# ----------------------------------------------------
