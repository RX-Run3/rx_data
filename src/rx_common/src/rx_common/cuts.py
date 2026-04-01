'''
Module with Cuts enum
'''
from enum import StrEnum, auto

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
    rich      = auto()
    acceptance= auto()
    jpsi_misid= auto()
    cascade   = auto()
    hop       = auto()
    cmb       = auto()
    prc       = auto()
    mass      = auto()
    brem      = auto()
    extra     = auto()
