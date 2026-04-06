'''
Module with Region enum
'''

from enum       import StrEnum, auto
from dmu.stats  import zfit

from .cuts      import Cuts
from .mass      import Mass
from .component import Component

# ------------------------
class Region(StrEnum):
    '''
    Enum meant to symbolize control and signal regions, 
    e.g. hadronic misID control region
    '''
    # ---------------------
    # Signal regions
    # ---------------------
    bpee   = auto()
    bdee   = auto()
    # ---------------------
    # MisID regions
    # ---------------------
    bpkk   = auto()
    bppipi = auto()
    # ---------------------
    # Brem regions
    # ---------------------
    brem_xx0 = auto()
    brem_xx1 = auto()
    brem_xx2 = auto()
    brem_x12 = auto()
    # ---------------------
    @property
    def selection(self) -> dict[Cuts,str]:
        '''
        Selection associated to this signal/control region
        '''
        match self:
            case Region.brem_xx0:
                return {Cuts.brem : 'nbrem == 0'}
            case Region.brem_xx1:
                return {Cuts.brem : 'nbrem == 1'}
            case Region.brem_xx2:
                return {Cuts.brem : 'nbrem == 2'}
            case Region.brem_x12:
                return {Cuts.brem : '(nbrem == 1) || (nbrem == 2)'}
            case _:
                raise ValueError(f'No cut defined for region: {self}')
    # ---------------------
    @property
    def signal(self) -> Component:
        '''
        Signal component for this region
        '''
        match self:
            case Region.bpkk:
                return Component.bpkkk
            case Region.bppipi:
                return Component.bpkpipi
            case Region.bdee:
                return Component.bdkstkpiee
            case Region.bpee:
                return Component.bpkpee
            case _:
                raise ValueError(f'No component associated to region: {self}')
    # ---------------------
    @property
    def obs(self) -> zfit.Space:
        '''
        Observable for corresponding region
        '''
        obs = zfit.Space(
            obs    = self.mass, 
            limits = self.mass.limits)

        return obs
    # ---------------------
    @property
    def mass(self) -> Mass:
        '''
        Mass that should be fitted in region
        '''
        match self:
            case Region.bpkk:
                return Mass.bp_kk
            case Region.bppipi:
                return Mass.bp_pipi
            case Region.bpee:
                return Mass.bp_bcor
            case Region.bdee:
                return Mass.bd_bcor
            case _:
                raise ValueError(f'No mass associated to region: {self}')
    # ---------------------
    @staticmethod
    def hadronic_misid() -> list['Region']:
        '''
        Returns list of hadronic misid regions
        '''
        return [Region.bpkk, Region.bppipi]
# ------------------------
