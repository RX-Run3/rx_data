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
    rk            = auto() 
    rk_no_pid     = auto() 
    rk_no_refit   = auto() 
    rk_sim10d     = auto() 
    # ---------------
    rkst          = auto() 
    rkst_no_pid   = auto() 
    rkst_no_refit = auto() 
    rkst_sim10d   = auto() 
    # ----------------------
    @classmethod
    def rk_projects(cls) -> set['Project']:
         return {
            cls.rk,
            cls.rk_no_pid,
            cls.rk_no_refit,
            cls.rk_sim10d}
    # ----------------------
    @classmethod
    def rkst_projects(cls) -> set['Project']:
         return {
            cls.rkst,
            cls.rkst_no_pid,
            cls.rkst_no_refit,
            cls.rkst_sim10d}
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
                return f'yld_{Component.bpkpee}_brem_x12'
            case Project.rk_no_pid:
                return f'yld_{Component.bpkpee}_brem_x12'
            case Project.rkst:
                return f'yld_{Component.bdkstkpiee}_brem_x12'
            case Project.rkst_no_pid:
                return f'yld_{Component.bdkstkpiee}_brem_x12'
            case _:
                raise ValueError(f'Invalid project: {self}')
