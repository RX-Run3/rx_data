'''
Module with Project enum
'''

from enum       import StrEnum, auto
from .component import Component

# ---------------
class AlternativeProject(StrEnum):
    '''
    Enum meant to describe alternative versions
    of different projects
    '''
    no_pid   = auto()
    no_refit = auto()
    sim10d   = auto()
    sim10f   = auto()
    bad_ecal = auto()
# ---------------
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
    rk_bad_ecal   = auto()
    # ---------------
    rkst          = auto() 
    rkst_no_pid   = auto() 
    rkst_no_refit = auto() 
    rkst_sim10d   = auto() 
    rkst_bad_ecal = auto()
    # --------------------------------------------
    @property
    def main(self) -> 'Project':
        '''
        Main project associated to current project
        '''
        match self:
            case Project.rk | Project.rk_no_pid | Project.rk_no_refit | Project.rk_sim10d | Project.rk_bad_ecal:
                return Project.rk
            case Project.rkst | Project.rkst_no_pid | Project.rkst_no_refit | Project.rkst_sim10d | Project.rkst_bad_ecal:
                return Project.rkst
            case Project.test:
                return self
    # --------------------------------------------
    @property
    def color(self) -> str:
        '''
        Color associated to project, for plots
        '''
        match self:
            case Project.rk:
                return r'blue'
            case Project.rkst:
                return r'red'
            case _:
                raise ValueError(f'Color not implemented for {self}')
    # --------------------------------------------
    @property
    def latex(self) -> str:
        '''
        Latex representation of project, for plots
        '''
        match self:
            case Project.rk:
                return r'$R_K$'
            case Project.rkst:
                return r'$R_{K^*}$'
            case _:
                raise ValueError(f'Latex not implemented for {self}')
    # --------------------------------------------
    @property
    def semileptonic(self) -> list[Component]:
        '''
        List of semileptonic components associated
        '''
        if self == Project.rk:
            return [Component.bpdnukpiee, Component.bpdpiknuee, Component.bpdnuknuee]

        if self == Project.rkst:
            return [Component.bdkpipienu, Component.bdkpienuenu]

        raise ValueError(f'No semileptonic components defined for project: {self}')
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
    # ----------------------
    def alternative(self, key : AlternativeProject | None) -> 'Project | None':
        '''
        Parameters
        ------------------
        key: Denotes alternative version of this project, e.g. bad_ecal
        '''
        if key is None:
            return None 

        if key == AlternativeProject.no_pid   and self == Project.rk:
            return Project.rk_no_pid

        if key == AlternativeProject.no_pid   and self == Project.rkst:
            return Project.rkst_no_pid

        if key == AlternativeProject.bad_ecal and self == Project.rk:
            return Project.rk_bad_ecal

        if key == AlternativeProject.bad_ecal and self == Project.rkst:
            return Project.rkst_bad_ecal

        raise ValueError(f'Invalid/Not implemented key: {key}')
# ----------------------
