
from pydantic  import BaseModel
from functools import cached_property
from dmu.stats import FitConf

# ----------------------
class CmbValidatorConf(BaseModel):
    '''
    Configuration needed to validate
    combinatorial model
    '''
    sel : str
    cut : str
    fit : str
    # ----------------------
    @cached_property
    def selection(self) -> dict[str,str]:
        '''
        Dictionary with selection needed to get dataset
        '''
        return dict()
    # ----------------------
    @cached_property
    def cutflow(self) -> dict[str,str]:
        '''
        Dictionary with cutflow to study
        '''
        return dict()
    # ----------------------
    @cached_property
    def fit_cfg(self) -> FitConf:
        '''
        Dictionary with cutflow to study
        '''
        return FitConf.default()
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
