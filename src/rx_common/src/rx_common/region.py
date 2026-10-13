'''
Module with Region enum
'''

from pydantic   import model_validator
from rx_common  import Particle
from rx_common  import Trigger
from rx_common  import Brem
from pydantic   import BaseModel
from dmu        import LogStore

log=LogStore.add_logger('rx_common:region')
# ------------------------
class Region(BaseModel, frozen = True):
    '''
    Enum meant to symbolize control and signal regions, 
    e.g. hadronic misID control region
    '''
    brem    : Brem     | None = None
    trigger : Trigger  | None = None
    lepton  : Particle | None = None
    # ---------------------
    @model_validator(mode = 'after')
    def _validate(self):
        nobr = self.brem    is None
        notr = self.trigger is None
        nolp = self.lepton  is None

        if nobr and notr and nolp:
            raise ValueError('No field specified in region')

        return self
    # ---------------------
    @property
    def name(self) -> str:
        '''
        Name associated to current region
        '''
        parts : list[str] = []
        if self.brem:
            parts.append(str(self.brem))

        if self.trigger:
            parts.append(str(self.trigger))

        if self.lepton:
            parts.append(str(self.lepton))

        return '_'.join(parts)
    # ---------------------
    @classmethod
    def merge(cls, regions : list['Region']) -> 'Region':
        raise NotImplementedError
    # ---------------------
    @classmethod
    def hadronic_misid(cls) -> list['Region']:
        '''
        Returns list of hadronic misid regions
        '''
        mid_rk_k    = cls(
            trigger = Trigger.rk_ee_nopid,
            lepton  = Particle.kaon)

        mid_rk_p    = cls(
            trigger = Trigger.rk_ee_nopid,
            lepton  = Particle.pion)

        mid_rkst_k  = cls(
            trigger = Trigger.rkst_ee_nopid,
            lepton  = Particle.kaon)

        mid_rkst_p  = cls(
            trigger = Trigger.rkst_ee_nopid,
            lepton  = Particle.pion)

        return [mid_rk_k, mid_rk_p, mid_rkst_k, mid_rkst_p]
# ------------------------
