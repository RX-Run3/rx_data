'''
Module containing Candidate class
'''

from pydantic  import BaseModel, model_validator
from rx_common import Component, Trigger
from rx_data   import CandidateRebuilder

# ------------------------------------------------
class CandidateRebuildConf(BaseModel):
    '''
    Class meant to hold configuration needed
    to plot rebuilt candidates
    '''
    trigger     : Trigger
    sample      : Component
    particles   : list[str]
    constraints : dict[int,list[str]]
    swaps       : dict[str,int]
    # ------------------------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'CandidateRebuildConf':
        if not self.particles:
            raise ValueError('Missing particles')

        if not all(swp in self.particles for swp in self.swaps):
            raise ValueError(f'At least one swap does not involve a valid particle: {self.swaps}')

        for parts in self.constraints.values():
            if not all(part in self.particles for part in parts):
                raise ValueError(f'At least one constraint contains invalid particles: {parts}')

        return self
# ------------------------------------------------
class CandidateRebuild:
    '''
    Class meant to plot quantities associated to
    rebuilt candidates
    '''
    def __init__(self, cfg : CandidateRebuildConf):
        '''
        Parameters
        -----------------
        cfg: configuration object
        '''
        self._cfg = cfg
    # --------------------------------
    def run(self) -> None:
        gtr = 

        bdr = CandidateRebuilder(
            rdf          = rdf,
            replacements = self._cfg.swaps,
            tracks       = self._cfg.tracks)

        bdr.run()
# ------------------------------------------------
