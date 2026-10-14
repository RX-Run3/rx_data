'''
Module holding channel enum
'''
from enum import auto
from enum import StrEnum

class Channel(StrEnum):
    '''
    This class repsesents the electron, muon or emu channel types
    '''
    ee = auto()
    mm = auto()
    me = auto()

    def __str__(self):
        return self.value

