
import yaml

from dmu.generic import UnpackerModel
from pydantic    import BaseModel
from rx_common   import Mass
from typing      import Self
from dmu.stats   import zfit
from rx_common   import Trigger

type zobs = zfit.Space
# ------------------------------
class ObservableConf(BaseModel, frozen = True):
    '''
    Class representing configuration for observable
    '''
    name : Mass
    '''Mass that should match a branch in the trees where the
    data to be fitted will be picked from'''

    range: tuple[int,int]
    '''range: Range where PDF is normalized to 1'''
    # ------------------------
    def __str__(self):
        lower, upper = self.range

        val = '\n------------------------\n'
        val+= f'Observable: {self.name}\n'
        val+= f'Range     : [{lower}, {upper}]\n'
        val+= '------------------------'

        return val
    # ------------------------
    @classmethod
    def default(cls) -> Self:
        '''
        Returns
        -------------
        Default instance of observable config
        needed for tests
        '''
        return cls(name = Mass.bp_bcor, range = (4500, 7000))
    # ------------------------
    @property
    def obs(self) -> zobs:
        '''
        Fit observable needed by zfit
        '''
        return zfit.Space(
            obs    = 'Mass',
            label  = self.name,
            limits = self.range)
# ------------------------------
class ComponentConf(UnpackerModel, frozen = True):
    '''
    Class meant to configure the fit for different components
    '''
    cfg_obs      : ObservableConf | None = None
    '''
    Controls observable building
    '''

    from_sim_fit : bool
    '''
    If true this component will be obtained from fitting MC
    through the SimFitter class
    '''
    # ----------------------------------
    @property
    def component_trigger(self) -> Trigger | None:
        '''
        Trigger for current component, if valid, or None
        if it does not exist
        '''
        return getattr(self, 'trigger', None)
    # ---------------------------
    def __str__(self):
        data   = self.model_dump()
        string = yaml.dump(data, indent = 2)

        return string
    # ---------------------------
    @property
    def obs(self) -> zobs:
        '''
        Returns
        ----------------
        Normalization observable
        '''
        if self.cfg_obs is None:
            raise ValueError('Normalization range was not initialized')

        return self.cfg_obs.obs
# ------------------------------
