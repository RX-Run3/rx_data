'''
Module holding Mode Enum
'''

from pathlib import Path
from enum    import StrEnum, auto

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
