
from pydantic    import BaseModel
from dmu         import LogStore
from dmu.stats   import ModelFactoryConf
from dmu.stats   import Model, Retries
from dmu.generic import utilities as gut
from rx_common   import Mass
from rx_common   import Cuts, Qsq, Component, Trigger

log=LogStore.add_logger('fitter:cmb_validator')
# --------------------------------
class FitConf(BaseModel):
    '''
    Fitting configuration
    '''
    strategy : Retries
    model    : ModelFactoryConf
# --------------------------------
class CmbInputConfig(BaseModel):
    '''
    Class meant to configure input for validation
    of configuration
    '''
    q2bin  : Qsq 
    mass   : Mass 
    model  : Model 
    trigger: Trigger 
    sample : Component 
    cutflow: str 
# --------------------------------
class CmbValidationConfig(BaseModel):
    '''
    Class meant to configure selection and fits
    '''
    selection : dict[Cuts,str]
    cutflows  : dict[str,dict[str,str]]
    fits      : FitConf
    # ---------------------------
    @classmethod
    def from_file(cls, fname : str) -> 'CmbValidationConfig':
        '''
        Parameters
        ---------------
        fname: Yaml file name where configuration is specified 

        Returns
        ---------------
        Config object
        '''
        data = gut.load_data(
            package = 'fitter_data',
            fpath   = fname)

        return cls(**data)
# --------------------------------
class CmbValidatorConf(BaseModel):
    '''
    Class meant to configure validation
    '''
    input      : CmbInputConfig
    validation : CmbValidationConfig
# ----------------------
class CmbValidator:
    '''
    Class meant to validate combinatorial model
    '''
    # ---------------------------
    def __init__(self, cfg : CmbValidatorConf):
        '''
        Parameters
        ----------------
        cfg: Configuration needed for fits, etc
        '''
        self._cfg = cfg
    # ---------------------------
    def run(self) -> None:
        '''
        Runs validation
        '''
# ---------------------------
