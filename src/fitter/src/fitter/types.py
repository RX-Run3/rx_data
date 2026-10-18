'''
Module holding enums needed for fitting models
'''

from enum import StrEnum, auto

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
# ------------------------------
