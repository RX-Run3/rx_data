'''
Module with Region enum
'''

from typing      import Any
from dmu.generic import Serializable
from dmu.stats   import zfit
from pydantic    import model_serializer
from pydantic    import model_validator
from rx_common   import Particle
from rx_common   import Trigger
from rx_common   import Brem
from rx_common   import Project
from rx_common   import Mass
from pydantic    import BaseModel
from dmu         import LogStore

log=LogStore.add_logger('rx_common:region')
# ------------------------
class Region(BaseModel, Serializable, frozen = True):
    '''
    Enum meant to symbolize control and signal regions, 
    e.g. hadronic misID control region
    '''
    brem    : Brem     | None = None
    trigger : Trigger  | None = None
    lepton  : Particle | None = None
    # ---------------------
    @property
    def obs(self) -> zfit.Space:
        '''
        Observable needed in given signal/control region
        '''
        if self.trigger is None:
            raise ValueError('Cannot provide observable without trigger')

        # Muon
        if self.trigger.is_muon and self.trigger.project == Project.rkst:
            return Mass.bd.obs

        if self.trigger.is_muon and self.trigger.project == Project.rk:
            return Mass.bp.obs

        # PID
        if self.trigger.has_pid and self.trigger.project == Project.rkst:
            return Mass.bd_bcor.obs

        if self.trigger.has_pid and self.trigger.project == Project.rk:
            return Mass.bp_bcor.obs

        # No PID
        if self.lepton == Particle.kaon and self.trigger.project == Project.rkst_no_pid:
            return Mass.bd_kk.obs

        if self.lepton == Particle.pion and self.trigger.project == Project.rkst_no_pid:
            return Mass.bd_pipi.obs

        if self.lepton == Particle.kaon and self.trigger.project == Project.rk_no_pid:
            return Mass.bp_kk.obs

        if self.lepton == Particle.pion and self.trigger.project == Project.rk_no_pid:
            return Mass.bp_pipi.obs

        raise ValueError(f'Cannot find observable for region: {self.name}')
    # ---------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate_before(cls, data : Any) -> Any:
        '''
        Allows to deserialize from name
        '''
        if isinstance(data, str):
            return cls.from_string(name = data)

        return data
    # ---------------------
    @classmethod
    def from_string(cls, name : str) -> dict[str,Any]:
        '''
        Parameters
        -----------------
        name: String representing region, e.g. brem_xx1-rk_ee_os

        Returns
        -----------------
        Dictionary representing data for current Region
        '''
        parts= name.split('-')

        brem = Brem(parts[0]) 
        trig = Trigger(parts[1])  if len(parts) > 1 else None
        lept = Particle(parts[2]) if len(parts) > 2 else None # noqa: PLR2004

        return {
            'brem'   : brem,
            'trigger': trig,
            'lepton' : lept} 
    # ---------------------
    @model_validator(mode = 'after')
    def _validate_after(self):
        nobr = self.brem    is None
        notr = self.trigger is None
        nolp = self.lepton  is None

        if nobr and notr and nolp:
            raise ValueError('No field specified in region')

        return self
    # ---------------------
    @model_serializer
    def _serialize(self) -> str:
        return self.name
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
            parts.append(self.trigger.name)

        if self.lepton:
            parts.append(str(self.lepton))

        return '-'.join(parts)
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
