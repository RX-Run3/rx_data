'''
Module storing enums
'''

from enum   import StrEnum, auto

class Production(StrEnum):
    '''
    Class meant to represent projects in Analysis Productions

    Attributes
    ----------------
    rx_filter            : Filtered ntuples
    rx_2024              : Taken from DaVinci
    btoxll_mva_2024_nopid: Taken from DaVinci and with special HLT config to remove PID
    '''
    rx_filter             = auto()
    rx_2024               = auto()
    btoxll_mva_2024_nopid = auto()
