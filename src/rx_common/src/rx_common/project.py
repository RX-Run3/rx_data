'''
Module with Project enum
'''

from enum       import StrEnum, auto
from .component import Component

class Project(StrEnum):
    '''
    This class represents the projects
    '''
    test          = auto() # needed for tests
    # ---------------
    rk            = 'rk'
    rk_no_pid     = 'rk_nopid'
    rk_no_refit   = 'rk_no_refit'
    rk_sim10d     = 'rk_sim10d'
    # ---------------
    rkst          = 'rkst'
    rkst_no_pid   = 'rkst_nopid'
    rkst_no_refit = 'rkst_no_refit'
    rkst_sim10d   = 'rkst_sim10d'
    # ----------------------
    @property
    def with_pid(self) -> 'Project':
        '''
        Return PID version of project
        Only makes sense for noPID projects
        '''
        match self:
            case Project.rk_no_pid:
                return Project.rk
            case Project.rkst_no_pid:
                return Project.rkst
            case _:
                return self
    # ----------------------
    def __str__(self):
        return self.value
    # ----------------------
    @property
    def signal_name(self) -> str:
        '''
        Name of signal parameter in model
        '''
        match self:
            case Project.rk:
                return f'yld_{Component.bpkpee}'
            case Project.rk_no_pid:
                return f'yld_{Component.bpkpee}'
            case Project.rkst:
                return f'yld_{Component.bdkstkpiee}'
            case Project.rkst_no_pid:
                return f'yld_{Component.bdkstkpiee}'
            case _:
                raise ValueError(f'Invalid project: {self}')
