'''
Module with Region enum
'''

from typing      import Any
from dmu.generic import Serializable
from dmu.stats   import zfit
from pydantic    import model_serializer
from pydantic    import model_validator
from rx_common   import Component
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
    brem    : Brem
    trigger : Trigger
    lepton  : Particle | None = None
    # ---------------------
    @property
    def signal(self) -> Component:
        '''
        Signal component that this region targets
        '''
        if not self.trigger:
            raise ValueError(f'Need triger to find signal in: {self.name}')

        if self.trigger.has_pid:
            raise NotImplementedError(f'No signal implemented for: {self.name}')

        if self.hadron == Particle.kaon and self.trigger.project == Project.rk:
            return Component.bpkkk
            
        if self.hadron == Particle.pion and self.trigger.project == Project.rk:
            return Component.bpkpipi

        if self.hadron == Particle.kaon and self.trigger.project == Project.rkst:
            return Component.bdkstkk
            
        if self.hadron == Particle.pion and self.trigger.project == Project.rkst:
            return Component.bdkstpipi

        raise NotImplementedError(f'No signal implemented for: {self.name}')
    # ---------------------
    @property
    def hadron(self) -> Particle:
        '''
        Hadron name that is used in this hadron MisID region
        If this is not a misID region, will raise ValueError
        '''
        if not self.lepton:
            raise ValueError(f'No lepton name defined for region {self.name}')

        if not self.lepton.is_hadron:
            raise ValueError(f'Particle is not a hadron, but: {self.lepton}')

        return self.lepton
    # ---------------------
    @property
    def mass(self) -> Mass:
        '''
        Mass used to describe signal/control region
        '''
        if self.trigger is None:
            raise ValueError('Cannot provide observable without trigger')

        # Muon
        if self.trigger.is_muon and self.trigger.project == Project.rkst:
            return Mass.bd

        if self.trigger.is_muon and self.trigger.project == Project.rk:
            return Mass.bp

        # PID
        if self.trigger.has_pid and self.trigger.project == Project.rkst:
            return Mass.bd_bcor

        if self.trigger.has_pid and self.trigger.project == Project.rk:
            return Mass.bp_bcor

        # No PID
        if self.lepton == Particle.kaon and self.trigger.project == Project.rkst_no_pid:
            return Mass.bd_kk

        if self.lepton == Particle.pion and self.trigger.project == Project.rkst_no_pid:
            return Mass.bd_pipi

        if self.lepton == Particle.kaon and self.trigger.project == Project.rk_no_pid:
            return Mass.bp_kk

        if self.lepton == Particle.pion and self.trigger.project == Project.rk_no_pid:
            return Mass.bp_pipi

        raise ValueError(f'Cannot find observable for region: {self.name}')
    # ---------------------
    @property
    def obs(self) -> zfit.Space:
        '''
        Zfit observable associated to region
        '''
        return self.mass.obs
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

        try:
            brem = Brem(parts[0]) 
            trig = Trigger(parts[1])
            lept = Particle(parts[2]) if len(parts) > 2 else None # noqa: PLR2004
        except Exception as exc:
            raise ValueError(f'Cannot build region from: {name}') from exc

        return {
            'brem'   : brem,
            'trigger': trig,
            'lepton' : lept} 
    # ---------------------
    @model_validator(mode = 'after')
    def _validate_after(self):
        nobr = self.brem    is None
        notr = self.trigger is None

        if nobr or notr:
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
            brem    = Brem.br012,
            trigger = Trigger.rk_ee_nopid,
            lepton  = Particle.kaon)

        mid_rk_p    = cls(
            brem    = Brem.br012,
            trigger = Trigger.rk_ee_nopid,
            lepton  = Particle.pion)

        mid_rkst_k  = cls(
            brem    = Brem.br012,
            trigger = Trigger.rkst_ee_nopid,
            lepton  = Particle.kaon)

        mid_rkst_p  = cls(
            brem    = Brem.br012,
            trigger = Trigger.rkst_ee_nopid,
            lepton  = Particle.pion)

        return [mid_rk_k, mid_rk_p, mid_rkst_k, mid_rkst_p]
# ------------------------
