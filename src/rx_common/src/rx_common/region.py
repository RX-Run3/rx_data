'''
Module with Region enum
'''

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
